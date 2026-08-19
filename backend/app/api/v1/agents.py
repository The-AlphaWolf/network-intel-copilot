"""Static supervisor-architecture description, enriched with the most recent
investigation's per-agent status if one has run."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.investigation_store import recent as recent_investigations

router = APIRouter(prefix="/agents", tags=["agents"])

ARCHITECTURE = [
    {
        "id": "supervisor", "name": "Supervisor", "role": "Coordinates the investigation: parses the request, routes to each specialist in sequence, writes the final summary.",
        "tools": [], "depends_on": [],
    },
    {
        "id": "network_analyst", "name": "Network Analyst", "role": "Pulls KPI time series, computes anomalies, searches logs, checks neighbor relations.",
        "tools": ["get_cell_status", "get_cell_kpis", "calculate_kpi_anomaly", "search_network_logs", "get_neighbor_cells"],
        "depends_on": ["supervisor"],
    },
    {
        "id": "rag_agent", "name": "RAG Agent", "role": "Generates targeted queries from the anomaly signature and retrieves cited technical documentation.",
        "tools": ["search_knowledge_base"], "depends_on": ["supervisor"],
    },
    {
        "id": "root_cause_agent", "name": "Root Cause Agent", "role": "Correlates all evidence into ranked root-cause hypotheses with confidence scores.",
        "tools": [], "depends_on": ["network_analyst", "rag_agent"],
    },
    {
        "id": "resolution_agent", "name": "Resolution Agent", "role": "Turns the top root cause into prioritized, citation-grounded remediation actions.",
        "tools": [], "depends_on": ["root_cause_agent"],
    },
]


@router.get("")
async def get_agents() -> dict:
    latest = recent_investigations(limit=1)
    last_status: dict[str, dict] = {}
    if latest:
        for event in latest[0].get("agent_execution", []):
            last_status[event["agent"]] = event
    return {"architecture": ARCHITECTURE, "last_run_status": last_status}
