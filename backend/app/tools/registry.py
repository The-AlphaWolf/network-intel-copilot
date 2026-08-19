"""The six network investigation tools. Plain functions are canonical - used
directly by LangGraph nodes and wrapped as-is by the MCP server. LangChain
StructuredTool wrappers (`LC_TOOLS`) exist alongside them for any component
that wants a typed, describable tool object (agent frameworks, tracing)."""
from __future__ import annotations

from functools import lru_cache

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.config import get_settings
from app.data.store import get_store
from app.rag.embeddings import get_embedder
from app.rag.vectorstore import VectorStore


@lru_cache
def _vector_store() -> VectorStore:
    settings = get_settings()
    return VectorStore(get_embedder(settings), settings)


# ---------------------------------------------------------------------------
# Plain callables
# ---------------------------------------------------------------------------


def get_cell_kpis(cell_id: str, hours: int = 6, kpis: list[str] | None = None) -> dict:
    """Get KPI time series and summary stats for a cell over the last N hours."""
    return get_store().get_kpi_series(cell_id, hours=hours, kpis=kpis)


def get_cell_status(cell_id: str) -> dict:
    """Get a cell's operational state, active alarms, and computed health score."""
    result = get_store().get_status(cell_id)
    if result is None:
        return {"error": f"unknown cell_id: {cell_id}"}
    return result


def search_network_logs(
    cell_id: str | None = None,
    query: str | None = None,
    severity: str | None = None,
    hours: int = 6,
    limit: int = 50,
) -> list[dict]:
    """Search network log/alarm events, optionally filtered by cell, free-text query, and severity."""
    return get_store().search_logs(cell_id=cell_id, query=query, severity=severity, hours=hours, limit=limit)


def get_neighbor_cells(cell_id: str) -> list[dict]:
    """Get a cell's neighbor relations, each with the neighbor's health score and relation status."""
    return get_store().get_neighbors(cell_id)


def calculate_kpi_anomaly(cell_id: str, kpi: str, hours: int = 6) -> dict:
    """Compute a KPI's anomaly score for a cell: z-score vs the diurnal-aware
    healthy baseline, deviation percentage, and severity (rule-threshold and
    statistical z-score combined)."""
    return get_store().anomaly(cell_id, kpi, hours=hours)


def search_knowledge_base(query: str, top_k: int = 5, category: str | None = None) -> list[dict]:
    """Semantic search over the technical knowledge base. Returns cited chunks
    with doc_id, section, chunk_id, score - never fabricate a citation, only
    use chunk_ids returned here."""
    return _vector_store().search(query, top_k=top_k, category=category)


# ---------------------------------------------------------------------------
# LangChain StructuredTool wrappers (typed args schemas)
# ---------------------------------------------------------------------------


class _CellKpisArgs(BaseModel):
    cell_id: str = Field(description="Cell identifier, e.g. KOL-5G-017")
    hours: int = Field(default=6, description="Lookback window in hours")
    kpis: list[str] | None = Field(default=None, description="Subset of KPI names, or None for all")


class _CellIdArgs(BaseModel):
    cell_id: str = Field(description="Cell identifier, e.g. KOL-5G-017")


class _SearchLogsArgs(BaseModel):
    cell_id: str | None = Field(default=None, description="Restrict to this cell, or None for all cells")
    query: str | None = Field(default=None, description="Free-text filter over event_type/message")
    severity: str | None = Field(default=None, description="info | warning | critical")
    hours: int = Field(default=6, description="Lookback window in hours")
    limit: int = Field(default=50, description="Max events to return")


class _AnomalyArgs(BaseModel):
    cell_id: str = Field(description="Cell identifier, e.g. KOL-5G-017")
    kpi: str = Field(description="KPI field name, e.g. latency_ms")
    hours: int = Field(default=6, description="Lookback window in hours")


class _KbSearchArgs(BaseModel):
    query: str = Field(description="Natural-language search query")
    top_k: int = Field(default=5, description="Number of chunks to return")
    category: str | None = Field(default=None, description="Restrict to a doc category")


LC_TOOLS: list[StructuredTool] = [
    StructuredTool.from_function(func=get_cell_kpis, name="get_cell_kpis", args_schema=_CellKpisArgs),
    StructuredTool.from_function(func=get_cell_status, name="get_cell_status", args_schema=_CellIdArgs),
    StructuredTool.from_function(func=search_network_logs, name="search_network_logs", args_schema=_SearchLogsArgs),
    StructuredTool.from_function(func=get_neighbor_cells, name="get_neighbor_cells", args_schema=_CellIdArgs),
    StructuredTool.from_function(func=calculate_kpi_anomaly, name="calculate_kpi_anomaly", args_schema=_AnomalyArgs),
    StructuredTool.from_function(func=search_knowledge_base, name="search_knowledge_base", args_schema=_KbSearchArgs),
]

ALL_KPI_NAMES = [
    "rsrp_dbm", "rsrq_db", "sinr_db", "latency_ms", "packet_loss_pct",
    "throughput_mbps", "prb_utilization_pct", "handover_success_rate_pct",
    "drop_rate_pct", "active_users",
]
