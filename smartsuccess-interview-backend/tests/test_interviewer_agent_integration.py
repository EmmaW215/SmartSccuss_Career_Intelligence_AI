"""
Phase 2 interviewer-agent integration tests.
"""

import asyncio

import pytest

from app.agents import interviewer_agent as interviewer_module
from app.api.routes import customize as customize_route
from app.config import settings
from app.graph.checkpoint_state_accessor import GraphCheckpointStateAccessor
from app.graph.customize_graph import reset_customize_graph_runtime_cache
from app.services.session_store import SessionStore


class _FakeGpuClient:
    async def check_health(self, force: bool = False):
        return {
            "available": True,
            "services": {"whisper": True, "tts": True, "rag": True},
            "latency_ms": 5,
        }


class _ToolStub:
    def __init__(self, handler):
        self._handler = handler

    async def ainvoke(self, payload):
        result = self._handler(payload)
        if asyncio.iscoroutine(result):
            return await result
        return result


class TestInterviewerAgentIntegration:
    @pytest.mark.asyncio
    async def test_agent_tools_path_persists_tool_call_log_in_checkpoint(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        monkeypatch.setattr(settings, "use_agent_tools", True)
        monkeypatch.setattr(settings, "max_agent_iterations", 4)
        reset_customize_graph_runtime_cache()

        client.app.state.session_store = SessionStore()
        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _FakeGpuClient())
        async def _force_manual_fallback(**kwargs):
            raise RuntimeError("force manual fallback for deterministic test")
        monkeypatch.setattr(interviewer_module, "_run_react_agent_once", _force_manual_fallback)

        monkeypatch.setattr(
            interviewer_module,
            "score_answer",
            _ToolStub(
                lambda payload: {
                    "score": 7.4,
                    "dimension_scores": {
                        "clarity": 7.5,
                        "depth": 7.0,
                        "relevance": 7.8,
                        "structure": 7.2,
                    },
                    "strengths": ["Relevant answer"],
                    "improvements": ["Add one metric"],
                    "followup_needed": False,
                    "suggested_followup_angle": None,
                    "reasoning": "Good but can be more concrete.",
                }
            ),
        )
        monkeypatch.setattr(
            interviewer_module,
            "search_question_bank",
            _ToolStub(lambda payload: []),
        )
        monkeypatch.setattr(
            interviewer_module,
            "generate_followup",
            _ToolStub(lambda payload: "Could you share one concrete example?"),
        )

        start_resp = client.post(
            "/api/interview/customize/start",
            json={"user_id": "agent_user_001", "user_name": "Emma", "voice_enabled": False},
        )
        assert start_resp.status_code == 200
        session_id = start_resp.json()["session_id"]

        respond_resp = client.post(
            "/api/interview/customize/respond",
            json={"session_id": session_id, "user_response": "I optimize reliability with SLOs and alerts."},
        )
        assert respond_resp.status_code == 200
        data = respond_resp.json()
        assert data["is_complete"] is False

        state = await GraphCheckpointStateAccessor.read_customize_state(session_id)
        assert state is not None
        tool_call_log = state.get("tool_call_log", [])
        assert isinstance(tool_call_log, list)
        assert len(tool_call_log) >= 2
        tool_names = {entry.get("tool") for entry in tool_call_log}
        assert "score_answer" in tool_names
        assert "search_question_bank" in tool_names

    @pytest.mark.asyncio
    async def test_manual_fallback_avoids_repeated_scoring_cost(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        monkeypatch.setattr(settings, "use_agent_tools", True)
        monkeypatch.setattr(settings, "max_agent_iterations", 5)
        reset_customize_graph_runtime_cache()

        client.app.state.session_store = SessionStore()
        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _FakeGpuClient())
        async def _force_manual_fallback(**kwargs):
            raise RuntimeError("force manual fallback for deterministic test")
        monkeypatch.setattr(interviewer_module, "_run_react_agent_once", _force_manual_fallback)

        call_counter = {"score_answer": 0}

        def _score_answer_handler(payload):
            call_counter["score_answer"] += 1
            return {
                "score": 4.8,
                "dimension_scores": {
                    "clarity": 5.0,
                    "depth": 4.0,
                    "relevance": 5.2,
                    "structure": 5.0,
                },
                "strengths": ["Response is on-topic"],
                "improvements": ["Need concrete implementation detail"],
                "followup_needed": True,
                "suggested_followup_angle": "Ask for implementation detail",
                "reasoning": "Needs deeper technical evidence.",
            }

        monkeypatch.setattr(
            interviewer_module,
            "score_answer",
            _ToolStub(_score_answer_handler),
        )
        monkeypatch.setattr(
            interviewer_module,
            "generate_followup",
            _ToolStub(lambda payload: ""),
        )
        monkeypatch.setattr(
            interviewer_module,
            "search_question_bank",
            _ToolStub(lambda payload: []),
        )

        start_resp = client.post(
            "/api/interview/customize/start",
            json={"user_id": "agent_user_002", "user_name": "Emma", "voice_enabled": False},
        )
        assert start_resp.status_code == 200
        session_id = start_resp.json()["session_id"]

        respond_resp = client.post(
            "/api/interview/customize/respond",
            json={"session_id": session_id, "user_response": "I can improve it."},
        )
        assert respond_resp.status_code == 200
        # Cost-protection assertion: same input should not trigger repeated scoring loops.
        assert call_counter["score_answer"] == 1

        state = await GraphCheckpointStateAccessor.read_customize_state(session_id)
        assert state is not None
        tool_call_log = state.get("tool_call_log", [])
        score_calls = [entry for entry in tool_call_log if entry.get("tool") == "score_answer"]
        guard_calls = [entry for entry in tool_call_log if entry.get("tool") == "agent_loop_guard"]
        assert len(score_calls) == 1
        assert len(guard_calls) == 0

    @pytest.mark.asyncio
    async def test_react_path_writes_tool_log_from_agent_messages(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        monkeypatch.setattr(settings, "use_agent_tools", True)
        reset_customize_graph_runtime_cache()

        client.app.state.session_store = SessionStore()
        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _FakeGpuClient())

        class _AiMessage:
            tool_calls = [
                {
                    "id": "call_1",
                    "name": "score_answer",
                    "args": {"question": "Q", "answer": "A"},
                }
            ]

        class _ToolMessage:
            type = "tool"
            tool_call_id = "call_1"
            name = "score_answer"
            content = (
                '{"score": 7.9, "dimension_scores": {"clarity": 8.0, "depth": 7.0, '
                '"relevance": 8.2, "structure": 7.8}, "strengths": ["Clear"], '
                '"improvements": ["Add metric"], "followup_needed": false, '
                '"suggested_followup_angle": null, "reasoning": "Good"}'
            )

        async def _fake_react_once(**kwargs):
            return {
                "messages": [_AiMessage(), _ToolMessage()],
                "structured_response": {
                    "next_action": "next_question",
                    "response_text": "Thanks. Next question: What was the impact?",
                    "reasoning": "Score is acceptable, move on.",
                },
            }

        monkeypatch.setattr(interviewer_module, "_run_react_agent_once", _fake_react_once)

        start_resp = client.post(
            "/api/interview/customize/start",
            json={"user_id": "agent_user_003", "user_name": "Emma", "voice_enabled": False},
        )
        assert start_resp.status_code == 200
        session_id = start_resp.json()["session_id"]

        respond_resp = client.post(
            "/api/interview/customize/respond",
            json={"session_id": session_id, "user_response": "I improved reliability with retries."},
        )
        assert respond_resp.status_code == 200

        state = await GraphCheckpointStateAccessor.read_customize_state(session_id)
        assert state is not None
        tool_call_log = state.get("tool_call_log", [])
        assert isinstance(tool_call_log, list)
        assert any(entry.get("tool") == "score_answer" for entry in tool_call_log)
