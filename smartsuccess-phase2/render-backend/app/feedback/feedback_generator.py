"""
Feedback Generator
Generates detailed interview feedback and scores
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from app.services.llm_service import get_llm_service


@dataclass
class QuestionFeedback:
    """Feedback for a single question"""
    question_index: int
    question: str
    user_response: str
    score: float  # 0-5
    strengths: List[str]
    improvements: List[str]
    

@dataclass
class InterviewFeedback:
    """Complete interview feedback"""
    session_id: str
    interview_type: str
    overall_score: float  # 0-100
    score_breakdown: Dict[str, float]
    strengths: List[str]
    areas_for_improvement: List[str]
    recommendations: List[str]
    question_feedback: List[Dict[str, Any]]
    generated_at: str


class FeedbackGenerator:
    """
    Generates comprehensive interview feedback
    
    Uses LLM to analyze responses and provide:
    - Overall score
    - Category breakdown (STAR for behavioral, etc.)
    - Specific strengths
    - Areas for improvement
    - Actionable recommendations
    """
    
    SCREENING_CRITERIA = ["communication", "relevance", "confidence", "professionalism"]
    BEHAVIORAL_CRITERIA = ["situation", "task", "action", "result", "clarity"]
    TECHNICAL_CRITERIA = ["accuracy", "depth", "problem_solving", "communication", "experience"]
    
    FEEDBACK_PROMPT = """Evaluate this interview response.

INTERVIEW TYPE: {interview_type}
QUESTION: {question}
CANDIDATE RESPONSE: {response}
EVALUATION CRITERIA: {criteria}

Provide evaluation as JSON:
{{
    "score": 0-5,
    "criteria_scores": {{"criterion1": 0-5, "criterion2": 0-5}},
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "brief_feedback": "1-2 sentence summary"
}}

Be constructive and specific. Return ONLY valid JSON."""

    OVERALL_FEEDBACK_PROMPT = """Generate overall interview feedback.

INTERVIEW TYPE: {interview_type}
RESPONSES: {responses_summary}
INDIVIDUAL SCORES: {scores}

Create comprehensive feedback as JSON:
{{
    "overall_score": 0-100,
    "score_breakdown": {{"category1": 0-5}},
    "top_strengths": ["strength1", "strength2", "strength3"],
    "areas_for_improvement": ["area1", "area2", "area3"],
    "recommendations": ["actionable tip 1", "actionable tip 2", "actionable tip 3"],
    "summary": "2-3 sentence overall assessment"
}}

