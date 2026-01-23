"""
Behavioral Interview RAG Service
Specialized for STAR method behavioral questions
"""

import os
import random
from typing import Optional, Dict, List
from openai import AsyncOpenAI

from .base_rag import BaseRAGService
from app.config import settings


class BehavioralRAGService(BaseRAGService):
    """
    RAG service for behavioral interviews using STAR method
    
    Focus areas:
    - Teamwork and collaboration
    - Problem-solving
    - Leadership and initiative
    - Adaptability and resilience
    - Communication
    """
    
    # STAR follow-up templates
    STAR_FOLLOW_UPS = {
        "situation": "Can you describe the specific situation or context in more detail?",
        "task": "What exactly was your role and responsibility in this situation?",
        "action": "What specific actions did you take? Walk me through the steps.",
        "result": "What was the outcome? How did you measure success?"
    }
    
    # Categories to rotate through
    QUESTION_CATEGORIES = [
        "teamwork",
        "problem_solving",
        "leadership",
        "deadline_management",
        "adaptability"
    ]
    
    def __init__(self):
        super().__init__("behavioral")
        
        # Initialize LLM
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
        
        # Build category index
        self._build_category_index()
    
    def _build_category_index(self):
        """Build an index of questions by category"""
        self.questions_by_category: Dict[str, List] = {}
        
        categories = self.question_bank.get("question_categories", {})
        for category, questions in categories.items():
            self.questions_by_category[category] = questions
    
    def get_all_questions(self) -> List[Dict]:
        """Get all behavioral questions from all categories"""
        questions = []
        for category_questions in self.questions_by_category.values():
            questions.extend(category_questions)
        return questions
    
    async def get_question(self, index: int) -> str:
        """Get a behavioral question, rotating through categories"""
        # Determine which category to use
        category_index = index % len(self.QUESTION_CATEGORIES)
        category = self.QUESTION_CATEGORIES[category_index]
        
        # Get questions for this category
        category_questions = self.questions_by_category.get(category, [])
        
        if category_questions:
            # Get specific question within category
            question_index = (index // len(self.QUESTION_CATEGORIES)) % len(category_questions)
            return category_questions[question_index].get("question", "")
        
        # Fallback
        all_questions = self.get_all_questions()
        if all_questions:
            return all_questions[index % len(all_questions)].get("question", "")
        
        return "Tell me about a challenge you faced working in a team. How did you handle it?"
    
    async def get_personalized_question(
        self,
        session,
        index: int
    ) -> str:
        """
        Generate a personalized behavioral question based on resume/JD context
        """
        # Get base question
        base_question = await self.get_question(index)
        
        # If no context or LLM, return base question
        if not (session.resume_text or session.job_description) or not self.llm_client:
            return base_question
        
        try:
            # Get relevant context
            resume_context = await self.query_context(
                session.user_id,
                "experience projects leadership teamwork achievements challenges",
                k=4
            )
            
            job_context = await self.get_job_context(session.user_id) if session.job_description else ""
            
            # Get questions already asked
            asked = session.questions_asked if hasattr(session, 'questions_asked') else []
            
            # Generate personalized question
            prompt = f"""You are a behavioral interviewer using the STAR method.

Based on the candidate's experience and the job requirements, generate a personalized behavioral question.

CANDIDATE EXPERIENCE:
{resume_context[:1500] if resume_context else "Not provided"}

JOB REQUIREMENTS:
{job_context[:1000] if job_context else "Not provided"}

BASE QUESTION TEMPLATE:
{base_question}

QUESTIONS ALREADY ASKED:
{chr(10).join(asked[-3:]) if asked else "None yet"}

Generate ONE behavioral question that:
1. Is based on the template but personalized to the candidate's experience
2. Focuses on past behavior that predicts future performance
3. Can be answered using the STAR method
4. Relates to skills needed for the job
5. Is different from questions already asked

Return ONLY the question, nothing else."""

            response = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            
            personalized = response.choices[0].message.content.strip()
            personalized = personalized.strip('"\'')
            
            if personalized and len(personalized) > 10:
                return personalized
            
            return base_question
            
        except Exception as e:
            print(f"Error generating personalized behavioral question: {e}")
            return base_question
    
    def get_star_follow_up(self, missing_component: str) -> str:
        """Get a STAR follow-up question for a missing component"""
        return self.STAR_FOLLOW_UPS.get(
            missing_component,
            "Can you tell me more about that situation?"
        )
    
    async def get_smart_follow_up(
        self,
        last_question: str,
        last_response: str,
        missing_component: str
    ) -> str:
        """
        Generate a contextual follow-up for missing STAR component
        """
        if not self.llm_client:
            return self.get_star_follow_up(missing_component)
        
        try:
            prompt = f"""The candidate's behavioral interview response was missing the {missing_component.upper()} component of the STAR method.

Original question: {last_question}
Their response: {last_response[:500]}

Generate a natural follow-up question to elicit the {missing_component}:
- For 'situation': Ask for more context/background
- For 'task': Ask what specifically was their responsibility
- For 'action': Ask what specific steps THEY took (not the team)
- For 'result': Ask about the outcome and impact

Return ONLY the follow-up question, keep it brief and natural."""

            response = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=75
            )
            
            follow_up = response.choices[0].message.content.strip()
            return follow_up if follow_up else self.get_star_follow_up(missing_component)
            
        except Exception:
            return self.get_star_follow_up(missing_component)
    
    def get_question_competencies(self, question_text: str) -> List[str]:
        """Get the competencies being assessed by a question"""
        for question in self.get_all_questions():
            if question.get("question") == question_text:
                return question.get("competencies", [])
        return []
    
    def get_question_star_prompts(self, question_text: str) -> Optional[Dict[str, str]]:
        """Get the STAR prompts for a specific question"""
        for question in self.get_all_questions():
            if question.get("question") == question_text:
                return question.get("star_prompts")
        return None


# Singleton instance
_behavioral_rag_instance: Optional[BehavioralRAGService] = None


def get_behavioral_rag_service() -> BehavioralRAGService:
    """Get the singleton behavioral RAG service"""
    global _behavioral_rag_instance
    if _behavioral_rag_instance is None:
        _behavioral_rag_instance = BehavioralRAGService()
    return _behavioral_rag_instance
