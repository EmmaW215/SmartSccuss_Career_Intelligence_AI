"""
Regression tests for the production 500:
    POST /api/interview/technical/message
    -> "'dict' object has no attribute 'user_id'"

Root cause: PersistentSessionStore._load_existing() put raw JSON dicts into
the cache after a server restart, while process_message() and the session
endpoints expect InterviewSession objects.
"""

from datetime import datetime

import pytest

from app.models import InterviewPhase, InterviewSession, InterviewType
from app.services.session_persistence import PersistentSessionStore


def _make_session(session_id: str = "technical_user_x_abc12345") -> InterviewSession:
    return InterviewSession(
        session_id=session_id,
        user_id="user_x",
        interview_type=InterviewType.TECHNICAL,
        phase=InterviewPhase.IN_PROGRESS,
        questions_asked=["Tell me about a system you built."],
        messages=[{"role": "assistant", "content": "Hi", "timestamp": "2026-06-12T00:00:00"}],
        started_at=datetime.utcnow(),
    )


class TestSessionRehydrationAfterRestart:
    def test_session_survives_restart_as_object(self, tmp_path):
        """Simulated restart: a new store over the same dir must return objects."""
        store = PersistentSessionStore(session_dir=tmp_path, model=InterviewSession)
        session = _make_session()
        store.save(session.session_id, session)

        # "Restart": fresh store instance loads the JSON files from disk.
        restarted = PersistentSessionStore(session_dir=tmp_path, model=InterviewSession)
        loaded = restarted.get(session.session_id)

        assert isinstance(loaded, InterviewSession)
        # The exact attribute chain that crashed in production:
        assert loaded.user_id == "user_x"
        assert loaded.phase == InterviewPhase.IN_PROGRESS.value or loaded.phase == InterviewPhase.IN_PROGRESS
        assert loaded.questions_asked == ["Tell me about a system you built."]

    def test_get_never_serves_raw_dict_when_model_set(self, tmp_path):
        """Even a dict injected into the cache must be rehydrated or dropped."""
        store = PersistentSessionStore(session_dir=tmp_path, model=InterviewSession)
        session = _make_session("technical_user_x_def67890")
        store._cache[session.session_id] = session.model_dump(mode="json")

        loaded = store.get(session.session_id)
        assert isinstance(loaded, InterviewSession)
        assert loaded.user_id == "user_x"

    def test_unparseable_session_dropped_not_served(self, tmp_path):
        """Incompatible payloads become a recoverable 404, never a dict -> 500."""
        (tmp_path / "broken_session.json").write_text('{"session_id": "broken_session"}')

        restarted = PersistentSessionStore(session_dir=tmp_path, model=InterviewSession)
        assert restarted.get("broken_session") is None

    def test_no_model_keeps_legacy_dict_behavior(self, tmp_path):
        """SessionStore's phase2 disk store (no model) must keep raw dicts."""
        store = PersistentSessionStore(session_dir=tmp_path)
        store.save("phase2_session", {"session_id": "phase2_session", "foo": "bar"})

        restarted = PersistentSessionStore(session_dir=tmp_path)
        loaded = restarted.get("phase2_session")
        assert isinstance(loaded, dict)
        assert loaded["foo"] == "bar"


class TestInterviewServiceRestartEndToEnd:
    @pytest.mark.asyncio
    async def test_process_message_after_restart(self, tmp_path, monkeypatch):
        """Full repro of the production flow: start -> restart -> message."""
        from app.interview.technical_interview import TechnicalInterviewService

        service = TechnicalInterviewService()
        service.sessions = PersistentSessionStore(session_dir=tmp_path, model=InterviewSession)

        session = await service.create_session(user_id="user_google_789")
        session.phase = InterviewPhase.IN_PROGRESS
        session.started_at = datetime.utcnow()
        session.questions_asked.append("Describe your Python experience.")
        service._persist_session(session)

        # Simulated Render restart: same disk, fresh cache.
        service.sessions = PersistentSessionStore(session_dir=tmp_path, model=InterviewSession)

        reloaded = service.get_session(session.session_id)
        assert isinstance(reloaded, InterviewSession)

        async def _fake_eval(*args, **kwargs):
            return {"score": 4.0, "feedback": "ok", "follow_up_needed": False}

        async def _fake_next(*args, **kwargs):
            return "Next question: how do you test async code?"

        for name in ("_handle_interview_response", "_handle_first_response"):
            if hasattr(service, name):
                monkeypatch.setattr(
                    service,
                    name,
                    lambda s, m, _n=_fake_next: _stub_response(),
                    raising=False,
                )

        def _stub_response():
            from app.models import MessageResponse

            async def _coro():
                return MessageResponse(type="question", message="Next question?")

            return _coro()

        response = await service.process_message(
            session_id=session.session_id,
            user_message="I have eight years of Python experience.",
        )
        # Before the fix this raised AttributeError ('dict' has no 'user_id')
        # inside process_message's rate-limit check and surfaced as HTTP 500.
        assert response.type != "error"
