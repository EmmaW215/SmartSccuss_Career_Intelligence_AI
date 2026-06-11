"""
Phase 2 Agent Tools — Direct tool implementations

Every tool returns a dict with an "ok" flag instead of raising, so the
agent loop can feed errors back to the LLM and keep the interview going
(self-healing loop, PRD 02_PHASE2_AGENT_TOOLS.md).

Tools:
- search_question_bank   Query the lightweight question bank
- score_answer           Rubric-score a candidate answer (LLM with
                         deterministic heuristic fallback)
- get_candidate_profile  Resume/JD/session context for question targeting
- save_interview_note    Persist interviewer observations for the summary
"""

import json
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.rag.question_bank import get_questions_for_type

logger = logging.getLogger(__name__)

# Async callable: (prompt, system_prompt) -> str
LLMGenerateFn = Callable[..., Awaitable[str]]

# Rubric criteria per interview type (mirrors app.models feedback models)
SCORING_RUBRICS: Dict[str, List[str]] = {
    "screening": [
        "communication_clarity", "relevance", "specificity",
        "professionalism", "self_awareness",
    ],
    "behavioral": ["situation", "task", "action", "result"],
    "technical": [
        "technical_accuracy", "depth_of_knowledge", "practical_experience",
        "system_thinking", "communication_clarity",
    ],
}

# Specificity signals for the heuristic fallback scorer
_SPECIFICITY_PATTERN = re.compile(
    r"\d|%|\$|python|sql|aws|gcp|docker|kubernetes|langchain|fastapi|react",
    re.IGNORECASE,
)
_STAR_KEYWORDS = {
    "situation": ["situation", "context", "when i", "at the time", "we had"],
    "task": ["task", "goal", "responsible", "needed to", "my job"],
    "action": ["action", "i did", "i built", "i led", "i decided", "implemented"],
    "result": ["result", "outcome", "impact", "improved", "increased", "reduced"],
}


