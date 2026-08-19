"""Single source of truth for synthetic topology + incident scenario definitions.

Every cell, site, baseline KPI range, and incident signature lives here. The
generator (generator.py) reads this module and turns it into time series +
log events. Nothing about "what an incident looks like" is duplicated anywhere
else - the root-cause agent's expected answers in eval/ground_truth.json are
derived from this file too.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

SITES = {
    "KOL": {"name": "Kolkata-SaltLake", "lat": 22.5726, "lon": 88.3639},
    "DEL": {"name": "Delhi-Connaught", "lat": 28.6329, "lon": 77.2195},
    "MUM": {"name": "Mumbai-Andheri", "lat": 19.1136, "lon": 72.8697},
    "BLR": {"name": "Bangalore-Whitefield", "lat": 12.9698, "lon": 77.7500},
}

BANDS = ["n78", "n41", "n28"]

# ---------------------------------------------------------------------------
# Cells: cell_id -> definition. scenario "healthy" = no incident injected.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CellDef:
    cell_id: str
    site: str
    band: str
    azimuth_deg: int
    scenario: str
    neighbor_ids: tuple[str, ...] = field(default_factory=tuple)


CELLS: list[CellDef] = [
    # Kolkata site - 4 cells
    CellDef("KOL-5G-017", "KOL", "n78", 40, "congestion",
            ("KOL-5G-004", "KOL-5G-002", "KOL-5G-009")),
    CellDef("KOL-5G-004", "KOL", "n78", 160, "interference",
            ("KOL-5G-017", "KOL-5G-002")),
    CellDef("KOL-5G-002", "KOL", "n41", 280, "healthy",
            ("KOL-5G-017", "KOL-5G-004", "KOL-5G-009")),
    CellDef("KOL-5G-009", "KOL", "n78", 0, "healthy",
            ("KOL-5G-017", "KOL-5G-002")),
    # Delhi site - 3 cells
    CellDef("DEL-5G-009", "DEL", "n41", 90, "backhaul_degradation",
            ("DEL-5G-001", "DEL-5G-005")),
    CellDef("DEL-5G-001", "DEL", "n78", 210, "healthy",
            ("DEL-5G-009", "DEL-5G-005")),
    CellDef("DEL-5G-005", "DEL", "n28", 330, "healthy",
            ("DEL-5G-009", "DEL-5G-001")),
    # Mumbai site - 3 cells
    CellDef("MUM-5G-012", "MUM", "n28", 120, "poor_coverage",
            ("MUM-5G-003", "MUM-5G-008")),
    CellDef("MUM-5G-003", "MUM", "n78", 240, "healthy",
            ("MUM-5G-012", "MUM-5G-008")),
    CellDef("MUM-5G-008", "MUM", "n41", 0, "healthy",
            ("MUM-5G-012", "MUM-5G-003")),
    # Bangalore site - 4 cells
    CellDef("BLR-5G-021", "BLR", "n78", 60, "handover_problems",
            ("BLR-5G-002", "BLR-5G-006")),  # BLR-5G-010 relation deliberately missing
    CellDef("BLR-5G-002", "BLR", "n41", 180, "healthy",
            ("BLR-5G-021", "BLR-5G-006", "BLR-5G-010")),
    CellDef("BLR-5G-006", "BLR", "n78", 300, "healthy",
            ("BLR-5G-021", "BLR-5G-002", "BLR-5G-010")),
    CellDef("BLR-5G-010", "BLR", "n28", 20, "healthy",
            ("BLR-5G-002", "BLR-5G-006")),
]

CELL_IDS = [c.cell_id for c in CELLS]
CELLS_BY_ID = {c.cell_id: c for c in CELLS}

# ---------------------------------------------------------------------------
# Healthy baseline: (mean, std) per KPI, before diurnal shaping / incidents.
# ---------------------------------------------------------------------------

BASELINE: dict[str, tuple[float, float]] = {
    "rsrp_dbm": (-78.0, 4.0),
    "rsrq_db": (-9.0, 1.3),
    "sinr_db": (18.0, 2.5),
    "latency_ms": (16.0, 2.5),
    "packet_loss_pct": (0.15, 0.07),
    "throughput_mbps": (48.0, 7.0),
    "prb_utilization_pct": (32.0, 8.0),
    "handover_success_rate_pct": (99.1, 0.35),
    "drop_rate_pct": (0.28, 0.12),
    "active_users": (55.0, 12.0),
}

# KPIs whose healthy-cell mean naturally tracks the diurnal traffic curve.
# Anomaly detection (calculate_kpi_anomaly) and the generator both use
# expected_baseline() so a healthy cell at a busy hour is never mistaken for
# an anomaly - only a deviation from what THAT hour normally looks like counts.
TRAFFIC_COUPLED_KPIS = {"active_users", "prb_utilization_pct", "throughput_mbps"}


def diurnal_factor(hour: float) -> float:
    """0..1 traffic curve, trough ~04:00, peak ~19:00."""
    return 0.55 + 0.45 * math.sin(2 * math.pi * (hour - 10.0) / 24.0)


def expected_baseline(kpi: str, hour: float) -> tuple[float, float]:
    """Healthy-cell (mean, std) for `kpi` at a given hour-of-day (0-24)."""
    mean, std = BASELINE[kpi]
    if kpi == "prb_utilization_pct":
        mean = mean * (0.4 + 0.9 * diurnal_factor(hour))
    elif kpi == "active_users":
        mean = mean * (0.3 + 1.4 * diurnal_factor(hour))
    elif kpi == "throughput_mbps":
        mean = mean * (0.75 + 0.35 * diurnal_factor(hour))
    return mean, std

# ---------------------------------------------------------------------------
# Incident signatures. `window` = (start_hour, end_hour) within the 24h
# generation window (hour 0 = start of the synthetic day). `peak_delta` is the
# additive shift applied to the KPI mean at full incident intensity (reached
# via a smooth ramp over the first 15% of the window and held). `noise_mult`
# scales baseline std during the incident (e.g. backhaul jitter).
# `cap` (optional) clamps the KPI to `min(value, cap)` - used for throughput
# hard-capped by a saturated backhaul link.
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict] = {
    "healthy": {"window": None, "effects": {}},
    "congestion": {
        "window": (17, 23),
        "effects": {
            "prb_utilization_pct": {"peak_delta": 62.0, "noise_mult": 1.2},
            "active_users": {"peak_delta": 130.0, "noise_mult": 1.3},
            "latency_ms": {"peak_delta": 67.0, "noise_mult": 1.6},
            "packet_loss_pct": {"peak_delta": 2.05, "noise_mult": 1.8},
            "throughput_mbps": {"peak_delta": -30.0, "noise_mult": 1.3},
        },
    },
    "interference": {
        "window": (14, 22),
        "effects": {
            "sinr_db": {"peak_delta": -15.0, "noise_mult": 1.5},
            "rsrq_db": {"peak_delta": -7.5, "noise_mult": 1.4},
            "drop_rate_pct": {"peak_delta": 2.7, "noise_mult": 1.6},
            "throughput_mbps": {"peak_delta": -20.0, "noise_mult": 1.3},
        },
    },
    "backhaul_degradation": {
        "window": (9, 21),
        "effects": {
            "latency_ms": {"peak_delta": 124.0, "noise_mult": 3.0},
            "packet_loss_pct": {"peak_delta": 5.8, "noise_mult": 2.2},
            "throughput_mbps": {"peak_delta": -32.0, "noise_mult": 1.1, "cap": 9.0},
        },
    },
    "poor_coverage": {
        "window": (0, 24),  # persistent - it's a physical siting/tilt problem
        "effects": {
            "rsrp_dbm": {"peak_delta": -27.0, "noise_mult": 1.3},
            "rsrq_db": {"peak_delta": -5.0, "noise_mult": 1.3},
            "sinr_db": {"peak_delta": -6.0, "noise_mult": 1.3},
            "drop_rate_pct": {"peak_delta": 1.8, "noise_mult": 1.5},
            "handover_success_rate_pct": {"peak_delta": -6.0, "noise_mult": 1.4},
        },
    },
    "handover_problems": {
        "window": (10, 20),
        "effects": {
            "handover_success_rate_pct": {"peak_delta": -18.0, "noise_mult": 1.8},
            "drop_rate_pct": {"peak_delta": 1.4, "noise_mult": 1.5},
        },
    },
}

# Log event templates keyed by scenario, used by generator to write realistic
# network_logs.jsonl entries during the incident window.
LOG_TEMPLATES: dict[str, list[tuple[str, str, str]]] = {
    # (severity, event_type, message)
    "congestion": [
        ("warning", "PRB_THRESHOLD_CROSSED", "PRB utilization exceeded 90% threshold for {cell_id}"),
        ("warning", "RRC_CONN_REJECT", "RRC connection request rejected on {cell_id} due to admission control"),
        ("critical", "CAPACITY_LICENSE_LIMIT", "Active user count approaching licensed capacity on {cell_id}"),
    ],
    "interference": [
        ("warning", "PIM_ALARM", "Passive intermodulation interference detected on {cell_id}"),
        ("warning", "UL_NOISE_RISE", "Uplink noise rise above baseline on {cell_id}"),
        ("critical", "SINR_DEGRADED", "Sustained SINR degradation reported on {cell_id}"),
    ],
    "backhaul_degradation": [
        ("critical", "TRANSPORT_LINK_ERROR", "Backhaul transport link CRC errors detected for {cell_id}"),
        ("warning", "S1_LATENCY_HIGH", "S1-U interface latency above SLA for {cell_id}"),
        ("warning", "BACKHAUL_JITTER", "Excess jitter observed on backhaul link serving {cell_id}"),
    ],
    "poor_coverage": [
        ("warning", "RSRP_BELOW_THRESHOLD", "RSRP below -105 dBm threshold reported at cell edge of {cell_id}"),
        ("warning", "VSWR_ALARM", "VSWR alarm raised on antenna port for {cell_id}"),
        ("critical", "COVERAGE_HOLE_SUSPECTED", "Coverage hole suspected near {cell_id} based on drive-test correlation"),
    ],
    "handover_problems": [
        ("warning", "X2_HO_FAILURE", "X2 handover preparation failure from {cell_id}"),
        ("warning", "HO_PING_PONG", "Handover ping-pong detected between {cell_id} and neighbor"),
        ("critical", "NEIGHBOR_RELATION_MISSING", "Missing neighbor relation suspected impacting handovers from {cell_id}"),
    ],
}
