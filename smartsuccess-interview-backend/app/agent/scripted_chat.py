"""
Phase 2 Agent Tools — Scripted chat client (offline LLM stand-in)

OpenAI-response-shaped objects plus a deterministic scripted "LLM" used
by the offline test suite and by scripts/collect_tool_call_logs.py when
no OPENAI_API_KEY is available. NOT used in production rounds — the real
agent path uses AsyncOpenAI (see AgentInterviewer._default_chat).
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FakeFunction:
    name: str
    arguments: str


@dataclass
class FakeToolCall:
    id: str
    function: FakeFunction
    type: str = "function"


@dataclass
class FakeMessage:
    content: Optional[str] = None
    tool_calls: Optional[List[FakeToolCall]] = None


@dataclass
class FakeChoice:
    message: FakeMessage


@dataclass
class FakeResponse:
    choices: List[FakeChoice]


def tool_call_turn(
    calls: List[Dict[str, Any]], content: Optional[str] = None
) -> FakeResponse:
    """Build an assistant turn that requests tool calls.

    calls: [{"name": ..., "arguments": {...}}, ...]
    content: optional assistant reasoning (becomes the decision text)
    """
    tool_calls = [
        FakeToolCall(
            id=f"call_{i}_{c['name']}",
            function=FakeFunction(
                name=c["name"], arguments=json.dumps(c.get("arguments", {}))
            ),
        )
        for i, c in enumerate(calls)
    ]
    return FakeResponse([FakeChoice(FakeMessage(content=content, tool_calls=tool_calls))])


def final_turn(question: str) -> FakeResponse:
    """Build a final assistant turn containing the next question."""
    return FakeResponse([FakeChoice(FakeMessage(content=question))])


@dataclass
class ScriptedChat:
    """
    Deterministic chat callable: returns pre-scripted turns in order and
    records every (messages, tools) invocation for assertions.
    """
    turns: List[FakeResponse]
    calls: List[Dict[str, Any]] = field(default_factory=list)

    async def __call__(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> FakeResponse:
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        if not self.turns:
            raise RuntimeError("ScriptedChat ran out of scripted turns")
        return self.turns.pop(0)


def standard_round_script(
    question: str,
    answer: str,
    next_question: str,
    interview_type: str = "screening",
    exclude_ids: Optional[List[str]] = None,
) -> List[FakeResponse]:
    """
    The canonical well-behaved round: score the answer, consult the
    question bank, note an observation, then ask the next question.
    """
    return [
        tool_call_turn(
            [{
                "name": "score_answer",
                "arguments": {
                    "question": question,
                    "answer": answer,
                    "interview_type": interview_type,
                },
            }],
            content="Scoring the candidate's answer before choosing the next question.",
        ),
        tool_call_turn(
            [
                {
                    "name": "search_question_bank",
                    "arguments": {
                        "interview_type": interview_type,
                        "exclude_ids": exclude_ids or [],
                        "limit": 3,
                    },
                },
                {
                    "name": "save_interview_note",
                    "arguments": {
                        "note": "Answer was structured; probe for specifics next.",
                        "category": "follow_up",
                    },
                },
            ],
            content="Answer scored; selecting an unasked question from the bank.",
        ),
        final_turn(next_question),
    ]
