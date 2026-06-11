"""
Phase 2 Agent Tools — Unit tests for AgentToolkit and ToolRegistry

Offline (no LLM). Covers tool behavior, OpenAI schema generation, and the
never-raise contract of ToolRegistry.execute (self-healing foundation).
"""

import pytest

from app.agent.tools import AgentToolkit, SCORING_RUBRICS
from app.agent.registry import ToolRegistry, TOOL_SCHEMAS


# ================================================================
# AgentToolkit — search_question_bank
# ================================================================

class TestSearchQuestionBank:

    def test_returns_questions_for_valid_type(self):
        result = AgentToolkit().search_question_bank("screening")
        assert result["ok"] is True
        assert len(result["questions"]) == 3  # default limit
        assert {"id", "question", "category"} <= set(result["questions"][0])

    def test_unknown_interview_type_is_error_payload(self):
        result = AgentToolkit().search_question_bank("astrology")
        assert result["ok"] is False
        assert "astrology" in result["error"]

    def test_category_filter(self):
        result = AgentToolkit().search_question_bank(
            "screening", category="motivation"
        )
        assert result["ok"] is True
        assert all(q["category"] == "motivation" for q in result["questions"])
        assert len(result["questions"]) >= 1

    def test_exclude_ids(self):
        toolkit = AgentToolkit()
        all_q = toolkit.search_question_bank("screening", limit=10)
        first_id = all_q["questions"][0]["id"]
        result = toolkit.search_question_bank(
            "screening", exclude_ids=[first_id], limit=10
        )
        assert first_id not in [q["id"] for q in result["questions"]]

    def test_limit_is_clamped(self):
        result = AgentToolkit().search_question_bank("technical", limit=99)
        assert len(result["questions"]) <= 10


# ================================================================
# AgentToolkit — score_answer
# ================================================================

GOOD_ANSWER = (
    "In my last role at TechCorp I led the migration of our Python services "
    "to FastAPI on GCP, which reduced p95 latency by 40% and cut costs by "
    "$2000 a month. I coordinated a team of 3 engineers and we delivered in "
    "6 weeks using Docker and a phased rollout."
)


class TestScoreAnswer:

    async def test_heuristic_scoring_without_llm(self):
        result = await AgentToolkit().score_answer(
            question="Tell me about a recent project.",
            answer=GOOD_ANSWER,
            interview_type="screening",
        )
        assert result["ok"] is True
        assert result["method"] == "heuristic"
        assert set(result["scores"]) == set(SCORING_RUBRICS["screening"])
        assert all(1 <= s <= 5 for s in result["scores"].values())
        assert 1 <= result["overall"] <= 5

    async def test_empty_answer_is_error_payload(self):
        result = await AgentToolkit().score_answer(
            question="Q?", answer="   ", interview_type="screening"
        )
        assert result["ok"] is False

    async def test_behavioral_rubric_uses_star_criteria(self):
        result = await AgentToolkit().score_answer(
            question="Tell me about a challenge.",
            answer=GOOD_ANSWER,
            interview_type="behavioral",
        )
        assert set(result["scores"]) == {"situation", "task", "action", "result"}

    async def test_llm_scoring_with_valid_json(self):
        async def fake_llm(prompt, system_prompt=None, **kwargs):
            return (
                '{"scores": {"communication_clarity": 4, "relevance": 5, '
                '"specificity": 4, "professionalism": 4, "self_awareness": 3}, '
                '"feedback": "Strong, specific answer."}'
            )

        result = await AgentToolkit(llm_generate=fake_llm).score_answer(
            question="Q?", answer=GOOD_ANSWER, interview_type="screening"
        )
        assert result["method"] == "llm"
        assert result["scores"]["relevance"] == 5
        assert result["feedback"] == "Strong, specific answer."

    async def test_llm_scoring_tolerates_code_fences(self):
        async def fenced_llm(prompt, system_prompt=None, **kwargs):
            return (
                '```json\n{"scores": {"communication_clarity": 3, "relevance": 3, '
                '"specificity": 3, "professionalism": 3, "self_awareness": 3}, '
                '"feedback": "ok"}\n```'
            )

        result = await AgentToolkit(llm_generate=fenced_llm).score_answer(
            question="Q?", answer=GOOD_ANSWER
        )
        assert result["method"] == "llm"

    async def test_llm_failure_falls_back_to_heuristic(self):
        async def broken_llm(prompt, system_prompt=None, **kwargs):
            return "I think the candidate did well!"  # not JSON

        result = await AgentToolkit(llm_generate=broken_llm).score_answer(
            question="Q?", answer=GOOD_ANSWER
        )
        assert result["ok"] is True
        assert result["method"] == "heuristic"

    async def test_llm_scores_are_clamped_to_1_5(self):
        async def wild_llm(prompt, system_prompt=None, **kwargs):
            return (
                '{"scores": {"communication_clarity": 99, "relevance": -3, '
                '"specificity": 4, "professionalism": 4, "self_awareness": 3}, '
                '"feedback": "x"}'
            )

        result = await AgentToolkit(llm_generate=wild_llm).score_answer(
            question="Q?", answer=GOOD_ANSWER
        )
        assert result["scores"]["communication_clarity"] == 5
        assert result["scores"]["relevance"] == 1


