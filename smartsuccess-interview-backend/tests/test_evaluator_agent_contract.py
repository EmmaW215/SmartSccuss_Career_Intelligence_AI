"""
Phase 2 evaluator agent contract tests.
"""

import pytest

from app.agents import evaluator_agent as evaluator_module


class _FakeStructuredModel:
    async def ainvoke(self, prompt: str):
        assert "Return JSON" in prompt
        return {
            "score": 8.6,
            "dimension_scores": {
                "clarity": 8.5,
                "depth": 8.0,
                "relevance": 9.0,
                "structure": 8.8,
            },
            "strengths": ["Strong relevance", "Clear communication"],
            "improvements": ["Add one concrete metric"],
            "followup_needed": False,
            "suggested_followup_angle": None,
            "reasoning": "Answer is clear and relevant.",
        }


class _FakeModel:
    def with_structured_output(self, schema):
        assert schema is evaluator_module.EvaluationVerdict
        return _FakeStructuredModel()


@pytest.mark.asyncio
async def test_evaluator_agent_structured_output_contract(monkeypatch):
    monkeypatch.setattr(
        evaluator_module,
        "get_chat_model",
        lambda *args, **kwargs: _FakeModel(),
    )
    agent = evaluator_module.EvaluatorAgent()

    verdict = await agent.evaluate(
        question="How do you design scalable systems?",
        answer="I start with throughput and latency targets, then choose data partitioning and cache strategy.",
    )
    payload = verdict.model_dump()

    assert 0 <= payload["score"] <= 10
    assert set(payload["dimension_scores"].keys()) == {
        "clarity",
        "depth",
        "relevance",
        "structure",
    }
    assert isinstance(payload["strengths"], list)
    assert isinstance(payload["improvements"], list)
    assert isinstance(payload["followup_needed"], bool)
    assert "reasoning" in payload


@pytest.mark.asyncio
async def test_evaluator_agent_fallback_contract_when_model_fails(monkeypatch):
    def _raise_model(*args, **kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(evaluator_module, "get_chat_model", _raise_model)
    agent = evaluator_module.EvaluatorAgent()

    verdict = await agent.evaluate(
        question="Tell me about a migration challenge.",
        answer="I migrated a monolith to services and reduced deployment risk.",
    )
    payload = verdict.model_dump()

    assert 0 <= payload["score"] <= 10
    assert set(payload["dimension_scores"].keys()) == {
        "clarity",
        "depth",
        "relevance",
        "structure",
    }
    assert isinstance(payload["followup_needed"], bool)
    assert isinstance(payload["reasoning"], str)
    assert len(payload["reasoning"]) > 0
