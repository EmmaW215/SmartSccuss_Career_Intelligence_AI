"""
State schema for the LangGraph-based Customize Interview flow.
Phase 1 starts by defining this schema before wiring graph nodes.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, NotRequired, Optional, TypedDict

try:
    from langgraph.graph.message import add_messages
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    def add_messages(existing: Optional[list[Any]], new: Optional[list[Any]]) -> list[Any]:
        base = existing or []
        addition = new or []
        return [*base, *addition]


class QuestionItem(TypedDict):
    question: str
    customized_question: NotRequired[Optional[str]]
    category: str
    difficulty: str


class TurnEvaluation(TypedDict, total=False):
    score: float
    strengths: list[str]
    improvements: list[str]
    followup_needed: bool
    reasoning: str
    quality: Literal["good", "fair", "needs_improvement"]
    hint: str


class ToolCallRecord(TypedDict, total=False):
    tool: str
    args: dict[str, Any]
    result_digest: str
    ts: str
    error: Optional[str]


class EvaluatorVerdictState(TypedDict, total=False):
    score: float
    dimension_scores: dict[str, float]
    strengths: list[str]
    improvements: list[str]
    followup_needed: bool
    suggested_followup_angle: Optional[str]
    reasoning: str


class InterviewState(TypedDict):
    # Conversation transcript (append-only via reducer)
    messages: Annotated[list[Any], add_messages]

    # Session context
    session_id: str
    user_id: str
    user_name: Optional[str]
    interview_type: Literal["customize"]
    user_profile: Optional[dict[str, Any]]
    questions: list[QuestionItem]

    # Progress state
    current_question_index: int
    followup_count: int
    phase: Literal["greeting", "questioning", "followup", "closing", "done"]

    # Per-turn working values
    last_user_response: Optional[str]
    should_end: bool
    last_evaluation: Optional[TurnEvaluation]
    evaluations: list[TurnEvaluation]
    next_action: Literal["followup", "next_question", "closing"]
    evaluator_verdict: Optional[EvaluatorVerdictState]
    tool_call_log: list[ToolCallRecord]

    # Invocation output
    ai_response: Optional[str]
    is_complete: bool
