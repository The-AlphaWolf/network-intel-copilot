"""Seeded synthetic KPI + log generator.

Deterministic: same DATA_SEED -> same bytes. Writes three files to data_out/:
  kpi_timeseries.csv   - 5-min granularity, 24h, all cells, all 10 KPIs
  network_logs.jsonl   - incident + light background log events
  cells.json           - topology (cells, sites, neighbor relations)

Run directly: `python -m app.data.generator`
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.data.scenarios import (
    BASELINE,
    CELLS,
    LOG_TEMPLATES,
    SCENARIOS,
    SITES,
    diurnal_factor,
    expected_baseline,
)

POINTS_PER_DAY = 288  # 24h * 60 / 5min
STEP_MINUTES = 5

CLIP_BOUNDS = {
    "rsrp_dbm": (-140.0, -55.0),
    "rsrq_db": (-20.0, -3.0),
    "sinr_db": (-10.0, 35.0),
    "latency_ms": (2.0, 400.0),
    "packet_loss_pct": (0.0, 25.0),
    "throughput_mbps": (0.0, 200.0),
    "prb_utilization_pct": (0.0, 100.0),
    "handover_success_rate_pct": (0.0, 100.0),
    "drop_rate_pct": (0.0, 20.0),
    "active_users": (0.0, 500.0),
}


def _ramp(hour: float, window: tuple[float, float] | None) -> float:
    """Ramp from 0->1 over the first 15% of the window, then hold at 1. Only
    ramps back down if the window closes before the end of the data (24h) -
    a window ending at/after 24 means the incident is still ongoing at
    "now", so it stays held rather than falling right at the data boundary."""
    if window is None:
        return 0.0
    start, end = window
    if start <= 0 and end >= 24:
        return 1.0  # persistent condition (e.g. physical coverage hole)
    if hour < start:
        return 0.0
    dur = max(end - start, 0.5)
    rise = min(1.0, (hour - start) / (dur * 0.15))
    if end >= 24:
        return max(0.0, min(rise, 1.0))  # held through end of data, no rampdown
    if hour > end:
        return 0.0
    fall = min(1.0, (end - hour) / (dur * 0.10))
    return max(0.0, min(rise, fall, 1.0))


def _cell_rng(base_seed: int, cell_id: str) -> np.random.Generator:
    # Stable per-cell seed derived from the cell_id string.
    offset = sum(ord(c) for c in cell_id)
    return np.random.default_rng(base_seed + offset)


def generate_kpi_dataframe(seed: int) -> pd.DataFrame:
    start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(hours=24)
    timestamps = [start + timedelta(minutes=STEP_MINUTES * i) for i in range(POINTS_PER_DAY)]
    hours = np.array([t.hour + t.minute / 60.0 for t in timestamps])

    rows: list[dict] = []
    for cell in CELLS:
        rng = _cell_rng(seed, cell.cell_id)
        scenario = SCENARIOS[cell.scenario]
        window = scenario["window"]
        effects = scenario["effects"]
        ramp = np.array([_ramp(h, window) for h in hours])

        series: dict[str, np.ndarray] = {}
        for kpi, (_, std) in BASELINE.items():
            base = np.array([expected_baseline(kpi, h)[0] for h in hours])

            effect = effects.get(kpi)
            noise_mult = effect.get("noise_mult", 1.0) if effect else 1.0
            noise = rng.normal(0.0, std * noise_mult, POINTS_PER_DAY)
            values = base + noise

            if effect:
                values = values + effect["peak_delta"] * ramp
                if "cap" in effect:
                    cap = effect["cap"]
                    values = np.minimum(values, cap + rng.normal(0, 0.4, POINTS_PER_DAY))

            lo, hi = CLIP_BOUNDS[kpi]
            values = np.clip(values, lo, hi)
            series[kpi] = values

        for i, ts in enumerate(timestamps):
            row = {"timestamp": ts.isoformat(), "cell_id": cell.cell_id}
            for kpi in BASELINE:
                v = series[kpi][i]
                row[kpi] = int(round(v)) if kpi == "active_users" else round(float(v), 3)
            rows.append(row)

    return pd.DataFrame(rows)


def generate_logs(seed: int) -> list[dict]:
    start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(hours=24)
    events: list[dict] = []

    for cell in CELLS:
        rng = _cell_rng(seed, cell.cell_id + "-logs")
        scenario_name = cell.scenario
        scenario = SCENARIOS[scenario_name]
        window = scenario["window"]

        # Background: sparse INFO health-check heartbeat for every cell.
        for _ in range(rng.integers(3, 7)):
            offset_min = int(rng.uniform(0, 24 * 60))
            events.append({
                "timestamp": (start + timedelta(minutes=offset_min)).isoformat(),
                "cell_id": cell.cell_id,
                "severity": "info",
                "event_type": "HEALTH_CHECK",
                "message": f"Periodic health check nominal for {cell.cell_id}",
            })

        # Incident-specific events, clustered inside the incident window.
        templates = LOG_TEMPLATES.get(scenario_name)
        if not templates or window is None:
            continue
        win_start, win_end = (0.0, 24.0) if (window[0] <= 0 and window[1] >= 24) else window
        n_events = int(rng.integers(6, 14))
        for _ in range(n_events):
            hour = float(rng.uniform(win_start, win_end))
            severity, event_type, template = templates[int(rng.integers(0, len(templates)))]
            offset_min = int(hour * 60)
            events.append({
                "timestamp": (start + timedelta(minutes=offset_min)).isoformat(),
                "cell_id": cell.cell_id,
                "severity": severity,
                "event_type": event_type,
                "message": template.format(cell_id=cell.cell_id),
            })

    events.sort(key=lambda e: e["timestamp"])
    return events


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def generate_cells_topology() -> dict:
    cells_out = []
    for cell in CELLS:
        site = SITES[cell.site]
        rng = _cell_rng(42, cell.cell_id + "-geo")
        jitter_lat = float(rng.uniform(-0.01, 0.01))
        jitter_lon = float(rng.uniform(-0.01, 0.01))
        cells_out.append({
            "cell_id": cell.cell_id,
            "site_id": cell.site,
            "site_name": site["name"],
            "band": cell.band,
            "technology": "5G-NR",
            "lat": round(site["lat"] + jitter_lat, 5),
            "lon": round(site["lon"] + jitter_lon, 5),
            "azimuth_deg": cell.azimuth_deg,
            "scenario": cell.scenario,
            "neighbor_ids": list(cell.neighbor_ids),
        })

    by_id = {c["cell_id"]: c for c in cells_out}
    neighbor_relations = []
    for cell in CELLS:
        src = by_id[cell.cell_id]
        for nid in cell.neighbor_ids:
            if nid not in by_id:
                continue
            dst = by_id[nid]
            dist = round(_haversine_km(src["lat"], src["lon"], dst["lat"], dst["lon"]), 3)
            # Deliberately break one relation to demonstrate a missing-neighbor
            # handover problem: BLR-5G-021 lists BLR-5G-010 nowhere, but
            # BLR-5G-010 is a physical neighbor at the same site -> "missing".
            status = "active"
            neighbor_relations.append({
                "cell_id": cell.cell_id,
                "neighbor_id": nid,
                "distance_km": dist,
                "relation_status": status,
            })

    # Missing relation: BLR-5G-021 <-> BLR-5G-010 (same site, no configured relation).
    src, dst = by_id["BLR-5G-021"], by_id["BLR-5G-010"]
    neighbor_relations.append({
        "cell_id": "BLR-5G-021",
        "neighbor_id": "BLR-5G-010",
        "distance_km": round(_haversine_km(src["lat"], src["lon"], dst["lat"], dst["lon"]), 3),
        "relation_status": "missing",
    })

    return {"sites": SITES, "cells": cells_out, "neighbor_relations": neighbor_relations}


def generate_all(force: bool = False) -> dict[str, Path]:
    settings = get_settings()
    out_dir = settings.data_out_dir
    csv_path = out_dir / "kpi_timeseries.csv"
    logs_path = out_dir / "network_logs.jsonl"
    cells_path = out_dir / "cells.json"

    if not force and csv_path.exists() and logs_path.exists() and cells_path.exists():
        return {"kpi": csv_path, "logs": logs_path, "cells": cells_path}

    seed = settings.data_seed
    df = generate_kpi_dataframe(seed)
    df.to_csv(csv_path, index=False, encoding="utf-8")

    logs = generate_logs(seed)
    with logs_path.open("w", encoding="utf-8") as f:
        for event in logs:
            f.write(json.dumps(event) + "\n")

    topology = generate_cells_topology()
    cells_path.write_text(json.dumps(topology, indent=2), encoding="utf-8")

    return {"kpi": csv_path, "logs": logs_path, "cells": cells_path}


if __name__ == "__main__":
    paths = generate_all(force=True)
    for name, path in paths.items():
        size_kb = path.stat().st_size / 1024
        print(f"{name}: {path} ({size_kb:.1f} KB)")
