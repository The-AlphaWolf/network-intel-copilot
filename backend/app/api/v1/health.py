"""Liveness + per-component system health."""
from __future__ import annotations

import sys
import time

from fastapi import APIRouter

from app.agents.llm import is_stub_mode
from app.config import get_settings
from app.data.store import get_store
from app.tools.registry import get_vector_store

router = APIRouter(tags=["health"])

_START_TIME = time.time()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "uptime_seconds": round(time.time() - _START_TIME, 1)}


@router.get("/health/system")
async def system_health() -> dict:
    settings = get_settings()
    components = []

    try:
        store = get_store()
        components.append({
            "name": "data_store", "status": "healthy",
            "detail": f"{len(store.cell_ids())} cells, {len(store.kpi_df)} KPI rows, {len(store.logs)} log events",
        })
    except Exception as exc:  # noqa: BLE001
        components.append({"name": "data_store", "status": "error", "detail": str(exc)})

    try:
        vs = get_vector_store()
        components.append({
            "name": "qdrant", "status": "healthy",
            "detail": f"{vs.count()} chunks in '{settings.qdrant_collection}' "
                      f"({'server: ' + settings.qdrant_url if settings.qdrant_url else 'embedded'})",
        })
    except Exception as exc:  # noqa: BLE001
        components.append({"name": "qdrant", "status": "error", "detail": str(exc)})

    components.append({
        "name": "embedder", "status": "healthy",
        "detail": f"{settings.embedding_backend} ({settings.embedding_model})",
    })

    components.append({
        "name": "llm", "status": "healthy" if not is_stub_mode() else "stub_mode",
        "detail": f"mode={settings.llm_mode}, model={settings.openai_model}" if not is_stub_mode()
                  else "LLM_MODE=stub - deterministic rule-based output, no external calls",
    })

    try:
        import mlflow  # noqa: F401
        components.append({"name": "mlflow", "status": "healthy", "detail": f"tracking_uri={settings.mlflow_tracking_uri}"})
    except ImportError:
        components.append({"name": "mlflow", "status": "not_installed", "detail": ""})

    overall = "healthy" if all(c["status"] in ("healthy", "stub_mode") for c in components) else "degraded"
    return {
        "status": overall,
        "components": components,
        "python_version": sys.version.split()[0],
        "app_env": settings.app_env,
    }
