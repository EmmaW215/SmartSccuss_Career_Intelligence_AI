"""
Technical Interview Service
AI/ML Engineering Skills Assessment (45 minutes)
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
    TechnicalFeedback,
    QuestionResponse
)
from app.rag.technical_rag import TechnicalRAGService, get_technical_rag_service
from app.config import settings


class TechnicalInterviewService(BaseInterviewService):
    """
    Technical Interview Service
    
    Purpose: Assess technical skills and knowledge
    Duration: 45 minutes
    Focus: AI/ML engineering, system design, practical experience
    """
    
    interview_type = InterviewType.TECHNICAL
    max_questions = settings.technical_max_questions
    duration_limit_minutes = settings.technical_duration_minutes
    
    def __init__(self, session_store=None):
        super().__init__(session_store=session_store)
        
        # Initialize RAG service
        self.rag_service = get_technical_rag_service()
        
        # Initialize LLM for evaluation
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
        
        # Track current domain for follow-ups
        self.current_domain: Dict[str, str] = {}
    
    async def get_greeting(self) -> str:
        """Return technical interview greeting"""
        return """Welcome to your Technical Interview! 🔧

This is a 45-minute deep-dive into your technical skills and experience.

We'll cover:
• AI/ML Engineering concepts
• System architecture and design
• Production ML experience
• Cloud deployment
• Problem-solving and debugging

Feel free to:
✓ Ask clarifying questions
✓ Think out loud
✓ Draw on your real project experience
✓ Discuss trade-offs and alternatives

Let's start:

Would you consider yourself an expert-level Python engineer? Can you share examples of complex systems you've built with Python?"""
    
    async def _build_context(self, session: InterviewSession) -> None:
        """Build RAG context from resume and job description"""
        await self.rag_service.build_user_context(
            user_id=session.user_id,
            resume_text=session.resume_text,
            job_description=session.job_description
        )
    
    async def _get_next_question(self, session: InterviewSession) -> str:
        """Get the next technical question"""
        # Determine current domain
        domain = self.rag_service.get_domain_for_question_index(session.current_question_index)
        self.current_domain[session.session_id] = domain
        
        # Use personalized question if we have context
        if session.resume_text or session.job_description or session.matchwise_analysis:
            return await self.rag_service.get_personalized_question(
                session,
                session.current_question_index,
                domain=domain
            )
        
        # Otherwise use standard question
        return await self.rag_service.get_question(session.current_question_index, domain)
    
    async def _evaluate_response(
        self,
        session: InterviewSession,
        response: str
    ) -> Dict[str, Any]:
        """Evaluate a technical response"""
        current_question = session.questions_asked[-1] if session.questions_asked else ""
        domain = self.current_domain.get(session.session_id, "general")
        
        # Get question metadata
        metadata = self.rag_service.get_question_metadata(current_question)
        expected_topics = metadata.get("expected_topics", [])
        key_concepts = metadata.get("key_concepts", [])
        
        if not self.llm_client:
            return self._default_evaluation()
        
        try:
            prompt = f"""Evaluate this technical interview response.

Domain: {domain}
Question: {current_question}
Response: {response}

Expected topics/concepts: {', '.join(expected_topics + key_concepts) if expected_topics or key_concepts else 'General technical knowledge'}

Evaluation criteria (rate each 1-5):

1. Technical Accuracy (1-5):
   - Are the facts and concepts correct?
   - Any misconceptions or errors?

2. Depth of Knowledge (1-5):
   - Surface-level or deep understanding?
   - Can they explain the "why" behind concepts?

3. Practical Experience (1-5):
   - Did they reference real projects?
   - Do examples sound authentic?

4. System Thinking (1-5):
   - Do they consider trade-offs?
   - Can they see the bigger picture?

5. Communication Clarity (1-5):
   - Can they explain complex concepts clearly?
   - Is the answer structured?

Provide your evaluation in this exact JSON format:
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
            
            eval_result = json.loads(result)
            eval_result["domain"] = domain
            return eval_result
            
        except Exception as e:
            print(f"Technical evaluation error: {e}")
            return self._default_evaluation()
    
    def _default_evaluation(self) -> Dict[str, Any]:
        """Return default evaluation when LLM is unavailable"""
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
            "domain": "general"
        }
    
    async def _check_follow_up(
        self,
        session: InterviewSession,
        evaluation: Dict[str, Any]
    ) -> Optional[str]:
        """Check if we need a technical follow-up"""
        # Follow up if there are interesting topics to probe
        follow_up_topics = evaluation.get("follow_up_topics", [])
        
        if follow_up_topics and len(session.questions_asked) < self.max_questions:
            # Only follow up occasionally (every other question)
            if session.current_question_index % 2 == 0:
                domain = evaluation.get("domain", "general")
                last_question = session.questions_asked[-1] if session.questions_asked else ""
                last_response = session.responses[-1].get("response", "") if session.responses else ""
                
                return await self.rag_service.get_follow_up_question(
                    last_question,
                    last_response,
                    domain
                )
        
        return None
    
    async def _generate_summary(self, session: InterviewSession) -> SessionSummary:
        """Generate technical interview summary"""
        # Aggregate technical scores
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
        for key, scores in score_categories.items():
            if scores:
                score_breakdown[key] = round(sum(scores) / len(scores), 2)
            else:
                score_breakdown[key] = 3.0
        
        # Overall score
        overall_score = sum(score_breakdown.values()) / len(score_breakdown) if score_breakdown else 3.0
        
        # Calculate duration
        duration = 0
        if session.started_at and session.completed_at:
            duration = (session.completed_at - session.started_at).total_seconds() / 60
        
        # Determine recommendation based on scores and hire signals
        strong_count = hire_signals.count("strong")
        moderate_count = hire_signals.count("moderate")
        weak_count = hire_signals.count("weak") + hire_signals.count("no")
        
        if overall_score >= 4.0 and strong_count >= moderate_count:
            recommendation = "Strong Hire - Demonstrates deep technical expertise and practical experience"
        elif overall_score >= 3.5:
            recommendation = "Hire - Good technical foundation with solid practical knowledge"
        elif overall_score >= 3.0:
            recommendation = "Maybe - Has potential but some technical gaps to address"
        else:
            recommendation = "No Hire - Significant technical gaps or lacks hands-on experience"
        
        # Remove duplicates and limit
        unique_strengths = list(dict.fromkeys(strengths))[:5]
        unique_gaps = list(dict.fromkeys(knowledge_gaps))[:5]
        
        # Add domains covered to score breakdown
        score_breakdown["domains_covered"] = len(set(domains_covered))
        
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
            detailed_feedback=detailed_feedback
        )
    
    async def _get_completion_message(self, session: InterviewSession) -> str:
        """Get technical completion message"""
        return """You've completed the Technical Interview! 🚀

I've assessed your technical abilities across:
• AI/ML Engineering
• System Architecture
• Production Experience
• Cloud Deployment
• Problem-Solving

Your detailed technical scorecard is being generated, including:
- Technical accuracy ratings
- Depth of knowledge assessment
- Practical experience evaluation
- Areas for improvement

Great technical discussion!"""


# Singleton instance
_technical_service_instance: Optional[TechnicalInterviewService] = None


def get_technical_interview_service(session_store=None) -> TechnicalInterviewService:
    """Get the singleton technical interview service"""
    global _technical_service_instance
    if _technical_service_instance is None:
        _technical_service_instance = TechnicalInterviewService(session_store=session_store)
    elif session_store and not _technical_service_instance.session_store:
        # Update session_store if provided and not already set
        _technical_service_instance.session_store = session_store
    return _technical_service_instance
