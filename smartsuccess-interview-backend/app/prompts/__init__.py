"""
Prompt Templates for SmartSuccess Interview Backend
Optimized prompts for each interview type
"""

from . import screening_prompts
from . import behavioral_prompts
from . import technical_prompts

__all__ = [
    "screening_prompts",
    "behavioral_prompts", 
    "technical_prompts"
]
