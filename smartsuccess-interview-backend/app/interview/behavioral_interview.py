"""
Behavioral Interview Service
STAR method assessment (25-30 minutes)

FIXES APPLIED:
- A-Q4 (Sprint 1): Conversation context in evaluation
- A-Q2 (Sprint 2): Centralized LLM via base._call_llm()
- A-Q3 (Sprint 2): Robust JSON parsing via json_parser utility
- A-Q5 (Sprint 2): Greeting separated from first question
- A-Q6 (Sprint 5): Fallback scores with transparency flag
- C-B1 (Sprint 1): Follow-up state moved to session (thread-safe)
- C-B2 (Sprint 3): STAR coaching templates for follow-ups
- C-B3 (Sprint 3): Competency coverage tracking
- G-P1 (Sprint 2): System prompt for evaluator role
- G-P2 (Sprint 2): Strengthened JSON output instructions
- G-P3 (Sprint 2): Calibrated scoring anchors in eval prompt
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
from app.rag.behavioral_rag import BehavioralRAGService, get_behavioral_rag_service
from app.rag.domain_config import (
    STAR_COACHING_TEMPLATES,
    QUESTION_COMPETENCY_MAP,
    TARGET_COMPETENCIES
)
from app.utils.json_parser import safe_parse_evaluation
from app.utils.response_analytics import compute_score_summary
from app.config import settings

logger = logging.getLogger(__name__)

# FIX: G-P1 (Sprint 2) — System prompt for evaluator role
BEHAVIORAL_EVALUATOR_SYSTEM = """You are an experienced behavioral interviewer using the STAR method.
You evaluate responses based on how well candidates describe real situations with specific actions and measurable results.
Always respond with valid JSON only — no markdown, no explanation, no preamble.
Rate strictly: a 5 requires exceptional detail and quantified results; a 3 is average with room for improvement."""


class BehavioralInterviewService(BaseInterviewService):
    """
    Behavioral Interview Service using STAR Method

    Purpose: Assess past behavior as predictor of future performance
    Duration: 25-30 minutes
    Focus: Teamwork, problem-solving, leadership, adaptability
    """

    interview_type = InterviewType.BEHAVIORAL
    max_questions = settings.behavioral_max_questions
    duration_limit_minutes = settings.behavioral_duration_minutes

    def __init__(self, session_store=None):
        super().__init__(session_store=session_store)

        # Initialize RAG service
        self.rag_service = get_behavioral_rag_service()

        # NOTE: Direct LLM client removed — using self._call_llm() from base
        # FIX: A-Q2 (Sprint 2)

        # FIX: C-B1 (Sprint 1) — REMOVED follow_up_count dict from service
        # Now tracked per-session via session.follow_up_count

    async def get_greeting(self, session: Optional[InterviewSession] = None) -> str:
        """
        Return behavioral interview greeting.

        FIX: A-Q5 (Sprint 2) — Greeting includes first question as one unit,
        but the question is tracked separately in questions_asked.
        """
        greeting = """Welcome to your Behavioral Interview! 💼

This is a 25-30 minute session where we'll explore how you've handled real situations in the past.

I'll be using the STAR method:
• **S**ituation — Describe the context
• **T**ask — Explain your responsibility
• **A**ction — Detail what YOU did
• **R**esult — Share the outcome

Tips for success:
✓ Use specific examples from your experience
✓ Focus on YOUR actions, not the team's
✓ Quantify results when possible

Let's start with a teamwork question:

