"""
Phase 3 — single chunking policy for the whole platform (PRD 03 §A4).

Every document type ingested anywhere (question bank, customize uploads,
resume/JD context) goes through this module so retrieval behaves the same
regardless of which store (NumPy / Chroma) sits underneath.

Policy:
| Content type     | Splitter                       | Size / overlap (tokens) |
|------------------|--------------------------------|-------------------------|
| question         | none (1 question = 1 doc)      | —                       |
| resume           | recursive, tiktoken encoder    | 512 / 64                |
| job_description  | recursive, tiktoken encoder    | 384 / 48                |
| supporting       | recursive, tiktoken encoder    | 512 / 64 (default)      |
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SEPARATORS = ["\n\n", "\n", ". "]


@dataclass(frozen=True)
class ChunkPolicy:
    chunk_size: int
    chunk_overlap: int


CHUNK_POLICIES: Dict[str, ChunkPolicy] = {
    "resume": ChunkPolicy(chunk_size=512, chunk_overlap=64),
    "job_description": ChunkPolicy(chunk_size=384, chunk_overlap=48),
    "supporting": ChunkPolicy(chunk_size=512, chunk_overlap=64),
}
DEFAULT_POLICY = CHUNK_POLICIES["supporting"]

# doc_type values that are atomic — never split.
ATOMIC_DOC_TYPES = {"question"}


def _build_splitter(policy: ChunkPolicy):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=policy.chunk_size,
        chunk_overlap=policy.chunk_overlap,
        separators=SEPARATORS,
    )


def _fallback_split(text: str, policy: ChunkPolicy) -> List[str]:
    """Char-approximation fallback when langchain/tiktoken is unavailable.
    ~4 chars/token keeps chunk granularity in the same ballpark."""
    size = policy.chunk_size * 4
    overlap = policy.chunk_overlap * 4
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += max(1, size - overlap)
    return chunks


def content_hash(text: str) -> str:
    """Stable content key for idempotent ingestion."""
    return hashlib.sha256(text.strip().encode("utf-8", errors="ignore")).hexdigest()[:16]


def chunk_document(
    text: str,
    *,
    doc_type: str,
    user_id: str = "",
    doc_id: Optional[str] = None,
    filename: str = "",
    created_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Split a document into chunks with the platform-wide policy.

    Returns a list of {"content": str, "metadata": {...}} dicts whose metadata
    always carries: user_id, doc_id, doc_type, filename, chunk_index,
    created_at — enabling per-user deletion (privacy) and filtered retrieval.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    normalized_type = (doc_type or "supporting").lower()
    resolved_doc_id = doc_id or content_hash(cleaned)
    resolved_created_at = created_at or datetime.now(timezone.utc).isoformat()

    if normalized_type in ATOMIC_DOC_TYPES:
        pieces = [cleaned]
    else:
        policy = CHUNK_POLICIES.get(normalized_type, DEFAULT_POLICY)
        try:
            pieces = _build_splitter(policy).split_text(cleaned)
        except Exception as exc:  # pragma: no cover - depends on optional deps
            logger.warning("tiktoken splitter unavailable (%s); using char fallback", exc)
            pieces = _fallback_split(cleaned, policy)

    chunks: List[Dict[str, Any]] = []
    for index, piece in enumerate(pieces):
        piece = piece.strip()
        if not piece:
            continue
        chunks.append(
            {
                "content": piece,
                "metadata": {
                    "user_id": user_id,
                    "doc_id": resolved_doc_id,
                    "doc_type": normalized_type,
                    "filename": filename,
                    "chunk_index": index,
                    "created_at": resolved_created_at,
                },
            }
        )
    return chunks
