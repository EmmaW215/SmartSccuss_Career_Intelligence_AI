"""
Lightweight accessor for reading graph checkpoint state.

Keeps route layer simple and decouples state-fetch from response mapping.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.graph.customize_graph import get_customize_state_from_checkpoint


class GraphCheckpointStateAccessor:
    @staticmethod
    async def read_customize_state(session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        state = await get_customize_state_from_checkpoint(session_id=session_id)
        if not isinstance(state, dict):
            return None
        return state

    @staticmethod
    async def read_customize_field(session_id: str, field_name: str) -> Optional[Any]:
        state = await GraphCheckpointStateAccessor.read_customize_state(session_id)
        if not state:
            return None
        return state.get(field_name)
