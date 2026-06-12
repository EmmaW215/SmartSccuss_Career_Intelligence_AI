"""
Phase 3 — local custom-RAG builder (PRD 03 §A5, /upload dual mode).

When the GPU server is offline, customize uploads are processed locally:
document_loader.extract -> chunking.split -> EmbeddingService.embed
-> vector store `user_docs_{user_id}` collection -> profile extraction.

The profile extraction is the proven keyword implementation ported from
smartsuccess-phase2/gpu-server/services/rag_service.py (deterministic,
zero LLM cost). Response shape matches the GPU path exactly.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.core.embedding_service import EmbeddingService
from app.core.vector_store import get_vector_store
from app.rag.chunking import chunk_document
from app.rag.document_loader import load_documents

logger = logging.getLogger(__name__)

USER_DOCS_PREFIX = "user_docs"

TECH_SKILLS = [
    "python", "java", "javascript", "typescript", "go", "rust", "c++",
    "sql", "nosql", "mongodb", "postgresql", "mysql",
    "aws", "gcp", "azure", "docker", "kubernetes",
    "react", "vue", "angular", "node", "fastapi", "django", "flask",
    "machine learning", "deep learning", "ai", "llm", "rag", "nlp",
    "tensorflow", "pytorch", "langchain", "openai",
    "git", "ci/cd", "agile", "scrum",
]

JOB_TITLE_KEYWORDS = ["engineer", "developer", "manager", "scientist", "analyst", "architect"]


def user_docs_collection(user_id: str) -> str:
    return f"{USER_DOCS_PREFIX}_{user_id}"


def extract_profile(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Keyword-based candidate profile (ported from gpu-server rag_service)."""
    profile: Dict[str, Any] = {
        "technical_skills": [],
        "soft_skills": [],
        "industries": [],
        "education": [],
        "career_level": "mid",
        "job_target": {},
    }

    for doc in documents:
        text_lower = doc["text"].lower()

        for skill in TECH_SKILLS:
            if skill in text_lower and skill not in profile["technical_skills"]:
                profile["technical_skills"].append(skill)

        if doc["doc_type"] == "job_description":
            for line in doc["text"].split("\n")[:15]:
                line = line.strip()
                if 10 < len(line) < 100 and any(
                    word in line.lower() for word in JOB_TITLE_KEYWORDS
                ):
                    profile["job_target"]["title"] = line
                    break

    skills_count = len(profile["technical_skills"])
    if skills_count > 10:
        profile["career_level"] = "senior"
    elif skills_count > 5:
        profile["career_level"] = "mid"
    else:
        profile["career_level"] = "junior"

    return profile


async def build_local_rag(user_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a local custom RAG from uploaded files.

    Returns the same shape the GPU path returns:
    {"profile", "questions", "document_count", "rag_id"}
    """
    from app.rag.question_bank import select_customize_questions

    documents = load_documents(files)
    profile = extract_profile(documents)

    collection_id = user_docs_collection(user_id)
    store = get_vector_store()
    # Re-upload replaces previous content (privacy + freshness).
    store.delete_collection(collection_id)

    chunks: List[Dict[str, Any]] = []
    for doc in documents:
        chunks.extend(
            chunk_document(
                doc["text"],
                doc_type=doc["doc_type"],
                user_id=user_id,
                filename=doc["filename"],
            )
        )

    stored = 0
    if chunks:
        embedding_service = EmbeddingService()
        embeddings = await embedding_service.embed_batch(
            [chunk["content"] for chunk in chunks]
        )
        payload = [
            {
                "content": chunk["content"],
                "embedding": embedding,
                "metadata": chunk["metadata"],
            }
            for chunk, embedding in zip(chunks, embeddings)
            if embedding and any(embedding)
        ]
        if payload:
            store.add_documents(collection_id, payload)
            stored = len(payload)

    if stored == 0 and chunks:
        logger.warning(
            "Local RAG build for %s stored no vectors (embedding provider "
            "unavailable?) — interview proceeds without retrieval grounding",
            user_id,
        )

    questions = select_customize_questions(profile=profile)

    logger.info(
        "Local RAG build — user=%s docs=%d chunks_stored=%d questions=%d",
        user_id, len(documents), stored, len(questions),
    )
    return {
        "profile": profile,
        "questions": questions,
        "document_count": len(documents),
        "rag_id": f"local:{collection_id}",
    }


async def query_local_rag(user_id: str, query: str, k: int = 3) -> List[str]:
    """Retrieve snippets from a user's locally-built collection."""
    collection_id = user_docs_collection(user_id)
    store = get_vector_store()
    if store.count_documents(collection_id) == 0:
        return []

    embedding = await EmbeddingService().embed_text(query)
    if not embedding or not any(embedding):
        return []

    results = store.search(collection_id, embedding, k=k)
    return [result.document.content[:800] for result in results]


def delete_local_rag(user_id: str) -> bool:
    """Privacy: drop a user's uploaded-document collection."""
    return get_vector_store().delete_collection(user_docs_collection(user_id))
