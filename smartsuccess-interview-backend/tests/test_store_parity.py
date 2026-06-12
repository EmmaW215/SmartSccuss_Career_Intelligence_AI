"""
Phase 3 Track A-5 — retrieval parity test (PRD 03 §A6).

Same documents + same embeddings into both stores; for 20 fixed queries the
NumPy top-5 and Chroma top-5 must overlap >= 4/5 (only ANN/normalization
differences are tolerated).
"""

import numpy as np
import pytest

pytest.importorskip("chromadb", reason="chromadb not installed")

from app.core.vector_store import VectorStore
from app.rag.chroma_store import ChromaVectorStore

DIM = 64
N_DOCS = 60
N_QUERIES = 20
COLLECTION = "parity_check"


@pytest.fixture(scope="module")
def corpus():
    rng = np.random.RandomState(42)
    doc_vectors = rng.randn(N_DOCS, DIM)
    doc_vectors /= np.linalg.norm(doc_vectors, axis=1, keepdims=True)
    query_vectors = rng.randn(N_QUERIES, DIM)
    query_vectors /= np.linalg.norm(query_vectors, axis=1, keepdims=True)
    documents = [
        {
            "content": f"question {i}",
            "embedding": doc_vectors[i].tolist(),
            "metadata": {"idx": i},
        }
        for i in range(N_DOCS)
    ]
    return documents, query_vectors


def test_numpy_vs_chroma_top5_overlap(tmp_path_factory, corpus):
    documents, query_vectors = corpus

    numpy_store = VectorStore()
    numpy_store.add_documents(COLLECTION, documents)

    chroma_store = ChromaVectorStore(persist_dir=str(tmp_path_factory.mktemp("chroma")))
    chroma_store.add_documents(COLLECTION, documents)

    overlaps = []
    for q in range(N_QUERIES):
        query = query_vectors[q].tolist()
        numpy_top5 = {
            r.document.content for r in numpy_store.search(COLLECTION, query, k=5)
        }
        chroma_top5 = {
            r.document.content for r in chroma_store.search(COLLECTION, query, k=5)
        }
        overlap = len(numpy_top5 & chroma_top5)
        overlaps.append(overlap)
        assert overlap >= 4, (
            f"query {q}: top-5 overlap {overlap}/5 below parity threshold\n"
            f"numpy:  {sorted(numpy_top5)}\nchroma: {sorted(chroma_top5)}"
        )

    # Report aggregate for the PR evidence
    print(f"\nparity: mean top-5 overlap {np.mean(overlaps):.2f}/5 across {N_QUERIES} queries")


def test_scores_are_comparable(tmp_path_factory, corpus):
    """Cosine scores from both stores agree within numerical tolerance."""
    documents, query_vectors = corpus

    numpy_store = VectorStore()
    numpy_store.add_documents(COLLECTION, documents)
    chroma_store = ChromaVectorStore(persist_dir=str(tmp_path_factory.mktemp("chroma_s")))
    chroma_store.add_documents(COLLECTION, documents)

    query = query_vectors[0].tolist()
    numpy_best = numpy_store.search(COLLECTION, query, k=1)[0]
    chroma_best = chroma_store.search(COLLECTION, query, k=1)[0]
    assert numpy_best.document.content == chroma_best.document.content
    assert abs(numpy_best.score - chroma_best.score) < 0.01


def test_ingest_upsert_is_idempotent(tmp_path):
    """Content-hash keyed upsert: re-ingesting identical content is a no-op."""
    from app.rag.chunking import content_hash

    store = ChromaVectorStore(persist_dir=str(tmp_path))
    docs = [
        {
            "id": content_hash(f"q:{i}"),
            "content": f"question text {i}",
            "embedding": [float(i)] * 8,
            "metadata": {"category": "technical"},
        }
        for i in range(10)
    ]
    store.upsert_documents("question_bank", docs)
    assert store.count_documents("question_bank") == 10

    # Second run with identical content: same ids -> same count
    store.upsert_documents("question_bank", docs)
    assert store.count_documents("question_bank") == 10

    # Changed content under same id overwrites, new content adds
    docs[0]["content"] = "updated question text 0"
    new_doc = {
        "id": content_hash("q:new"),
        "content": "a brand new question",
        "embedding": [9.0] * 8,
        "metadata": {"category": "technical"},
    }
    store.upsert_documents("question_bank", docs + [new_doc])
    assert store.count_documents("question_bank") == 11
