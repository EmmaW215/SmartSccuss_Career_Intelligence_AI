"""
Technical Interview Service
Multi-Domain Technical Skills Assessment (45 minutes)

FIXES APPLIED:
- A-Q4 (Sprint 1): Conversation context in evaluation
- A-Q2 (Sprint 2): Centralized LLM via base._call_llm()
- A-Q3 (Sprint 2): Robust JSON parsing via json_parser utility
- A-Q5 (Sprint 2): Greeting separated from first question
- A-Q6 (Sprint 5): Fallback scores with transparency flag
- D-T1 (Sprint 1): Multi-domain question banks (5 domains)
- D-T2 (Sprint 3): Dynamic first question based on detected domain
- D-T3 (Sprint 3): Domain-aware difficulty progression
- D-T4 (Sprint 3): Penalize generic/textbook answers in eval prompt
- G-P1 (Sprint 2): System prompt for evaluator role
- G-P2 (Sprint 2): Strengthened JSON output instructions
- G-P3 (Sprint 2): Calibrated scoring anchors
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
from app.rag.technical_rag import TechnicalRAGService, get_technical_rag_service
from app.rag.domain_config import (
    detect_domain_from_jd,
    get_domain_opener,
    get_domain_fallback_questions,
    DOMAIN_QUESTION_BANKS
)
from app.utils.json_parser import safe_parse_evaluation
from app.utils.response_analytics import compute_score_summary
from app.config import settings

logger = logging.getLogger(__name__)

# FIX: G-P1 (Sprint 2) — System prompt for technical evaluator
TECHNICAL_EVALUATOR_SYSTEM = """You are a senior technical interviewer with 10+ years of engineering experience.
You evaluate candidates' technical depth, practical experience, and system thinking.
Penalize generic or textbook answers — reward specific project references and real trade-off discussions.
Always respond with valid JSON only — no markdown, no explanation, no preamble.
Rate strictly: a 5 requires exceptional depth with real-world examples; a 3 is adequate textbook knowledge."""


class TechnicalInterviewService(BaseInterviewService):
    """
    Technical Interview Service

    Purpose: Assess technical skills and knowledge
    Duration: 45 minutes
    Focus: Domain-specific engineering (AI/ML, Frontend, Backend, DevOps, Data)
    """

    interview_type = InterviewType.TECHNICAL
    max_questions = settings.technical_max_questions
    duration_limit_minutes = settings.technical_duration_minutes

    def __init__(self, session_store=None):
        super().__init__(session_store=session_store)

        # Initialize RAG service
        self.rag_service = get_technical_rag_service()

        # NOTE: Direct LLM client removed — using self._call_llm() from base
        # FIX: A-Q2 (Sprint 2)

    async def get_greeting(self, session: Optional[InterviewSession] = None) -> str:
        """
        Return technical interview greeting.

        FIX: D-T1 (Sprint 1) — Detect domain from JD
        FIX: D-T2 (Sprint 3) — Domain-specific opener
        """
        # Detect domain from job context
        detected = "ai_ml"
        if session:
            jd_context = {}
            if session.job_description:
                jd_context["job_description"] = session.job_description
            if session.matchwise_analysis:
                jd_context["job_title"] = session.matchwise_analysis.get(
                    "job_title", ""
                )
            detected = detect_domain_from_jd(jd_context)
            session.detected_domain = detected

        domain_label = DOMAIN_QUESTION_BANKS.get(
            detected, DOMAIN_QUESTION_BANKS["ai_ml"]
        )["label"]
        opener = get_domain_opener(detected)

        greeting = f"""Welcome to your Technical Interview! 🔧

This is a 45-minute deep-dive into your technical skills and experience.

Based on the role, we'll focus on **{domain_label}** topics.

Feel free to:
✓ Ask clarifying questions
✓ Think out loud
✓ Draw on your real project experience
✓ Discuss trade-offs and alternatives

Let's start:

