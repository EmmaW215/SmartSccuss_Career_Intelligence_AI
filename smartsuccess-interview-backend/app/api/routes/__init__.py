"""
API Routes for SmartSuccess Interview Backend
"""

from . import health
from . import screening
from . import behavioral
from . import technical
from . import voice

# Phase 2: Optional routes (only imported if available)
try:
    from . import customize
    from . import dashboard
    __all__ = ["health", "screening", "behavioral", "technical", "voice", "customize", "dashboard"]
except ImportError:
    customize = None
    dashboard = None
    __all__ = ["health", "screening", "behavioral", "technical", "voice"]
