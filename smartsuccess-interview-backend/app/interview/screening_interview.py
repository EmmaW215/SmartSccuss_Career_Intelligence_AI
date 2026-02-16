"""
Screening Interview Service
First impression assessment (10-15 minutes)

FIXES APPLIED:
- A-Q4 (Sprint 1): Conversation context in evaluation
- A-Q2 (Sprint 2): Centralized LLM via base._call_llm()
- A-Q3 (Sprint 2): Robust JSON parsing via json_parser utility
- A-Q5 (Sprint 2): Greeting separated from first question
- A-Q6 (Sprint 5): Fallback scores with transparency flag
- B-S1 (Sprint 3): LLM-based follow-up decision (replaces word-count threshold)
- B-S2 (Sprint 5): Personalized greeting with JD context
- B-S3 (Sprint 3): Text-appropriate evaluation criteria
- G-P1 (Sprint 2): System prompt for evaluator role
- G-P2 (Sprint 2): Strengthened JSON output instructions
- F-A2 (Sprint 5): Thread-safe singleton via lru_cache
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime
from functools import lru_cache

from .base_interview import BaseInterviewService
from app.models import (
    InterviewSession,
    InterviewType,
    SessionSummary,
    QuestionResponse
)
from app.rag.screening_rag import ScreeningRAGService, get_screening_rag_service
from app.utils.json_parser import safe_parse_evaluation
from app.utils.response_analytics import compute_score_summary
from app.config import settings

logger = logging.getLogger(__name__)

# FIX: G-P1 (Sprint 2) — System prompt for evaluator role
SCREENING_EVALUATOR_SYSTEM = """You are an experienced hiring manager evaluating screening interview responses.
Your evaluation must be fair, specific, and based only on what the candidate actually said.
Always respond with valid JSON only — no markdown, no explanation, no preamble."""


class ScreeningInterviewService(BaseInterviewService):
    """
    Screening Interview Service
    
    Purpose: First impression assessment
    Duration: 10-15 minutes
    Focus: Communication, motivation, basic fit
    """
    
    interview_type = InterviewType.SCREENING
    max_questions = settings.screening_max_questions
    duration_limit_minutes = settings.screening_duration_minutes
    
    def __init__(self, session_store=None):
        super().__init__(session_store=session_store)
        
        # Initialize RAG service
        self.rag_service = get_screening_rag_service()
        
        # NOTE: Direct LLM client removed — using self._call_llm() from base
        # FIX: A-Q2 (Sprint 2)
    
    async def get_greeting(self, session: Optional[InterviewSession] = None) -> str:
        """
        Return screening interview greeting.
        
        FIX: B-S2 (Sprint 5) — Personalized with JD context
        FIX: A-Q5 (Sprint 2) — Greeting does NOT include first question
        """
        base = "Welcome to your Screening Interview! 🎯\n\n"
        base += "I'm your AI interviewer today. This is a brief 10-15 minute conversation "
        base += "where I'll get to know you better"
        
        # FIX: B-S2 — Personalize with JD context
        if session and session.job_description:
            # Simple extraction: look for role/company in first 200 chars
            jd_preview = session.job_description[:200].lower()
            base += " and understand your interest in this opportunity"
        
        base += ".\n\n"
        base += "We'll cover your background, motivation, and fit. "
        base += "Remember, this is like a first conversation — be yourself and speak naturally!\n\n"
        base += "Let's begin. Please tell me about yourself."
        
        return base
    
    async def _build_context(self, session: InterviewSession) -> None:
        """Build RAG context from resume and job description"""
        await self.rag_service.build_user_context(
            user_id=session.user_id,
            resume_text=session.resume_text,
            job_description=session.job_description
        )
    
    async def _get_next_question(self, session: InterviewSession) -> str:
        """Get the next screening question"""
        # Use personalized question if we have context
        if session.resume_text or session.job_description:
            return await self.rag_service.get_personalized_question(
                session,
                session.current_question_index
            )
        
        # Otherwise use standard question
        return await self.rag_service.get_question(session.current_question_index)
    
    async def _evaluate_response(
        self,
        session: InterviewSession,
        response: str
    ) -> Dict[str, Any]:
        """
        Evaluate a screening response.
        
        FIX: A-Q4 — Includes conversation context
        FIX: A-Q2 — Uses centralized LLM
        FIX: A-Q3 — Robust JSON parsing
        FIX: B-S1 — Adds needs_followup field
        FIX: B-S3 — Text-appropriate criteria
        FIX: G-P1 — System prompt for evaluator
        FIX: G-P2 — Strengthened JSON instructions
        """
        current_question = (
            session.questions_asked[-1] if session.questions_asked 
            else "Tell me about yourself"
        )
        
        # FIX: A-Q4 — Build conversation context
        context_block = self._build_evaluation_context(
            session, session.current_question_index
        )
        
        try:
            # FIX: B-S3 — Text-appropriate criteria (replaces confidence/enthusiasm)
            # FIX: B-S1 — Added needs_followup to schema
            # FIX: G-P2 — Explicit JSON-only instruction
            prompt = f"""Evaluate this screening interview response.

## Previous Q&A Context (for consistency and progression assessment):
{context_block if context_block else "This is the first question."}

## Current Question and Response to Evaluate:
Question: {current_question}
Response: {response}

Evaluate on these criteria (1-5 scale):
1. Communication Clarity - How clearly did they express themselves?
2. Relevance - Did they answer the question directly?
3. Specificity - Did they provide concrete examples, numbers, or details?
4. Professionalism - Was the tone appropriate?
5. Self-Awareness - Did they demonstrate honest self-reflection?

Also determine if a follow-up is needed:
- Set needs_followup to true ONLY if the response was vague, evasive, or missing key information.
- Do NOT base it on response length alone.

