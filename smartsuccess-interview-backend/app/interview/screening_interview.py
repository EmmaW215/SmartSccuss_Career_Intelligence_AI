"""
Screening Interview Service
First impression assessment (10-15 minutes)
"""

import os
from typing import Dict, Optional, Any
from datetime import datetime
from openai import AsyncOpenAI

from .base_interview import BaseInterviewService
from app.models import (
    InterviewSession,
    InterviewType,
    SessionSummary,
    ScreeningFeedback,
    QuestionResponse
)
from app.rag.screening_rag import ScreeningRAGService, get_screening_rag_service
from app.config import settings


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
    
    def __init__(self):
        super().__init__()
        
        # Initialize RAG service
        self.rag_service = get_screening_rag_service()
        
        # Initialize LLM for evaluation
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
    
    async def get_greeting(self) -> str:
        """Return screening interview greeting"""
        return """Welcome to your Screening Interview! 🎯

I'm your AI interviewer today. This is a brief 10-15 minute conversation where I'll get to know you better and understand your interest in this role.

We'll cover:
• A quick self-introduction
• Your motivation for this role
• Why you're the right fit

Remember, this is like a first conversation - be yourself and speak naturally!

Let's begin. Please tell me about yourself."""
    
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
        """Evaluate a screening response"""
        current_question = session.questions_asked[-1] if session.questions_asked else "Tell me about yourself"
        
        if not self.llm_client:
            # Return default scores if no LLM
            return {
                "communication_clarity": 3,
                "relevance": 3,
                "confidence": 3,
                "professionalism": 3,
                "enthusiasm": 3,
                "strength": "Good effort",
                "improvement": "Could provide more detail",
                "first_impression": "Neutral"
            }
        
        try:
            prompt = f"""Evaluate this screening interview response.

Question: {current_question}
Response: {response}

Evaluate on these criteria (1-5 scale):
1. Communication Clarity - How clearly did they express themselves?
2. Relevance - Did they answer the question directly?
3. Confidence - Did they sound confident without being arrogant?
4. Professionalism - Was the tone appropriate?
5. Enthusiasm - Did they show genuine interest?

Provide your evaluation in this exact JSON format:
{{
  "communication_clarity": <1-5>,
  "relevance": <1-5>,
  "confidence": <1-5>,
  "professionalism": <1-5>,
  "enthusiasm": <1-5>,
  "strength": "<one specific strength observed>",
  "improvement": "<one specific area for improvement>",
  "first_impression": "<Positive|Neutral|Concerning>"
}}

Return ONLY the JSON, no other text."""

            response_obj = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            import json
            result = response_obj.choices[0].message.content.strip()
            
            # Clean up JSON if needed
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            
            return json.loads(result)
            
        except Exception as e:
            print(f"Evaluation error: {e}")
            return {
                "communication_clarity": 3,
                "relevance": 3,
                "confidence": 3,
                "professionalism": 3,
                "enthusiasm": 3,
                "strength": "Response recorded",
                "improvement": "Evaluation unavailable",
                "first_impression": "Neutral"
            }
    
    async def _check_follow_up(
        self,
        session: InterviewSession,
        evaluation: Dict[str, Any]
    ) -> Optional[str]:
        """Check if we need a follow-up (usually not for screening)"""
        # Screening interviews typically don't do follow-ups to keep them brief
        # But if response was very short, we might ask for more
        if session.responses:
            last_response = session.responses[-1].get("response", "")
            if len(last_response.split()) < 20:  # Very brief response
                return await self.rag_service.get_follow_up_question(
                    session.questions_asked[-1] if session.questions_asked else "",
                    last_response
                )
        return None
    
    async def _generate_summary(self, session: InterviewSession) -> SessionSummary:
        """Generate screening interview summary"""
        # Calculate scores
        total_scores = {
            "communication_clarity": [],
            "relevance": [],
            "confidence": [],
            "professionalism": [],
            "enthusiasm": []
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
        for key, scores in total_scores.items():
            if scores:
                score_breakdown[key] = sum(scores) / len(scores)
            else:
                score_breakdown[key] = 3.0
        
        overall_score = sum(score_breakdown.values()) / len(score_breakdown) if score_breakdown else 3.0
        
        # Calculate duration
        duration = 0
        if session.started_at and session.completed_at:
            duration = (session.completed_at - session.started_at).total_seconds() / 60
        
        # Determine recommendation
        if overall_score >= 4.0:
            recommendation = "Strong candidate - recommend moving to behavioral interview"
        elif overall_score >= 3.0:
            recommendation = "Adequate screening - consider for next round with some reservations"
        else:
            recommendation = "Some concerns noted - recommend additional screening or pass"
        
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
            detailed_feedback=detailed_feedback
        )
    
    async def _get_completion_message(self, session: InterviewSession) -> str:
        """Get screening completion message"""
        return """Thank you for completing the Screening Interview! 🎉

You've given me a great first impression. I've noted your background, motivation, and how you'd fit with this role.

Your feedback summary is being prepared. In a real interview process, this would be the first step before moving to behavioral or technical rounds.

Great job!"""


# Singleton instance
_screening_service_instance: Optional[ScreeningInterviewService] = None


def get_screening_interview_service() -> ScreeningInterviewService:
    """Get the singleton screening interview service"""
    global _screening_service_instance
    if _screening_service_instance is None:
        _screening_service_instance = ScreeningInterviewService()
    return _screening_service_instance
