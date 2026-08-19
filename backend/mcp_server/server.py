"""MCP server exposing the network investigation tools over stdio, reusing
the exact same functions the LangGraph agents call - zero duplication.

Run directly: `python -m mcp_server.server` (from backend/)
Or configure in an MCP client as a stdio server: `python -m mcp_server.server`
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from app.tools.registry import (
    calculate_kpi_anomaly,
    get_cell_kpis,
    get_cell_status,
    search_knowledge_base,
    search_network_logs,
)

mcp = MCPServer("network-intelligence-copilot")


@mcp.tool()
def get_cell_kpis_tool(cell_id: str, hours: int = 6, kpis: list[str] | None = None) -> dict:
    """Get KPI time series and summary stats for a cell over the last N hours."""
    return get_cell_kpis(cell_id, hours=hours, kpis=kpis)


@mcp.tool()
def get_cell_status_tool(cell_id: str) -> dict:
    """Get a cell's operational state, active alarms, and computed health score."""
    return get_cell_status(cell_id)


@mcp.tool()
def search_network_logs_tool(
    cell_id: str | None = None,
    query: str | None = None,
    severity: str | None = None,
    hours: int = 6,
    limit: int = 50,
) -> list[dict]:
    """Search network log/alarm events, optionally filtered by cell, free-text query, and severity."""
    return search_network_logs(cell_id=cell_id, query=query, severity=severity, hours=hours, limit=limit)


@mcp.tool()
def calculate_kpi_anomaly_tool(cell_id: str, kpi: str, hours: int = 6) -> dict:
    """Compute a KPI's anomaly score for a cell: z-score vs the diurnal-aware
    healthy baseline, deviation percentage, and severity."""
    return calculate_kpi_anomaly(cell_id, kpi, hours=hours)


@mcp.tool()
def search_knowledge_base_tool(query: str, top_k: int = 5, category: str | None = None) -> list[dict]:
    """Semantic search over the technical knowledge base. Returns cited chunks
    with doc_id, section, chunk_id, score - never fabricate a citation."""
    return search_knowledge_base(query, top_k=top_k, category=category)


if __name__ == "__main__":
    mcp.run(transport="stdio")
