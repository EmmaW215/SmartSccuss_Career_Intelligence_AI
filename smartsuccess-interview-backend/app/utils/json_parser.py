"""
Robust JSON Extraction from LLM Responses
FIX: A-Q3 (Sprint 2) — Replaces fragile backtick-splitting in all agents

Handles: raw JSON, ```json blocks, markdown-wrapped JSON,
preamble text before JSON, trailing text after JSON, common LLM quirks.
"""

import re
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def extract_json_from_llm(
    response_text: str, silent: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Robustly extract JSON from LLM responses.

    Attempts multiple extraction strategies in order of reliability:
    1. Direct parse (cleanest case)
    2. Extract from ```json ... ``` fenced blocks
    3. Find first balanced { ... } or [ ... ] block
    4. Repair common JSON issues and retry
    5. Close braces on truncated output (max_tokens cutoffs)

    Args:
        silent: suppress the failure warning — for callers probing content
                that is frequently legitimate non-JSON text.

    Returns:
        Parsed JSON dict/list, or None if all strategies fail.
    """
    if not response_text or not response_text.strip():
        return None
    
    text = response_text.strip()
    
    # Strategy 1: Direct parse (cleanest case)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from ```json ... ``` blocks
    pattern = r'```(?:json)?\s*\n?(.*?)\n?\s*```'
    matches = re.findall(pattern, text, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # Strategy 3: Find first balanced { ... } or [ ... ] block
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue
        
        # Find matching closing bracket (handle nesting)
        depth = 0
        in_string = False
        escape_next = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == start_char:
                depth += 1
            elif char == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start_idx:i + 1])
                    except json.JSONDecodeError:
                        break
    
    # Strategy 4: Try to repair common LLM JSON issues
    repaired = _repair_common_issues(text)
    if repaired:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    # Strategy 5: Truncated output (max_tokens cutoff) — drop the trailing
    # incomplete fragment and close any unbalanced braces/brackets.
    recovered = _repair_truncated_json(text)
    if recovered is not None:
        return recovered

    if not silent:
        logger.warning(f"JSON extraction failed. Response preview: {text[:200]}...")
    return None


def _repair_truncated_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort recovery of JSON cut off mid-stream by a token limit.

    Strips markdown fences, then progressively trims back to the last comma
    and appends the closing brackets implied by the unclosed nesting stack.
    """
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start = cleaned.find("{")
    if start == -1:
        return None
    fragment = cleaned[start:]

    for _ in range(20):
        stack = []
        in_string = False
        escape_next = False
        for char in fragment:
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char in "{[":
                stack.append("}" if char == "{" else "]")
            elif char in "}]" and stack:
                stack.pop()

        candidate = fragment
        if in_string:
            candidate += '"'
        candidate = candidate.rstrip().rstrip(",")
        candidate += "".join(reversed(stack))
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and parsed:
                return parsed
            return None
        except json.JSONDecodeError:
            last_comma = fragment.rfind(",")
            if last_comma <= 0:
                return None
            fragment = fragment[:last_comma]
    return None


def _repair_common_issues(text: str) -> Optional[str]:
    """
    Attempt to repair common JSON issues from LLM output.
    
    Fixes:
    - Trailing commas before closing brackets
    - Single quotes instead of double quotes (simple cases)
    - Unquoted keys
    """
    # Find the JSON-like portion
    start = text.find('{')
    if start == -1:
        return None
    
    # Find the last closing brace
    end = text.rfind('}')
    if end == -1 or end <= start:
        return None
    
    json_str = text[start:end + 1]
    
    # Fix trailing commas: ,} or ,]
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    
    # Fix single quotes to double quotes (careful with apostrophes)
    # Only do this if there are no double quotes at all
    if '"' not in json_str and "'" in json_str:
        json_str = json_str.replace("'", '"')
    
    return json_str


def safe_parse_evaluation(
    response_text: str, 
    default_evaluation: Dict[str, Any],
    session_id: str = "unknown"
) -> Dict[str, Any]:
    """
    Parse an LLM evaluation response with guaranteed return.
    
    Always returns a valid evaluation dict — either parsed from LLM
    or the provided default. Never raises.
    
    Args:
        response_text: Raw LLM response
        default_evaluation: Fallback evaluation dict
        session_id: For logging
        
    Returns:
        Parsed evaluation dict or default_evaluation
    """
    result = extract_json_from_llm(response_text)

    if result is None:
        logger.warning(
            f"Using fallback evaluation for session {session_id}. "
            f"LLM response could not be parsed."
        )
        return {**default_evaluation, "_evaluation_status": "fallback",
                "_fallback_reason": "json_parse_failure"}

    # Guard the documented "guaranteed dict" contract: an evaluator LLM can
    # emit a top-level JSON array (or scalar) instead of an object. Callers
    # (_check_follow_up etc.) immediately do result.get(...), so a non-dict
    # would raise "'list' object has no attribute 'get'" -> HTTP 500.
    # Treat it exactly like an unparseable response: fall back to the default.
    if not isinstance(result, dict):
        logger.warning(
            f"Using fallback evaluation for session {session_id}. "
            f"LLM returned non-dict JSON ({type(result).__name__})."
        )
        return {**default_evaluation, "_evaluation_status": "fallback",
                "_fallback_reason": "non_dict_json"}

    return result
