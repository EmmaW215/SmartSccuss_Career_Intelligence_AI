"""
Phase 2 interviewer agent node.

Primary path uses LangGraph ReAct (`create_react_agent` + ToolNode runtime).
Fallback path retains deterministic manual loop for resilience.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from app.agents.tools import (
    generate_followup,
    get_agent_tools,
    score_answer,
    search_question_bank,
)
from app.config import settings
from app.graph.llm import get_chat_model
from app.graph.state import InterviewState
from app.utils.json_parser import extract_json_from_llm

try:
    from langgraph.prebuilt import create_react_agent
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    create_react_agent = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

NEXT_ACTION_ROUTE = {
    "closing": "generate_closing",
    "followup": "end",
    "next_question": "end",
}
_QUALITY_GOOD_THRESHOLD = 8.0
_QUALITY_FAIR_THRESHOLD = 6.0
_MCP_TOOLS_CACHE: Optional[List[Any]] = None
_MCP_TOOLS_LOCK: Optional[asyncio.Lock] = None

INTERVIEWER_SYSTEM_PROMPT = (
    "You are a senior technical interviewer conducting a personalized interview.\n"
    "You can use tools: search_question_bank, fetch_resume_context, score_answer, "
    "generate_followup, get_session_progress.\n"
    "Rules:\n"
    "- Always call score_answer once before deciding next action.\n"
    "- If score < 7 and no follow-up used yet, prefer a focused follow-up.\n"
    "- One question at a time, concise and professional tone.\n"
    "- Output final decision ONLY as JSON: "
    '{"next_action":"followup|next_question|closing","response_text":"...","reasoning":"..."}'
)


class TurnDecision(BaseModel):
    next_action: Literal["followup", "next_question", "closing"] = "next_question"
    response_text: str = Field(default="")
    reasoning: str = Field(default="")


def _current_question(state: InterviewState) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
    questions = state.get("questions", [])
    idx = int(state.get("current_question_index", 0) or 0)
    if idx < 0 or idx >= len(questions):
        return idx, None, None
    question = questions[idx]
    text = question.get("customized_question") or question.get("question")
    return idx, question, text


def _digest_payload(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8", errors="ignore")
    return hashlib.sha1(raw, usedforsecurity=False).hexdigest()[:12]


def _append_tool_call_log(
    log: List[Dict[str, Any]],
    *,
    tool: str,
    args: Dict[str, Any],
    result: Any,
    error: Optional[str] = None,
) -> None:
    entry: Dict[str, Any] = {
        "tool": tool,
        "args": args,
        "result_digest": _digest_payload(result),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        entry["error"] = error
    log.append(entry)


def _to_turn_evaluation(verdict: Dict[str, Any]) -> Dict[str, Any]:
    score = float(verdict.get("score", 0.0) or 0.0)
    if score >= _QUALITY_GOOD_THRESHOLD:
        quality = "good"
    elif score >= _QUALITY_FAIR_THRESHOLD:
        quality = "fair"
    else:
        quality = "needs_improvement"
    improvements = [str(v) for v in verdict.get("improvements", [])][:3]
    strengths = [str(v) for v in verdict.get("strengths", [])][:3]
    hint = improvements[0] if improvements else "Continue adding concrete examples."
    return {
        "score": score,
        "quality": quality,
        "hint": hint,
        "followup_needed": bool(verdict.get("followup_needed", False)),
        "strengths": strengths,
        "improvements": improvements,
        "reasoning": str(verdict.get("reasoning", "")),
    }


async def _load_mcp_tools() -> List[Any]:
    global _MCP_TOOLS_CACHE
    if _MCP_TOOLS_CACHE is not None:
        return _MCP_TOOLS_CACHE

    global _MCP_TOOLS_LOCK
    if _MCP_TOOLS_LOCK is None:
        _MCP_TOOLS_LOCK = asyncio.Lock()

    async with _MCP_TOOLS_LOCK:
        if _MCP_TOOLS_CACHE is not None:
            return _MCP_TOOLS_CACHE
        try:
            client = _build_mcp_client()
            loaded_tools = await client.get_tools()
            _MCP_TOOLS_CACHE = loaded_tools if isinstance(loaded_tools, list) else []
            return _MCP_TOOLS_CACHE
        except Exception as exc:  # pragma: no cover - depends on MCP runtime
            logger.warning("MCP tools unavailable, fallback to direct tools: %s", exc)
            # Do not cache transient failures (avoid cache poisoning).
            return []


def _build_mcp_client() -> Any:
    # Deferred optional dependency.
    from langchain_mcp_adapters.client import MultiServerMCPClient

    return MultiServerMCPClient(
        {
            "knowledge": {
                "url": settings.mcp_server_url,
                "transport": "streamable_http",
            }
        }
    )


async def _load_interviewer_tools() -> List[Any]:
    if getattr(settings, "use_mcp_tools", False):
        mcp_tools = await _load_mcp_tools()
        if mcp_tools:
            return mcp_tools
    return get_agent_tools()


async def _run_react_agent_once(
    *,
    session_id: str,
    question_text: str,
    user_response: str,
    followup_count: int,
    total_questions: int,
    current_question_index: int,
    max_iterations: int,
) -> Dict[str, Any]:
    if create_react_agent is None:
        raise RuntimeError("langgraph.prebuilt.create_react_agent is unavailable")

    tools = await _load_interviewer_tools()
    model = get_chat_model(tier="standard", force_provider="openai")
    react_agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=INTERVIEWER_SYSTEM_PROMPT,
        response_format=TurnDecision,
    )

    user_prompt = (
        f"session_id={session_id}\n"
        f"current_question_index={current_question_index}\n"
        f"total_questions={total_questions}\n"
        f"followup_count={followup_count}\n"
        f"current_question={question_text}\n"
        f"user_response={user_response}\n"
        "First call score_answer on user_response (mandatory, exactly once), "
        "then decide next action and provide response_text."
    )
    # Each agent iteration costs ~2 graph super-steps (model + tools), plus the
    # structured-response step; max(4, n) alone starves a real ReAct loop.
    return await react_agent.ainvoke(
        {"messages": [("user", user_prompt)]},
        config={"recursion_limit": max(4, 2 * max_iterations + 2)},
    )


def _extract_decision(react_result: Dict[str, Any]) -> Dict[str, Any]:
    structured = react_result.get("structured_response")
    if structured:
        if isinstance(structured, dict):
            return structured
        if hasattr(structured, "model_dump"):
            return structured.model_dump()

    messages = react_result.get("messages") or []
    if messages:
        last = messages[-1]
        content = getattr(last, "content", "")
        parsed = extract_json_from_llm(str(content))
        if isinstance(parsed, dict):
            return parsed
    return {"next_action": "next_question", "response_text": "", "reasoning": ""}


def _extract_tool_log_and_verdict(messages: List[Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    log_entries: List[Dict[str, Any]] = []
    latest_verdict: Dict[str, Any] = {}
    pending_calls: Dict[str, Dict[str, Any]] = {}

    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None) or []
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            call_id = str(call.get("id", ""))
            pending_calls[call_id] = {
                "tool": str(call.get("name", "unknown")),
                "args": call.get("args", {}) if isinstance(call.get("args"), dict) else {},
            }

        is_tool_message = getattr(msg, "type", "") == "tool" or msg.__class__.__name__ == "ToolMessage"
        if not is_tool_message:
            continue

        call_id = str(getattr(msg, "tool_call_id", ""))
        pending = pending_calls.pop(call_id, {})
        tool_name = pending.get("tool") or getattr(msg, "name", None) or "unknown"
        args = pending.get("args", {})
        content = getattr(msg, "content", "")
        parsed_content = extract_json_from_llm(str(content))
        if tool_name == "score_answer" and isinstance(parsed_content, dict):
            latest_verdict = parsed_content
        _append_tool_call_log(
            log_entries,
            tool=str(tool_name),
            args=args if isinstance(args, dict) else {},
            result=parsed_content if parsed_content is not None else str(content)[:500],
        )

    return log_entries, latest_verdict


def _manual_default_next_question(
    *,
    questions: List[Dict[str, Any]],
    current_idx: int,
) -> Dict[str, Any]:
    next_idx = current_idx + 1
    if next_idx >= len(questions):
        return {
            "phase": "closing",
            "next_action": "closing",
        }
    next_question = questions[next_idx]
    next_question_text = (
        next_question.get("customized_question")
        or next_question.get("question")
        or "Tell me more."
    )
    response = f"Thanks, that's helpful. Next question: {next_question_text}"
    return {
        "current_question_index": next_idx,
        "followup_count": 0,
        "phase": "questioning",
        "next_action": "next_question",
        "ai_response": response,
        "is_complete": False,
        "messages": [("assistant", response)],
    }


async def _manual_agent_fallback(state: InterviewState) -> Dict[str, Any]:
    current_idx, current_question, question_text = _current_question(state)
    questions = state.get("questions", [])
    if not question_text or current_question is None:
        return {"next_action": "closing", "phase": "closing"}

    user_response = (state.get("last_user_response") or "").strip()
    followup_count = int(state.get("followup_count", 0) or 0)
    evaluations = list(state.get("evaluations", []))
    tool_call_log = list(state.get("tool_call_log", []))
    max_iterations = max(1, int(getattr(settings, "max_agent_iterations", 4) or 4))

    if not user_response:
        if current_idx + 1 >= len(questions):
            return {"phase": "closing", "next_action": "closing", "tool_call_log": tool_call_log}
        result = _manual_default_next_question(questions=questions, current_idx=current_idx)
        result["tool_call_log"] = tool_call_log
        return result

    latest_verdict: Dict[str, Any] = {}
    latest_evaluation: Optional[Dict[str, Any]] = None
    iteration = 0
    chosen_action = "next_question"
    followup_text = ""

    while iteration < max_iterations:
        iteration += 1
        verdict = await score_answer.ainvoke({"question": question_text, "answer": user_response})
        latest_verdict = verdict if isinstance(verdict, dict) else {}
        _append_tool_call_log(
            tool_call_log,
            tool="score_answer",
            args={"question": question_text, "answer_length": len(user_response)},
            result=latest_verdict,
            error=latest_verdict.get("error"),
        )
        latest_evaluation = _to_turn_evaluation(latest_verdict)
        followup_needed = bool(latest_verdict.get("followup_needed", False))
        if followup_needed and followup_count < 1:
            gap = latest_verdict.get("suggested_followup_angle") or latest_evaluation.get("hint")
            generated_followup = await generate_followup.ainvoke(
                {"question": question_text, "answer": user_response, "gap": str(gap or "")}
            )
            generated_followup_text = str(generated_followup or "").strip()
            _append_tool_call_log(
                tool_call_log,
                tool="generate_followup",
                args={"question": question_text, "answer_length": len(user_response), "gap": str(gap or "")[:120]},
                result={"response_length": len(generated_followup_text)},
            )
            if generated_followup_text:
                followup_text = generated_followup_text
                chosen_action = "followup"
                followup_count += 1
                break
            logger.warning(
                "Fallback follow-up generation returned empty; defaulting to next_question."
            )
            break
        if current_idx + 1 >= len(questions):
            chosen_action = "closing"
            break
        search_results = await search_question_bank.ainvoke(
            {"query": current_question.get("category", "general"), "category": current_question.get("category", "general"), "k": 3}
        )
        _append_tool_call_log(
            tool_call_log,
            tool="search_question_bank",
            args={"query": current_question.get("category", "general"), "category": current_question.get("category", "general"), "k": 3},
            result={"count": len(search_results) if isinstance(search_results, list) else 0},
        )
        break

    if iteration >= max_iterations and chosen_action not in {"followup", "closing"}:
        _append_tool_call_log(
            tool_call_log,
            tool="agent_loop_guard",
            args={"max_agent_iterations": max_iterations},
            result={"action": "next_question"},
            error="iteration_cap_reached",
        )

    if chosen_action == "followup":
        ai_response = followup_text or "Could you share one concrete example?"
        if latest_evaluation:
            evaluations.append(latest_evaluation)
        return {
            "ai_response": ai_response,
            "phase": "followup",
            "next_action": "followup",
            "followup_count": followup_count,
            "is_complete": False,
            "messages": [("assistant", ai_response)],
            "last_evaluation": latest_evaluation,
            "evaluator_verdict": latest_verdict or None,
            "evaluations": evaluations,
            "tool_call_log": tool_call_log,
        }
    if chosen_action == "closing":
        if latest_evaluation:
            evaluations.append(latest_evaluation)
        return {
            "phase": "closing",
            "next_action": "closing",
            "last_evaluation": latest_evaluation,
            "evaluator_verdict": latest_verdict or None,
            "evaluations": evaluations,
            "tool_call_log": tool_call_log,
        }
    result = _manual_default_next_question(questions=questions, current_idx=current_idx)
    if latest_evaluation:
        evaluations.append(latest_evaluation)
    result.update(
        {
            "last_evaluation": latest_evaluation,
            "evaluator_verdict": latest_verdict or None,
            "evaluations": evaluations,
            "tool_call_log": tool_call_log,
        }
    )
    return result


async def interviewer_agent_turn(state: InterviewState) -> Dict[str, Any]:
    """
    ReAct-first interviewer node (option 2), with deterministic fallback.
    """
    if state.get("should_end"):
        return {"next_action": "closing", "phase": "closing"}

    current_idx, current_question, question_text = _current_question(state)
    questions = state.get("questions", [])
    if not question_text or current_question is None:
        return {"next_action": "closing", "phase": "closing"}

    user_response = (state.get("last_user_response") or "").strip()
    followup_count = int(state.get("followup_count", 0) or 0)
    tool_call_log = list(state.get("tool_call_log", []))
    evaluations = list(state.get("evaluations", []))
    max_iterations = max(1, int(getattr(settings, "max_agent_iterations", 4) or 4))

    try:
        react_result = await _run_react_agent_once(
            session_id=state.get("session_id", ""),
            question_text=question_text,
            user_response=user_response,
            followup_count=followup_count,
            total_questions=len(questions),
            current_question_index=current_idx,
            max_iterations=max_iterations,
        )
        react_messages = react_result.get("messages", [])
        extracted_log, latest_verdict = _extract_tool_log_and_verdict(react_messages)
        tool_call_log.extend(extracted_log)

        decision = _extract_decision(react_result)
        next_action = str(decision.get("next_action", "next_question"))
        if next_action not in {"followup", "next_question", "closing"}:
            logger.warning("Invalid next_action from ReAct agent: %s", next_action)
            next_action = "next_question"
        response_text = str(decision.get("response_text", "")).strip()

        latest_evaluation: Optional[Dict[str, Any]] = None
        if latest_verdict:
            latest_evaluation = _to_turn_evaluation(latest_verdict)
            evaluations.append(latest_evaluation)

        if next_action == "followup":
            if not response_text:
                response_text = (
                    "Thanks for sharing that. Could you walk me through one concrete example?"
                )
            return {
                "ai_response": response_text,
                "phase": "followup",
                "next_action": "followup",
                "followup_count": followup_count + 1,
                "is_complete": False,
                "messages": [("assistant", response_text)],
                "last_evaluation": latest_evaluation,
                "evaluator_verdict": latest_verdict or None,
                "evaluations": evaluations,
                "tool_call_log": tool_call_log,
            }

        if next_action == "closing" or current_idx + 1 >= len(questions):
            return {
                "phase": "closing",
                "next_action": "closing",
                "last_evaluation": latest_evaluation,
                "evaluator_verdict": latest_verdict or None,
                "evaluations": evaluations,
                "tool_call_log": tool_call_log,
            }

        next_idx = current_idx + 1
        if not response_text:
            next_question = questions[next_idx]
            next_question_text = (
                next_question.get("customized_question")
                or next_question.get("question")
                or "Tell me more."
            )
            response_text = f"Thanks, that's helpful. Next question: {next_question_text}"
        return {
            "current_question_index": next_idx,
            "followup_count": 0,
            "phase": "questioning",
            "next_action": "next_question",
            "ai_response": response_text,
            "is_complete": False,
            "messages": [("assistant", response_text)],
            "last_evaluation": latest_evaluation,
            "evaluator_verdict": latest_verdict or None,
            "evaluations": evaluations,
            "tool_call_log": tool_call_log,
        }
    except Exception as exc:
        logger.warning("ReAct interviewer fallback to deterministic loop: %s", exc)
        fallback = await _manual_agent_fallback(state)
        existing_log = list(fallback.get("tool_call_log", []))
        _append_tool_call_log(
            existing_log,
            tool="react_fallback",
            args={"max_agent_iterations": max_iterations},
            result={"fallback": "manual_agent_loop"},
            error=str(exc),
        )
        fallback["tool_call_log"] = existing_log
        return fallback


def route_after_interviewer_agent(state: InterviewState) -> str:
    action = str(state.get("next_action", "next_question"))
    route = NEXT_ACTION_ROUTE.get(action)
    if route is None:
        logger.error("Unknown next_action in route_after_interviewer_agent: %s", action)
        return "end"
    return route


def reset_interviewer_agent_runtime_cache() -> None:
    global _MCP_TOOLS_CACHE
    global _MCP_TOOLS_LOCK
    _MCP_TOOLS_CACHE = None
    _MCP_TOOLS_LOCK = None
