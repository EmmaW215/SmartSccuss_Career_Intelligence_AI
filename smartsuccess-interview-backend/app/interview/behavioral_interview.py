"""
Behavioral Interview Service
STAR method assessment (25-30 minutes)
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
    BehavioralFeedback,
    STARScore,
    QuestionResponse
)
from app.rag.behavioral_rag import BehavioralRAGService, get_behavioral_rag_service
from app.config import settings


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
    
    def __init__(self):
        super().__init__()
        
        # Initialize RAG service
        self.rag_service = get_behavioral_rag_service()
        
        # Initialize LLM for evaluation
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
        
        # Track follow-ups to avoid infinite loops
        self.follow_up_count: Dict[str, int] = {}
    
    async def get_greeting(self) -> str:
        """Return behavioral interview greeting"""
        return """Welcome to your Behavioral Interview! 💼

This is a 25-30 minute session where we'll explore how you've handled real situations in the past.

I'll be using the STAR method:
• **S**ituation - Describe the context
• **T**ask - Explain your responsibility  
• **A**ction - Detail what YOU did
• **R**esult - Share the outcome

Tips for success:
✓ Use specific examples from your experience
✓ Focus on YOUR actions, not the team's
✓ Quantify results when possible

Let's start with a teamwork question:

Tell me about a challenge you faced working in a team. How did you handle it?"""
    
    async def _build_context(self, session: InterviewSession) -> None:
        """Build RAG context from resume and job description"""
        await self.rag_service.build_user_context(
            user_id=session.user_id,
            resume_text=session.resume_text,
            job_description=session.job_description
        )
    
    async def _get_next_question(self, session: InterviewSession) -> str:
        """Get the next behavioral question"""
        # Reset follow-up counter for new question
        self.follow_up_count[session.session_id] = 0
        
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
        """Evaluate a behavioral response using STAR method"""
        current_question = session.questions_asked[-1] if session.questions_asked else ""
        
        if not self.llm_client:
            return self._default_evaluation()
        
        try:
            prompt = f"""Evaluate this behavioral interview response using the STAR method.

Question: {current_question}
Response: {response}

STAR Analysis (rate each 1-5):

1. Situation (1-5):
   - Was the context clearly described?
   - Was it a real, specific example?
   
2. Task (1-5):
   - Was their role clearly defined?
   - Did they own the responsibility?

3. Action (1-5):
   - Did they describe THEIR specific actions?
   - Were the steps logical and detailed?
   - Did they say "I" not just "we"?

4. Result (1-5):
   - Was there a clear outcome?
   - Were results quantified if possible?
   - Did they reflect on learnings?

Provide your evaluation in this exact JSON format:
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
}}

Return ONLY the JSON, no other text."""

            response_obj = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            
            import json
            result = response_obj.choices[0].message.content.strip()
            
            # Clean up JSON
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            
            return json.loads(result)
            
        except Exception as e:
            print(f"STAR evaluation error: {e}")
            return self._default_evaluation()
    
    def _default_evaluation(self) -> Dict[str, Any]:
        """Return default evaluation when LLM is unavailable"""
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
            "follow_up_needed": "none"
        }
    
    async def _check_follow_up(
        self,
        session: InterviewSession,
        evaluation: Dict[str, Any]
    ) -> Optional[str]:
        """Check if we need a STAR follow-up"""
        # Limit follow-ups per question
        session_id = session.session_id
        current_count = self.follow_up_count.get(session_id, 0)
        
        if current_count >= 2:  # Max 2 follow-ups per question
            return None
        
        follow_up_needed = evaluation.get("follow_up_needed", "none")
        
        if follow_up_needed and follow_up_needed != "none":
            self.follow_up_count[session_id] = current_count + 1
            
            # Get smart follow-up
            last_question = session.questions_asked[-1] if session.questions_asked else ""
            last_response = session.responses[-1].get("response", "") if session.responses else ""
            
            return await self.rag_service.get_smart_follow_up(
                last_question,
                last_response,
                follow_up_needed
            )
        
        return None
    
    async def _generate_summary(self, session: InterviewSession) -> SessionSummary:
        """Generate behavioral interview summary"""
        # Aggregate STAR scores
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
        for key, scores in all_star_scores.items():
            if scores:
                score_breakdown[f"star_{key}"] = sum(scores) / len(scores)
            else:
                score_breakdown[f"star_{key}"] = 3.0
        
        # Overall STAR score
        star_values = list(score_breakdown.values())
        overall_score = sum(star_values) / len(star_values) if star_values else 3.0
        
        # Calculate duration
        duration = 0
        if session.started_at and session.completed_at:
            duration = (session.completed_at - session.started_at).total_seconds() / 60
        
        # Determine recommendation
        if overall_score >= 4.0:
            recommendation = "Strong behavioral performance - demonstrates excellent soft skills and STAR method mastery"
        elif overall_score >= 3.5:
            recommendation = "Good behavioral responses - solid examples with room for more detail"
        elif overall_score >= 3.0:
            recommendation = "Adequate behavioral responses - some STAR components could be stronger"
        else:
            recommendation = "Needs improvement - responses lack structure or specific examples"
        
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
            detailed_feedback=detailed_feedback
        )
    
    async def _get_completion_message(self, session: InterviewSession) -> str:
        """Get behavioral completion message"""
        return """Excellent! You've completed the Behavioral Interview! 🌟

I've assessed your responses using the STAR method across several competency areas:
• Teamwork & Collaboration
• Problem-Solving
• Leadership & Initiative
• Communication

Your detailed feedback with STAR scores is being generated. 

In a real interview, your specific examples and the way you structured your answers would be key factors in the evaluation.

Well done!"""


# Singleton instance
_behavioral_service_instance: Optional[BehavioralInterviewService] = None


def get_behavioral_interview_service() -> BehavioralInterviewService:
    """Get the singleton behavioral interview service"""
    global _behavioral_service_instance
    if _behavioral_service_instance is None:
        _behavioral_service_instance = BehavioralInterviewService()
    return _behavioral_service_instance
