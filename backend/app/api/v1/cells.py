"""Cell topology, KPI, neighbor, and network-health-overview endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.data.store import get_store
from app.tools.registry import ALL_KPI_NAMES

router = APIRouter(prefix="/cells", tags=["cells"])


@router.get("")
async def list_cells() -> list[dict]:
    store = get_store()
    out = []
    for cell_id, cell in store.cells.items():
        status = store.get_status(cell_id)
        out.append({**cell, **status})
    return out


@router.get("/{cell_id}")
async def get_cell(cell_id: str) -> dict:
    store = get_store()
    cell = store.get_cell(cell_id)
    if not cell:
        raise HTTPException(status_code=404, detail=f"unknown cell_id: {cell_id}")
    return {**cell, **store.get_status(cell_id)}


@router.get("/{cell_id}/kpis")
async def get_cell_kpis_endpoint(cell_id: str, hours: int = 24) -> dict:
    store = get_store()
    if not store.get_cell(cell_id):
        raise HTTPException(status_code=404, detail=f"unknown cell_id: {cell_id}")
    return store.get_kpi_series(cell_id, hours=hours)


@router.get("/{cell_id}/anomalies")
async def get_cell_anomalies(cell_id: str, hours: int = 6) -> list[dict]:
    store = get_store()
    if not store.get_cell(cell_id):
        raise HTTPException(status_code=404, detail=f"unknown cell_id: {cell_id}")
    return [store.anomaly(cell_id, kpi, hours=hours) for kpi in ALL_KPI_NAMES]


@router.get("/{cell_id}/neighbors")
async def get_cell_neighbors(cell_id: str) -> list[dict]:
    store = get_store()
    if not store.get_cell(cell_id):
        raise HTTPException(status_code=404, detail=f"unknown cell_id: {cell_id}")
    return store.get_neighbors(cell_id)


topology_router = APIRouter(tags=["cells"])


@topology_router.get("/topology")
async def get_topology() -> dict:
    store = get_store()
    cells = []
    for cell_id, cell in store.cells.items():
        status = store.get_status(cell_id)
        cells.append({**cell, **status})
    return {"sites": store.sites, "cells": cells, "neighbor_relations": store.neighbor_relations}


@topology_router.get("/overview")
async def get_overview() -> dict:
    """Backs the dashboard's top KPI cards."""
    store = get_store()
    cell_ids = store.cell_ids()
    anomaly_count = 0
    active_incidents = 0
    for cell_id in cell_ids:
        breached = [store.anomaly(cell_id, kpi, hours=6) for kpi in ALL_KPI_NAMES]
        breached = [a for a in breached if a["severity"] != "normal"]
        anomaly_count += len(breached)
        if any(a["severity"] == "critical" for a in breached):
            active_incidents += 1
    return {
        "active_incidents": active_incidents,
        "cells_monitored": len(cell_ids),
        "anomalies_24h": anomaly_count,
    }
