"""
Customize Interview Feedback Service (Phase 2)
FIX: E-E1 (Sprint 4) — Feedback for custom interview sessions
FIX: E-E2 (Sprint 4) — Placeholder for custom RAG context integration

NOTE: This is a STUB for the Phase 2 Customize Interview feature.
The backend routing for this feature was not fully implemented in the
original codebase. This stub provides the feedback interface that can
be wired up when the Customize Interview backend is completed.
"""

import logging
from typing import Dict, Optional, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CustomizeFeedbackService:
    """
    Feedback generation for Customize Interview sessions.
    
    Uses the same evaluation patterns as the standard interview agents
    but adapted for user-defined questions and criteria.
    """
    
    def __init__(self):
        # Will be initialized when backend routing is implemented
        self._initialized = False
    
    async def generate_feedback(
        self,
        session_id: str,
        questions: List[str],
        responses: List[str],
        evaluation_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate feedback for a custom interview session.
        
        Args:
            session_id: Session identifier
            questions: List of questions asked
            responses: List of user responses
            evaluation_criteria: Optional custom criteria from user
            
        Returns:
            Feedback dict with scores and recommendations
        """
        if not questions or not responses:
            return {
                "status": "error",
                "message": "No questions or responses to evaluate"
            }
        
        # Pair questions with responses
        pairs = list(zip(questions, responses))
        
        # TODO: E-E1 — Implement full LLM-based evaluation
        # For now, return structured placeholder
        feedback = {
            "session_id": session_id,
            "total_questions": len(pairs),
            "total_responses": len(responses),
            "evaluation_status": "stub",
            "message": (
                "Customize interview feedback will be available when the "
                "backend routing is fully implemented. "
                "See MIGRATION_GUIDE.md Sprint 4 for details."
            ),
            "question_feedback": [
                {
                    "question_index": i,
                    "question": q,
                    "response_length": len(r.split()),
                    "status": "pending_evaluation"
                }
                for i, (q, r) in enumerate(pairs)
            ],
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return feedback
    
    async def generate_custom_rag_feedback(
        self,
        session_id: str,
        rag_context: Dict[str, Any],
        responses: List[str]
    ) -> Dict[str, Any]:
        """
        FIX: E-E2 — Generate feedback using custom RAG context.
        
        Placeholder for when GPU-based custom RAG is integrated.
        """
        return {
            "session_id": session_id,
            "status": "stub",
            "message": (
                "Custom RAG feedback requires GPU server integration. "
                "See MIGRATION_GUIDE.md Sprint 4."
            ),
            "rag_context_available": bool(rag_context)
        }


# Singleton
_customize_feedback: Optional[CustomizeFeedbackService] = None


def get_customize_feedback_service() -> CustomizeFeedbackService:
    """Get singleton customize feedback service"""
    global _customize_feedback
    if _customize_feedback is None:
        _customize_feedback = CustomizeFeedbackService()
    return _customize_feedback
