"""
Adapter utilities between LangGraph checkpoint state and SessionStore responses.

This keeps route handlers thin while preserving existing API response contracts.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.session_store import SessionStore


class CheckpointStoreAdapter:
    @staticmethod
    def feedback_hint_from_graph_state(state: dict[str, Any]) -> Optional[dict[str, Any]]:
        evaluation = state.get("last_evaluation") or {}
        hint = evaluation.get("hint")
        quality = evaluation.get("quality")
        if not hint and not quality:
            return None
        result: dict[str, Any] = {}
        if hint:
            result["hint"] = hint
        if quality:
            result["quality"] = quality
        return result

    @staticmethod
    def start_response(
        *,
        session_id: str,
        greeting: str,
        total_questions: int,
        voice_enabled: bool,
        gpu_available: bool,
    ) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "greeting": greeting,
            "total_questions": total_questions,
            "voice_enabled": voice_enabled,
            "interview_type": "customize",
            "profile_used": False,
            "gpu_available": gpu_available,
        }

    @staticmethod
    def respond_response(
        *,
        session_store: SessionStore,
        session: Any,
        session_id: str,
        user_response: str,
        graph_state: dict[str, Any],
    ) -> Dict[str, Any]:
        feedback_hint = CheckpointStoreAdapter.feedback_hint_from_graph_state(graph_state)
        ai_response = graph_state.get("ai_response") or "Thanks for sharing. Please continue."
        is_complete = bool(graph_state.get("is_complete", False))

        if is_complete:
            session_store.complete_session(session_id)
            return {
                "ai_response": ai_response,
                "is_complete": True,
                "feedback_hint": feedback_hint,
                "session_id": session_id,
            }

        graph_idx = int(graph_state.get("current_question_index", session.current_question_index))
        next_action = graph_state.get("next_action")
        answered_index = graph_idx
        if next_action == "next_question":
            answered_index = max(0, graph_idx - 1)

        session_store.add_response(
            session_id=session_id,
            question_index=answered_index,
            user_response=user_response,
            ai_response=ai_response,
            feedback_hint=feedback_hint,
        )
        # Keep session store aligned with graph-derived index.
        session_store.update_session(
            session_id,
            current_question_index=graph_idx,
        )

        updated_session = session_store.get_session(session_id)
        current_idx = (
            updated_session.current_question_index
            if updated_session
            else graph_idx
        )
        current_q = (
            session.questions[current_idx]
            if current_idx < len(session.questions)
            else None
        )
        category = current_q.get("category", "general") if current_q else None

        return {
            "ai_response": ai_response,
            "tone": "neutral",
            "feedback_hint": feedback_hint,
            "current_question": current_idx,
            "total_questions": len(session.questions),
            "current_category": category,
            "is_complete": False,
            "session_id": session_id,
        }
