"""
Phase 3 Track A-2 tests — ChromaVectorStore adapter + factory (PRD 03 §A).

Uses fake embeddings only: no network, no embedding model, no ONNX.
"""

import pytest

pytest.importorskip("chromadb", reason="chromadb not installed")

from app.core.vector_store import (
    VectorStore,
    VectorStoreProtocol,
    get_vector_store,
    reset_vector_store_singleton,
)
from app.rag.chroma_store import ChromaVectorStore, sanitize_collection_name


def _fake_embedding(seed: float) -> list:
    """Deterministic 8-dim unit-ish vectors; nearby seeds are similar."""
    return [seed, 1.0 - seed, seed / 2, 0.1, 0.2, 0.3, seed * seed, 1.0]


@pytest.fixture
def store(tmp_path):
    return ChromaVectorStore(persist_dir=str(tmp_path))


def _add_three_docs(store, collection="user_docs_test_user"):
    store.add_documents(
        collection,
        [
            {
                "content": "Built a RAG pipeline with ChromaDB and OpenAI embeddings.",
                "embedding": _fake_embedding(0.9),
                "metadata": {"user_id": "test_user", "doc_type": "resume", "chunk_index": 0},
            },
            {
                "content": "Led a team migrating services to Kubernetes.",
                "embedding": _fake_embedding(0.5),
                "metadata": {"user_id": "test_user", "doc_type": "resume", "chunk_index": 1},
            },
            {
                "content": "Job requires experience with LLM application development.",
                "embedding": _fake_embedding(0.1),
                "metadata": {"user_id": "test_user", "doc_type": "job_description", "chunk_index": 0},
            },
        ],
    )


class TestChromaStoreAdapter:
    def test_add_and_count(self, store):
        _add_three_docs(store)
        assert store.count_documents("user_docs_test_user") == 3

    def test_search_returns_results_in_similarity_order(self, store):
        _add_three_docs(store)
        results = store.search("user_docs_test_user", _fake_embedding(0.88), k=3)
        assert len(results) == 3
        assert results[0].score >= results[1].score >= results[2].score
        assert "RAG pipeline" in results[0].document.content
        # SearchResult/VectorDocument contract identical to NumPy store
        assert results[0].document.metadata["doc_type"] == "resume"

    def test_metadata_filter(self, store):
        _add_three_docs(store)
        results = store.search(
            "user_docs_test_user",
            _fake_embedding(0.5),
            k=3,
            metadata_filter={"doc_type": "job_description"},
        )
        assert len(results) == 1
        assert results[0].document.metadata["doc_type"] == "job_description"

    def test_metadata_filter_with_list_values(self, store):
        _add_three_docs(store)
        results = store.search(
            "user_docs_test_user",
            _fake_embedding(0.5),
            k=5,
            metadata_filter={"doc_type": ["resume", "job_description"]},
        )
        assert len(results) == 3

    def test_per_user_deletion_privacy(self, store):
        """PRD acceptance: delete user collection -> search returns empty."""
        _add_three_docs(store, collection="user_docs_privacy_user")
        assert store.count_documents("user_docs_privacy_user") == 3

        assert store.delete_collection("user_docs_privacy_user") is True
        assert store.count_documents("user_docs_privacy_user") == 0
        assert store.search("user_docs_privacy_user", _fake_embedding(0.9), k=3) == []

    def test_search_on_missing_collection_returns_empty(self, store):
        assert store.search("never_created", _fake_embedding(0.5), k=3) == []

    def test_persistence_across_client_instances(self, tmp_path):
        first = ChromaVectorStore(persist_dir=str(tmp_path))
        _add_three_docs(first, collection="persist_check")

        second = ChromaVectorStore(persist_dir=str(tmp_path))
        assert second.count_documents("persist_check") == 3

    def test_get_all_documents(self, store):
        _add_three_docs(store)
        docs = store.get_all_documents("user_docs_test_user")
        assert len(docs) == 3
        docs_filtered = store.get_all_documents(
            "user_docs_test_user", metadata_filter={"doc_type": "resume"}
        )
        assert len(docs_filtered) == 2

    def test_collection_name_sanitization(self):
        assert sanitize_collection_name("user docs/emma@example.com") == "user-docs-emma-example.com"
        assert len(sanitize_collection_name("x" * 100)) <= 63
        assert sanitize_collection_name("ab") == "ab-col"

    def test_protocol_conformance(self, store):
        assert isinstance(store, VectorStoreProtocol)
        assert isinstance(VectorStore(), VectorStoreProtocol)


class TestVectorStoreFactory:
    def test_flag_off_returns_numpy_store(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "use_chroma_store", False)
        reset_vector_store_singleton()
        try:
            assert isinstance(get_vector_store(), VectorStore)
        finally:
            reset_vector_store_singleton()

    def test_flag_on_returns_chroma_store(self, monkeypatch, tmp_path):
        from app.config import settings

        monkeypatch.setattr(settings, "use_chroma_store", True)
        monkeypatch.setattr(settings, "chroma_persist_dir", str(tmp_path))
        monkeypatch.setattr(settings, "chroma_remote_url", "")
        reset_vector_store_singleton()
        try:
            assert isinstance(get_vector_store(), ChromaVectorStore)
        finally:
            reset_vector_store_singleton()
