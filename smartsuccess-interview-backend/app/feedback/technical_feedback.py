"""
Technical Feedback Service
AI/ML Engineering skills evaluation
"""

import os
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from app.config import settings
from app.prompts.technical_prompts import TECHNICAL_EVALUATION_PROMPT


class TechnicalFeedbackService:
    """
    Feedback service for technical interviews
    
    Evaluates:
    - Technical accuracy
    - Depth of knowledge
    - Practical experience
    - System thinking
    - Communication clarity
    """
    
    HIRE_SIGNALS = ["strong", "moderate", "weak", "no"]
    
    def __init__(self):
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
    
    async def evaluate_response(
        self,
        question: str,
        response: str,
        domain: str = "general",
        criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a technical interview response
        
        Returns scores, knowledge gaps, and hire signal
        """
        if not self.llm_client:
            return self._default_evaluation(domain)
        
        try:
            prompt = TECHNICAL_EVALUATION_PROMPT.format(
                domain=domain,
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
            
            eval_result = json.loads(content)
            eval_result["domain"] = domain
            return eval_result
            
        except Exception as e:
            print(f"Technical evaluation error: {e}")
            return self._default_evaluation(domain)
    
    def _default_evaluation(self, domain: str = "general") -> Dict[str, Any]:
        """Default evaluation when LLM unavailable"""
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
            "domain": domain
        }
    
    def calculate_overall_score(self, evaluation: Dict[str, Any]) -> float:
        """Calculate overall technical score"""
        score_keys = [
            "technical_accuracy",
            "depth_of_knowledge",
            "practical_experience",
            "system_thinking",
            "communication_clarity"
        ]
        
        # Weighted scoring (accuracy and depth weighted more)
        weights = {
            "technical_accuracy": 0.25,
            "depth_of_knowledge": 0.25,
            "practical_experience": 0.20,
            "system_thinking": 0.15,
            "communication_clarity": 0.15
        }
        
        total = 0
        for key in score_keys:
            score = evaluation.get(key, 3)
            weight = weights.get(key, 0.2)
            total += score * weight
        
        return round(total, 2)
    
    def generate_technical_summary(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate aggregate technical analysis"""
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
        
        for eval_data in evaluations:
            for key in score_categories:
                if key in eval_data:
                    score_categories[key].append(eval_data[key])
            
            if eval_data.get("domain"):
                domains_covered.append(eval_data["domain"])
            
            if eval_data.get("hire_signal"):
                hire_signals.append(eval_data["hire_signal"])
            
            strengths.extend(eval_data.get("key_strengths", []))
            knowledge_gaps.extend(eval_data.get("knowledge_gaps", []))
        
        # Calculate averages
        averages = {}
        for key, scores in score_categories.items():
            averages[key] = round(sum(scores) / len(scores), 2) if scores else 3.0
        
        # Calculate overall
        overall = sum(averages.values()) / len(averages) if averages else 3.0
        
        # Determine consensus hire signal
        signal_counts = {s: hire_signals.count(s) for s in self.HIRE_SIGNALS}
        consensus_signal = max(signal_counts, key=signal_counts.get) if hire_signals else "moderate"
        
        return {
            "score_breakdown": averages,
            "overall_score": round(overall, 2),
            "domains_covered": list(set(domains_covered)),
            "domains_count": len(set(domains_covered)),
            "hire_signal_consensus": consensus_signal,
            "hire_signal_distribution": signal_counts,
            "top_strengths": list(dict.fromkeys(strengths))[:5],
            "knowledge_gaps": list(dict.fromkeys(knowledge_gaps))[:5]
        }
    
    def generate_recommendation(
        self,
        overall_score: float,
        technical_summary: Dict[str, Any]
    ) -> str:
        """Generate technical interview recommendation"""
        consensus = technical_summary.get("hire_signal_consensus", "moderate")
        domains = technical_summary.get("domains_count", 0)
        
        if overall_score >= 4.0 and consensus in ["strong", "moderate"]:
            return f"Strong Hire - Demonstrates deep technical expertise across {domains} domains"
        elif overall_score >= 3.5:
            gaps = technical_summary.get("knowledge_gaps", [])
            if gaps:
                return f"Hire - Good technical foundation, consider probing: {', '.join(gaps[:2])}"
            return "Hire - Solid technical knowledge with practical experience"
        elif overall_score >= 3.0:
            return "Maybe - Has potential but needs to strengthen technical depth"
        else:
            return "No Hire - Significant technical gaps or lacks hands-on experience"


# Singleton
_instance: Optional[TechnicalFeedbackService] = None


def get_technical_feedback_service() -> TechnicalFeedbackService:
    global _instance
    if _instance is None:
        _instance = TechnicalFeedbackService()
    return _instance
