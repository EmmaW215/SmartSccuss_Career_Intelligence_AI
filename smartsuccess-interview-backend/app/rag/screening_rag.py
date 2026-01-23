"""
Screening Interview RAG Service
Specialized for first-impression assessment questions
"""

import os
from typing import Optional
from openai import AsyncOpenAI

from .base_rag import BaseRAGService
from app.config import settings


class ScreeningRAGService(BaseRAGService):
    """
    RAG service for screening interviews
    
    Focus areas:
    - Self-introduction
    - Motivation and interest
    - Basic fit assessment
    - Communication evaluation
    """
    
    def __init__(self):
        super().__init__("screening")
        
        # Initialize LLM for personalized question generation
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
    
    async def get_question(self, index: int) -> str:
        """Get a screening question by index"""
        question = self.get_question_by_index(index)
        if question:
            return question.get("question", "")
        
        # Fallback questions if index out of range
        fallback_questions = [
            "Tell me about yourself.",
            "Why are you interested in this role?",
            "Why did you leave (or are considering leaving) your last job?",
            "Why do you think you are the best fit for this role?",
            "What would you do if you were assigned a task you've never done before?"
        ]
        
        return fallback_questions[index % len(fallback_questions)]
    
    async def get_personalized_question(
        self,
        session,
        index: int
    ) -> str:
        """
        Generate a personalized screening question based on resume/JD context
        """
        # Get base question
        base_question = await self.get_question(index)
        
        # If no context or LLM, return base question
        if not (session.resume_text or session.job_description) or not self.llm_client:
            return base_question
        
        try:
            # Get relevant context
            resume_context = await self.get_resume_context(session.user_id) if session.resume_text else ""
            job_context = await self.get_job_context(session.user_id) if session.job_description else ""
            
            # Get questions already asked
            asked = session.questions_asked if hasattr(session, 'questions_asked') else []
            
            # Generate personalized question
            prompt = f"""You are a professional HR screener conducting a brief phone interview.

Based on the candidate's resume and job requirements, generate a personalized screening question.

CANDIDATE RESUME HIGHLIGHTS:
{resume_context[:1500] if resume_context else "Not provided"}

JOB REQUIREMENTS:
{job_context[:1000] if job_context else "Not provided"}

BASE QUESTION TO PERSONALIZE:
{base_question}

QUESTIONS ALREADY ASKED:
{', '.join(asked[-3:]) if asked else "None yet"}

Generate ONE screening question that:
1. Is based on the template but personalized to the candidate
2. Is appropriate for a 10-15 minute phone screen
3. Assesses communication skills or motivation
4. Is conversational and NOT deeply technical
5. Is different from questions already asked

Return ONLY the question, nothing else."""

            response = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            
            personalized = response.choices[0].message.content.strip()
            
            # Clean up the response
            personalized = personalized.strip('"\'')
            
            # Validate it looks like a question
            if personalized and len(personalized) > 10:
                return personalized
            
            return base_question
            
        except Exception as e:
            print(f"Error generating personalized screening question: {e}")
            return base_question
    
    async def get_follow_up_question(self, last_question: str, last_response: str) -> Optional[str]:
        """
        Generate a follow-up question if the response was too brief
        """
        if not self.llm_client:
            return None
        
        # Find the question in our bank to get follow-ups
        for question in self.get_all_questions():
            if question.get("question") == last_question:
                follow_ups = question.get("follow_ups", [])
                if follow_ups:
                    # Return a relevant follow-up
                    return follow_ups[0]
        
        # Generate a dynamic follow-up
        try:
            prompt = f"""The candidate gave a brief response to a screening question.
            
Question: {last_question}
Response: {last_response}

Generate a brief, natural follow-up question to get more detail. 
Return ONLY the follow-up question."""

            response = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception:
            return None


# Singleton instance
_screening_rag_instance: Optional[ScreeningRAGService] = None


def get_screening_rag_service() -> ScreeningRAGService:
    """Get the singleton screening RAG service"""
    global _screening_rag_instance
    if _screening_rag_instance is None:
        _screening_rag_instance = ScreeningRAGService()
    return _screening_rag_instance
