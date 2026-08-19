"""Knowledge base document listing + live semantic search."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.config import get_settings
from app.rag.chunker import parse_frontmatter
from app.tools.registry import get_vector_store, search_knowledge_base

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents")
async def list_documents() -> list[dict]:
    settings = get_settings()
    vs = get_vector_store()
    docs = []
    for path in sorted(settings.knowledge_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(raw)
        doc_id = meta.get("doc_id", path.stem)
        chunk_count = vs.client.count(
            vs.collection,
            count_filter=Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]),
            exact=True,
        ).count
        docs.append({
            "doc_id": doc_id,
            "title": meta.get("title", doc_id),
            "category": meta.get("category", "reference"),
            "version": meta.get("version", "1.0"),
            "owner": meta.get("owner", "unknown"),
            "chunk_count": chunk_count,
        })
    return docs


class KbSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    category: str | None = None


@router.post("/search")
async def search(req: KbSearchRequest) -> list[dict]:
    return search_knowledge_base(req.query, top_k=req.top_k, category=req.category)
