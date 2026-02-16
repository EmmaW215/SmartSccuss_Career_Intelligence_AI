"""
Simple In-Memory Rate Limiter
FIX: F-A3 (Sprint 5) — Prevents LLM API abuse

Lightweight rate limiting per user. No external dependencies.
"""

import logging
from collections import defaultdict
from time import time
from typing import Dict

logger = logging.getLogger(__name__)


class SimpleRateLimiter:
    """
    Per-user rate limiter using sliding window.
    
    Default: 30 LLM calls per minute per user.
    """
    
    def __init__(self, max_calls_per_minute: int = 30):
        self.max_calls = max_calls_per_minute
        self.calls: Dict[str, list] = defaultdict(list)
    
    def check(self, user_id: str) -> bool:
        """
        Check if a call is allowed for this user.
        
        Returns True if allowed, False if rate limited.
        """
        now = time()
        # Clean entries older than 60 seconds
        self.calls[user_id] = [t for t in self.calls[user_id] if now - t < 60]
        
        if len(self.calls[user_id]) >= self.max_calls:
            logger.warning(f"Rate limit hit for user {user_id}: "
                          f"{len(self.calls[user_id])}/{self.max_calls} calls/min")
            return False
        
        self.calls[user_id].append(now)
        return True
    
    def get_remaining(self, user_id: str) -> int:
        """Get remaining allowed calls for this user."""
        now = time()
        self.calls[user_id] = [t for t in self.calls[user_id] if now - t < 60]
        return max(0, self.max_calls - len(self.calls[user_id]))
    
    def cleanup(self):
        """Remove stale entries to prevent memory growth."""
        now = time()
        stale_users = [
            uid for uid, calls in self.calls.items()
            if not calls or (now - max(calls)) > 300  # 5 min stale
        ]
        for uid in stale_users:
            del self.calls[uid]


# Singleton
_rate_limiter = SimpleRateLimiter()


def get_rate_limiter() -> SimpleRateLimiter:
    return _rate_limiter
