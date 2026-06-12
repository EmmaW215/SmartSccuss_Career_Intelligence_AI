"""
Regression tests for the production report-400 bugs (2026-06-12):

1. session_adapter status_map was keyed by InterviewPhase enums while
   `phase` is a plain string (use_enum_values=True) -> every mirror stuck
   at PENDING -> /report always 400 for standard interviews.
2. "stop" (4 chars) was rejected by the min-length input validator before
   the end-intent check ran -> ending an interview early never completed
   the session -> /report 400.
3. json_parser could not recover fenced JSON truncated by max_tokens.
"""

import pytest

from app.models import InterviewPhase, InterviewSession, InterviewType
from app.services.session_adapter import convert_base_session_to_store
from app.services.session_store import InterviewStatus, SessionStore
from app.utils.json_parser import extract_json_from_llm


# ──────────────────────────────────────────────
# Bug 1: phase-string -> status mapping
# ──────────────────────────────────────────────

class TestSessionAdapterStatusMapping:
    @pytest.mark.parametrize(
        "phase,expected",
        [
            (InterviewPhase.GREETING, InterviewStatus.PENDING),
            (InterviewPhase.IN_PROGRESS, InterviewStatus.IN_PROGRESS),
            (InterviewPhase.COMPLETED, InterviewStatus.COMPLETED),
        ],
    )
    def test_status_maps_from_string_phase(self, phase, expected):
        session = InterviewSession(
            session_id="technical_user_x_abc",
            user_id="user_x",
            interview_type=InterviewType.TECHNICAL,
            phase=phase,
        )
        # use_enum_values=True means the model stores the *string*
        assert isinstance(session.phase, str)
        store_session = convert_base_session_to_store(session)
        assert store_session.status == expected


# ──────────────────────────────────────────────
# Bug 2: "stop" ends the interview despite min-length validation
# ──────────────────────────────────────────────

class TestEndIntentBeforeValidation:
    @pytest.fixture
    def service(self, tmp_path, monkeypatch):
        from app.interview.technical_interview import TechnicalInterviewService
        from app.services.session_persistence import PersistentSessionStore

        svc = TechnicalInterviewService(session_store=SessionStore())
        svc.sessions = PersistentSessionStore(
            session_dir=tmp_path, model=InterviewSession
        )

        async def _no_summary(*args, **kwargs):
            return None

        async def _no_llm(*args, **kwargs):
            return "Thanks for the interview!"

        monkeypatch.setattr(svc, "_generate_summary", _no_summary, raising=False)
        monkeypatch.setattr(svc, "_get_completion_message", _no_llm, raising=False)
        return svc

    @pytest.mark.asyncio
    @pytest.mark.parametrize("end_message", ["stop", "Stop.", "end", "I want to stop"])
    async def test_short_stop_completes_interview(self, service, end_message):
        session = await service.create_session(user_id="user_end_intent")
        session.phase = InterviewPhase.IN_PROGRESS
        session.questions_asked.append("Tell me about your experience.")
        service._persist_session(session)

        response = await service.process_message(
            session_id=session.session_id, user_message=end_message
        )

        assert response.type != "validation_guidance", (
            f"'{end_message}' must reach the end-intent check, not be "
            "rejected by the min-length validator"
        )
        reloaded = service.get_session(session.session_id)
        assert str(reloaded.phase) in ("completed", "InterviewPhase.COMPLETED")

        # The dashboard mirror must say COMPLETED so /report returns 200
        mirror = service.session_store.get_session(session.session_id)
        assert mirror is not None
        assert mirror.status == InterviewStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_answers_containing_end_words_do_not_end_interview(self, service, monkeypatch):
        """'recommend'/'done deploying' style answers must NOT trigger end-intent."""
        session = await service.create_session(user_id="user_no_false_end")
        session.phase = InterviewPhase.IN_PROGRESS
        session.questions_asked.append("Tell me about your deployment process.")
        service._persist_session(session)

        async def _eval(*args, **kwargs):
            return {"score": 4.0, "feedback": "ok"}

        async def _next_q(*args, **kwargs):
            return "What monitoring did you add?"

        async def _no_follow_up(*args, **kwargs):
            return None

        monkeypatch.setattr(service, "_evaluate_response", _eval, raising=False)
        monkeypatch.setattr(service, "_get_next_question", _next_q, raising=False)
        monkeypatch.setattr(service, "_check_follow_up", _no_follow_up, raising=False)

        response = await service.process_message(
            session_id=session.session_id,
            user_message=(
                "I would recommend blue-green deployment; once we were done "
                "deploying we monitored error rates for an hour."
            ),
        )
        assert response.type == "question"
        reloaded = service.get_session(session.session_id)
        assert str(reloaded.phase) != "completed"


# ──────────────────────────────────────────────
# Customize graph: 'stop' -> is_complete -> report 200 (end-to-end)
# ──────────────────────────────────────────────

class TestCustomizeStopToReport:
    @pytest.mark.asyncio
    async def test_stop_completes_and_report_succeeds(self, client, monkeypatch):
        from app.api.routes import customize as customize_route
        from app.config import settings
        from app.graph.customize_graph import reset_customize_graph_runtime_cache

        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        monkeypatch.setattr(settings, "use_agent_tools", True)
        reset_customize_graph_runtime_cache()

        class _FakeGpu:
            async def check_health(self, force: bool = False):
                return {"available": False, "services": {}, "latency_ms": 0}

        store = SessionStore()
        client.app.state.session_store = store
        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _FakeGpu())

        start = client.post(
            "/api/interview/customize/start",
            json={"user_id": "stop_flow_user", "user_name": "Emma", "voice_enabled": False},
        )
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        respond = client.post(
            "/api/interview/customize/respond",
            json={"session_id": session_id, "user_response": "stop"},
        )
        assert respond.status_code == 200
        assert respond.json()["is_complete"] is True

        report = client.get(f"/api/dashboard/session/{session_id}/report")
        assert report.status_code == 200, report.text
        assert report.json()["session_id"] == session_id


# ──────────────────────────────────────────────
# json_parser: fenced + truncated recovery
# ──────────────────────────────────────────────

class TestJsonParserTruncated:
    def test_fenced_json_still_parses(self):
        text = '```json\n{"score": 4, "feedback": "good"}\n```'
        assert extract_json_from_llm(text) == {"score": 4, "feedback": "good"}

    def test_truncated_fenced_json_recovers_complete_fields(self):
        # Simulates a max_tokens cutoff mid-value (the production case).
        text = (
            '```json\n{\n  "communication_clarity": 4,\n'
            '  "relevance": 5,\n  "feedback": "Great answer but the resp'
        )
        parsed = extract_json_from_llm(text)
        assert parsed is not None
        assert parsed["communication_clarity"] == 4
        assert parsed["relevance"] == 5

    def test_silent_flag_suppresses_warning(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            assert extract_json_from_llm("just a plain sentence", silent=True) is None
        assert "JSON extraction failed" not in caplog.text

    def test_plain_text_still_returns_none_loudly(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            assert extract_json_from_llm("no json here at all") is None
        assert "JSON extraction failed" in caplog.text
