"""FastAPI application entrypoint. Run with:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.agents import router as agents_router
from app.api.v1.cells import router as cells_router
from app.api.v1.cells import topology_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.health import router as health_router
from app.api.v1.investigate import investigations_router
from app.api.v1.investigate import router as investigate_router
from app.api.v1.knowledge import router as knowledge_router
from app.config import get_settings
from app.data.store import get_store
from app.logging_conf import configure_logging, get_logger
from app.rag.ingest import ingest_into
from app.tools.registry import get_vector_store

configure_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("startup_begin", env=settings.app_env)

    store = get_store()
    logger.info("data_store_ready", cells=len(store.cell_ids()), kpi_rows=len(store.kpi_df))

    vs = get_vector_store()
    if vs.count() == 0:
        logger.info("qdrant_empty_ingesting")
        ingest_into(vs, recreate=True)
    logger.info("qdrant_ready", chunks=vs.count())

    logger.info("startup_complete")
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Network Intelligence Copilot API",
    description="AI-powered telecom network incident investigation system.",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(cells_router, prefix=API_PREFIX)
app.include_router(topology_router, prefix=API_PREFIX)
app.include_router(investigate_router, prefix=API_PREFIX)
app.include_router(investigations_router, prefix=API_PREFIX)
app.include_router(knowledge_router, prefix=API_PREFIX)
app.include_router(agents_router, prefix=API_PREFIX)
app.include_router(evaluation_router, prefix=API_PREFIX)


@app.get("/")
async def root() -> dict:
    return {"name": "Network Intelligence Copilot API", "docs": "/docs", "health": f"{API_PREFIX}/health"}
