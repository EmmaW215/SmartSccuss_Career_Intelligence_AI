"""
Phase 3 Track A-4 integration tests — /upload dual mode (PRD 03 §A5).

GPU offline -> local extract/chunk/embed/store pipeline -> 200 with
local: rag_id -> uploaded content retrievable via fetch_resume_context
(the exact call the interviewer agent makes during /respond).
"""

import hashlib

import pytest

from app.core.embedding_service import EmbeddingService
from app.core.vector_store import reset_vector_store_singleton

RESUME_TEXT = (
    "Emma Wang — Senior AI Engineer resume. Experience: built a LangGraph "
    "interview platform with Postgres checkpointing, ChromaDB retrieval and "
    "OpenAI embeddings. Skills: Python, FastAPI, Docker, RAG, LLM, education "
    "in Computer Science, employment at SmartSuccess."
)


def _fake_vector(text: str) -> list:
    """Deterministic pseudo-embedding: same text -> same vector; different
    texts -> different vectors. Good enough for retrieval-order tests."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [b / 255.0 for b in digest[:16]]


class _OfflineGpuClient:
    async def check_health(self, force: bool = False):
        return {"available": False, "services": {}, "latency_ms": 0}


@pytest.fixture
def fake_embeddings(monkeypatch):
    async def _embed_text(self, text: str):
        return _fake_vector(text)

    async def _embed_batch(self, texts):
        return [_fake_vector(t) for t in texts]

    monkeypatch.setattr(EmbeddingService, "embed_text", _embed_text)
    monkeypatch.setattr(EmbeddingService, "embed_batch", _embed_batch)


@pytest.fixture
def isolated_store():
    reset_vector_store_singleton()
    yield
    reset_vector_store_singleton()


class TestUploadDualMode:
    @pytest.mark.asyncio
    async def test_upload_succeeds_with_gpu_offline_and_content_is_retrievable(
        self, client, monkeypatch, fake_embeddings, isolated_store
    ):
        from app.api.routes import customize as customize_route

        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _OfflineGpuClient())

        resp = client.post(
            "/api/interview/customize/upload",
            data={"user_id": "dual_mode_user"},
            files={"files": ("emma_resume.txt", RESUME_TEXT.encode("utf-8"), "text/plain")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["success"] is True
        assert data["files_processed"] == 1
        assert str(data["rag_id"]).startswith("local:"), data["rag_id"]
        # Profile extracted from the document content
        assert "python" in data["profile"]["technical_skills"]
        assert data["selected_questions"], "questions must be selected for the interview"

        # Same-interview retrieval: fetch_resume_context is the exact tool the
        # interviewer agent calls during /respond.
        from app.agents.tools import fetch_resume_context

        snippets = await fetch_resume_context.ainvoke(
            {"user_id": "dual_mode_user", "query": "LangGraph interview platform", "k": 3}
        )
        assert snippets, "uploaded resume content must be retrievable"
        assert any("LangGraph" in snippet for snippet in snippets)

    @pytest.mark.asyncio
    async def test_gpu_path_unchanged_when_healthy(self, client, monkeypatch, isolated_store):
        from app.api.routes import customize as customize_route

        class _HealthyGpuClient:
            async def check_health(self, force: bool = False):
                return {"available": True, "services": {"rag": True}, "latency_ms": 5}

            async def build_custom_rag(self, user_id, files):
                return {
                    "profile": {"technical_skills": ["python"]},
                    "questions": [{"id": "q1", "question": "Tell me about yourself."}],
                    "document_count": len(files),
                    "rag_id": f"custom_rag_{user_id}",
                }

        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _HealthyGpuClient())

        resp = client.post(
            "/api/interview/customize/upload",
            data={"user_id": "gpu_user"},
            files={"files": ("resume.txt", b"python developer resume", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["rag_id"] == "gpu:custom_rag_gpu_user"

    @pytest.mark.asyncio
    async def test_local_rag_privacy_deletion(self, fake_embeddings, isolated_store):
        from app.rag.local_rag import build_local_rag, delete_local_rag, query_local_rag

        await build_local_rag(
            "privacy_user",
            [{"filename": "resume.txt", "content": RESUME_TEXT, "content_type": "text/plain"}],
        )
        assert await query_local_rag("privacy_user", "LangGraph", k=2)

        assert delete_local_rag("privacy_user") is True
        assert await query_local_rag("privacy_user", "LangGraph", k=2) == []

    @pytest.mark.asyncio
    async def test_dual_mode_works_with_chroma_flag_on(
        self, client, monkeypatch, fake_embeddings, tmp_path
    ):
        from app.api.routes import customize as customize_route
        from app.config import settings

        monkeypatch.setattr(settings, "use_chroma_store", True)
        monkeypatch.setattr(settings, "chroma_persist_dir", str(tmp_path))
        monkeypatch.setattr(settings, "chroma_remote_url", "")
        reset_vector_store_singleton()
        try:
            monkeypatch.setattr(
                customize_route, "get_gpu_client", lambda: _OfflineGpuClient()
            )
            resp = client.post(
                "/api/interview/customize/upload",
                data={"user_id": "chroma_dual_user"},
                files={"files": ("emma_resume.txt", RESUME_TEXT.encode("utf-8"), "text/plain")},
            )
            assert resp.status_code == 200, resp.text
            assert str(resp.json()["rag_id"]).startswith("local:")

            from app.rag.local_rag import query_local_rag

            snippets = await query_local_rag("chroma_dual_user", "ChromaDB retrieval", k=2)
            assert snippets
        finally:
            reset_vector_store_singleton()
