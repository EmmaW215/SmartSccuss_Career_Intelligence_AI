"""
Data Models for SmartSuccess Interview Backend
Pydantic models for API requests/responses and internal data structures
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class InterviewType(str, Enum):
    SCREENING = "screening"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"


class InterviewPhase(str, Enum):
    NOT_STARTED = "not_started"
    GREETING = "greeting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class QuestionDifficulty(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ==================== SESSION MODELS ====================

class InterviewSession(BaseModel):
    """Interview session state"""
    session_id: str
    user_id: str
    interview_type: InterviewType
    phase: InterviewPhase = InterviewPhase.NOT_STARTED
    current_question_index: int = 0
    questions_asked: List[str] = Field(default_factory=list)
    responses: List[Dict[str, Any]] = Field(default_factory=list)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Optional context
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    matchwise_analysis: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Configuration
    max_questions: int = 5
    duration_limit_minutes: int = 15
    
    class Config:
        use_enum_values = True


# ==================== QUESTION MODELS ====================

class Question(BaseModel):
    """Interview question"""
    id: str
    question: str
    question_type: str  # "self_introduction", "motivation", "situational", etc.
    difficulty: QuestionDifficulty = QuestionDifficulty.INTERMEDIATE
    follow_ups: List[str] = Field(default_factory=list)
    evaluation_criteria: List[str] = Field(default_factory=list)
    expected_topics: List[str] = Field(default_factory=list)
    
    # For behavioral questions
    star_prompts: Optional[Dict[str, str]] = None
    
    # For technical questions
    domain: Optional[str] = None
    key_concepts: List[str] = Field(default_factory=list)


class QuestionBank(BaseModel):
    """Collection of questions for an interview type"""
    category: InterviewType
    purpose: str
    duration_minutes: int
    questions: List[Question] = Field(default_factory=list)
    evaluation_rubric: Dict[str, Any] = Field(default_factory=dict)


# ==================== FEEDBACK MODELS ====================

class STARScore(BaseModel):
    """STAR method scoring for behavioral questions"""
    situation: int = Field(ge=1, le=5, default=3)
    task: int = Field(ge=1, le=5, default=3)
    action: int = Field(ge=1, le=5, default=3)
    result: int = Field(ge=1, le=5, default=3)
    
    @property
    def total(self) -> int:
        return self.situation + self.task + self.action + self.result
    
    @property
    def average(self) -> float:
        return self.total / 4


class ScreeningFeedback(BaseModel):
    """Feedback for screening interview responses"""
    communication_clarity: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)
    confidence: int = Field(ge=1, le=5)
    professionalism: int = Field(ge=1, le=5)
    enthusiasm: int = Field(ge=1, le=5)
    
    strength: str = ""
    improvement: str = ""
    first_impression: str = "Neutral"  # Positive, Neutral, Concerning
    
    @property
    def overall_score(self) -> float:
        scores = [
            self.communication_clarity,
            self.relevance,
            self.confidence,
            self.professionalism,
            self.enthusiasm
        ]
        return sum(scores) / len(scores)


class BehavioralFeedback(BaseModel):
    """Feedback for behavioral interview responses"""
    star_scores: STARScore = Field(default_factory=STARScore)
    
    primary_competency: str = ""
    secondary_competency: str = ""
    missing_competency: str = ""
    
    strengths: List[str] = Field(default_factory=list)
    growth_areas: List[str] = Field(default_factory=list)
    
    follow_up_needed: Optional[str] = None  # "situation", "task", "action", "result", None
    
    @property
    def overall_score(self) -> float:
        return self.star_scores.average


class TechnicalFeedback(BaseModel):
    """Feedback for technical interview responses"""
    technical_accuracy: int = Field(ge=1, le=5)
    depth_of_knowledge: int = Field(ge=1, le=5)
    practical_experience: int = Field(ge=1, le=5)
    system_thinking: int = Field(ge=1, le=5)
    communication_clarity: int = Field(ge=1, le=5)
    
    key_strengths: List[str] = Field(default_factory=list)
    knowledge_gaps: List[str] = Field(default_factory=list)
    follow_up_topics: List[str] = Field(default_factory=list)
    
    hire_signal: str = "moderate"  # strong, moderate, weak, no
    
    @property
    def overall_score(self) -> float:
        scores = [
            self.technical_accuracy,
            self.depth_of_knowledge,
            self.practical_experience,
            self.system_thinking,
            self.communication_clarity
        ]
        return sum(scores) / len(scores)


class QuestionResponse(BaseModel):
    """A single question-response pair with feedback"""
    question_index: int
    question: str
    response: str
    feedback: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionSummary(BaseModel):
    """Summary of a completed interview session"""
    session_id: str
    interview_type: InterviewType
    total_questions: int
    total_responses: int
    duration_minutes: float
    
    overall_score: float
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    
    top_strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    
    recommendation: str = ""
    detailed_feedback: List[QuestionResponse] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


# ==================== API REQUEST/RESPONSE MODELS ====================

class StartSessionRequest(BaseModel):
    """Request to start a new interview session"""
    user_id: str
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    matchwise_analysis: Optional[Dict[str, Any]] = None


class StartSessionResponse(BaseModel):
    """Response when starting a new session"""
    session_id: str
    interview_type: str
    greeting: str
    duration_limit_minutes: int
    max_questions: int


class MessageRequest(BaseModel):
    """Request to send a message in an interview"""
    session_id: str
    message: str


class MessageResponse(BaseModel):
    """Response to a message in an interview"""
    type: str  # "question", "completion", "error"
    message: str
    question_number: Optional[int] = None
    total_questions: Optional[int] = None
    evaluation: Optional[Dict[str, Any]] = None
    summary: Optional[SessionSummary] = None


class VoiceRequest(BaseModel):
    """Request for voice interaction"""
    session_id: str
    language: str = "en"
    voice: str = "alloy"


class VoiceResponse(BaseModel):
    """Response for voice interaction"""
    user_transcript: str
    assistant_response: str
    audio_base64: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None
