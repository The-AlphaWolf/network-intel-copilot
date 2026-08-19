"""Embedder backends behind one Protocol so vectorstore/ingest never care which
model actually produced the vectors.

Default is `fastembed` (ONNX runtime, HF model BAAI/bge-small-en-v1.5,
384-dim, ~50MB) - avoids pulling in torch (2.5GB) for a task this small.
`sentence-transformers` stays available as an opt-in backend behind the same
interface. `fake` is deterministic (hash-based) and used by tests so they
never need model weights or network access.
"""
from __future__ import annotations

import hashlib
from typing import Protocol

from app.config import Settings, get_settings


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """HuggingFace model BAAI/bge-small-en-v1.5 via fastembed (ONNX)."""

    dim = 384

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class SentenceTransformerEmbedder:
    """Optional heavier backend (torch-based), same interface."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class FakeEmbedder:
    """Deterministic hash-based embedder. No model weights, no network.
    Used by tests and offline stub mode - same text always maps to the same
    vector, and different texts are (with very high probability) distinct."""

    dim = 64

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # 64 floats in [-1, 1] derived from the hash bytes, deterministic.
        return [(b / 127.5) - 1.0 for b in digest[: self.dim]] + [0.0] * max(
            0, self.dim - len(digest)
        )


def get_embedder(settings: Settings | None = None) -> Embedder:
    settings = settings or get_settings()
    backend = settings.embedding_backend
    if backend == "fastembed":
        return FastEmbedEmbedder(settings.embedding_model)
    if backend == "sentence-transformers":
        return SentenceTransformerEmbedder(settings.embedding_model)
    if backend == "fake":
        return FakeEmbedder()
    raise ValueError(f"Unknown embedding backend: {backend}")
