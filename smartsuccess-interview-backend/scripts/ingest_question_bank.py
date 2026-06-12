"""
Phase 3 Track A-5 — idempotent question-bank ingest (PRD 03 §A6).

Embeds every question from the JSON banks under data/ and upserts them into
the Chroma `question_bank` collection, keyed by content hash: re-running with
unchanged content is a no-op (overwrite in place), so this is safe to run on
every deploy. Render's disk is ephemeral per deploy — run this at release
time (render.yaml preDeploy/start hook or manually):

    USE_CHROMA_STORE=true python scripts/ingest_question_bank.py

Requires OPENAI_API_KEY (embeddings: ~1k questions ≈ a fraction of a cent).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main() -> None:
    from app.core.embedding_service import EmbeddingService
    from app.rag.chroma_store import ChromaVectorStore
    from app.rag.chunking import content_hash
    from app.rag.question_bank import load_all_question_banks

    from app.agents.tools import QUESTION_BANK_COLLECTION

    store = ChromaVectorStore()
    embedding_service = EmbeddingService()
    banks = load_all_question_banks()

    documents = []
    for category, questions in banks.items():
        for question in questions:
            text = (question.get("question") or "").strip()
            if not text:
                continue
            documents.append(
                {
                    "id": content_hash(f"{category}:{text}"),
                    "content": text,
                    "metadata": {
                        "question_id": question.get("id", ""),
                        "category": question.get("category", category),
                        "interview_type": category,
                        "difficulty": question.get("difficulty", "intermediate"),
                        "doc_type": "question",
                    },
                }
            )

    if not documents:
        raise SystemExit("No questions found under data/ — nothing to ingest.")

    before = store.count_documents(QUESTION_BANK_COLLECTION)
    print(f"Ingesting {len(documents)} questions (collection currently {before})...")

    batch_size = 64
    ingested = 0
    for start in range(0, len(documents), batch_size):
        batch = documents[start:start + batch_size]
        embeddings = await embedding_service.embed_batch([d["content"] for d in batch])
        payload = []
        for doc, embedding in zip(batch, embeddings):
            if not embedding or not any(embedding):
                print(f"  WARN: empty embedding for {doc['metadata']['question_id']}, skipped")
                continue
            payload.append({**doc, "embedding": embedding})
        if payload:
            store.upsert_documents(QUESTION_BANK_COLLECTION, payload)
            ingested += len(payload)
        print(f"  {min(start + batch_size, len(documents))}/{len(documents)}")

    after = store.count_documents(QUESTION_BANK_COLLECTION)
    print(f"Done: upserted {ingested}; collection size {before} -> {after} (idempotent).")


if __name__ == "__main__":
    asyncio.run(main())
