"""
Behavioral Feedback Service
STAR method evaluation
"""

import os
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from app.config import settings
from app.prompts.behavioral_prompts import BEHAVIORAL_STAR_EVALUATION


class BehavioralFeedbackService:
    """
    Feedback service for behavioral interviews using STAR method
    
    Evaluates:
    - Situation clarity
    - Task definition
    - Action specificity
    - Result impact
    - Competencies demonstrated
    """
    
    def __init__(self):
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
    
    async def evaluate_response(
        self,
        question: str,
        response: str,
        star_method: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate a behavioral interview response using STAR method
        
        Returns STAR scores, competencies, and feedback
        """
        if not self.llm_client:
            return self._default_evaluation()
        
        try:
            prompt = BEHAVIORAL_STAR_EVALUATION.format(
                question=question,
                response=response
            )
            
            result = await self.llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            import json
            content = result.choices[0].message.content.strip()
            
            # Clean JSON
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Behavioral evaluation error: {e}")
            return self._default_evaluation()
    
    def _default_evaluation(self) -> Dict[str, Any]:
        """Default evaluation when LLM unavailable"""
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
    
    def calculate_star_average(self, star_scores: Dict[str, int]) -> float:
        """Calculate average STAR score"""
        scores = [
            star_scores.get("situation", 3),
            star_scores.get("task", 3),
            star_scores.get("action", 3),
            star_scores.get("result", 3)
        ]
        return sum(scores) / len(scores)
    
    def identify_missing_component(self, star_scores: Dict[str, int]) -> Optional[str]:
        """Identify which STAR component needs follow-up"""
        threshold = 3  # Score below this needs follow-up
        
        for component in ["situation", "task", "action", "result"]:
            if star_scores.get(component, 5) < threshold:
                return component
        
        return None
    
    def generate_star_summary(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate aggregate STAR analysis"""
        all_scores = {"situation": [], "task": [], "action": [], "result": []}
        competencies = []
        strengths = []
        growth_areas = []
        
        for eval_data in evaluations:
            star_scores = eval_data.get("star_scores", {})
            for key in all_scores:
                if key in star_scores:
                    all_scores[key].append(star_scores[key])
            
            if eval_data.get("primary_competency"):
                competencies.append(eval_data["primary_competency"])
            
            strengths.extend(eval_data.get("strengths", []))
            growth_areas.extend(eval_data.get("growth_areas", []))
        
        # Calculate averages
        averages = {}
        for key, scores in all_scores.items():
            averages[key] = round(sum(scores) / len(scores), 2) if scores else 3.0
        
        # Find strongest and weakest components
        sorted_components = sorted(averages.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "star_averages": averages,
            "overall_star_score": round(sum(averages.values()) / 4, 2),
            "strongest_component": sorted_components[0][0] if sorted_components else "action",
            "weakest_component": sorted_components[-1][0] if sorted_components else "result",
            "competencies_demonstrated": list(set(competencies)),
            "top_strengths": list(dict.fromkeys(strengths))[:5],
            "growth_areas": list(dict.fromkeys(growth_areas))[:5]
        }
    
    def generate_recommendation(
        self,
        overall_score: float,
        star_summary: Dict[str, Any]
    ) -> str:
        """Generate behavioral interview recommendation"""
        if overall_score >= 4.0:
            return "Strong behavioral performance - demonstrates excellent soft skills and STAR method mastery"
        elif overall_score >= 3.5:
            weak = star_summary.get("weakest_component", "detail")
            return f"Good behavioral responses - consider probing more on {weak} in follow-up"
        elif overall_score >= 3.0:
            return "Adequate behavioral responses - some STAR components need strengthening"
        else:
            return "Needs improvement - responses lack structure or specific examples"


# Singleton
_instance: Optional[BehavioralFeedbackService] = None


def get_behavioral_feedback_service() -> BehavioralFeedbackService:
    global _instance
    if _instance is None:
        _instance = BehavioralFeedbackService()
    return _instance
