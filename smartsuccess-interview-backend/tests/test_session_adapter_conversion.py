"""
Regression tests for convert_base_session_to_store.

Pins two dashboard-facing fixes:
  - 2A: interview_type is mapped from the lowercase enum value, not a title-case
        lookup that fell back to "screening" for every non-screening session.
  - 2B: a response whose evaluation has no feedback text degrades to a
        meaningful note (once), instead of an empty string that the dashboard
        renders as "No detailed feedback available."
"""

import pytest

from app.models import InterviewSession as BaseInterviewSession, InterviewType, InterviewPhase
from app.services.session_adapter import (
    convert_base_session_to_store,
    _EMPTY_FEEDBACK_NOTE,
)


def _make_session(interview_type, responses=None):
    return BaseInterviewSession(
        session_id=f"{interview_type.value}_user_x_abc123",
        user_id="user_x",
        interview_type=interview_type,
        phase=InterviewPhase.COMPLETED,
        responses=responses or [],
    )


# ──────────────────────────────────────────────────────────────────
# 2A — interview_type mapping
# ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("itype,expected", [
    (InterviewType.SCREENING, "screening"),
    (InterviewType.BEHAVIORAL, "behavioral"),
    (InterviewType.TECHNICAL, "technical"),
])
def test_interview_type_preserved(itype, expected):
    store = convert_base_session_to_store(_make_session(itype))
    assert store.interview_type == expected


def test_technical_is_not_mislabeled_as_screening():
    # The exact regression: technical must NOT collapse to "screening".
    store = convert_base_session_to_store(_make_session(InterviewType.TECHNICAL))
    assert store.interview_type == "technical"
    assert store.interview_type != "screening"


# ──────────────────────────────────────────────────────────────────
# 2B — empty-feedback degradation
# ──────────────────────────────────────────────────────────────────

def test_empty_feedback_degrades_to_meaningful_note():
    session = _make_session(
        InterviewType.TECHNICAL,
        responses=[
            {"evaluation": {"score": 3.0, "feedback": ""}},
            {"evaluation": {"score": 2.0, "feedback": "   "}},  # whitespace-only
        ],
    )
    store = convert_base_session_to_store(session)
    hints = store.feedback_hints
    assert len(hints) == 2
    # The note appears exactly once (so the dashboard summary doesn't repeat it).
    note_hints = [h for h in hints if h["hint"] == _EMPTY_FEEDBACK_NOTE]
    assert len(note_hints) == 1
    # The other empty one stays empty (frontend filters it), but quality is kept.
    assert any(h["hint"] == "" for h in hints)
    assert all(h["quality"] in {"good", "fair", "needs_improvement"} for h in hints)


def test_real_feedback_is_preserved():
    session = _make_session(
        InterviewType.SCREENING,
        responses=[
            {"evaluation": {"score": 4.5, "feedback": "Strong, specific answer."}},
        ],
    )
    store = convert_base_session_to_store(session)
    assert store.feedback_hints == [
        {"hint": "Strong, specific answer.", "quality": "good"}
    ]


def test_no_evaluation_yields_no_hints():
    session = _make_session(
        InterviewType.BEHAVIORAL,
        responses=[{"response": "ok"}],  # no "evaluation" key
    )
    store = convert_base_session_to_store(session)
    assert store.feedback_hints == []