class AgentToolkit:
    """
    Direct tool implementations bound to a single interview round.

    session_context keys (all optional):
        session_id, interview_type, resume_text, job_description,
        questions_asked (list[str]), current_question_index (int)
    """

    def __init__(
        self,
        session_context: Optional[Dict[str, Any]] = None,
        llm_generate: Optional[LLMGenerateFn] = None,
    ):
        self.session_context = session_context or {}
        self.llm_generate = llm_generate
        self.notes: List[Dict[str, str]] = []

    # ================================================================
    # Tool: search_question_bank
    # ================================================================

    def search_question_bank(
        self,
        interview_type: str,
        category: Optional[str] = None,
        exclude_ids: Optional[List[str]] = None,
        limit: int = 3,
    ) -> Dict[str, Any]:
        """Search the question bank, optionally filtered by category."""
        questions = get_questions_for_type(interview_type)
        if not questions:
            return {
                "ok": False,
                "error": f"Unknown interview_type '{interview_type}'. "
                         f"Valid: screening, behavioral, technical",
            }

        exclude = set(exclude_ids or [])
        results = [
            {
                "id": q["id"],
                "question": q["question"],
                "category": q.get("category", ""),
                "evaluation_criteria": q.get("evaluation_criteria", []),
            }
            for q in questions
            if q["id"] not in exclude
            and (category is None or q.get("category") == category)
        ]
        return {
            "ok": True,
            "questions": results[: max(1, min(limit, 10))],
            "total_available": len(results),
        }

    # ================================================================
    # Tool: score_answer
    # ================================================================

    async def score_answer(
        self,
        question: str,
        answer: str,
        interview_type: str = "screening",
    ) -> Dict[str, Any]:
        """
        Score a candidate answer 1-5 on the rubric for the interview type.

        Uses the LLM when available; falls back to a deterministic
        heuristic so the agent loop never stalls on scoring.
        """
        if not answer or not answer.strip():
            return {"ok": False, "error": "Cannot score an empty answer"}

        criteria = SCORING_RUBRICS.get(interview_type, SCORING_RUBRICS["screening"])

        if self.llm_generate is not None:
            try:
                return await self._score_with_llm(
                    question, answer, interview_type, criteria
                )
            except Exception as e:
                logger.warning(f"LLM scoring failed, using heuristic: {e}")

        return self._score_heuristic(answer, interview_type, criteria)

    async def _score_with_llm(
        self,
        question: str,
        answer: str,
        interview_type: str,
        criteria: List[str],
    ) -> Dict[str, Any]:
        """LLM rubric scoring with strict JSON output."""
        prompt = (
            f"Score this {interview_type} interview answer on each criterion "
            f"from 1 (poor) to 5 (excellent).\n\n"
            f"Question: {question}\n"
            f"Answer: {answer}\n\n"
            f"Criteria: {', '.join(criteria)}\n\n"
            f'Reply with ONLY JSON: {{"scores": {{<criterion>: <int>}}, '
            f'"feedback": "<one sentence>"}}'
        )
        raw = await self.llm_generate(
            prompt=prompt,
            system_prompt="You are a strict interview evaluator. Output only valid JSON.",
        )
        # Tolerate code fences around the JSON
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
        scores = {
            c: max(1, min(5, int(parsed["scores"].get(c, 3)))) for c in criteria
        }
        overall = round(sum(scores.values()) / len(scores), 2)
        return {
            "ok": True,
            "scores": scores,
            "overall": overall,
            "feedback": str(parsed.get("feedback", "")),
            "method": "llm",
        }

    def _score_heuristic(
        self,
        answer: str,
        interview_type: str,
        criteria: List[str],
    ) -> Dict[str, Any]:
        """
        Deterministic fallback scoring based on length, structure and
        specificity signals. Bounded 1-5, same shape as LLM scoring.
        """
        words = answer.split()
        length_score = 1 + min(3, len(words) // 30)  # 1..4 by length
        specificity_hits = len(_SPECIFICITY_PATTERN.findall(answer))
        specificity_score = 1 + min(4, specificity_hits)  # 1..5

        scores: Dict[str, int] = {}
        answer_lower = answer.lower()
        for c in criteria:
            if interview_type == "behavioral" and c in _STAR_KEYWORDS:
                hit = any(kw in answer_lower for kw in _STAR_KEYWORDS[c])
                scores[c] = min(5, (3 if hit else 2) + (1 if length_score >= 3 else 0))
            elif c in ("specificity", "technical_accuracy", "practical_experience"):
                scores[c] = min(5, max(1, (specificity_score + length_score) // 2))
            else:
                scores[c] = min(5, max(1, length_score))

        overall = round(sum(scores.values()) / len(scores), 2)
        return {
            "ok": True,
            "scores": scores,
            "overall": overall,
            "feedback": "Heuristic score (LLM unavailable): based on answer "
                        "length, structure and specificity.",
            "method": "heuristic",
        }

    # ================================================================
    # Tool: get_candidate_profile
    # ================================================================

    def get_candidate_profile(self) -> Dict[str, Any]:
        """Return candidate/session context for question targeting."""
        ctx = self.session_context
        resume = (ctx.get("resume_text") or "").strip()
        jd = (ctx.get("job_description") or "").strip()
        return {
            "ok": True,
            "has_resume": bool(resume),
            "has_job_description": bool(jd),
            "resume_excerpt": resume[:800],
            "job_description_excerpt": jd[:800],
            "interview_type": ctx.get("interview_type", "screening"),
            "questions_already_asked": ctx.get("questions_asked", []),
            "current_question_index": ctx.get("current_question_index", 0),
        }

    # ================================================================
    # Tool: save_interview_note
    # ================================================================

    def save_interview_note(
        self, note: str, category: str = "general"
    ) -> Dict[str, Any]:
        """Save an interviewer observation for the final summary."""
        if not note or not note.strip():
            return {"ok": False, "error": "Note text is required"}
        self.notes.append({"category": category, "note": note.strip()})
        return {"ok": True, "note_count": len(self.notes)}
