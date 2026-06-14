"""
Session Adapter
Converts BaseInterviewService sessions to SessionStore format
Provides unified session access interface
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from app.models import InterviewSession as BaseInterviewSession, InterviewPhase
from app.services.session_store import InterviewSession as StoreSession, InterviewStatus, SessionStore

# Canonical (lowercase) interview types stored on the dashboard.
_KNOWN_INTERVIEW_TYPES = {"screening", "behavioral", "technical", "customize"}

# Shown for a response whose evaluation produced no feedback text (e.g. the LLM
# evaluator was rate-limited and fell back). Beats an empty string, which the
# dashboard renders as the bare "No detailed feedback available." placeholder.
_EMPTY_FEEDBACK_NOTE = (
    "Detailed AI feedback wasn't available for this answer "
    "(the evaluation service was temporarily busy)."
)


def convert_base_session_to_store(
    base_session: BaseInterviewSession,
    session_store: Optional[SessionStore] = None
) -> StoreSession:
    """
    Convert BaseInterviewService session to SessionStore format
    
    Args:
        base_session: Session from BaseInterviewService
        session_store: Optional SessionStore instance (for creating new session)
    
    Returns:
        StoreSession compatible with SessionStore
    """
    # Map interview type.
    # The InterviewType enum values are lowercase ("technical"), and with
    # use_enum_values=True the field is already that string. A previous title-case
    # lookup table ("Technical Interview") never matched and fell back to
    # "screening" on every miss — so EVERY non-screening session was mislabeled as
    # "screening" on the dashboard. Normalize the raw value directly instead.
    _raw_type = (
        base_session.interview_type.value
        if hasattr(base_session.interview_type, "value")
        else str(base_session.interview_type)
    )
    _normalized_type = _raw_type.strip().lower().replace(" interview", "").strip()
    interview_type = (
        _normalized_type if _normalized_type in _KNOWN_INTERVIEW_TYPES else "screening"
    )
    
    # Map phase to status.
    # InterviewSession uses `use_enum_values=True`, so `phase` is a plain
    # string ("in_progress") — an enum-keyed map never matches and every
    # session mirrors as PENDING, which blocks report generation forever.
    phase_value = (
        base_session.phase.value
        if hasattr(base_session.phase, "value")
        else str(base_session.phase)
    ).lower()
    status_map = {
        InterviewPhase.NOT_STARTED.value: InterviewStatus.PENDING,
        InterviewPhase.GREETING.value: InterviewStatus.PENDING,
        InterviewPhase.IN_PROGRESS.value: InterviewStatus.IN_PROGRESS,
        InterviewPhase.COMPLETED.value: InterviewStatus.COMPLETED,
    }
    status = status_map.get(phase_value, InterviewStatus.PENDING)
    
    # Convert questions
    questions = []
    for i, question in enumerate(base_session.questions_asked):
        questions.append({
            "question": question,
            "question_index": i,
            "category": "general"
        })
    
    # Convert responses
    responses = []
    for response in base_session.responses:
        responses.append({
            "question_index": response.get("question_index", 0),
            "question": {"question": response.get("question", "")},
            "user_response": response.get("response", ""),
            "ai_response": "",  # Will be filled from messages
            "timestamp": response.get("timestamp", datetime.now().isoformat())
        })
    
    # Extract AI responses from messages - match by question order
    ai_messages = [msg for msg in base_session.messages if msg.get("role") == "assistant"]
    # Map AI responses to questions (skip greeting, match by question index)
    question_ai_map = {}
    question_index = 0
    for msg in base_session.messages:
        if msg.get("role") == "assistant":
            if question_index < len(base_session.questions_asked):
                question_ai_map[question_index] = msg.get("content", "")
                question_index += 1
    
    for i, response in enumerate(responses):
        resp_q_index = response.get("question_index", i)
        if resp_q_index in question_ai_map:
            responses[i]["ai_response"] = question_ai_map[resp_q_index]
    
    # Extract feedback hints from evaluations
    feedback_hints = []
    _empty_note_added = False  # add the "feedback unavailable" note at most once
    for response in base_session.responses:
        evaluation = response.get("evaluation", {})
        if evaluation:
            # Convert evaluation to feedback hint format
            score = evaluation.get("score", 3.0)
            if score >= 4.0:
                quality = "good"
            elif score >= 2.5:
                quality = "fair"
            else:
                quality = "needs_improvement"

            # Degrade empty feedback to a meaningful note (only the first time,
            # so the dashboard summary reads it once rather than repeating it).
            # The quality tag is still kept for every response so score counts
            # stay accurate.
            hint_text = (evaluation.get("feedback") or "").strip()
            if not hint_text and not _empty_note_added:
                hint_text = _EMPTY_FEEDBACK_NOTE
                _empty_note_added = True

            feedback_hints.append({
                "hint": hint_text,
                "quality": quality
            })
    
    # Create StoreSession
    store_session = StoreSession(
        session_id=base_session.session_id,
        user_id=base_session.user_id,
        interview_type=interview_type,
        status=status,
        current_question_index=base_session.current_question_index,
        questions=questions,
        responses=responses,
        feedback_hints=feedback_hints,
        created_at=base_session.created_at,
        started_at=base_session.started_at,
        completed_at=base_session.completed_at,
        last_activity=base_session.completed_at or base_session.started_at or base_session.created_at,
        voice_enabled=False,
        voice_provider="none"
    )
    
    return store_session


def sync_base_session_to_store(
    base_session: BaseInterviewSession,
    session_store: SessionStore
) -> Optional[StoreSession]:
    """
    Sync BaseInterviewService session to SessionStore
    
    Creates or updates the session in SessionStore
    """
    try:
        # Check if session already exists
        existing = session_store.get_session(base_session.session_id)
        
        if existing:
            # Update existing session
            store_session = convert_base_session_to_store(base_session)
            session_store.update_session(
                base_session.session_id,
                status=store_session.status,
                current_question_index=store_session.current_question_index,
                questions=store_session.questions,
                responses=store_session.responses,
                feedback_hints=store_session.feedback_hints,
                completed_at=store_session.completed_at
            )
            return session_store.get_session(base_session.session_id)
        else:
            # Create new session in store
            store_session = convert_base_session_to_store(base_session)
            # Note: We can't directly create using SessionStore.create_session
            # because it requires questions list upfront. Instead, we'll manually add it.
            session_store._sessions[base_session.session_id] = store_session
            
            # Track user's sessions
            if base_session.user_id not in session_store._user_sessions:
                session_store._user_sessions[base_session.user_id] = []
            if base_session.session_id not in session_store._user_sessions[base_session.user_id]:
                session_store._user_sessions[base_session.user_id].append(base_session.session_id)
            
            return store_session
    except Exception as e:
        print(f"Error syncing session to store: {e}")
        return None
