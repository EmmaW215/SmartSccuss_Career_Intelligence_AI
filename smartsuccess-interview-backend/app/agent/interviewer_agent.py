"""
Phase 2 Agent Tools — Agent-driven interviewer loop

One `run_round()` call = one interview round:
  candidate answer in → (LLM + tools agent loop) → next question out

Guarantees (PRD 02_PHASE2_AGENT_TOOLS.md acceptance criteria):
- Self-healing: tool errors are returned to the LLM as tool results and
  the loop continues; the round ALWAYS produces a next question (question
  bank fallback as last resort).
- Every round's tool_call_log contains at least one successful
  score_answer call (enforced directly if the LLM skipped it) and a
  decision-chain entry for every tool call.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.agent.registry import ToolRegistry
from app.agent.tools import AgentToolkit, LLMGenerateFn

logger = logging.getLogger(__name__)

# Async callable: (messages, tools) -> OpenAI-style chat completion response
ChatFn = Callable[[List[Dict[str, Any]], List[Dict[str, Any]]], Awaitable[Any]]

AGENT_SYSTEM_PROMPT = """You are an AI interviewer running a {interview_type} interview round.

Protocol for EVERY round (follow strictly):
1. FIRST call score_answer on the candidate's latest answer.
2. Optionally call get_candidate_profile and/or search_question_bank to choose \
a relevant next question (exclude questions already asked). Use \
save_interview_note for notable strengths or concerns.
3. If any tool returns an error ("ok": false), do NOT stop or apologize — \
continue with your own judgment and keep the interview moving.
4. When done with tools, reply with ONLY the next interview question text \
(one question, no preamble, no numbering)."""


@dataclass
class ToolCallRecord:
    """One entry in the round's tool_call_log."""
    seq: int
    tool: str
    arguments: Dict[str, Any]
    status: str  # "ok" | "error"
    result_summary: str
    latency_ms: float
    decision: str  # why the agent made this call (decision chain)
    enforced: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq,
            "tool": self.tool,
            "arguments": self.arguments,
            "status": self.status,
            "result_summary": self.result_summary,
            "latency_ms": self.latency_ms,
            "decision": self.decision,
            "enforced": self.enforced,
        }


@dataclass
class AgentRoundResult:
    """Outcome of one agent-driven interview round."""
    next_question: str
    evaluation: Dict[str, Any]
    tool_call_log: List[ToolCallRecord] = field(default_factory=list)
    decision_chain: List[str] = field(default_factory=list)
    healed_errors: int = 0
    score_enforced: bool = False
    used_fallback: bool = False
    notes: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "next_question": self.next_question,
            "evaluation": self.evaluation,
            "tool_call_log": [r.to_dict() for r in self.tool_call_log],
            "decision_chain": self.decision_chain,
            "healed_errors": self.healed_errors,
            "score_enforced": self.score_enforced,
            "used_fallback": self.used_fallback,
            "notes": self.notes,
        }


