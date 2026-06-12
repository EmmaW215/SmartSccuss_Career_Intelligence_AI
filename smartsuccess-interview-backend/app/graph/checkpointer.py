"""
LangGraph checkpointer factory.

Provides a managed async context that yields either:
- Async SQLite checkpointer (preferred when available), or
- In-memory checkpointer fallback.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Literal, Optional

from app.config import settings

try:
    from langgraph.checkpoint.memory import MemorySaver
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    MemorySaver = None  # type: ignore[assignment]

try:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    AsyncSqliteSaver = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

CheckpointMode = Literal["sqlite", "memory"]
_MEMORY_CHECKPOINTER: Optional[Any] = None


def get_checkpoint_db_path() -> Path:
    """Resolve SQLite checkpoint path from settings/env with sane defaults."""
    configured = getattr(settings, "langgraph_checkpoint_db", None)
    env_override = os.getenv("LANGGRAPH_CHECKPOINT_DB")
    db_value = env_override or configured
    if db_value:
        return Path(db_value).expanduser()

    data_dir = Path(getattr(settings, "data_dir", "data"))
    return data_dir / "checkpoints" / "customize.sqlite"


def get_checkpoint_mode(prefer_sqlite: bool = True) -> CheckpointMode:
    env_mode = os.getenv("LANGGRAPH_CHECKPOINT_MODE", "").strip().lower()
    if env_mode in {"memory", "sqlite"}:
        return "sqlite" if env_mode == "sqlite" else "memory"

    if getattr(settings, "environment", "development") == "production":
        # Render free-tier filesystem is ephemeral; avoid implying durable state by default.
        return "memory"

    if prefer_sqlite and AsyncSqliteSaver is not None:
        return "sqlite"
    return "memory"


def _build_memory_checkpointer() -> Any:
    global _MEMORY_CHECKPOINTER
    if _MEMORY_CHECKPOINTER is not None:
        return _MEMORY_CHECKPOINTER
    if MemorySaver is None:
        raise RuntimeError(
            "MemorySaver is unavailable. Install langgraph to enable graph checkpointing."
        )
    _MEMORY_CHECKPOINTER = MemorySaver()
    return _MEMORY_CHECKPOINTER


def get_memory_checkpointer() -> Any:
    """Get singleton in-memory checkpointer."""
    return _build_memory_checkpointer()


@asynccontextmanager
async def checkpointer_context(
    *,
    prefer_sqlite: bool = True,
    db_path: Optional[Path] = None,
) -> AsyncIterator[Any]:
    """
    Yield a LangGraph checkpointer for graph compilation/execution.

    Usage:
        async with checkpointer_context() as checkpointer:
            graph = builder.compile(checkpointer=checkpointer)
            ...
    """
    mode = get_checkpoint_mode(prefer_sqlite=prefer_sqlite)
    if mode == "sqlite":
        resolved_path = (db_path or get_checkpoint_db_path()).expanduser()
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        conn_string = str(resolved_path)
        try:
            logger.info("Using SQLite graph checkpoint: %s", conn_string)
            async with AsyncSqliteSaver.from_conn_string(conn_string) as saver:  # type: ignore[union-attr]
                yield saver
            return
        except Exception as exc:
            logger.warning(
                "SQLite graph checkpoint failed (%s), falling back to memory.", exc
            )

    logger.warning("Falling back to in-memory graph checkpointing.")
    yield _build_memory_checkpointer()
