"""
Screening Feedback Service
First impression evaluation
"""

import os
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from app.config import settings
from app.prompts.screening_prompts import SCREENING_EVALUATION_PROMPT


class ScreeningFeedbackService:
    """
    Feedback service for screening interviews
    
    Evaluates:
    - Communication clarity
    - Relevance
    - Confidence
    - Professionalism
    - Enthusiasm
    """
    
    def __init__(self):
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
    
    async def evaluate_response(
        self,
        question: str,
        response: str,
        criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a screening interview response
        
        Returns scores and feedback on communication and fit
        """
        if not self.llm_client:
            return self._default_evaluation()
        
        criteria = criteria or [
            "communication_clarity",
            "relevance",
            "confidence",
            "professionalism",
            "enthusiasm"
        ]
        
        try:
            prompt = SCREENING_EVALUATION_PROMPT.format(
                question=question,
                response=response
            )
            
            result = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            
            import json
            content = result.choices[0].message.content.strip()
            
            # Clean JSON if wrapped in code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Screening evaluation error: {e}")
            return self._default_evaluation()
    
    def _default_evaluation(self) -> Dict[str, Any]:
        """Default evaluation when LLM unavailable"""
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
    
    def calculate_overall_score(self, evaluation: Dict[str, Any]) -> float:
        """Calculate overall screening score"""
        score_keys = [
            "communication_clarity",
            "relevance",
            "confidence",
            "professionalism",
            "enthusiasm"
        ]
        
        scores = [evaluation.get(k, 3) for k in score_keys if k in evaluation]
        return sum(scores) / len(scores) if scores else 3.0
    
    def generate_recommendation(
        self,
        overall_score: float,
        evaluations: List[Dict[str, Any]]
    ) -> str:
        """Generate screening recommendation"""
        # Count first impressions
        impressions = [e.get("first_impression", "Neutral") for e in evaluations]
        positive_count = impressions.count("Positive")
        concerning_count = impressions.count("Concerning")
        
        if overall_score >= 4.0 and concerning_count == 0:
            return "Strong candidate - recommend moving to behavioral interview"
        elif overall_score >= 3.5 and concerning_count <= 1:
            return "Good potential - consider for next round"
        elif overall_score >= 3.0:
            return "Adequate - may proceed with some reservations"
        else:
            return "Concerns noted - recommend additional screening"


# Singleton
_instance: Optional[ScreeningFeedbackService] = None


def get_screening_feedback_service() -> ScreeningFeedbackService:
    global _instance
    if _instance is None:
        _instance = ScreeningFeedbackService()
    return _instance
