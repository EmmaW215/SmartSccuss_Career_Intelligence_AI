"""
Base Interview Service
Common functionality for all interview types

FIXES APPLIED:
- A-Q4 (Sprint 1): Conversation context injected into evaluation
- A-Q2 (Sprint 2): Centralized LLM calls through llm_service.py fallback chain
- A-Q5 (Sprint 2): Separate greeting from first question
- A-Q6 (Sprint 5): Default fallback scores with transparency flag
- A-Q7 (Sprint 5): Input validation before evaluation
- F-A1 (Sprint 1): File-based session persistence
- F-A2 (Sprint 5): Thread-safe singleton via functools.lru_cache
- F-A3 (Sprint 5): Rate limiting on LLM calls
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from datetime import datetime
import uuid
import logging

from app.models import (
    InterviewSession,
    InterviewType,
    InterviewPhase,
    MessageResponse,
    SessionSummary
)

# FIX: A-Q2 (Sprint 2) — Import centralized LLM service
from app.services.llm_service import LLMService, get_llm_service

# FIX: F-A1 (Sprint 1) — Import persistent session store
from app.services.session_persistence import PersistentSessionStore

# FIX: A-Q7 (Sprint 5) — Import input validation
from app.utils.input_validator import validate_response

# FIX: F-A3 (Sprint 5) — Import rate limiter
from app.utils.rate_limiter import get_rate_limiter

# Phase 2: Import session adapter for syncing to SessionStore
try:
    from app.services.session_adapter import sync_base_session_to_store
    from app.services.session_store import SessionStore
    SESSION_STORE_AVAILABLE = True
except ImportError:
    SESSION_STORE_AVAILABLE = False
    sync_base_session_to_store = None
    SessionStore = None

logger = logging.getLogger(__name__)


class BaseInterviewService(ABC):
    """
    Base class for all interview services
    
    Provides:
    - Session management (file-backed persistence)
    - Message processing flow
    - Centralized LLM access with fallback chain
    - Conversation context for evaluation
    - Input validation & rate limiting
    - Abstract methods for type-specific logic
    """
    
    interview_type: InterviewType
    max_questions: int
    duration_limit_minutes: int
    
    def __init__(self, session_store: Optional[Any] = None):
        # FIX: F-A1 (Sprint 1) — Use persistent session store instead of bare dict
        self.sessions = PersistentSessionStore()
        
        # FIX: A-Q2 (Sprint 2) — Centralized LLM service with fallback chain
        self.llm = get_llm_service()
        
        # FIX: F-A3 (Sprint 5) — Rate limiter
        self.rate_limiter = get_rate_limiter()
        
        # Phase 2: Store reference to SessionStore for syncing
        self.session_store: Optional[SessionStore] = (
            session_store if SESSION_STORE_AVAILABLE else None
        )
    
    # ================================================================
    # FIX: A-Q4 (Sprint 1) — Conversation context for evaluation
    # ================================================================
    
    def _build_evaluation_context(
        self, session: InterviewSession, current_index: int
    ) -> str:
        """
        Build conversation history string for evaluation context.
        
        Includes up to last 3 Q&A pairs for consistency and progression
        assessment. Keeps token cost low (~200-400 extra tokens).
        
        BUGFIX: Defensive access for sessions loaded from disk as raw dicts
        via PersistentSessionStore._load_existing().
        """
        history_lines = []
        start = max(0, current_index - 3)
        
        questions = getattr(session, "questions_asked", []) or []
        responses = getattr(session, "responses", []) or []
        
        for i in range(start, current_index):
            # Defensive question access
            q = ""
            if isinstance(questions, list) and i < len(questions):
                q = str(questions[i]) if questions[i] else ""
            
            # Defensive response access — handle both list[dict] and edge cases
            r = ""
            if isinstance(responses, list) and i < len(responses):
                resp = responses[i]
                if isinstance(resp, dict):
                    r = resp.get("response", "")
                elif isinstance(resp, str):
                    r = resp
                else:
                    r = str(resp) if resp else ""
            
            if q or r:
                history_lines.append(f"Q{i+1}: {q}\nA{i+1}: {r}")
        
        return "\n\n".join(history_lines)
    
    # ================================================================
    # FIX: A-Q2 (Sprint 2) — Unified LLM call method
    # ================================================================
    
    async def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024
    ) -> str:
        """
        Unified LLM call using the centralized fallback chain.
        
        Replaces direct AsyncOpenAI client calls in each agent.
        Automatically uses: Gemini (free) → Groq (free) → OpenAI (paid)
        """
        return await self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    # ================================================================
    # Session Management
    # ================================================================
    
    async def create_session(
        self,
        user_id: str,
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None,
        matchwise_analysis: Optional[Dict[str, Any]] = None
    ) -> InterviewSession:
        """Create a new interview session"""
        session_id = (
            f"{self.interview_type.value}_{user_id}_{uuid.uuid4().hex[:8]}"
        )
        
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
        
        # FIX: F-A1 — Save to persistent store
        self.sessions.save(session_id, session)
        
        # Phase 2: Sync to SessionStore if available
        if self.session_store and SESSION_STORE_AVAILABLE:
            try:
                sync_base_session_to_store(session, self.session_store)
            except Exception as e:
                logger.warning(f"Failed to sync session to SessionStore: {e}")
        
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
            self.sessions.delete(session_id)
            return True
        return False
    
    def _persist_session(self, session: InterviewSession):
        """Save session state to persistent store after changes."""
        self.sessions.save(session.session_id, session)
    
    # ================================================================
    # Message Processing
    # ================================================================
    
    async def process_message(
        self,
        session_id: str,
        user_message: str
    ) -> MessageResponse:
        """Process a user message and return the response"""
        session = self.get_session(session_id)
        if not session:
            return MessageResponse(
                type="error",
                message=f"Session {session_id} not found"
            )
        
        # FIX: F-A3 (Sprint 5) — Rate limiting
        if not self.rate_limiter.check(session.user_id):
            return MessageResponse(
                type="error",
                message="You're sending messages too quickly. Please wait a moment."
            )
        
        # FIX: A-Q7 (Sprint 5) — Input validation
        is_valid, guidance = validate_response(user_message)
        if not is_valid:
            return MessageResponse(
                type="validation_guidance",
                message=guidance,
                should_retry=True
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
            result = await self._handle_first_response(session, user_message)
            self._persist_session(session)  # FIX: F-A1
            return result
        
        elif session.phase == InterviewPhase.IN_PROGRESS:
            result = await self._handle_interview_response(session, user_message)
            self._persist_session(session)  # FIX: F-A1
            return result
        
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
            "question": (session.questions_asked[0] 
                        if session.questions_asked else "Introduction"),
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
        end_keywords = [
            'stop', 'end', 'finish', 'done', "that's all", 'that is all',
            "i'm done", 'i am done', 'i want to stop', 'i want to end'
        ]
        if any(keyword in user_lower for keyword in end_keywords):
            return await self._complete_interview(session)
        
        # Evaluate the response
        evaluation = await self._evaluate_response(session, user_message)
        
        # Record the response
        current_question = (
            session.questions_asked[-1] if session.questions_asked else ""
        )
        session.responses.append({
            "question_index": session.current_question_index,
            "question": current_question,
            "response": user_message,
            "evaluation": evaluation,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Phase 2: Sync to SessionStore after recording response
        if self.session_store and SESSION_STORE_AVAILABLE:
            try:
                sync_base_session_to_store(session, self.session_store)
            except Exception as e:
                logger.warning(f"Failed to sync session to SessionStore: {e}")
        
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
        if session.current_question_index >= self.max_questions:
            return True
        
        if session.started_at:
            elapsed = (
                (datetime.utcnow() - session.started_at).total_seconds() / 60
            )
            if elapsed >= self.duration_limit_minutes:
                return True
        
        return False
    
    async def _complete_interview(
        self, session: InterviewSession
    ) -> MessageResponse:
        """Complete the interview and generate summary"""
        session.phase = InterviewPhase.COMPLETED
        session.completed_at = datetime.utcnow()
        
        # Phase 2: Sync to SessionStore and mark as completed
        if self.session_store and SESSION_STORE_AVAILABLE:
            try:
                sync_base_session_to_store(session, self.session_store)
                self.session_store.complete_session(session.session_id)
            except Exception as e:
                logger.warning(
                    f"Failed to sync completed session to SessionStore: {e}"
                )
        
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
        
        # FIX: F-A1 — Persist completed session
        self._persist_session(session)
        
        return MessageResponse(
            type="completion",
            message=completion_message,
            summary=summary,
            is_complete=True
        )
    
    # ================================================================
    # Abstract methods — implemented by each agent subclass
    # ================================================================
    
    @abstractmethod
    async def get_greeting(self) -> str:
        """Get the interview-specific greeting"""
        pass
    
    @abstractmethod
    async def _build_context(self, session: InterviewSession) -> None:
        """Build RAG context for the session"""
        pass
    
    @abstractmethod
    async def _get_next_question(self, session: InterviewSession) -> str:
        """Get the next question"""
        pass
    
    @abstractmethod
    async def _evaluate_response(
        self,
        session: InterviewSession,
        response: str
    ) -> Dict[str, Any]:
        """Evaluate a response"""
        pass
    
    @abstractmethod
    async def _check_follow_up(
        self,
        session: InterviewSession,
        evaluation: Dict[str, Any]
    ) -> Optional[str]:
        """Check if a follow-up is needed"""
        pass
    
    @abstractmethod
    async def _generate_summary(
        self, session: InterviewSession
    ) -> SessionSummary:
        """Generate session summary"""
        pass
    
    @abstractmethod
    async def _get_completion_message(
        self, session: InterviewSession
    ) -> str:
        """Get the completion message"""
        pass
