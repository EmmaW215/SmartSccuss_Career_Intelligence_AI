"""
Customize Interview LangGraph wiring (Phase 1).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from app.agents.interviewer_agent import (
    interviewer_agent_turn,
    route_after_interviewer_agent,
)
from app.config import settings
from app.graph.checkpointer import (
    checkpointer_context,
    get_checkpoint_mode,
    get_memory_checkpointer,
)
from app.graph.nodes import (
    ask_next_question,
    decide_next,
    evaluate_response,
    generate_closing,
    generate_followup,
    generate_greeting,
    route_after_decide,
    route_entry,
    understand_response,
)
from app.graph.state import InterviewState

try:
    from langgraph.graph import END, START, StateGraph
except (ImportError, ModuleNotFoundError):  # pragma: no cover
    StateGraph = None  # type: ignore[assignment]
    START = "__start__"  # type: ignore[assignment]
    END = "__end__"  # type: ignore[assignment]

logger = logging.getLogger(__name__)
_MEMORY_COMPILED_GRAPHS: Dict[bool, Any] = {}


def _create_customize_graph(use_agent_tools: bool) -> Any:
    if StateGraph is None:
        raise RuntimeError(
            "LangGraph is not installed. Install 'langgraph' and graph checkpoint dependencies."
        )

    graph_builder = StateGraph(InterviewState)

    graph_builder.add_node("generate_greeting", generate_greeting)
    graph_builder.add_node("understand_response", understand_response)
    if use_agent_tools:
        graph_builder.add_node("interviewer_agent_turn", interviewer_agent_turn)
    else:
        graph_builder.add_node("evaluate_response", evaluate_response)
        graph_builder.add_node("decide_next", decide_next)
        graph_builder.add_node("generate_followup", generate_followup)
        graph_builder.add_node("ask_next_question", ask_next_question)
    graph_builder.add_node("generate_closing", generate_closing)

    graph_builder.add_conditional_edges(
        START,
        route_entry,
        {
            "generate_greeting": "generate_greeting",
            "understand_response": "understand_response",
            "generate_closing": "generate_closing",
        },
    )
    graph_builder.add_edge("generate_greeting", END)
    if use_agent_tools:
        graph_builder.add_edge("understand_response", "interviewer_agent_turn")
        graph_builder.add_conditional_edges(
            "interviewer_agent_turn",
            route_after_interviewer_agent,
            {
                "generate_closing": "generate_closing",
                "end": END,
            },
        )
    else:
        graph_builder.add_edge("understand_response", "evaluate_response")
        graph_builder.add_edge("evaluate_response", "decide_next")
        graph_builder.add_conditional_edges(
            "decide_next",
            route_after_decide,
            {
                "generate_followup": "generate_followup",
                "ask_next_question": "ask_next_question",
                "generate_closing": "generate_closing",
            },
        )
        graph_builder.add_edge("generate_followup", END)
        graph_builder.add_edge("ask_next_question", END)
    graph_builder.add_edge("generate_closing", END)
    return graph_builder


async def _ainvoke_customize_graph(
    *,
    session_id: str,
    input_state: Dict[str, Any],
) -> Dict[str, Any]:
    use_agent_tools = bool(getattr(settings, "use_agent_tools", False))
    builder = _create_customize_graph(use_agent_tools)
    config = {"configurable": {"thread_id": session_id}}
    mode = get_checkpoint_mode()

    global _MEMORY_COMPILED_GRAPHS
    if mode == "memory":
        if use_agent_tools not in _MEMORY_COMPILED_GRAPHS:
            _MEMORY_COMPILED_GRAPHS[use_agent_tools] = builder.compile(
                checkpointer=get_memory_checkpointer()
            )
        return await _MEMORY_COMPILED_GRAPHS[use_agent_tools].ainvoke(
            input_state, config=config
        )

    async with checkpointer_context() as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        result = await graph.ainvoke(input_state, config=config)
    return result


async def _aget_customize_graph_state(*, session_id: str) -> Optional[Dict[str, Any]]:
    use_agent_tools = bool(getattr(settings, "use_agent_tools", False))
    builder = _create_customize_graph(use_agent_tools)
    config = {"configurable": {"thread_id": session_id}}
    mode = get_checkpoint_mode()

    async def _extract_values(compiled_graph: Any) -> Optional[Dict[str, Any]]:
        if hasattr(compiled_graph, "aget_state"):
            snapshot = await compiled_graph.aget_state(config)
        else:
            snapshot = compiled_graph.get_state(config)
        if snapshot is None:
            return None
        values = getattr(snapshot, "values", None)
        return values if isinstance(values, dict) else None

    global _MEMORY_COMPILED_GRAPHS
    if mode == "memory":
        if use_agent_tools not in _MEMORY_COMPILED_GRAPHS:
            _MEMORY_COMPILED_GRAPHS[use_agent_tools] = builder.compile(
                checkpointer=get_memory_checkpointer()
            )
        return await _extract_values(_MEMORY_COMPILED_GRAPHS[use_agent_tools])

    async with checkpointer_context() as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        return await _extract_values(graph)


async def start_customize_with_graph(
    *,
    user_id: str,
    user_name: Optional[str],
    questions: list[dict[str, Any]],
    session_id: Optional[str] = None,
    user_profile: Optional[dict[str, Any]] = None,
) -> Dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    initial_state: InterviewState = {
        "messages": [],
        "session_id": sid,
        "user_id": user_id,
        "user_name": user_name,
        "interview_type": "customize",
        "user_profile": user_profile,
        "questions": questions,
        "current_question_index": 0,
        "followup_count": 0,
        "phase": "greeting",
        "last_user_response": None,
        "should_end": False,
        "last_evaluation": None,
        "evaluations": [],
        "next_action": "next_question",
        "evaluator_verdict": None,
        "tool_call_log": [],
        "ai_response": None,
        "is_complete": False,
    }
    return await _ainvoke_customize_graph(session_id=sid, input_state=initial_state)


async def respond_customize_with_graph(
    *,
    session_id: str,
    user_response: str,
) -> Dict[str, Any]:
    update_state: Dict[str, Any] = {
        "last_user_response": user_response,
    }
    return await _ainvoke_customize_graph(session_id=session_id, input_state=update_state)


async def get_customize_state_from_checkpoint(*, session_id: str) -> Optional[Dict[str, Any]]:
    """Read latest customize interview state from graph checkpoint."""
    try:
        return await _aget_customize_graph_state(session_id=session_id)
    except Exception:
        logger.exception(
            "Failed to read customize graph state from checkpoint for session_id=%s",
            session_id,
        )
        return None


def reset_customize_graph_runtime_cache() -> None:
    """Test helper: reset cached graph builders and compiled graph instances."""
    global _MEMORY_COMPILED_GRAPHS
    _MEMORY_COMPILED_GRAPHS = {}