Tell me about a challenge you faced working in a team. How did you handle it?"""
        return greeting

    async def _build_context(self, session: InterviewSession) -> None:
        """Build RAG context from resume and job description"""
        await self.rag_service.build_user_context(
            user_id=session.user_id,
            resume_text=session.resume_text,
            job_description=session.job_description
        )

    async def _get_next_question(self, session: InterviewSession) -> str:
        """
        Get the next behavioral question.

        FIX: C-B3 (Sprint 3) — Track competencies covered and avoid repeats.
        """
        # Determine target competency for this question
        target_competency = QUESTION_COMPETENCY_MAP.get(
            session.current_question_index % len(TARGET_COMPETENCIES),
            "problem_solving"
        )

        # Track competency
        if target_competency not in session.competencies_covered:
            session.competencies_covered.append(target_competency)

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
        Evaluate a behavioral response using STAR method.

        FIX: A-Q4 — Conversation context
        FIX: A-Q2 — Centralized LLM
        FIX: A-Q3 — Robust JSON parsing
        FIX: G-P3 — Calibrated scoring anchors
        """
        current_question = (
            session.questions_asked[-1] if session.questions_asked else ""
        )

        # FIX: A-Q4 — Build conversation context
        context_block = self._build_evaluation_context(
            session, session.current_question_index
        )

        try:
            # FIX: G-P3 — Calibrated scoring anchors
            prompt = f"""Evaluate this behavioral interview response using the STAR method.

## Previous Q&A Context (for consistency and progression assessment):
{context_block if context_block else "This is the first question."}

## Current Question and Response:
Question: {current_question}
Response: {response}

## STAR Analysis (rate each 1-5):
Use these calibration anchors:
- 1: No attempt or completely off-topic
- 2: Vague generalities, no specific example
- 3: Adequate — a real example but lacking detail in some STAR components
- 4: Strong — clear example with most STAR components well-addressed
- 5: Exceptional — vivid, specific example with quantified results and reflection

1. Situation (1-5): Was the context clearly described? Was it a real, specific example?
2. Task (1-5): Was their role clearly defined? Did they own the responsibility?
3. Action (1-5): Did they describe THEIR specific actions? Did they say "I" not just "we"?
4. Result (1-5): Was there a clear outcome? Were results quantified?

Return ONLY valid JSON in this exact format, with no other text:
{{
  "star_scores": {{
    "situation": <1-5>,
    "task": <1-5>,
    "action": <1-5>,
    "result": <1-5>
  }},
  "primary_competency": "<main competency demonstrated>",
  "secondary_competency": "<secondary competency if any>",
  "missing_competency": "<competency not well demonstrated>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "growth_areas": ["<area 1>", "<area 2>"],
  "follow_up_needed": "<situation|task|action|result|none>"
}}"""

            # FIX: A-Q2 — Use centralized LLM
            # FIX: G-P1 — System prompt
            result_text = await self._call_llm(
                prompt=prompt,
                system_prompt=BEHAVIORAL_EVALUATOR_SYSTEM,
                temperature=0.3,
                max_tokens=500
            )

            # FIX: A-Q3 — Robust JSON parsing
            return safe_parse_evaluation(
                result_text,
                self._default_evaluation(),
                session_id=session.session_id
            )

        except Exception as e:
            logger.error(f"STAR evaluation error for {session.session_id}: {e}")
            return self._default_evaluation()

    def _default_evaluation(self) -> Dict[str, Any]:
        """FIX: A-Q6 — Default with transparency flag."""
        return {
            "star_scores": {
                "situation": 3,
                "task": 3,
                "action": 3,
                "result": 3
            },
            "primary_competency": "Communication",
            "secondary_competency": "",
            "missing_competency": "",
            "strengths": ["Response recorded"],
            "growth_areas": ["Evaluation unavailable"],
            "follow_up_needed": "none",
            "_evaluation_status": "fallback",
            "_fallback_reason": "evaluation_unavailable"
        }

    async def _check_follow_up(
        self,
        session: InterviewSession,
        evaluation: Dict[str, Any]
    ) -> Optional[str]:
        """
        Check if we need a STAR follow-up.

        FIX: C-B1 (Sprint 1) — Follow-up state on SESSION, not service singleton.
        FIX: C-B2 (Sprint 3) — Uses STAR coaching templates.
        """
        q_idx = session.current_question_index
        current_count = session.follow_up_count.get(q_idx, 0)

        if current_count >= 2:  # Max 2 follow-ups per question
            return None

        follow_up_needed = evaluation.get("follow_up_needed", "none")

        if follow_up_needed and follow_up_needed != "none":
            # FIX: C-B1 — Update count on session object
            session.follow_up_count[q_idx] = current_count + 1
            session.follow_ups_used += 1

            # FIX: C-B2 — Use coaching template if available
            if follow_up_needed in STAR_COACHING_TEMPLATES:
                return STAR_COACHING_TEMPLATES[follow_up_needed]

            # Otherwise, use RAG smart follow-up
            last_question = (
                session.questions_asked[-1] if session.questions_asked else ""
            )
            last_response = (
                session.responses[-1].get("response", "")
                if session.responses else ""
            )

            return await self.rag_service.get_smart_follow_up(
                last_question,
                last_response,
                follow_up_needed
            )

        return None

    async def _generate_summary(self, session: InterviewSession) -> SessionSummary:
        """Generate behavioral interview summary"""
        all_star_scores = {
            "situation": [],
            "task": [],
            "action": [],
            "result": []
        }

        competencies_shown = []
        strengths = []
        growth_areas = []
        detailed_feedback = []

        for resp in session.responses:
            eval_data = resp.get("evaluation", {})
            star_scores = eval_data.get("star_scores", {})

            for key in all_star_scores:
                if key in star_scores:
                    all_star_scores[key].append(star_scores[key])

            if eval_data.get("primary_competency"):
                competencies_shown.append(eval_data["primary_competency"])

            strengths.extend(eval_data.get("strengths", []))
            growth_areas.extend(eval_data.get("growth_areas", []))

            detailed_feedback.append(QuestionResponse(
                question_index=resp.get("question_index", 0),
                question=resp.get("question", ""),
                response=resp.get("response", ""),
                feedback=eval_data
            ))

        # Calculate average STAR scores
        score_breakdown = {}
        all_scores = []
        for key, scores in all_star_scores.items():
            if scores:
                avg = sum(scores) / len(scores)
                score_breakdown[f"star_{key}"] = avg
                all_scores.extend(scores)
            else:
                score_breakdown[f"star_{key}"] = 3.0

        # Overall STAR score
        star_values = list(score_breakdown.values())
        overall_score = (
            sum(star_values) / len(star_values) if star_values else 3.0
        )

        # FIX: I-D2 (Sprint 5) — Score distribution metrics
        score_stats = compute_score_summary(all_scores) if all_scores else None

        # FIX: C-B3 (Sprint 3) — Include competency coverage in breakdown
        score_breakdown["competencies_covered"] = len(
            set(session.competencies_covered)
        )
        score_breakdown["competencies_total"] = len(TARGET_COMPETENCIES)

        # Calculate duration
        duration = 0
        if session.started_at and session.completed_at:
            duration = (
                (session.completed_at - session.started_at).total_seconds() / 60
            )

        # Determine recommendation
        if overall_score >= 4.0:
            recommendation = (
                "Strong behavioral performance — demonstrates excellent "
                "soft skills and STAR method mastery"
            )
        elif overall_score >= 3.5:
            recommendation = (
                "Good behavioral responses — solid examples with room "
                "for more detail"
            )
        elif overall_score >= 3.0:
            recommendation = (
                "Adequate behavioral responses — some STAR components "
                "could be stronger"
            )
        else:
            recommendation = (
                "Needs improvement — responses lack structure or "
                "specific examples"
            )

        # Remove duplicates
        unique_strengths = list(dict.fromkeys(strengths))[:5]
        unique_growth = list(dict.fromkeys(growth_areas))[:5]

        return SessionSummary(
            session_id=session.session_id,
            interview_type=InterviewType.BEHAVIORAL,
            total_questions=len(session.questions_asked),
            total_responses=len(session.responses),
            duration_minutes=round(duration, 1),
            overall_score=round(overall_score, 2),
            score_breakdown=score_breakdown,
            top_strengths=unique_strengths,
            areas_for_improvement=unique_growth,
            recommendation=recommendation,
            detailed_feedback=detailed_feedback,
            score_statistics=score_stats
        )

    async def _get_completion_message(self, session: InterviewSession) -> str:
        """Get behavioral completion message"""
        # FIX: C-B3 — Include competency coverage in completion
        covered = set(session.competencies_covered)
        coverage_pct = (
            int(len(covered) / len(TARGET_COMPETENCIES) * 100)
            if TARGET_COMPETENCIES else 0
        )

        return f"""Excellent! You've completed the Behavioral Interview! 🌟

I've assessed your responses using the STAR method across several competency areas.

Competency coverage: {coverage_pct}% ({len(covered)}/{len(TARGET_COMPETENCIES)} areas)

Your detailed feedback with STAR scores is being generated.

In a real interview, your specific examples and the way you structured your answers would be key factors in the evaluation.

Well done!"""


# FIX: F-A2 (Sprint 5) — Thread-safe singleton
@lru_cache(maxsize=1)
def get_behavioral_interview_service(session_store=None) -> BehavioralInterviewService:
    """Get the singleton behavioral interview service (thread-safe)"""
    return BehavioralInterviewService(session_store=session_store)