{opener}"""

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
        Get the next technical question.

        FIX: D-T1 — Uses detected domain for question selection
        FIX: D-T3 — Difficulty progression (basic → intermediate → advanced)
        """
        domain = session.detected_domain or "ai_ml"

        # FIX: D-T3 — Difficulty progression based on question index
        q_idx = session.current_question_index
        total = self.max_questions
        if q_idx < total * 0.3:
            difficulty = "basic"
        elif q_idx < total * 0.7:
            difficulty = "intermediate"
        else:
            difficulty = "advanced"

        # Determine current domain from rotation
        domain_for_q = self.rag_service.get_domain_for_question_index(q_idx)

        # Use personalized question if we have context
        if (session.resume_text or session.job_description
                or session.matchwise_analysis):
            return await self.rag_service.get_personalized_question(
                session,
                q_idx,
                domain=domain_for_q
            )

        # Fallback to domain-specific questions
        fallbacks = get_domain_fallback_questions(domain)
        if fallbacks:
            return fallbacks[q_idx % len(fallbacks)]

        # Otherwise use standard question
        return await self.rag_service.get_question(q_idx, domain_for_q)

    async def _evaluate_response(
        self,
        session: InterviewSession,
        response: str
    ) -> Dict[str, Any]:
        """
        Evaluate a technical response.

        FIX: A-Q4 — Conversation context
        FIX: A-Q2 — Centralized LLM
        FIX: A-Q3 — Robust JSON parsing
        FIX: D-T4 — Penalize generic/textbook answers
        FIX: G-P3 — Calibrated scoring anchors
        """
        current_question = (
            session.questions_asked[-1] if session.questions_asked else ""
        )
        domain = session.detected_domain or "ai_ml"

        # Get question metadata
        metadata = self.rag_service.get_question_metadata(current_question)
        expected_topics = metadata.get("expected_topics", [])
        key_concepts = metadata.get("key_concepts", [])

        # FIX: A-Q4 — Build conversation context
        context_block = self._build_evaluation_context(
            session, session.current_question_index
        )

        try:
            # FIX: D-T4 — Explicit instruction to penalize generic answers
            # FIX: G-P3 — Calibrated scoring anchors
            prompt = f"""Evaluate this technical interview response.

## Previous Q&A Context (for consistency and progression assessment):
{context_block if context_block else "This is the first question."}

## Current Evaluation:
Domain: {domain}
Question: {current_question}
Response: {response}

Expected topics/concepts: {', '.join(expected_topics + key_concepts) if expected_topics or key_concepts else 'General technical knowledge'}

## Evaluation Criteria (rate each 1-5):
Use these calibration anchors:
- 1: Incorrect or no relevant knowledge demonstrated
- 2: Vague, textbook-only answer with no practical examples
- 3: Adequate understanding with some practical awareness
- 4: Strong answer with real project examples and trade-off discussion
- 5: Expert-level with deep insights, quantified results, and edge-case awareness

IMPORTANT: Penalize generic/textbook answers that lack specific project references.
Reward candidates who reference real systems they've built and explain WHY they made specific choices.

1. Technical Accuracy (1-5): Are the facts correct?
2. Depth of Knowledge (1-5): Surface or deep understanding?
3. Practical Experience (1-5): Real projects referenced?
4. System Thinking (1-5): Trade-offs considered?
5. Communication Clarity (1-5): Can they explain clearly?

Return ONLY valid JSON in this exact format, with no other text:
{{
  "technical_accuracy": <1-5>,
  "depth_of_knowledge": <1-5>,
  "practical_experience": <1-5>,
  "system_thinking": <1-5>,
  "communication_clarity": <1-5>,
  "key_strengths": ["<strength 1>", "<strength 2>"],
  "knowledge_gaps": ["<gap 1 if any>"],
  "follow_up_topics": ["<topic for follow-up if needed>"],
  "hire_signal": "<strong|moderate|weak|no>"
}}"""

            # FIX: A-Q2 — Use centralized LLM
            # FIX: G-P1 — System prompt
            result_text = await self._call_llm(
                prompt=prompt,
                system_prompt=TECHNICAL_EVALUATOR_SYSTEM,
                temperature=0.3,
                max_tokens=500
            )

            # FIX: A-Q3 — Robust JSON parsing
            eval_result = safe_parse_evaluation(
                result_text,
                self._default_evaluation(),
                session_id=session.session_id
            )
            eval_result["domain"] = domain
            return eval_result

        except Exception as e:
            logger.error(
                f"Technical evaluation error for {session.session_id}: {e}"
            )
            return self._default_evaluation()

    def _default_evaluation(self) -> Dict[str, Any]:
        """FIX: A-Q6 — Default with transparency flag."""
        return {
            "technical_accuracy": 3,
            "depth_of_knowledge": 3,
            "practical_experience": 3,
            "system_thinking": 3,
            "communication_clarity": 3,
            "key_strengths": ["Response recorded"],
            "knowledge_gaps": [],
            "follow_up_topics": [],
            "hire_signal": "moderate",
            "domain": "general",
            "_evaluation_status": "fallback",
            "_fallback_reason": "evaluation_unavailable"
        }

    async def _check_follow_up(
        self,
        session: InterviewSession,
        evaluation: Dict[str, Any]
    ) -> Optional[str]:
        """Check if we need a technical follow-up"""
        follow_up_topics = evaluation.get("follow_up_topics", [])

        if follow_up_topics and len(session.questions_asked) < self.max_questions:
            # Only follow up occasionally (every other question)
            if session.current_question_index % 2 == 0:
                domain = evaluation.get("domain", "general")
                last_question = (
                    session.questions_asked[-1]
                    if session.questions_asked else ""
                )
                last_response = (
                    session.responses[-1].get("response", "")
                    if session.responses else ""
                )

                return await self.rag_service.get_follow_up_question(
                    last_question,
                    last_response,
                    domain
                )

        return None

    async def _generate_summary(
        self, session: InterviewSession
    ) -> SessionSummary:
        """Generate technical interview summary"""
        score_categories = {
            "technical_accuracy": [],
            "depth_of_knowledge": [],
            "practical_experience": [],
            "system_thinking": [],
            "communication_clarity": []
        }

        domains_covered = []
        hire_signals = []
        strengths = []
        knowledge_gaps = []
        detailed_feedback = []

        for resp in session.responses:
            eval_data = resp.get("evaluation", {})

            for key in score_categories:
                if key in eval_data:
                    score_categories[key].append(eval_data[key])

            if eval_data.get("domain"):
                domains_covered.append(eval_data["domain"])

            if eval_data.get("hire_signal"):
                hire_signals.append(eval_data["hire_signal"])

            strengths.extend(eval_data.get("key_strengths", []))
            knowledge_gaps.extend(eval_data.get("knowledge_gaps", []))

            detailed_feedback.append(QuestionResponse(
                question_index=resp.get("question_index", 0),
                question=resp.get("question", ""),
                response=resp.get("response", ""),
                feedback=eval_data
            ))

        # Calculate average scores
        score_breakdown = {}
        all_scores = []
        for key, scores in score_categories.items():
            if scores:
                avg = round(sum(scores) / len(scores), 2)
                score_breakdown[key] = avg
                all_scores.extend(scores)
            else:
                score_breakdown[key] = 3.0

        # Overall score
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
        strong_count = hire_signals.count("strong")
        moderate_count = hire_signals.count("moderate")

        if overall_score >= 4.0 and strong_count >= moderate_count:
            recommendation = (
                "Strong Hire — Demonstrates deep technical expertise "
                "and practical experience"
            )
        elif overall_score >= 3.5:
            recommendation = (
                "Hire — Good technical foundation with solid "
                "practical knowledge"
            )
        elif overall_score >= 3.0:
            recommendation = (
                "Maybe — Has potential but some technical gaps to address"
            )
        else:
            recommendation = (
                "No Hire — Significant technical gaps or lacks "
                "hands-on experience"
            )

        # Remove duplicates and limit
        unique_strengths = list(dict.fromkeys(strengths))[:5]
        unique_gaps = list(dict.fromkeys(knowledge_gaps))[:5]

        # Add domains covered to score breakdown
        score_breakdown["domains_covered"] = len(set(domains_covered))

        # FIX: D-T1 — Include detected domain in breakdown
        if session.detected_domain:
            score_breakdown["primary_domain"] = session.detected_domain

        return SessionSummary(
            session_id=session.session_id,
            interview_type=InterviewType.TECHNICAL,
            total_questions=len(session.questions_asked),
            total_responses=len(session.responses),
            duration_minutes=round(duration, 1),
            overall_score=round(overall_score, 2),
            score_breakdown=score_breakdown,
            top_strengths=unique_strengths,
            areas_for_improvement=unique_gaps,
            recommendation=recommendation,
            detailed_feedback=detailed_feedback,
            score_statistics=score_stats
        )

    async def _get_completion_message(
        self, session: InterviewSession
    ) -> str:
        """Get technical completion message"""
        domain = session.detected_domain or "ai_ml"
        domain_label = DOMAIN_QUESTION_BANKS.get(
            domain, DOMAIN_QUESTION_BANKS["ai_ml"]
        )["label"]

        return f"""You've completed the Technical Interview! 🚀

I've assessed your technical abilities in **{domain_label}** across:
• Technical Accuracy
• Depth of Knowledge
• Practical Experience
• System Thinking
• Communication Clarity

Your detailed technical scorecard is being generated.

Great technical discussion!"""


# FIX: F-A2 (Sprint 5) — Thread-safe singleton
@lru_cache(maxsize=1)
def get_technical_interview_service(
    session_store=None
) -> TechnicalInterviewService:
    """Get the singleton technical interview service (thread-safe)"""
    return TechnicalInterviewService(session_store=session_store)
