import tempfile

from app.config import Settings
from app.rag.chunker import chunk_document
from app.rag.embeddings import FakeEmbedder
from app.rag.vectorstore import VectorStore

DOC = """---
doc_id: vs-test-doc
title: VS Test Doc
category: reference
---

## Alpha Section

Congestion and PRB utilization content here.

## Beta Section

Interference and SINR content here.
"""


def _isolated_store() -> VectorStore:
    tmp = tempfile.mkdtemp(prefix="nic_vs_test_")
    settings = Settings(qdrant_path=tmp + "/qdrant", qdrant_collection="vs_test", embedding_backend="fake")
    return VectorStore(FakeEmbedder(), settings)


def test_upsert_and_count():
    store = _isolated_store()
    store.ensure_collection(recreate=True)
    chunks = chunk_document("vs-test-doc", DOC)
    n = store.upsert_chunks(chunks)
    assert n == len(chunks)
    assert store.count() == len(chunks)


def test_upsert_empty_list_is_noop():
    store = _isolated_store()
    store.ensure_collection(recreate=True)
    assert store.upsert_chunks([]) == 0


def test_search_respects_top_k():
    store = _isolated_store()
    store.ensure_collection(recreate=True)
    store.upsert_chunks(chunk_document("vs-test-doc", DOC))
    results = store.search("congestion", top_k=1)
    assert len(results) <= 1


def test_search_returns_expected_payload_fields():
    store = _isolated_store()
    store.ensure_collection(recreate=True)
    store.upsert_chunks(chunk_document("vs-test-doc", DOC))
    results = store.search("congestion", top_k=5)
    assert results
    for r in results:
        assert set(["chunk_id", "doc_id", "title", "section", "text", "score"]).issubset(r)


def test_count_zero_before_ingest():
    store = _isolated_store()
    assert store.count() == 0
