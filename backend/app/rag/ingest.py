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


def ingest_into(store: VectorStore, recreate: bool = True) -> int:
    """Ingest all knowledge docs into an already-open VectorStore. Embedded
    Qdrant only permits one client per storage path within a process, so
    callers that already hold a VectorStore (e.g. the FastAPI lifespan) must
    reuse it rather than opening a second one."""
    store.ensure_collection(recreate=recreate)
    total = 0
    for doc_id, raw in load_documents():
        chunks = chunk_document(doc_id, raw)
        n = store.upsert_chunks(chunks)
        logger.info("ingested_document", doc_id=doc_id, chunks=n)
        total += n
    logger.info("ingest_complete", total_chunks=total, collection=store.collection)
    return total


def ingest(recreate: bool = True) -> int:
    """Standalone ingest: opens its own VectorStore. Only safe to call when
    nothing else in-process already holds a client on the same embedded path."""
    settings = get_settings()
    store = VectorStore(get_embedder(settings), settings)
    return ingest_into(store, recreate=recreate)


if __name__ == "__main__":
    count = ingest(recreate=True)
    print(f"Ingested {count} chunks into Qdrant collection.")
