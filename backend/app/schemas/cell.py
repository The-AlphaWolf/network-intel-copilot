"""Cell topology, status, log event, neighbor schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Cell(BaseModel):
    cell_id: str
    site_id: str
    site_name: str
    band: str
    technology: str = "5G-NR"
    lat: float
    lon: float
    azimuth_deg: int
    scenario: str  # "healthy" | "congestion" | "interference" | ...
    neighbor_ids: list[str] = []


class CellStatus(BaseModel):
    cell_id: str
    admin_state: str  # "active" | "maintenance"
    oper_state: str  # "up" | "degraded" | "down"
    active_alarms: list[str] = []
    health_score: float  # 0-100
    scenario: str


class LogEvent(BaseModel):
    timestamp: datetime
    cell_id: str
    severity: str  # "info" | "warning" | "critical"
    event_type: str
    message: str


class NeighborRelation(BaseModel):
    cell_id: str
    neighbor_id: str
    distance_km: float
    relation_status: str  # "active" | "missing" | "degraded"
    neighbor_health_score: float
