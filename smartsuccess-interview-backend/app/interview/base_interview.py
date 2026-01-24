"""
Base Interview Service
Common functionality for all interview types
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from datetime import datetime
import uuid

from app.models import (
    InterviewSession,
    InterviewType,
    InterviewPhase,
    MessageResponse,
    SessionSummary
)


class BaseInterviewService(ABC):
    """
    Base class for all interview services
    
    Provides:
    - Session management
    - Message processing flow
    - Abstract methods for type-specific logic
    """
    
    interview_type: InterviewType
    max_questions: int
    duration_limit_minutes: int
    
    def __init__(self):
        # Store active sessions
        self.sessions: Dict[str, InterviewSession] = {}
    
    async def create_session(
        self,
        user_id: str,
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None,
        matchwise_analysis: Optional[Dict[str, Any]] = None
    ) -> InterviewSession:
        """
        Create a new interview session
        """
        session_id = f"{self.interview_type.value}_{user_id}_{uuid.uuid4().hex[:8]}"
        
        session = InterviewSession(
            session_id=session_id,
            user_id=user_id,
            interview_type=self.interview_type,
            phase=InterviewPhase.GREETING,
            max_questions=self.max_questions,
            duration_limit_minutes=self.duration_limit_minutes,
            resume_text=resume_text,
            job_description=job_description,
            matchwise_analysis=matchwise_analysis
        )
        
        self.sessions[session_id] = session
        
        # Build RAG context if we have resume/JD
        if resume_text or job_description:
            await self._build_context(session)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """Get an existing session by ID"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    async def process_message(
        self,
        session_id: str,
        user_message: str
    ) -> MessageResponse:
        """
        Process a user message and return the response
        """
        session = self.get_session(session_id)
        if not session:
            return MessageResponse(
                type="error",
                message=f"Session {session_id} not found"
            )
        
        # Record user message
        session.messages.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Handle based on phase
        if session.phase == InterviewPhase.GREETING:
            session.phase = InterviewPhase.IN_PROGRESS
            session.started_at = datetime.utcnow()
            return await self._handle_first_response(session, user_message)
        
        elif session.phase == InterviewPhase.IN_PROGRESS:
            return await self._handle_interview_response(session, user_message)
        
        elif session.phase == InterviewPhase.COMPLETED:
            return MessageResponse(
                type="completion",
                message="This interview session has already been completed."
            )
        
        return MessageResponse(
            type="error",
            message="Invalid session state"
        )
    
    async def _handle_first_response(
        self,
        session: InterviewSession,
        user_message: str
    ) -> MessageResponse:
        """Handle the first response after greeting"""
        # Evaluate the response
        evaluation = await self._evaluate_response(session, user_message)
        
        # Record the response
        session.responses.append({
            "question_index": 0,
            "question": session.questions_asked[0] if session.questions_asked else "Introduction",
            "response": user_message,
            "evaluation": evaluation,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Move to next question
        session.current_question_index = 1
        
        # Get next question
        next_question = await self._get_next_question(session)
        session.questions_asked.append(next_question)
        
        # Record assistant message
        session.messages.append({
            "role": "assistant",
            "content": next_question,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return MessageResponse(
            type="question",
            message=next_question,
            question_number=session.current_question_index + 1,
            total_questions=self.max_questions,
            evaluation=evaluation
        )
    
    async def _handle_interview_response(
        self,
        session: InterviewSession,
        user_message: str
    ) -> MessageResponse:
        """Handle responses during the interview"""
        # Check if user wants to end interview early
        user_lower = user_message.lower().strip()
        end_keywords = ['stop', 'end', 'finish', 'done', "that's all", 'that is all', 'i\'m done', 'i am done', 'i want to stop', 'i want to end']
        if any(keyword in user_lower for keyword in end_keywords):
            # Complete interview early
            return await self._complete_interview(session)
        
        # Evaluate the response
        evaluation = await self._evaluate_response(session, user_message)
        
        # Record the response
        current_question = session.questions_asked[-1] if session.questions_asked else ""
        session.responses.append({
            "question_index": session.current_question_index,
            "question": current_question,
            "response": user_message,
            "evaluation": evaluation,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Check if we need a follow-up
        follow_up = await self._check_follow_up(session, evaluation)
        if follow_up:
            session.messages.append({
                "role": "assistant",
                "content": follow_up,
                "timestamp": datetime.utcnow().isoformat()
            })
            session.questions_asked.append(follow_up)
            
            return MessageResponse(
                type="question",
                message=follow_up,
                question_number=session.current_question_index + 1,
                total_questions=self.max_questions,
                evaluation=evaluation
            )
        
        # Move to next question
        session.current_question_index += 1
        
        # Check if interview should complete
        if self._should_complete(session):
            return await self._complete_interview(session)
        
        # Get next question
        next_question = await self._get_next_question(session)
        session.questions_asked.append(next_question)
        
        # Record assistant message
        session.messages.append({
            "role": "assistant",
            "content": next_question,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return MessageResponse(
            type="question",
            message=next_question,
            question_number=session.current_question_index + 1,
            total_questions=self.max_questions,
            evaluation=evaluation
        )
    
    def _should_complete(self, session: InterviewSession) -> bool:
        """Check if the interview should complete"""
        # Complete if we've asked enough questions
        if session.current_question_index >= self.max_questions:
            return True
        
        # Complete if time limit exceeded (if started_at is set)
        if session.started_at:
            elapsed = (datetime.utcnow() - session.started_at).total_seconds() / 60
            if elapsed >= self.duration_limit_minutes:
                return True
        
        return False
    
    async def _complete_interview(self, session: InterviewSession) -> MessageResponse:
        """Complete the interview and generate summary"""
        session.phase = InterviewPhase.COMPLETED
        session.completed_at = datetime.utcnow()
        
        # Generate summary
        summary = await self._generate_summary(session)
        
        # Get completion message
        completion_message = await self._get_completion_message(session)
        
        # Record final message
        session.messages.append({
            "role": "assistant",
            "content": completion_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return MessageResponse(
            type="completion",
            message=completion_message,
            summary=summary
        )
    
    @abstractmethod
    async def get_greeting(self) -> str:
        """Get the interview-specific greeting - implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _build_context(self, session: InterviewSession) -> None:
        """Build RAG context for the session - implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _get_next_question(self, session: InterviewSession) -> str:
        """Get the next question - implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _evaluate_response(
        self,
        session: InterviewSession,
        response: str
    ) -> Dict[str, Any]:
        """Evaluate a response - implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _check_follow_up(
        self,
        session: InterviewSession,
        evaluation: Dict[str, Any]
    ) -> Optional[str]:
        """Check if a follow-up is needed - implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _generate_summary(self, session: InterviewSession) -> SessionSummary:
        """Generate session summary - implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _get_completion_message(self, session: InterviewSession) -> str:
        """Get the completion message - implemented by subclasses"""
        pass