Be encouraging but honest. Return ONLY valid JSON."""

    def __init__(self):
        self.llm_service = get_llm_service()
    
    async def generate_feedback(
        self,
        session_id: str,
        interview_type: str,
        responses: List[Dict[str, Any]]
    ) -> InterviewFeedback:
        """
        Generate complete interview feedback
        
        Args:
            session_id: Interview session ID
            interview_type: screening, behavioral, technical, customize
            responses: List of Q&A exchanges
            
        Returns:
            InterviewFeedback with scores and recommendations
        """
        # Get criteria for this interview type
        criteria = self._get_criteria(interview_type)
        
        # Generate feedback for each question
        question_feedback = []
        scores = []
        
        for i, response in enumerate(responses):
            q_feedback = await self._evaluate_response(
                interview_type=interview_type,
                question=response.get("question", ""),
                user_response=response.get("user_response", ""),
                criteria=criteria
            )
            question_feedback.append(q_feedback)
            scores.append(q_feedback.get("score", 3.0))
        
        # Generate overall feedback
        overall = await self._generate_overall(
            interview_type=interview_type,
            responses=responses,
            question_feedback=question_feedback,
            scores=scores
        )
        
        return InterviewFeedback(
            session_id=session_id,
            interview_type=interview_type,
            overall_score=overall.get("overall_score", 70),
            score_breakdown=overall.get("score_breakdown", {}),
            strengths=overall.get("top_strengths", []),
            areas_for_improvement=overall.get("areas_for_improvement", []),
            recommendations=overall.get("recommendations", []),
            question_feedback=question_feedback,
            generated_at=datetime.now().isoformat()
        )
    
    def _get_criteria(self, interview_type: str) -> List[str]:
        """Get evaluation criteria for interview type"""
        if interview_type == "screening":
            return self.SCREENING_CRITERIA
        elif interview_type == "behavioral":
            return self.BEHAVIORAL_CRITERIA
        elif interview_type in ("technical", "customize"):
            return self.TECHNICAL_CRITERIA
        return self.SCREENING_CRITERIA
    
    async def _evaluate_response(
        self,
        interview_type: str,
        question: str,
        user_response: str,
        criteria: List[str]
    ) -> Dict[str, Any]:
        """Evaluate a single response"""
        if not user_response or len(user_response.strip()) < 10:
            return {
                "score": 1.0,
                "criteria_scores": {c: 1.0 for c in criteria},
                "strengths": [],
                "improvements": ["Response was too brief"],
                "brief_feedback": "The response needs more detail."
            }
        
        prompt = self.FEEDBACK_PROMPT.format(
            interview_type=interview_type,
            question=question[:500],
            response=user_response[:1000],
            criteria=", ".join(criteria)
        )
        
        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=500
            )
            
            return self._parse_json(response, default={
                "score": 3.0,
                "criteria_scores": {c: 3.0 for c in criteria},
                "strengths": ["Provided a response"],
                "improvements": ["Consider adding more specific examples"],
                "brief_feedback": "Response covered the basics."
            })
            
        except Exception as e:
            print(f"Response evaluation error: {e}")
            return {
                "score": 3.0,
                "criteria_scores": {c: 3.0 for c in criteria},
                "strengths": ["Attempted to answer"],
                "improvements": ["Add more detail"],
                "brief_feedback": "Response noted."
            }
    
    async def _generate_overall(
        self,
        interview_type: str,
        responses: List[Dict[str, Any]],
        question_feedback: List[Dict[str, Any]],
        scores: List[float]
    ) -> Dict[str, Any]:
        """Generate overall feedback summary"""
        # Create summary
        responses_summary = "\n".join([
            f"Q{i+1}: {r.get('question', '')[:100]}...\nA: {r.get('user_response', '')[:200]}..."
            for i, r in enumerate(responses[:5])  # Limit to 5 for context
        ])
        
        scores_text = f"Individual scores: {scores}, Average: {sum(scores)/len(scores) if scores else 0:.1f}/5"
        
        prompt = self.OVERALL_FEEDBACK_PROMPT.format(
            interview_type=interview_type,
            responses_summary=responses_summary,
            scores=scores_text
        )
        
        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.4,
                max_tokens=800
            )
            
            result = self._parse_json(response)
            
            # Validate and normalize
            if "overall_score" not in result:
                avg_score = sum(scores) / len(scores) if scores else 3.0
                result["overall_score"] = min(100, max(0, avg_score * 20))
            
            return result
            
        except Exception as e:
            print(f"Overall feedback error: {e}")
            avg_score = sum(scores) / len(scores) if scores else 3.0
            
            return {
                "overall_score": min(100, max(0, avg_score * 20)),
                "score_breakdown": self._calculate_breakdown(question_feedback),
                "top_strengths": ["Completed the interview"],
                "areas_for_improvement": ["Practice giving more detailed responses"],
                "recommendations": ["Review your answers and prepare examples for common questions"],
                "summary": "Thank you for completing the interview."
            }
    
    def _calculate_breakdown(
        self,
        question_feedback: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate score breakdown from question feedback"""
        all_criteria = {}
        
        for qf in question_feedback:
            criteria_scores = qf.get("criteria_scores", {})
            for criterion, score in criteria_scores.items():
                if criterion not in all_criteria:
                    all_criteria[criterion] = []
                all_criteria[criterion].append(score)
        
        return {
            criterion: sum(scores) / len(scores)
            for criterion, scores in all_criteria.items()
            if scores
        }
    
    def _parse_json(
        self,
        text: str,
        default: Any = None
    ) -> Any:
        """Parse JSON from LLM response"""
        if default is None:
            default = {}
        
        try:
            text = text.strip()
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            text = text.strip()
            
            if text.startswith("{"):
                end = text.rfind("}") + 1
                text = text[:end]
            
            return json.loads(text)
            
        except (json.JSONDecodeError, IndexError, ValueError):
            return default
    
    def generate_quick_hint(
        self,
        response: str,
        question_type: str
    ) -> Dict[str, Any]:
        """Generate quick feedback hint (synchronous, no LLM)"""
        hints = []
        quality = "fair"
        
        word_count = len(response.split())
        
        if word_count < 20:
            hints.append("Response is brief - consider adding more detail")
            quality = "needs_improvement"
        elif word_count > 300:
            hints.append("Good detail - consider being more concise")
            quality = "good"
        else:
            quality = "good"
        
        # Check for specific elements
        if question_type == "behavioral":
            has_situation = any(w in response.lower() for w in ["when", "situation", "context", "was"])
            has_action = any(w in response.lower() for w in ["i did", "i decided", "i took", "my approach"])
            has_result = any(w in response.lower() for w in ["result", "outcome", "led to", "achieved"])
            
            if not has_situation:
                hints.append("Include the situation/context")
            if not has_action:
                hints.append("Describe your specific actions")
            if not has_result:
                hints.append("Share the outcome/result")
        
        if not hints:
            hints.append("Good response!")
        
        return {
            "hint": hints[0],
            "quality": quality,
            "all_hints": hints
        }


# Singleton
_generator_instance: Optional[FeedbackGenerator] = None


def get_feedback_generator() -> FeedbackGenerator:
    """Get singleton FeedbackGenerator instance"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = FeedbackGenerator()
    return _generator_instance
