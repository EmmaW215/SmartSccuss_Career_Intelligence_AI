"""
Technical Interview RAG Service
Specialized for AI/ML engineering technical questions
"""

import os
import random
from typing import Optional, Dict, List
from openai import AsyncOpenAI

from .base_rag import BaseRAGService
from app.config import settings


class TechnicalRAGService(BaseRAGService):
    """
    RAG service for technical interviews
    
    Focus domains:
    - Python engineering
    - LLM frameworks (LangChain, LangGraph, etc.)
    - RAG architecture
    - ML production systems
    - Cloud deployment
    - Security and integration
    """
    
    # Technical domains to rotate through
    DOMAINS = [
        "python_engineering",
        "llm_frameworks",
        "rag_architecture",
        "ml_production",
        "cloud_deployment",
        "security",
        "integration",
        "debugging",
        "model_training",
        "concept_explanation"
    ]
    
    def __init__(self):
        super().__init__("technical")
        
        # Initialize LLM
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
        
        # Build domain index
        self._build_domain_index()
    
    def _build_domain_index(self):
        """Build an index of questions by domain"""
        self.questions_by_domain: Dict[str, List] = {}
        
        domains = self.question_bank.get("domains", {})
        for domain, questions in domains.items():
            self.questions_by_domain[domain] = questions
    
    def get_all_questions(self) -> List[Dict]:
        """Get all technical questions from all domains"""
        questions = []
        for domain_questions in self.questions_by_domain.values():
            questions.extend(domain_questions)
        return questions
    
    def get_available_domains(self) -> List[str]:
        """Get list of domains that have questions"""
        return [d for d in self.DOMAINS if d in self.questions_by_domain and self.questions_by_domain[d]]
    
    async def get_question(self, index: int, domain: Optional[str] = None) -> str:
        """
        Get a technical question
        
        Args:
            index: Question index
            domain: Optional specific domain to query
        """
        # If domain specified, get from that domain
        if domain and domain in self.questions_by_domain:
            domain_questions = self.questions_by_domain[domain]
            if domain_questions:
                q_index = index % len(domain_questions)
                return domain_questions[q_index].get("question", "")
        
        # Otherwise, rotate through domains
        available_domains = self.get_available_domains()
        if available_domains:
            domain_index = index % len(available_domains)
            domain = available_domains[domain_index]
            domain_questions = self.questions_by_domain.get(domain, [])
            
            if domain_questions:
                q_index = (index // len(available_domains)) % len(domain_questions)
                return domain_questions[q_index].get("question", "")
        
        # Fallback
        return "Would you consider yourself an expert-level Python engineer? Can you share examples of complex systems you've built?"
    
    async def get_personalized_question(
        self,
        session,
        index: int,
        domain: Optional[str] = None
    ) -> str:
        """
        Generate a personalized technical question based on resume/JD context
        """
        # Get base question
        base_question = await self.get_question(index, domain)
        
        # If no context or LLM, return base question
        if not (session.resume_text or session.job_description or session.matchwise_analysis) or not self.llm_client:
            return base_question
        
        try:
            # Get technical context from resume
            technical_context = await self.query_context(
                session.user_id,
                "technical skills programming languages frameworks tools technologies experience projects",
                k=5
            )
            
            job_context = await self.get_job_context(session.user_id) if session.job_description else ""
            
            # Get skills from MatchWise analysis if available
            skills = []
            if session.matchwise_analysis:
                skills = session.matchwise_analysis.get("matched_skills", [])
                skills.extend(session.matchwise_analysis.get("skill_gaps", []))
            
            # Get questions already asked
            asked = session.questions_asked if hasattr(session, 'questions_asked') else []
            
            # Generate personalized question
            prompt = f"""You are a senior technical interviewer assessing an AI/ML engineering candidate.

Based on the candidate's technical background and the job requirements, generate a personalized technical question.

CANDIDATE TECHNICAL BACKGROUND:
{technical_context[:1500] if technical_context else "Not provided"}

JOB TECHNICAL REQUIREMENTS:
{job_context[:1000] if job_context else "Not provided"}

CANDIDATE'S SKILLS:
{', '.join(skills) if skills else "Not analyzed"}

BASE QUESTION TEMPLATE:
{base_question}

QUESTIONS ALREADY ASKED:
{chr(10).join(asked[-3:]) if asked else "None yet"}

Generate ONE technical question that:
1. Is based on the template but personalized to the candidate's experience
2. Tests technical depth and practical experience
3. Allows the candidate to draw from their specific projects
4. Is appropriately challenging for their experience level
5. Is different from questions already asked

Return ONLY the question, nothing else."""

            response = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200
            )
            
            personalized = response.choices[0].message.content.strip()
            personalized = personalized.strip('"\'')
            
            if personalized and len(personalized) > 15:
                return personalized
            
            return base_question
            
        except Exception as e:
            print(f"Error generating personalized technical question: {e}")
            return base_question
    
    async def get_follow_up_question(
        self,
        last_question: str,
        last_response: str,
        domain: str
    ) -> Optional[str]:
        """
        Generate a technical follow-up to probe deeper
        """
        if not self.llm_client:
            return None
        
        # Find the question in our bank to get follow-ups
        for domain_questions in self.questions_by_domain.values():
            for question in domain_questions:
                if question.get("question") == last_question:
                    follow_ups = question.get("follow_ups", [])
                    if follow_ups:
                        return follow_ups[0]
        
        # Generate a dynamic follow-up
        try:
            prompt = f"""The candidate answered a technical question about {domain}.

Question: {last_question}
Response: {last_response[:500]}

Generate a brief technical follow-up question that:
1. Probes deeper into their answer
2. Tests practical understanding
3. Asks about trade-offs or alternatives

Return ONLY the follow-up question, keep it brief."""

            response = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=75
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception:
            return None
    
    def get_question_metadata(self, question_text: str) -> Dict:
        """Get metadata about a specific question"""
        for domain, questions in self.questions_by_domain.items():
            for question in questions:
                if question.get("question") == question_text:
                    return {
                        "domain": domain,
                        "type": question.get("type", ""),
                        "difficulty": question.get("difficulty", "intermediate"),
                        "expected_topics": question.get("expected_topics", []),
                        "key_concepts": question.get("key_concepts", []),
                        "evaluation_criteria": question.get("evaluation_criteria", [])
                    }
        return {}
    
    def get_domain_for_question_index(self, index: int) -> str:
        """Get which domain a question index corresponds to"""
        available_domains = self.get_available_domains()
        if available_domains:
            return available_domains[index % len(available_domains)]
        return "general"


# Singleton instance
_technical_rag_instance: Optional[TechnicalRAGService] = None


def get_technical_rag_service() -> TechnicalRAGService:
    """Get the singleton technical RAG service"""
    global _technical_rag_instance
    if _technical_rag_instance is None:
        _technical_rag_instance = TechnicalRAGService()
    return _technical_rag_instance
