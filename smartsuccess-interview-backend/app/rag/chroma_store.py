"""
Phase 3 — persistent ChromaDB vector store (PRD 03 §A).

Implements the same public surface as app/core/vector_store.VectorStore
(VectorStoreProtocol) so callers cannot tell the difference; selection
happens in the get_vector_store() factory behind USE_CHROMA_STORE.

Render 512 MB guard:
- anonymized_telemetry=False
- embedding_function is NEVER used: every add/search passes pre-computed
  embeddings (OpenAI text-embedding-3-small via EmbeddingService), so
  Chroma's default ONNX model is never loaded.
- CHROMA_REMOTE_URL switches to an HttpClient without code changes.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.vector_store import SearchResult, VectorDocument

logger = logging.getLogger(__name__)

# Chroma collection names: 3-63 chars of [a-zA-Z0-9._-], alnum at both ends.
_NAME_SANITIZER = re.compile(r"[^a-zA-Z0-9._-]")


def sanitize_collection_name(collection_id: str) -> str:
    name = _NAME_SANITIZER.sub("-", str(collection_id))
    name = name.strip("._-") or "default"
    if len(name) < 3:
        name = f"{name}-col"
    return name[:63].rstrip("._-")


class ChromaVectorStore:
    """Persistent Chroma-backed implementation of VectorStoreProtocol."""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        remote_url: Optional[str] = None,
    ):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        chroma_settings = ChromaSettings(anonymized_telemetry=False, allow_reset=True)
        resolved_remote = (
            remote_url if remote_url is not None else getattr(settings, "chroma_remote_url", "")
        )
        if resolved_remote:
            from urllib.parse import urlparse

            parsed = urlparse(resolved_remote)
            self._client = chromadb.HttpClient(
                host=parsed.hostname or resolved_remote,
                port=parsed.port or 8000,
                ssl=parsed.scheme == "https",
                settings=chroma_settings,
            )
            logger.info("ChromaVectorStore using remote client: %s", resolved_remote)
        else:
            path = persist_dir or getattr(settings, "chroma_persist_dir", "data/chroma")
            self._client = chromadb.PersistentClient(path=path, settings=chroma_settings)
            logger.info("ChromaVectorStore using persistent client: %s", path)

    # ── collection helpers ──────────────────────────────────────────

    def _get_collection(self, collection_id: str, create: bool = False):
        name = sanitize_collection_name(collection_id)
        if create:
            return self._client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"}
            )
        try:
            return self._client.get_collection(name=name)
        except Exception:
            return None

    # ── VectorStoreProtocol surface ─────────────────────────────────

    def create_collection(self, collection_id: str) -> None:
        self._get_collection(collection_id, create=True)

    def delete_collection(self, collection_id: str) -> bool:
        name = sanitize_collection_name(collection_id)
        try:
            self._client.delete_collection(name=name)
            return True
        except Exception:
            return False

    def add_document(
        self,
        collection_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.add_documents(
            collection_id,
            [{"content": content, "embedding": embedding, "metadata": metadata or {}}],
        )[0]

    def add_documents(
        self,
        collection_id: str,
        documents: List[Dict[str, Any]],
    ) -> List[str]:
        if not documents:
            return []
        collection = self._get_collection(collection_id, create=True)

        ids: List[str] = []
        contents: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, Any]] = []
        for doc in documents:
            ids.append(str(uuid.uuid4()))
            contents.append(doc["content"])
            embeddings.append(doc["embedding"])
            # Chroma metadata values must be scalars; coerce defensively.
            metadata = {
                key: (value if isinstance(value, (str, int, float, bool)) else str(value))
                for key, value in (doc.get("metadata") or {}).items()
            }
            metadatas.append(metadata or {"_": "none"})

        collection.add(
            ids=ids, documents=contents, embeddings=embeddings, metadatas=metadatas
        )
        return ids

    def upsert_documents(
        self,
        collection_id: str,
        documents: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Idempotent ingest (Chroma-specific, used by scripts/ingest_question_bank.py):
        each document carries its own stable "id" (content hash) — re-running
        with unchanged content overwrites in place instead of duplicating.
        """
        if not documents:
            return []
        collection = self._get_collection(collection_id, create=True)
        ids = [str(doc["id"]) for doc in documents]
        collection.upsert(
            ids=ids,
            documents=[doc["content"] for doc in documents],
            embeddings=[doc["embedding"] for doc in documents],
            metadatas=[
                {
                    key: (value if isinstance(value, (str, int, float, bool)) else str(value))
                    for key, value in (doc.get("metadata") or {}).items()
                }
                or {"_": "none"}
                for doc in documents
            ],
        )
        return ids

    def search(
        self,
        collection_id: str,
        query_embedding: List[float],
        k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        collection = self._get_collection(collection_id)
        if collection is None or collection.count() == 0:
            return []

        where = self._build_where(metadata_filter)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        search_results: List[SearchResult] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for doc_id, content, metadata, distance in zip(ids, documents, metadatas, distances):
            similarity = 1.0 - float(distance)
            search_results.append(
                SearchResult(
                    document=VectorDocument(
                        id=doc_id,
                        content=content,
                        embedding=[],  # not returned; callers never read it
                        metadata=dict(metadata or {}),
                    ),
                    score=similarity,
                    distance=float(distance),
                )
            )
        return search_results

    def get_document(self, collection_id: str, document_id: str) -> Optional[VectorDocument]:
        collection = self._get_collection(collection_id)
        if collection is None:
            return None
        result = collection.get(ids=[document_id], include=["documents", "metadatas"])
        if not result.get("ids"):
            return None
        return VectorDocument(
            id=result["ids"][0],
            content=(result.get("documents") or [""])[0],
            embedding=[],
            metadata=dict((result.get("metadatas") or [{}])[0] or {}),
        )

    def get_all_documents(
        self,
        collection_id: str,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[VectorDocument]:
        collection = self._get_collection(collection_id)
        if collection is None:
            return []
        result = collection.get(
            where=self._build_where(metadata_filter), include=["documents", "metadatas"]
        )
        documents: List[VectorDocument] = []
        for doc_id, content, metadata in zip(
            result.get("ids", []),
            result.get("documents", []) or [],
            result.get("metadatas", []) or [],
        ):
            documents.append(
                VectorDocument(
                    id=doc_id, content=content, embedding=[], metadata=dict(metadata or {})
                )
            )
        return documents

    def count_documents(self, collection_id: str) -> int:
        collection = self._get_collection(collection_id)
        return collection.count() if collection is not None else 0

    def clear_all(self) -> None:
        for collection in self._client.list_collections():
            try:
                name = collection.name if hasattr(collection, "name") else str(collection)
                self._client.delete_collection(name=name)
            except Exception:  # pragma: no cover - best effort
                pass

    # ── helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _build_where(metadata_filter: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Translate the NumPy store's filter dict into a Chroma `where` clause."""
        if not metadata_filter:
            return None
        clauses = []
        for key, value in metadata_filter.items():
            if isinstance(value, list):
                clauses.append({key: {"$in": value}})
            else:
                clauses.append({key: value})
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}
