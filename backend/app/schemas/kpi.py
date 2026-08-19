"""KPI schemas shared by generator, tools, API, frontend contract."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# Single source of truth for which KPIs exist and their units/direction.
# "higher_is_better" drives anomaly severity direction in calculate_kpi_anomaly.
KPI_FIELDS: dict[str, dict] = {
    "rsrp_dbm": {"unit": "dBm", "higher_is_better": True},
    "rsrq_db": {"unit": "dB", "higher_is_better": True},
    "sinr_db": {"unit": "dB", "higher_is_better": True},
    "latency_ms": {"unit": "ms", "higher_is_better": False},
    "packet_loss_pct": {"unit": "%", "higher_is_better": False},
    "throughput_mbps": {"unit": "Mbps", "higher_is_better": True},
    "prb_utilization_pct": {"unit": "%", "higher_is_better": False},
    "handover_success_rate_pct": {"unit": "%", "higher_is_better": True},
    "drop_rate_pct": {"unit": "%", "higher_is_better": False},
    "active_users": {"unit": "count", "higher_is_better": None},
}


class KpiPoint(BaseModel):
    timestamp: datetime
    cell_id: str
    rsrp_dbm: float
    rsrq_db: float
    sinr_db: float
    latency_ms: float
    packet_loss_pct: float
    throughput_mbps: float
    prb_utilization_pct: float
    handover_success_rate_pct: float
    drop_rate_pct: float
    active_users: int


class KpiSeries(BaseModel):
    cell_id: str
    kpi: str
    points: list[dict] = Field(description="[{timestamp, value}, ...]")


class KpiSummary(BaseModel):
    cell_id: str
    kpi: str
    current: float
    baseline_mean: float
    baseline_std: float
    min: float
    max: float
    unit: str
