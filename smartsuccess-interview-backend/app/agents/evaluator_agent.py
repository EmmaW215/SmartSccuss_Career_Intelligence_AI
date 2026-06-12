"""
Phase 2 evaluator agent contract.

This module defines a strict evaluator output schema and a resilient evaluator
runtime that always returns a valid contract, even when LLM calls fail.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.graph.llm import get_chat_model
from app.utils.json_parser import extract_json_from_llm

logger = logging.getLogger(__name__)

EVAL_DIMENSIONS = ("clarity", "depth", "relevance", "structure")
MAX_QUESTION_CHARS = 400
MAX_ANSWER_CHARS = 3000


class EvaluationVerdict(BaseModel):
    score: float = Field(ge=0, le=10)
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    followup_needed: bool = False
    suggested_followup_angle: Optional[str] = None
    reasoning: str = ""


def _normalize_model_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "\n".join(parts).strip()
    return str(content)


def _clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0:
        return 0.0
    if score > 10:
        return 10.0
    return score


def _normalize_dimension_scores(raw: Any, overall_score: float) -> Dict[str, float]:
    data = raw if isinstance(raw, dict) else {}
    normalized: Dict[str, float] = {}
    for dimension in EVAL_DIMENSIONS:
        normalized[dimension] = _clamp_score(data.get(dimension, overall_score))
    return normalized


def _fallback_verdict(question: str, answer: str) -> EvaluationVerdict:
    answer_len = len((answer or "").strip())
    if answer_len < 30:
        score = 4.0
        strengths = ["You responded to the question."]
        improvements = ["Add a concrete example and measurable outcome."]
        followup_needed = True
        angle = "Ask for a specific project example."
        reasoning = "Response is too brief for robust technical evaluation."
    elif answer_len < 120:
        score = 6.2
        strengths = ["The response stays relevant to the question."]
        improvements = ["Increase depth and explain trade-offs."]
        followup_needed = True
        angle = "Probe technical decision-making depth."
        reasoning = "Response has baseline relevance but limited detail."
    else:
        score = 7.8
        strengths = ["Response is structured and includes meaningful detail."]
        improvements = ["Add one concrete metric to strengthen impact."]
        followup_needed = False
        angle = None
        reasoning = "Response demonstrates adequate depth for this round."

    return EvaluationVerdict(
        score=score,
        dimension_scores=_normalize_dimension_scores({}, score),
        strengths=strengths[:3],
        improvements=improvements[:3],
        followup_needed=followup_needed,
        suggested_followup_angle=angle,
        reasoning=reasoning,
    )


def _normalize_verdict(verdict: EvaluationVerdict) -> EvaluationVerdict:
    score = _clamp_score(verdict.score)
    dimensions = _normalize_dimension_scores(verdict.dimension_scores, score)
    strengths = [str(item).strip() for item in verdict.strengths if str(item).strip()][:3]
    improvements = [
        str(item).strip() for item in verdict.improvements if str(item).strip()
    ][:3]
    reasoning = (verdict.reasoning or "").strip()
    followup_needed = bool(verdict.followup_needed)
    suggested_followup_angle = (
        verdict.suggested_followup_angle.strip()
        if verdict.suggested_followup_angle
        else None
    )
    return EvaluationVerdict(
        score=score,
        dimension_scores=dimensions,
        strengths=strengths,
        improvements=improvements,
        followup_needed=followup_needed,
        suggested_followup_angle=suggested_followup_angle,
        reasoning=reasoning,
    )


class EvaluatorAgent:
    """
    Independent evaluator agent for Phase 2.
    Contract-first: always returns a valid EvaluationVerdict.
    """

    async def evaluate(
        self,
        *,
        question: str,
        answer: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvaluationVerdict:
        safe_question = (question or "").strip()[:MAX_QUESTION_CHARS]
        safe_answer = (answer or "").strip()[:MAX_ANSWER_CHARS]
        if not safe_question or not safe_answer:
            return _fallback_verdict(safe_question, safe_answer)

        context_text = ""
        if context:
            context_pairs = [f"{k}: {v}" for k, v in context.items()]
            context_text = "\n".join(context_pairs)[:800]
        context_line = f"Context: {context_text}\n" if context_text else ""

        prompt = (
            "Evaluate the interview answer with strict rubric. "
            "Return JSON with keys:\n"
            "{"
            '"score": number(0-10),'
            '"dimension_scores": {"clarity":number,"depth":number,"relevance":number,"structure":number},'
            '"strengths":[string],'
            '"improvements":[string],'
            '"followup_needed": boolean,'
            '"suggested_followup_angle": string|null,'
            '"reasoning": string'
            "}\n"
            "Do not include extra keys.\n\n"
            f"Question: {safe_question}\n"
            f"Answer: {safe_answer}\n"
            f"{context_line}"
        )

        try:
            model = get_chat_model(tier="eval", force_provider="openai")
            if hasattr(model, "with_structured_output"):
                # function_calling: OpenAI strict json_schema mode rejects
                # free-form Dict fields like dimension_scores.
                structured_model = model.with_structured_output(
                    EvaluationVerdict, method="function_calling"
                )
                structured_result = await structured_model.ainvoke(prompt)
                if isinstance(structured_result, EvaluationVerdict):
                    return _normalize_verdict(structured_result)
                validated = EvaluationVerdict.model_validate(structured_result)
                return _normalize_verdict(validated)

            raw = await model.ainvoke(prompt)
            parsed = extract_json_from_llm(
                _normalize_model_content(getattr(raw, "content", raw))
            )
            validated = EvaluationVerdict.model_validate(parsed)
            return _normalize_verdict(validated)
        except Exception as exc:
            logger.warning("EvaluatorAgent fallback used: %s", exc, exc_info=True)
            return _fallback_verdict(safe_question, safe_answer)

    async def evaluate_to_dict(
        self,
        *,
        question: str,
        answer: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        verdict = await self.evaluate(question=question, answer=answer, context=context)
        return verdict.model_dump()


_EVALUATOR_AGENT: Optional[EvaluatorAgent] = None


def get_evaluator_agent() -> EvaluatorAgent:
    global _EVALUATOR_AGENT
    if _EVALUATOR_AGENT is None:
        _EVALUATOR_AGENT = EvaluatorAgent()
    return _EVALUATOR_AGENT
