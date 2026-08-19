"""knowledge/*.md -> chunks -> embeddings -> Qdrant.

Run directly: `python -m app.rag.ingest`
"""
from __future__ import annotations

from app.config import get_settings
from app.logging_conf import get_logger
from app.rag.chunker import chunk_document
from app.rag.embeddings import get_embedder
from app.rag.vectorstore import VectorStore

logger = get_logger("rag.ingest")


def load_documents() -> list[tuple[str, str]]:
    settings = get_settings()
    docs = []
    for path in sorted(settings.knowledge_dir.glob("*.md")):
        doc_id = path.stem.split("-", 1)[1] if "-" in path.stem else path.stem
        docs.append((doc_id, path.read_text(encoding="utf-8")))
    return docs


def ingest(recreate: bool = True) -> int:
    settings = get_settings()
    embedder = get_embedder(settings)
    store = VectorStore(embedder, settings)
    store.ensure_collection(recreate=recreate)

    total = 0
    for doc_id, raw in load_documents():
        chunks = chunk_document(doc_id, raw)
        n = store.upsert_chunks(chunks)
        logger.info("ingested_document", doc_id=doc_id, chunks=n)
        total += n

    logger.info("ingest_complete", total_chunks=total, collection=settings.qdrant_collection)
    return total


if __name__ == "__main__":
    count = ingest(recreate=True)
    print(f"Ingested {count} chunks into Qdrant collection.")