class AgentInterviewer:
    """
    Tool-calling interview agent.

    chat_fn is injectable for tests (scripted LLM); when omitted, a real
    AsyncOpenAI client is created lazily on first use.
    """

    def __init__(
        self,
        chat_fn: Optional[ChatFn] = None,
        llm_generate: Optional[LLMGenerateFn] = None,
        model: Optional[str] = None,
        max_iterations: Optional[int] = None,
    ):
        from app.config import settings

        self._chat_fn = chat_fn
        self.llm_generate = llm_generate
        self.model = model or settings.llm_model
        self.max_iterations = max_iterations or settings.agent_max_tool_iterations

    async def _default_chat(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Any:
        """Real OpenAI chat completion with tool calling."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI()
        return await client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.4,
        )

    async def run_round(
        self,
        session_context: Dict[str, Any],
        current_question: str,
        user_answer: str,
    ) -> AgentRoundResult:
        """
        Run one agent-driven interview round.

        session_context: see AgentToolkit (interview_type, resume_text,
        job_description, questions_asked, current_question_index).
        """
        interview_type = session_context.get("interview_type", "screening")
        toolkit = AgentToolkit(
            session_context=session_context, llm_generate=self.llm_generate
        )
        registry = ToolRegistry(toolkit=toolkit)
        result = AgentRoundResult(next_question="", evaluation={})

        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": AGENT_SYSTEM_PROMPT.format(interview_type=interview_type),
            },
            {
                "role": "user",
                "content": (
                    f"Current question: {current_question}\n\n"
                    f"Candidate's answer: {user_answer}\n\n"
                    f"Questions already asked: "
                    f"{json.dumps(session_context.get('questions_asked', []))}"
                ),
            },
        ]

        chat = self._chat_fn or self._default_chat
        seq = 0

        try:
            for _ in range(self.max_iterations):
                response = await chat(messages, registry.openai_tools())
                message = response.choices[0].message
                tool_calls = getattr(message, "tool_calls", None)

                if not tool_calls:
                    # Final answer: the next interview question
                    result.next_question = (message.content or "").strip()
                    break

                # Assistant turn with tool calls — record decision context
                decision_text = (message.content or "").strip()
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in tool_calls
                        ],
                    }
                )

                for tc in tool_calls:
                    seq += 1
                    tool_name = tc.function.name
                    decision = decision_text or self._infer_decision(tool_name)
                    tool_result = await registry.execute(
                        tool_name, tc.function.arguments
                    )
                    latency = tool_result.pop("_latency_ms", 0.0)
                    status = "ok" if tool_result.get("ok") else "error"
                    if status == "error":
                        result.healed_errors += 1

                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except (json.JSONDecodeError, TypeError):
                        args = {"_raw": str(tc.function.arguments)}

                    record = ToolCallRecord(
                        seq=seq,
                        tool=tool_name,
                        arguments=args,
                        status=status,
                        result_summary=self._summarize(tool_result),
                        latency_ms=latency,
                        decision=decision,
                    )
                    result.tool_call_log.append(record)
                    result.decision_chain.append(f"[{tool_name}] {decision}")

                    if tool_name == "score_answer" and status == "ok":
                        result.evaluation = tool_result

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(tool_result),
                        }
                    )
        except Exception as e:
            logger.warning(f"Agent loop failed, using fallback question: {e}")
            result.decision_chain.append(f"[loop_error] {type(e).__name__}: {e}")

        # ── Guarantee 1: score_answer present every round (enforce) ─────
        if not self._has_successful_score(result):
            seq += 1
            enforced_result = await registry.execute(
                "score_answer",
                {
                    "question": current_question,
                    "answer": user_answer,
                    "interview_type": interview_type,
                },
            )
            latency = enforced_result.pop("_latency_ms", 0.0)
            status = "ok" if enforced_result.get("ok") else "error"
            decision = "Enforced scoring: agent did not call score_answer this round"
            result.tool_call_log.append(
                ToolCallRecord(
                    seq=seq,
                    tool="score_answer",
                    arguments={"question": current_question, "answer": user_answer},
                    status=status,
                    result_summary=self._summarize(enforced_result),
                    latency_ms=latency,
                    decision=decision,
                    enforced=True,
                )
            )
            result.decision_chain.append(f"[score_answer] {decision}")
            result.score_enforced = True
            if status == "ok":
                result.evaluation = enforced_result

        # ── Guarantee 2: round always produces a next question ──────────
        if not result.next_question:
            result.next_question = self._fallback_question(
                registry, interview_type, session_context
            )
            result.used_fallback = True
            result.decision_chain.append(
                "[fallback] Agent produced no question; selected next unasked "
                "question from the question bank"
            )

        result.notes = toolkit.notes
        return result

    # ================================================================
    # Helpers
    # ================================================================

    @staticmethod
    def _has_successful_score(result: AgentRoundResult) -> bool:
        return any(
            r.tool == "score_answer" and r.status == "ok"
            for r in result.tool_call_log
        )

    @staticmethod
    def _infer_decision(tool_name: str) -> str:
        return {
            "score_answer": "Scoring the candidate's latest answer per round protocol",
            "search_question_bank": "Searching the question bank for the next question",
            "get_candidate_profile": "Reviewing candidate context to target the next question",
            "save_interview_note": "Recording an interviewer observation",
        }.get(tool_name, f"Calling {tool_name}")

    @staticmethod
    def _summarize(tool_result: Dict[str, Any], max_len: int = 200) -> str:
        text = json.dumps(tool_result, default=str)
        return text if len(text) <= max_len else text[: max_len - 3] + "..."

    def _fallback_question(
        self,
        registry: ToolRegistry,
        interview_type: str,
        session_context: Dict[str, Any],
    ) -> str:
        """Deterministic next question when the agent loop fails."""
        asked = set(session_context.get("questions_asked", []))
        bank = registry.toolkit.search_question_bank(
            interview_type=interview_type, limit=10
        )
        for q in bank.get("questions", []):
            if q["question"] not in asked:
                return q["question"]
        return "Is there anything else you'd like to share about your experience?"


def write_tool_call_log(
    result: AgentRoundResult,
    session_id: str,
    round_index: int,
    user_answer: str,
    log_dir: str,
    mode: str = "real_llm",
) -> Path:
    """
    Persist one round's tool_call_log as a JSON evidence file.

    Files land in {log_dir}/{session_id}_round{N}.json — these are the
    Step D evidence samples referenced by the PRD.
    """
    path = Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id,
        "round": round_index,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": mode,
        "user_answer_preview": user_answer[:200],
        **result.to_dict(),
    }
    file_path = path / f"{session_id}_round{round_index}.json"
    file_path.write_text(json.dumps(payload, indent=2, default=str))
    return file_path
