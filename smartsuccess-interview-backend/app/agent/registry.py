"""
Phase 2 Agent Tools — Tool Registry

Maps tool names to implementations and OpenAI function-calling schemas.
`execute()` NEVER raises: any exception is captured and returned as an
error payload so the agent loop can self-heal (feed the error back to the
LLM and continue the interview).
"""

import inspect
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from app.agent.tools import AgentToolkit

logger = logging.getLogger(__name__)


# OpenAI function-calling schemas for the toolkit
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "search_question_bank": {
        "description": (
            "Search the interview question bank. Use this to pick the next "
            "question, excluding ids already asked."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "interview_type": {
                    "type": "string",
                    "enum": ["screening", "behavioral", "technical"],
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter, e.g. 'motivation'",
                },
                "exclude_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Question ids already asked",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["interview_type"],
        },
    },
    "score_answer": {
        "description": (
            "Score the candidate's latest answer on the rubric for this "
            "interview type. MUST be called once every round."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "answer": {"type": "string"},
                "interview_type": {
                    "type": "string",
                    "enum": ["screening", "behavioral", "technical"],
                },
            },
            "required": ["question", "answer"],
        },
    },
    "get_candidate_profile": {
        "description": (
            "Get the candidate's resume/job-description context and the "
            "questions already asked in this session."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    "save_interview_note": {
        "description": "Save a short interviewer observation for the final summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "note": {"type": "string"},
                "category": {
                    "type": "string",
                    "description": "e.g. 'strength', 'concern', 'follow_up'",
                },
            },
            "required": ["note"],
        },
    },
}


class ToolRegistry:
    """Registry of agent tools with OpenAI schemas and safe execution."""

    def __init__(self, toolkit: Optional[AgentToolkit] = None):
        self.toolkit = toolkit or AgentToolkit()
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._register_toolkit_tools()

    def _register_toolkit_tools(self):
        self.register(
            "search_question_bank",
            self.toolkit.search_question_bank,
            TOOL_SCHEMAS["search_question_bank"],
        )
        self.register(
            "score_answer", self.toolkit.score_answer, TOOL_SCHEMAS["score_answer"]
        )
        self.register(
            "get_candidate_profile",
            self.toolkit.get_candidate_profile,
            TOOL_SCHEMAS["get_candidate_profile"],
        )
        self.register(
            "save_interview_note",
            self.toolkit.save_interview_note,
            TOOL_SCHEMAS["save_interview_note"],
        )

    def register(
        self, name: str, fn: Callable[..., Any], schema: Dict[str, Any]
    ) -> None:
        """Register a tool implementation with its schema."""
        self._tools[name] = fn
        self._schemas[name] = schema

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def openai_tools(self) -> List[Dict[str, Any]]:
        """Tool definitions in OpenAI chat.completions `tools` format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": schema["description"],
                    "parameters": schema["parameters"],
                },
            }
            for name, schema in self._schemas.items()
        ]

    async def execute(self, name: str, arguments: Any) -> Dict[str, Any]:
        """
        Execute a tool by name with JSON-string or dict arguments.

        Never raises — errors come back as {"ok": False, "error": ...}
        with timing metadata, so the agent loop can continue.
        """
        started = time.monotonic()
        try:
            if name not in self._tools:
                raise KeyError(
                    f"Unknown tool '{name}'. Available: {self.tool_names}"
                )
            if isinstance(arguments, str):
                args = json.loads(arguments) if arguments.strip() else {}
            else:
                args = dict(arguments or {})

            result = self._tools[name](**args)
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, dict):
                result = {"ok": True, "result": result}
        except Exception as e:
            logger.warning(f"Tool '{name}' failed: {e}")
            result = {"ok": False, "error": f"{type(e).__name__}: {e}"}

        result["_latency_ms"] = round((time.monotonic() - started) * 1000, 2)
        return result
