"""
Lightweight File-Based Session Persistence
FIX: F-A1 (Sprint 1) — Sessions survive server restarts

Replaces bare `Dict[str, InterviewSession]` with a file-backed store.
Uses JSON files on disk for zero-cost persistence on Render.

Design decisions:
- In-memory cache + JSON files on disk (best of both)
- Auto-cleanup of sessions older than 24 hours
- Graceful degradation: if disk fails, falls back to memory-only
- Thread-safe via file-level atomicity (write-then-rename)
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Default session directory
SESSION_DIR = Path(os.getenv("SESSION_DATA_DIR", "data/sessions"))


class PersistentSessionStore:
    """
    File-backed session store with in-memory cache.
    
    Drop-in replacement for `Dict[str, InterviewSession]`.
    Supports dict-like access: store[session_id], store.get(session_id), etc.
    """
    
    def __init__(self, session_dir: Optional[Path] = None):
        self.session_dir = session_dir or SESSION_DIR
        self._cache: Dict[str, Any] = {}
        self._ensure_directory()
        self._load_existing()
    
    def _ensure_directory(self):
        """Create session directory if it doesn't exist."""
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Cannot create session directory {self.session_dir}: {e}. "
                          f"Falling back to memory-only mode.")
            self.session_dir = None
    
    def _load_existing(self):
        """Load existing sessions from disk on startup."""
        if not self.session_dir:
            return
        
        loaded = 0
        for f in self.session_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                session_id = data.get("session_id", f.stem)
                self._cache[session_id] = data
                loaded += 1
            except Exception as e:
                logger.warning(f"Skipping corrupted session file {f}: {e}")
        
        if loaded > 0:
            logger.info(f"Loaded {loaded} existing sessions from disk.")
    
    def save(self, session_id: str, session_data: Any):
        """
        Save session to cache and disk.
        
        Args:
            session_id: Session identifier
            session_data: InterviewSession object or dict.
                         If it has a `.dict()` or `.model_dump()` method, it will be called.
        """
        # Convert to dict if it's a Pydantic model
        if hasattr(session_data, 'model_dump'):
            data = session_data.model_dump(mode='json')
        elif hasattr(session_data, 'dict'):
            data = session_data.dict()
        elif isinstance(session_data, dict):
            data = session_data
        else:
            # Store the object in cache but skip disk persistence
            self._cache[session_id] = session_data
            return
        
        # Ensure session_id is in the data
        data["session_id"] = session_id
        data["_last_saved"] = datetime.utcnow().isoformat()
        
        # Save to cache
        self._cache[session_id] = session_data
        
        # Save to disk (atomic write: write to temp, then rename)
        if self.session_dir:
            try:
                path = self.session_dir / f"{session_id}.json"
                tmp_path = path.with_suffix('.tmp')
                
                with open(tmp_path, "w") as fp:
                    json.dump(data, fp, default=str)
                
                tmp_path.rename(path)  # Atomic on most filesystems
            except Exception as e:
                logger.warning(f"Failed to persist session {session_id} to disk: {e}")
    
    def get(self, session_id: str) -> Optional[Any]:
        """Get a session by ID."""
        return self._cache.get(session_id)
    
    def delete(self, session_id: str):
        """Delete a session from cache and disk."""
        self._cache.pop(session_id, None)
        
        if self.session_dir:
            try:
                path = self.session_dir / f"{session_id}.json"
                path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to delete session file {session_id}: {e}")
    
    def cleanup_old(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        if not self.session_dir:
            return
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        cleaned = 0
        
        for f in self.session_dir.glob("*.json"):
            try:
                if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    sid = f.stem
                    f.unlink()
                    self._cache.pop(sid, None)
                    cleaned += 1
            except Exception:
                pass
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired sessions.")
    
    def list_sessions(self) -> list:
        """List all active session IDs."""
        return list(self._cache.keys())
    
    @property
    def count(self) -> int:
        """Number of active sessions."""
        return len(self._cache)
    
    # Dict-like interface for backward compatibility
    def __contains__(self, session_id: str) -> bool:
        return session_id in self._cache
    
    def __getitem__(self, session_id: str) -> Any:
        return self._cache[session_id]
    
    def __setitem__(self, session_id: str, session_data: Any):
        self.save(session_id, session_data)
    
    def __delitem__(self, session_id: str):
        self.delete(session_id)
    
    def pop(self, session_id: str, default=None):
        result = self._cache.pop(session_id, default)
        if self.session_dir:
            try:
                (self.session_dir / f"{session_id}.json").unlink(missing_ok=True)
            except Exception:
                pass
        return result
