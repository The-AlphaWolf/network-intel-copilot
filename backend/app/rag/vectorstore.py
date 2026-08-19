"""Qdrant wrapper. Embedded (on-disk) client by default so the demo runs with
no Docker daemon; set QDRANT_URL to point at a real server (e.g. the
docker-compose service) instead."""
from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import Settings, get_settings
from app.rag.chunker import Chunk
from app.rag.embeddings import Embedder

_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, chunk_id))


class VectorStore:
    def __init__(self, embedder: Embedder, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.embedder = embedder
        self.collection = self.settings.qdrant_collection
        if self.settings.qdrant_url:
            self.client = QdrantClient(url=self.settings.qdrant_url)
        else:
            self.client = QdrantClient(path=self.settings.qdrant_path)

    def ensure_collection(self, recreate: bool = False) -> None:
        exists = self.client.collection_exists(self.collection)
        if exists and not recreate:
            return
        if exists and recreate:
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=self.embedder.dim, distance=Distance.COSINE),
        )

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        vectors = self.embedder.embed([c.text for c in chunks])
        points = [
            PointStruct(
                id=_point_id(c.chunk_id),
                vector=vec,
                payload={
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "category": c.category,
                    "section": c.section,
                    "order": c.order,
                    "text": c.text,
                },
            )
            for c, vec in zip(chunks, vectors)
        ]
        self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    def count(self) -> int:
        if not self.client.collection_exists(self.collection):
            return 0
        return self.client.count(self.collection, exact=True).count

    def search(
        self, query: str, top_k: int = 5, category: str | None = None, score_threshold: float = 0.0
    ) -> list[dict]:
        vector = self.embedder.embed_query(query)
        query_filter = None
        if category:
            query_filter = Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=category))]
            )
        hits = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            query_filter=query_filter,
            score_threshold=score_threshold or None,
        ).points
        return [
            {
                "chunk_id": h.payload["chunk_id"],
                "doc_id": h.payload["doc_id"],
                "title": h.payload["title"],
                "section": h.payload["section"],
                "category": h.payload["category"],
                "text": h.payload["text"],
                "score": h.score,
            }
            for h in hits
        ]
