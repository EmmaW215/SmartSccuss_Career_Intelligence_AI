"""
Phase 2 tool boundary/contract tests.
"""

import pytest

from app.agents import tools as tools_module


@pytest.mark.asyncio
async def test_search_question_bank_enforces_k_boundary():
    result = await tools_module.search_question_bank.ainvoke(
        {
            "query": "python backend system design scalability",
            "category": "technical",
            "k": 999,
        }
    )
    assert isinstance(result, list)
    assert len(result) <= 10
    if result and "error" not in result[0]:
        assert {"id", "question", "category", "difficulty"}.issubset(result[0].keys())


@pytest.mark.asyncio
async def test_fetch_resume_context_returns_empty_when_query_api_unavailable(monkeypatch):
    class _FakeGpuClient:
        async def check_health(self, force: bool = False):
            return {"available": True, "services": {"rag": True}}

    monkeypatch.setattr(tools_module, "get_gpu_client", lambda: _FakeGpuClient())
    result = await tools_module.fetch_resume_context.ainvoke(
        {"user_id": "user_001", "query": "langgraph", "k": 3}
    )
    assert result == []


@pytest.mark.asyncio
async def test_fetch_resume_context_returns_empty_when_gpu_offline(monkeypatch):
    class _FakeGpuClient:
        async def check_health(self, force: bool = False):
            return {"available": False, "error": "offline"}

    monkeypatch.setattr(tools_module, "get_gpu_client", lambda: _FakeGpuClient())
    result = await tools_module.fetch_resume_context.ainvoke(
        {"user_id": "user_001", "query": "python", "k": 3}
    )
    assert result == []


@pytest.mark.asyncio
async def test_score_answer_contract_and_input_truncation(monkeypatch):
    observed = {}

    class _FakeEvaluator:
        async def evaluate_to_dict(self, *, question: str, answer: str, context=None):
            observed["question"] = question
            observed["answer"] = answer
            return {
                "score": 7.5,
                "dimension_scores": {
                    "clarity": 8.0,
                    "depth": 7.0,
                    "relevance": 8.5,
                    "structure": 7.5,
                },
                "strengths": ["Good relevance"],
                "improvements": ["Add metrics"],
                "followup_needed": False,
                "suggested_followup_angle": None,
                "reasoning": "Balanced technical answer.",
            }

    monkeypatch.setattr(tools_module, "get_evaluator_agent", lambda: _FakeEvaluator())
    result = await tools_module.score_answer.ainvoke(
        {
            "question": "How do you improve reliability?",
            "answer": "A" * 6000,
        }
    )
    assert isinstance(result, dict)
    assert 0 <= result["score"] <= 10
    assert set(result["dimension_scores"].keys()) == {
        "clarity",
        "depth",
        "relevance",
        "structure",
    }
    assert "tool_log" in result
    assert len(observed["answer"]) <= 3000


@pytest.mark.asyncio
async def test_score_answer_fallback_keeps_tool_log(monkeypatch):
    class _FailEvaluator:
        async def evaluate_to_dict(self, *, question: str, answer: str, context=None):
            raise RuntimeError("evaluator failure")

    monkeypatch.setattr(tools_module, "get_evaluator_agent", lambda: _FailEvaluator())
    result = await tools_module.score_answer.ainvoke(
        {
            "question": "How do you test APIs?",
            "answer": "I write contract and integration tests.",
        }
    )
    assert result["error"] == "evaluator_unavailable"
    assert "tool_log" in result
    assert result["tool_log"]["tool"] == "score_answer"


@pytest.mark.asyncio
async def test_get_session_progress_contract(monkeypatch):
    async def _fake_read_state(session_id: str):
        assert session_id == "sess_123"
        return {
            "current_question_index": 3,
            "questions": [{"q": 1}, {"q": 2}, {"q": 3}, {"q": 4}],
            "is_complete": False,
            "followup_count": 1,
            "phase": "questioning",
        }

    monkeypatch.setattr(tools_module, "_read_customize_state", _fake_read_state)
    result = await tools_module.get_session_progress.ainvoke({"session_id": "sess_123"})
    assert result["found"] is True
    assert result["questions_answered"] == 3
    assert result["questions_total"] == 4
    assert result["is_complete"] is False
    assert result["phase"] == "questioning"


@pytest.mark.asyncio
async def test_get_session_progress_fallback_shape_when_accessor_raises(monkeypatch):
    async def _raise_read_state(session_id: str):
        raise RuntimeError("checkpoint down")

    monkeypatch.setattr(tools_module, "_read_customize_state", _raise_read_state)
    result = await tools_module.get_session_progress.ainvoke({"session_id": "sess_123"})
    assert result["found"] is False
    assert result["questions_answered"] == 0
    assert result["questions_total"] == 0
    assert result["is_complete"] is False
    assert result["error"] == "progress_unavailable"