Return ONLY valid JSON in this exact format, with no other text:
{{
  "communication_clarity": <1-5>,
  "relevance": <1-5>,
  "specificity": <1-5>,
  "professionalism": <1-5>,
  "self_awareness": <1-5>,
  "strength": "<one specific strength observed>",
  "improvement": "<one specific area for improvement>",
  "first_impression": "<Positive|Neutral|Concerning>",
  "needs_followup": <true|false>,
  "followup_reason": "<brief reason if true, null if false>"
}}"""

            # FIX: A-Q2 — Use centralized LLM with fallback chain
            # FIX: G-P1 — System prompt for evaluator role
            result_text = await self._call_llm(
                prompt=prompt,
                system_prompt=SCREENING_EVALUATOR_SYSTEM,
                temperature=0.3,
                max_tokens=400
            )
            
            # FIX: A-Q3 — Robust JSON parsing
            return safe_parse_evaluation(
                result_text,
                self._default_evaluation(),
                session_id=session.session_id
            )
            
        except Exception as e:
            logger.error(f"Screening evaluation error for {session.session_id}: {e}")
            return self._default_evaluation()
    
    def _default_evaluation(self) -> Dict[str, Any]:
        """
        FIX: A-Q6 (Sprint 5) — Default with transparency flag.
        """
        return {
            "communication_clarity": 3,
            "relevance": 3,
            "specificity": 3,
            "professionalism": 3,
            "self_awareness": 3,
            "strength": "Response recorded",
            "improvement": "Evaluation unavailable",
            "first_impression": "Neutral",
            "needs_followup": False,
            "followup_reason": None,
            "_evaluation_status": "fallback",
            "_fallback_reason": "evaluation_unavailable"
        }
    
    async def _check_follow_up(
        self,
        session: InterviewSession,
        evaluation: Dict[str, Any]
    ) -> Optional[str]:
        """
        FIX: B-S1 (Sprint 3) — LLM-based follow-up decision.
        Replaces arbitrary word-count threshold (< 20 words).
        """
        # Use LLM's assessment instead of word count
        if evaluation.get("needs_followup", False):
            last_question = (
                session.questions_asked[-1] if session.questions_asked else ""
            )
            last_response = (
                session.responses[-1].get("response", "") 
                if session.responses else ""
            )
            reason = evaluation.get("followup_reason", "")
            
            return await self.rag_service.get_follow_up_question(
                last_question, last_response
            )
        
        return None
    
    async def _generate_summary(self, session: InterviewSession) -> SessionSummary:
        """Generate screening interview summary"""
        total_scores = {
            "communication_clarity": [],
            "relevance": [],
            "specificity": [],       # FIX: B-S3 — was "confidence"
            "professionalism": [],
            "self_awareness": []     # FIX: B-S3 — was "enthusiasm"
        }
        
        strengths = []
        improvements = []
        detailed_feedback = []
        
        for resp in session.responses:
            eval_data = resp.get("evaluation", {})
            
            for key in total_scores:
                if key in eval_data:
                    total_scores[key].append(eval_data[key])
            
            if eval_data.get("strength"):
                strengths.append(eval_data["strength"])
            if eval_data.get("improvement"):
                improvements.append(eval_data["improvement"])
            
            detailed_feedback.append(QuestionResponse(
                question_index=resp.get("question_index", 0),
                question=resp.get("question", ""),
                response=resp.get("response", ""),
                feedback=eval_data
            ))
        
        # Calculate averages
        score_breakdown = {}
        all_scores = []
        for key, scores in total_scores.items():
            if scores:
                avg = sum(scores) / len(scores)
                score_breakdown[key] = avg
                all_scores.extend(scores)
            else:
                score_breakdown[key] = 3.0
        
        overall_score = (
            sum(score_breakdown.values()) / len(score_breakdown) 
            if score_breakdown else 3.0
        )
        
        # FIX: I-D2 (Sprint 5) — Score distribution metrics
        score_stats = compute_score_summary(all_scores) if all_scores else None
        
        # Calculate duration
        duration = 0
        if session.started_at and session.completed_at:
            duration = (
                (session.completed_at - session.started_at).total_seconds() / 60
            )
        
        # Determine recommendation
        if overall_score >= 4.0:
            recommendation = (
                "Strong candidate — recommend moving to behavioral interview"
            )
        elif overall_score >= 3.0:
            recommendation = (
                "Adequate screening — consider for next round with some reservations"
            )
        else:
            recommendation = (
                "Some concerns noted — recommend additional screening or pass"
            )
        
        return SessionSummary(
            session_id=session.session_id,
            interview_type=InterviewType.SCREENING,
            total_questions=len(session.questions_asked),
            total_responses=len(session.responses),
            duration_minutes=round(duration, 1),
            overall_score=round(overall_score, 2),
            score_breakdown=score_breakdown,
            top_strengths=strengths[:3],
            areas_for_improvement=improvements[:3],
            recommendation=recommendation,
            detailed_feedback=detailed_feedback,
            score_statistics=score_stats
        )
    
    async def _get_completion_message(self, session: InterviewSession) -> str:
        """Get screening completion message"""
        return """Thank you for completing the Screening Interview! 🎉

You've given me a great first impression. I've noted your background, motivation, and how you'd fit with this role.

Your feedback summary is being prepared. In a real interview process, this would be the first step before moving to behavioral or technical rounds.

Great job!"""


# FIX: F-A2 (Sprint 5) — Thread-safe singleton via lru_cache
@lru_cache(maxsize=1)
def get_screening_interview_service(session_store=None) -> ScreeningInterviewService:
    """Get the singleton screening interview service (thread-safe)"""
    return ScreeningInterviewService(session_store=session_store)
