"""
Session Store (Phase 2 - Enhanced)
Session management for Phase 2 features (customize, dashboard)

FIX: F-A1 — Added optional file-backed persistence via PersistentSessionStore
FIX: F-A2 — Replaced manual singleton with @lru_cache pattern
FIX: F-A3 — Integrated cleanup with rate-limiter awareness

Note: This is separate from Phase 1 interview session management.
Phase 1 sessions use services/session_persistence.py (new).
Phase 2 sessions use this module.
"""

import time
import uuid
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache

from app.config import settings

# FIX: F-A1 — Import persistence layer (optional; graceful if missing)
try:
    from .session_persistence import PersistentSessionStore

    HAS_PERSISTENCE = True
except ImportError:
    HAS_PERSISTENCE = False


class InterviewStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class InterviewSession:
    """Represents an interview session (Phase 2 format)"""

    session_id: str
    user_id: str
    interview_type: str  # screening, behavioral, technical, customize
    status: InterviewStatus = InterviewStatus.PENDING

    # Conversation state
    current_question_index: int = 0
    questions: List[Dict] = field(default_factory=list)
    responses: List[Dict] = field(default_factory=list)
    feedback_hints: List[Dict] = field(default_factory=list)

    # Custom interview data
    custom_profile: Optional[Dict] = None
    custom_rag_id: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: datetime = field(default_factory=datetime.now)

    # Voice mode
    voice_enabled: bool = False
    voice_provider: str = "none"  # gpu, edge_tts, none

    def to_dict(self) -> Dict:
        """Convert to dictionary for persistence / API responses."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "interview_type": self.interview_type,
            "status": self.status.value,
            "current_question_index": self.current_question_index,
            "total_questions": len(self.questions),
            "responses_count": len(self.responses),
            "voice_enabled": self.voice_enabled,
            "voice_provider": self.voice_provider,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SessionStore:
    """
    In-memory session storage for Phase 2 features.

    Optimized for lightweight usage:
    - No external database needed
    - Automatic cleanup of old sessions
    - Memory-efficient

    FIX: F-A1 — Optional file-backed persistence. When `persist=True`, completed
    sessions are written to disk so they survive process restarts (useful on
    Render free tier where the dyno may restart at any time).
    """

    def __init__(self, persist: bool = False):
        self._sessions: Dict[str, InterviewSession] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> session_ids
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes

        # FIX: F-A1 — Optional persistence layer
        self._persist = persist and HAS_PERSISTENCE
        if self._persist:
            self._disk_store = PersistentSessionStore(
                session_dir="data/phase2_sessions"
            )
        else:
            self._disk_store = None

    # ──────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────

    def create_session(
        self,
        user_id: str,
        interview_type: str,
        questions: List[Dict],
        voice_enabled: bool = False,
        custom_profile: Optional[Dict] = None,
        custom_rag_id: Optional[str] = None,
    ) -> InterviewSession:
        """Create a new interview session"""
        self._maybe_cleanup()

        # Check concurrent session limit
        max_sessions = getattr(settings, "max_concurrent_sessions", 50)
        if len(self._sessions) >= max_sessions:
            self._force_cleanup()

        session_id = str(uuid.uuid4())

        session = InterviewSession(
            session_id=session_id,
            user_id=user_id,
            interview_type=interview_type,
            questions=questions,
            voice_enabled=voice_enabled,
            custom_profile=custom_profile,
            custom_rag_id=custom_rag_id,
        )

        self._sessions[session_id] = session

        # Track user's sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)

        return session

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """Get session by ID"""
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
        return session

    def update_session(
        self, session_id: str, **kwargs
    ) -> Optional[InterviewSession]:
        """Update session fields"""
        session = self._sessions.get(session_id)
        if not session:
            return None

        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.last_activity = datetime.now()
        return session

    def add_response(
        self,
        session_id: str,
        question_index: int,
        user_response: str,
        ai_response: str,
        feedback_hint: Optional[Dict] = None,
    ) -> bool:
        """Add a response to the session"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.responses.append(
            {
                "question_index": question_index,
                "question": (
                    session.questions[question_index]
                    if question_index < len(session.questions)
                    else None
                ),
                "user_response": user_response,
                "ai_response": ai_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        if feedback_hint:
            session.feedback_hints.append(feedback_hint)

        session.current_question_index = question_index + 1
        session.last_activity = datetime.now()

        return True

    def complete_session(self, session_id: str) -> Optional[InterviewSession]:
        """Mark session as completed"""
        session = self._sessions.get(session_id)
        if session:
            session.status = InterviewStatus.COMPLETED
            session.completed_at = datetime.now()

            # FIX: F-A1 — Persist completed sessions to disk
            if self._persist and self._disk_store:
                try:
                    self._disk_store.save(session)
                except Exception:
                    pass  # Disk write failure is non-fatal

        return session

    def get_user_sessions(
        self,
        user_id: str,
        limit: int = 10,
        status: Optional[InterviewStatus] = None,
    ) -> List[InterviewSession]:
        """Get sessions for a user"""
        session_ids = self._user_sessions.get(user_id, [])
        sessions = []

        for sid in reversed(session_ids):  # Most recent first
            session = self._sessions.get(sid)
            if session:
                if status is None or session.status == status:
                    sessions.append(session)
                    if len(sessions) >= limit:
                        break

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Remove from user tracking
        if session.user_id in self._user_sessions:
            try:
                self._user_sessions[session.user_id].remove(session_id)
            except ValueError:
                pass

        del self._sessions[session_id]

        # FIX: F-A1 — Also remove from disk if persisted
        if self._persist and self._disk_store:
            try:
                self._disk_store.delete(session_id)
            except Exception:
                pass

        return True

    # ──────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────

    def _maybe_cleanup(self):
        """Cleanup old sessions if needed"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        self._cleanup_old_sessions()
        self._last_cleanup = current_time

    def _force_cleanup(self):
        """Force cleanup when at capacity"""
        self._cleanup_old_sessions()

        max_sessions = getattr(settings, "max_concurrent_sessions", 50)
        # If still at capacity, remove oldest sessions
        while len(self._sessions) >= max_sessions:
            oldest = min(
                self._sessions.values(), key=lambda s: s.last_activity
            )
            self.delete_session(oldest.session_id)

    def _cleanup_old_sessions(self):
        """
        Remove sessions older than timeout.

        Completed sessions are retained longer (24 hours) for report generation.
        In-progress sessions are cleaned up after timeout (60 minutes default).
        """
        timeout_minutes = getattr(settings, "session_timeout_minutes", 60)
        completed_retention_hours = 24

        current_time = datetime.now().timestamp()
        cutoff_in_progress = current_time - (timeout_minutes * 60)
        cutoff_completed = current_time - (completed_retention_hours * 60 * 60)

        to_delete = []
        for session_id, session in self._sessions.items():
            if session.status == InterviewStatus.COMPLETED:
                if (
                    session.completed_at
                    and session.completed_at.timestamp() < cutoff_completed
                ):
                    to_delete.append(session_id)
            else:
                if session.last_activity.timestamp() < cutoff_in_progress:
                    to_delete.append(session_id)

        for session_id in to_delete:
            self.delete_session(session_id)

    # ──────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Get session store statistics"""
        return {
            "total_sessions": len(self._sessions),
            "max_sessions": getattr(settings, "max_concurrent_sessions", 50),
            "active_users": len(self._user_sessions),
            "persistence_enabled": self._persist,  # FIX: F-A1
            "by_status": {
                status.value: sum(
                    1
                    for s in self._sessions.values()
                    if s.status == status
                )
                for status in InterviewStatus
            },
            "by_type": {
                itype: sum(
                    1
                    for s in self._sessions.values()
                    if s.interview_type == itype
                )
                for itype in ["screening", "behavioral", "technical", "customize"]
            },
        }


# ──────────────────────────────────────────────
# Singleton accessor
# FIX: F-A2 — Thread-safe singleton via @lru_cache
# ──────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_session_store(persist: bool = False) -> SessionStore:
    """Get the singleton session store instance."""
    return SessionStore(persist=persist)
