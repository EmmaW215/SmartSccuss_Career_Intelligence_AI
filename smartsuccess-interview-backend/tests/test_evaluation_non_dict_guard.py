"""
Regression tests for the production 500:
    POST /api/interview/behavioral/message
    -> "'list' object has no attribute 'get'"

Root cause: an evaluator LLM occasionally returns a top-level JSON array
(or other non-dict) instead of an object. safe_parse_evaluation returned it
verbatim, and the per-type _check_follow_up immediately called .get() on it.

Fix: safe_parse_evaluation guarantees a dict (the default evaluation) when
the parsed JSON is not a dict — identical handling to an unparseable response.
"""

import pytest

from app.utils.json_parser import extract_json_from_llm, safe_parse_evaluation


DEFAULT_EVAL = {"needs_followup": False, "follow_up_needed": "none", "score": 3}


class TestSafeParseEvaluationGuard:
    def test_top_level_array_falls_back_to_dict(self):
        # extract_json_from_llm legitimately parses an array into a list...
        assert isinstance(extract_json_from_llm('[{"a": 1}]'), list)
        # ...but the evaluation wrapper must hand back a dict.
        result = safe_parse_evaluation('[{"a": 1}]', DEFAULT_EVAL, "sess_array")
        assert isinstance(result, dict)
        assert result["_fallback_reason"] == "non_dict_json"
        # The exact call that used to 500:
        assert result.get("needs_followup") is False

    def test_scalar_json_falls_back_to_dict(self):
        for raw in ("42", '"just a string"', "true"):
            result = safe_parse_evaluation(raw, DEFAULT_EVAL, "sess_scalar")
            assert isinstance(result, dict)
            assert result.get("needs_followup") is False

    def test_valid_dict_is_unchanged(self):
        raw = '{"needs_followup": true, "follow_up_needed": "action", "score": 5}'
        result = safe_parse_evaluation(raw, DEFAULT_EVAL, "sess_ok")
        assert result["needs_followup"] is True
        assert result["follow_up_needed"] == "action"
        assert result["score"] == 5
        assert "_fallback_reason" not in result  # untouched happy path

    def test_unparseable_still_falls_back(self):
        result = safe_parse_evaluation("not json at all", DEFAULT_EVAL, "sess_bad")
        assert isinstance(result, dict)
        assert result["_fallback_reason"] == "json_parse_failure"


class TestCheckFollowUpSurvivesNonDictEvaluation:
    """
    The three interview types each call evaluation.get(...) in _check_follow_up.
    With the guard, an array-returning evaluator no longer 500s — the turn
    proceeds with the default (no follow-up) instead.
    """

    @pytest.mark.asyncio
    async def test_behavioral_follow_up_with_array_evaluation(self, monkeypatch):
        from app.interview.behavioral_interview import BehavioralInterviewService

        service = BehavioralInterviewService()
        session = _make_behavioral_session()

        # Evaluator emits a JSON array -> guard converts to default dict.
        evaluation = safe_parse_evaluation(
            '["situation", "task"]', service._default_evaluation(), session.session_id
        )
        assert isinstance(evaluation, dict)
        follow_up = await service._check_follow_up(session, evaluation)
        # default evaluation has follow_up_needed="none" -> no follow-up, no raise
        assert follow_up is None

    @pytest.mark.asyncio
    async def test_screening_follow_up_with_array_evaluation(self, monkeypatch):
        from app.interview.screening_interview import ScreeningInterviewService

        service = ScreeningInterviewService()
        session = _make_screening_session()

        evaluation = safe_parse_evaluation(
            '[1, 2, 3]', service._default_evaluation(), session.session_id
        )
        assert isinstance(evaluation, dict)
        follow_up = await service._check_follow_up(session, evaluation)
        assert follow_up is None


def _make_behavioral_session():
    from app.models import InterviewPhase, InterviewSession, InterviewType

    return InterviewSession(
        session_id="behavioral_user_x_abc",
        user_id="user_x",
        interview_type=InterviewType.BEHAVIORAL,
        phase=InterviewPhase.IN_PROGRESS,
        questions_asked=["Tell me about a time you led a project."],
        responses=[{"question_index": 0, "response": "I led a team.", "evaluation": {}}],
    )


def _make_screening_session():
    from app.models import InterviewPhase, InterviewSession, InterviewType

    return InterviewSession(
        session_id="screening_user_x_abc",
        user_id="user_x",
        interview_type=InterviewType.SCREENING,
        phase=InterviewPhase.IN_PROGRESS,
        questions_asked=["Tell me about yourself."],
        responses=[{"question_index": 0, "response": "I am an engineer.", "evaluation": {}}],
    )
