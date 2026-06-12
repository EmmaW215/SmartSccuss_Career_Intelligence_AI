"""
Phase 2 agent tools with defensive boundaries.

Design goals:
- Explicit parameter caps for tool safety
- Never raise to the agent loop (return safe fallback payloads)
- Thin wrappers over existing app services/modules
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from langchain_core.tools import tool

from app.agents.evaluator_agent import get_evaluator_agent
from app.graph.llm import get_chat_model
from app.rag.question_bank import load_all_question_banks
from app.services.gpu_client import get_gpu_client

logger = logging.getLogger(__name__)

MAX_QUERY_CHARS = 500
MAX_QUESTION_CHARS = 500
MAX_ANSWER_CHARS = 3000
MAX_GAP_CHARS = 300
MAX_K = 10

_INTERVIEW_TYPE_CATEGORIES = {"screening", "behavioral", "technical"}


def _safe_text(value: Any, max_chars: int) -> str:
    return str(value or "").strip()[:max_chars]


def _safe_k(value: Any, default: int = 3) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if number < 1:
        return 1
    if number > MAX_K:
        return MAX_K
    return number


def _digest_result(payload: Any) -> str:
    data = str(payload).encode("utf-8", errors="ignore")
    return hashlib.sha1(data, usedforsecurity=False).hexdigest()[:12]


def _tool_log_record(tool_name: str, args: Dict[str, Any], result: Any) -> Dict[str, Any]:
    return {
        "tool": tool_name,
        "args": args,
        "result_digest": _digest_result(result),
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def _question_match_score(question: Dict[str, Any], query_terms: List[str]) -> int:
    haystack = (
        f"{question.get('question', '')} {question.get('category', '')} "
        f"{question.get('difficulty', '')}"
    ).lower()
    return sum(1 for term in query_terms if term and term in haystack)


async def _read_customize_state(session_id: str) -> Any:
    # Deferred import avoids circular dependency:
    # tools -> checkpoint_state_accessor -> customize_graph -> interviewer_agent -> tools
    from app.graph.checkpoint_state_accessor import GraphCheckpointStateAccessor

    return await GraphCheckpointStateAccessor.read_customize_state(session_id)


@tool
async def search_question_bank(
    query: str,
    category: str = "general",
    k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Search interview question bank by topic/skill.
    Use when the interviewer agent needs targeted next-question candidates.
    """
    safe_query = _safe_text(query, MAX_QUERY_CHARS)
    safe_category = _safe_text(category, 64).lower() or "general"
    safe_k = _safe_k(k)
    try:
        banks = load_all_question_banks()
        if safe_category in _INTERVIEW_TYPE_CATEGORIES:
            candidates = list(banks.get(safe_category, []))
        else:
            candidates = []
            for question_list in banks.values():
                candidates.extend(question_list)

        query_terms = [term for term in safe_query.lower().split() if len(term) >= 2][:12]
        if query_terms:
            ranked = sorted(
                candidates,
                key=lambda item: _question_match_score(item, query_terms),
                reverse=True,
            )
        else:
            ranked = candidates

        results: List[Dict[str, Any]] = []
        for question in ranked[:safe_k]:
            results.append(
                {
                    "id": question.get("id", ""),
                    "question": question.get("question", ""),
                    "category": question.get("category", "general"),
                    "difficulty": question.get("difficulty", "intermediate"),
                }
            )
        return results
    except Exception as exc:
        logger.warning("search_question_bank fallback: %s", exc)
        return []


@tool
async def fetch_resume_context(
    user_id: str,
    query: str,
    k: int = 3,
) -> List[str]:
    """
    Retrieve candidate resume/JD snippets.
    Falls back to empty list when RAG backend is unavailable.
    """
    safe_user_id = _safe_text(user_id, 128)
    safe_query = _safe_text(query, MAX_QUERY_CHARS)
    safe_k = _safe_k(k)
    if not safe_user_id or not safe_query:
        return []

    try:
        gpu_client = get_gpu_client()
        health = await gpu_client.check_health()
        if not health.get("available"):
            return []
        query_method = getattr(gpu_client, "query_custom_rag", None)
        if query_method is None:
            return []
        raw_result = await query_method(user_id=safe_user_id, query=safe_query, k=safe_k)
        if not isinstance(raw_result, list):
            return []
        snippets: List[str] = []
        for item in raw_result[:safe_k]:
            if isinstance(item, str):
                snippets.append(item[:800])
            elif isinstance(item, dict):
                text = _safe_text(item.get("text") or item.get("content"), 800)
                if text:
                    snippets.append(text)
        return snippets
    except Exception as exc:
        logger.warning("fetch_resume_context fallback: %s", exc)
        return []