# ================================================================
# AgentToolkit — profile and notes
# ================================================================

class TestProfileAndNotes:

    def test_profile_reflects_session_context(self, sample_resume, sample_job_description):
        toolkit = AgentToolkit(session_context={
            "interview_type": "technical",
            "resume_text": sample_resume,
            "job_description": sample_job_description,
            "questions_asked": ["Q1", "Q2"],
            "current_question_index": 2,
        })
        profile = toolkit.get_candidate_profile()
        assert profile["ok"] is True
        assert profile["has_resume"] and profile["has_job_description"]
        assert profile["questions_already_asked"] == ["Q1", "Q2"]
        assert profile["interview_type"] == "technical"

    def test_profile_with_empty_context(self):
        profile = AgentToolkit().get_candidate_profile()
        assert profile["ok"] is True
        assert profile["has_resume"] is False

    def test_save_note_accumulates(self):
        toolkit = AgentToolkit()
        assert toolkit.save_interview_note("Strong intro", "strength")["ok"]
        result = toolkit.save_interview_note("Vague on metrics", "concern")
        assert result["note_count"] == 2
        assert toolkit.notes[1]["category"] == "concern"

    def test_save_empty_note_is_error_payload(self):
        assert AgentToolkit().save_interview_note("  ")["ok"] is False


# ================================================================
# ToolRegistry
# ================================================================

class TestToolRegistry:

    def test_all_four_tools_registered(self):
        registry = ToolRegistry()
        assert set(registry.tool_names) == set(TOOL_SCHEMAS)

    def test_openai_tools_schema_shape(self):
        for tool in ToolRegistry().openai_tools():
            assert tool["type"] == "function"
            fn = tool["function"]
            assert fn["name"] and fn["description"]
            assert fn["parameters"]["type"] == "object"

    async def test_execute_with_json_string_arguments(self):
        result = await ToolRegistry().execute(
            "search_question_bank", '{"interview_type": "screening"}'
        )
        assert result["ok"] is True
        assert result["_latency_ms"] >= 0

    async def test_execute_with_dict_arguments(self):
        result = await ToolRegistry().execute(
            "save_interview_note", {"note": "test"}
        )
        assert result["ok"] is True

    async def test_execute_awaits_async_tools(self):
        result = await ToolRegistry().execute(
            "score_answer", {"question": "Q?", "answer": GOOD_ANSWER}
        )
        assert result["ok"] is True

    async def test_unknown_tool_never_raises(self):
        result = await ToolRegistry().execute("launch_rocket", "{}")
        assert result["ok"] is False
        assert "launch_rocket" in result["error"]

    async def test_malformed_json_arguments_never_raise(self):
        result = await ToolRegistry().execute("score_answer", "{not json")
        assert result["ok"] is False
        assert "JSONDecodeError" in result["error"]

    async def test_tool_exception_captured_as_error_payload(self):
        registry = ToolRegistry()

        def exploding_tool():
            raise RuntimeError("question bank database is down")

        registry.register(
            "exploding_tool", exploding_tool,
            {"description": "boom", "parameters": {"type": "object", "properties": {}}},
        )
        result = await registry.execute("exploding_tool", "{}")
        assert result["ok"] is False
        assert "question bank database is down" in result["error"]
