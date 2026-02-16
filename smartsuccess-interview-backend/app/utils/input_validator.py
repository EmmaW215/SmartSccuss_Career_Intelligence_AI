"""
User Response Input Validation
FIX: A-Q7 (Sprint 5) — Pre-evaluation validation for user responses

Prevents empty, gibberish, or extremely short responses from
wasting LLM evaluation tokens.
"""

import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def validate_response(response: str) -> Tuple[bool, Optional[str]]:
    """
    Validate user response before sending to LLM evaluation.
    
    Returns:
        Tuple of (is_valid, guidance_message_if_invalid)
    """
    cleaned = response.strip()
    
    # Check empty
    if not cleaned:
        return False, (
            "It looks like your response was empty. "
            "Could you try again with your answer?"
        )
    
    # Check extremely short (less than 10 chars)
    if len(cleaned) < 10:
        return False, (
            "Your response seems quite brief. "
            "Could you elaborate a bit more? Even a few sentences would help me "
            "give you better feedback."
        )
    
    # Check for gibberish (no real words — mostly non-alpha)
    alpha_ratio = sum(1 for c in cleaned if c.isalpha()) / max(len(cleaned), 1)
    if alpha_ratio < 0.3 and len(cleaned) > 5:
        return False, (
            "I had trouble understanding your response. "
            "Could you rephrase that in a complete sentence?"
        )
    
    # Check for single repeated character
    if len(set(cleaned.lower().replace(" ", ""))) <= 2 and len(cleaned) > 5:
        return False, (
            "It seems like your response might not be complete. "
            "Please share your actual answer and I'll provide helpful feedback."
        )
    
    return True, None


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format."""
    if not session_id or not isinstance(session_id, str):
        return False
    # Expected format: {type}_{user_id}_{hex}
    return bool(re.match(r'^[a-z]+_[a-zA-Z0-9_-]+_[a-f0-9]{8}$', session_id))