@tool
async def score_answer(question: str, answer: str) -> Dict[str, Any]:
    """
    Get structured evaluator verdict for the current answer.
    """
    safe_question = _safe_text(question, MAX_QUESTION_CHARS)
    safe_answer = _safe_text(answer, MAX_ANSWER_CHARS)
    if not safe_question or not safe_answer:
        return {
            "error": "invalid_input",
            "score": 0.0,
            "followup_needed": True,
        }
    try:
        evaluator = get_evaluator_agent()
        verdict = await evaluator.evaluate_to_dict(
            question=safe_question,
            answer=safe_answer,
        )
        verdict["tool_log"] = _tool_log_record(
            "score_answer",
            {"question": safe_question, "answer_length": len(safe_answer)},
            {"score": verdict.get("score"), "followup_needed": verdict.get("followup_needed")},
        )
        return verdict
    except Exception as exc:
        logger.warning("score_answer fallback: %s", exc)
        fallback_result = {
            "error": "evaluator_unavailable",
            "score": 0.0,
            "dimension_scores": {
                "clarity": 0.0,
                "depth": 0.0,
                "relevance": 0.0,
                "structure": 0.0,
            },
            "strengths": [],
            "improvements": ["Evaluator temporarily unavailable."],
            "followup_needed": True,
            "suggested_followup_angle": "Ask for a concrete example.",
            "reasoning": "Fallback due to evaluator exception.",
        }
        fallback_result["tool_log"] = _tool_log_record(
            "score_answer",
            {"question": safe_question, "answer_length": len(safe_answer)},
            {"error": fallback_result["error"]},
        )
        return fallback_result


@tool
async def generate_followup(question: str, answer: str, gap: str) -> str:
    """
    Draft a single probing follow-up question for a specific gap.
    """
    safe_question = _safe_text(question, MAX_QUESTION_CHARS)
    safe_answer = _safe_text(answer, MAX_ANSWER_CHARS)
    safe_gap = _safe_text(gap, MAX_GAP_CHARS)
    if not safe_question or not safe_answer:
        return "Could you share one concrete example to support your answer?"

    prompt = (
        "Generate one concise interview follow-up question.\n"
        "Output only the question.\n"
        f"Question context: {safe_question}\n"
        f"Candidate answer: {safe_answer}\n"
        f"Gap to probe: {safe_gap}\n"
    )
    try:
        model = get_chat_model(tier="cheap")
        raw = await model.ainvoke(prompt)
        content = getattr(raw, "content", raw)
        text = _safe_text(content, 220).strip('"')
        if text:
            return text
    except Exception as exc:
        logger.warning("generate_followup fallback: %s", exc)
    return "Thanks for that. Could you walk me through one specific example and the measurable outcome?"


@tool
async def get_session_progress(session_id: str) -> Dict[str, Any]:
    """
    Read current interview progress from graph checkpoint state (read-only).
    """
    safe_session_id = _safe_text(session_id, 128)
    if not safe_session_id:
        return {"error": "invalid_session_id"}
    try:
        state = await _read_customize_state(safe_session_id)
        if not state:
            return {
                "session_id": safe_session_id,
                "found": False,
                "questions_answered": 0,
                "questions_total": 0,
                "is_complete": False,
                "followup_count": 0,
            }
        questions = state.get("questions", [])
        question_index = int(state.get("current_question_index", 0) or 0)
        return {
            "session_id": safe_session_id,
            "found": True,
            "questions_answered": question_index,
            "questions_total": len(questions) if isinstance(questions, list) else 0,
            "is_complete": bool(state.get("is_complete", False)),
            "followup_count": int(state.get("followup_count", 0) or 0),
            "phase": state.get("phase", "questioning"),
        }
    except Exception as exc:
        logger.warning("get_session_progress fallback: %s", exc)
        return {
            "session_id": safe_session_id,
            "found": False,
            "questions_answered": 0,
            "questions_total": 0,
            "is_complete": False,
            "followup_count": 0,
            "phase": "unknown",
            "error": "progress_unavailable",
        }


def get_agent_tools() -> List[Any]:
    return [
        search_question_bank,
        fetch_resume_context,
        score_answer,
        generate_followup,
        get_session_progress,
    ]
