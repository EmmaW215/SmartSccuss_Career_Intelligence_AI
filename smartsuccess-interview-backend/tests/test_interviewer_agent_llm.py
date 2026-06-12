"""
Phase 2 real-LLM acceptance tests (PRD 02 §9, @pytest.mark.llm).

These tests call the real OpenAI API (~$0.05/run) and are excluded from the
default test run by pytest.ini. Run manually with:

    pytest -m llm tests/test_interviewer_agent_llm.py -v

Covers:
- Scripted real interviewer round through the ReAct agent (no fallback).
- tool_call_log quality: >=1 score_answer per answered turn + decision chain.
"""

import pytest

from app.api.routes import customize as customize_route
from app.config import settings
from app.graph.checkpoint_state_accessor import GraphCheckpointStateAccessor
from app.graph.customize_graph import reset_customize_graph_runtime_cache
from app.services.session_store import SessionStore

_REAL_KEY = bool(
    (settings.openai_api_key or "").startswith("sk-")
)

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(not _REAL_KEY, reason="requires a real OPENAI_API_KEY"),
]

REQUIRED_LOG_KEYS = {"tool", "args", "result_digest", "ts"}


class _FakeGpuClient:
    """RAG backend offline -> fetch_resume_context degrades to []; agent must cope."""

    async def check_health(self, force: bool = False):
        return {"available": False, "services": {}, "latency_ms": 0}


def _setup_agent_session(client, monkeypatch, user_id: str) -> str:
    monkeypatch.setattr(settings, "use_langgraph_customize", True)
    monkeypatch.setattr(settings, "use_agent_tools", True)
    monkeypatch.setattr(settings, "use_mcp_tools", False)
    monkeypatch.setattr(settings, "max_agent_iterations", 4)
    reset_customize_graph_runtime_cache()

    client.app.state.session_store = SessionStore()
    monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _FakeGpuClient())

    start_resp = client.post(
        "/api/interview/customize/start",
        json={"user_id": user_id, "user_name": "Emma", "voice_enabled": False},
    )
    assert start_resp.status_code == 200
    return start_resp.json()["session_id"]


GOOD_ANSWER = (
    "I led the migration of our interview platform to LangGraph. I designed the "
    "state schema, added a Postgres checkpointer for session recovery, and rolled "
    "it out behind a feature flag. P95 latency stayed under 2 seconds and we had "
    "zero regressions across 37 contract tests."
)

SECOND_ANSWER = (
    "For observability I added structured tool-call logging: every agent decision "
    "is appended to a tool_call_log with a result digest and timestamp, so we can "
    "audit exactly why the agent chose to probe deeper or move on."
)


@pytest.mark.asyncio
async def test_llm_scripted_real_interviewer_round(client, monkeypatch):
    """One scripted round against the real ReAct interviewer (gpt-4o-mini).

    Retries once with a fresh session: OpenAI occasionally returns transient
    edge errors (e.g. 431 request_headers_too_large) that the self-healing
    fallback absorbs in production but that would mask what this test proves.
    """
    attempt_errors = []
    for attempt in range(2):
        session_id = _setup_agent_session(client, monkeypatch, f"llm_user_001_{attempt}")

        respond_resp = client.post(
            "/api/interview/customize/respond",
            json={"session_id": session_id, "user_response": GOOD_ANSWER},
        )
        assert respond_resp.status_code == 200
        data = respond_resp.json()
        ai_text = (data.get("ai_response") or data.get("question") or "").strip()
        assert len(ai_text) > 10, "real agent must produce a substantive question/response"

        state = await GraphCheckpointStateAccessor.read_customize_state(session_id)
        assert state is not None
        tool_call_log = state.get("tool_call_log", [])
        assert tool_call_log, "real agent run must produce tool_call_log entries"

        # Self-healing fallback firing means the real ReAct path did not complete;
        # retry once in case the provider returned a transient error.
        fallback_errors = [
            entry.get("error") for entry in tool_call_log if entry.get("tool") == "react_fallback"
        ]
        if fallback_errors:
            attempt_errors.append(fallback_errors)
            continue

        tools_used = [entry.get("tool") for entry in tool_call_log]
        assert "score_answer" in tools_used, f"agent skipped evaluator: {tools_used}"
        assert state.get("next_action") in {"followup", "next_question", "closing"}
        return

    pytest.fail(f"ReAct path fell back on every attempt: {attempt_errors}")


@pytest.mark.asyncio
async def test_llm_tool_call_log_quality_and_decision_chain(client, monkeypatch):
    """Two scripted turns: >=1 score_answer per question cycle, well-formed log,
    decision chain (PRD 02 acceptance: score_answer -> probe/advance correlation).

    Note: a turn answering a follow-up belongs to the same question cycle the
    agent already scored, so the metric is per cycle, not per HTTP turn.
    """
    session_id = _setup_agent_session(client, monkeypatch, "llm_user_002")

    for answer in (GOOD_ANSWER, SECOND_ANSWER):
        resp = client.post(
            "/api/interview/customize/respond",
            json={"session_id": session_id, "user_response": answer},
        )
        assert resp.status_code == 200
        data = resp.json()
        ai_text = (data.get("ai_response") or data.get("question") or "").strip()
        assert ai_text, "every answered turn must produce an interviewer response"
        if data.get("is_complete"):
            break

    final_state = await GraphCheckpointStateAccessor.read_customize_state(session_id)
    assert final_state is not None
    final_log = final_state.get("tool_call_log", [])
    assert final_log, "session must accumulate tool_call_log entries"

    # Log quality: every entry carries the full audit schema.
    for entry in final_log:
        missing = REQUIRED_LOG_KEYS - set(entry.keys())
        assert not missing, f"tool_call_log entry missing {missing}: {entry}"

    # Statistical assertion: every question cycle that triggered tool usage
    # contains at least one score_answer call for that question.
    cycles = {
        entry["args"]["question"]
        for entry in final_log
        if isinstance(entry.get("args"), dict) and entry["args"].get("question")
    }
    assert cycles, "tool calls must be attributable to question cycles via args.question"
    scored_cycles = {
        entry["args"]["question"]
        for entry in final_log
        if entry.get("tool") == "score_answer"
        and isinstance(entry.get("args"), dict)
        and entry["args"].get("question")
    }
    unscored = cycles - scored_cycles
    assert not unscored, f"question cycles without score_answer: {unscored}"

    # Decision chain: verdict persisted and a routing decision derived from it.
    evaluations = final_state.get("evaluations", [])
    assert evaluations, "evaluator verdicts must be persisted to state.evaluations"
    assert final_state.get("evaluator_verdict"), "latest verdict must be in state"
    assert final_state.get("next_action") in {"followup", "next_question", "closing"}
    assert "react_fallback" not in [e.get("tool") for e in final_log]
