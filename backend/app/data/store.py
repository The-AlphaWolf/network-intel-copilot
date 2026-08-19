"""Load-once in-memory store over generated synthetic data + query helpers.
Backs every tool in tools/registry.py. Cached at module level via get_store() -
call that everywhere rather than re-reading files or re-instantiating.
"""
from __future__ import annotations

import json
import math
from datetime import timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

from app.data.generator import generate_all
from app.data.scenarios import BASELINE, expected_baseline

# Static severity bands, matching knowledge/01-kpi-definitions-thresholds.md.
# Each entry: (kpi -> list of (bound, severity)) evaluated in the "bad
# direction" for that KPI (lower-is-worse KPIs use ascending bounds meaning
# "value <= bound"; higher-is-worse KPIs use "value >= bound").
_LOWER_IS_WORSE = {
    # kpi: [(bound, severity), ...] ascending bound, "value <= bound" triggers
    "rsrp_dbm": [(-115, "critical"), (-105, "warning")],
    "rsrq_db": [(-15, "warning")],
    "sinr_db": [(0, "critical"), (13, "warning")],
    "handover_success_rate_pct": [(95, "critical"), (98, "warning")],
}
_HIGHER_IS_WORSE = {
    # kpi: [(bound, severity), ...] ascending bound, "value >= bound" triggers
    "latency_ms": [(100, "critical"), (50, "warning")],
    "packet_loss_pct": [(5, "critical"), (2, "warning")],
    "prb_utilization_pct": [(95, "critical"), (85, "warning")],
    "drop_rate_pct": [(1.5, "critical"), (0.5, "warning")],
}


def classify_threshold(kpi: str, value: float) -> str:
    """Rule-based severity from the KPI spec thresholds, independent of the
    statistical z-score. 'normal' if no band is breached or no bands defined."""
    if kpi in _LOWER_IS_WORSE:
        for bound, sev in _LOWER_IS_WORSE[kpi]:  # bounds pre-sorted worst-first
            if value <= bound:
                return sev
        return "normal"
    if kpi in _HIGHER_IS_WORSE:
        for bound, sev in _HIGHER_IS_WORSE[kpi]:
            if value >= bound:
                return sev
        return "normal"
    return "normal"


_SEVERITY_RANK = {"normal": 0, "warning": 1, "critical": 2}


def combine_severity(a: str, b: str) -> str:
    return a if _SEVERITY_RANK[a] >= _SEVERITY_RANK[b] else b


class NetworkDataStore:
    def __init__(self):
        paths = generate_all()
        self.kpi_df = pd.read_csv(paths["kpi"], parse_dates=["timestamp"])
        self.kpi_df["timestamp"] = pd.to_datetime(self.kpi_df["timestamp"], utc=True)

        with open(paths["logs"], encoding="utf-8") as f:
            self.logs = [json.loads(line) for line in f if line.strip()]
        for e in self.logs:
            e["timestamp"] = pd.Timestamp(e["timestamp"])

        topo = json.loads(paths["cells"].read_text(encoding="utf-8"))
        self.sites = topo["sites"]
        self.cells = {c["cell_id"]: c for c in topo["cells"]}
        self.neighbor_relations = topo["neighbor_relations"]

        self.now = self.kpi_df["timestamp"].max()

    # -- cells / topology ---------------------------------------------------

    def cell_ids(self) -> list[str]:
        return list(self.cells.keys())

    def get_cell(self, cell_id: str) -> dict | None:
        return self.cells.get(cell_id)

    def get_neighbors(self, cell_id: str) -> list[dict]:
        out = []
        for rel in self.neighbor_relations:
            if rel["cell_id"] != cell_id:
                continue
            neighbor = self.cells.get(rel["neighbor_id"], {})
            out.append({
                **rel,
                "neighbor_health_score": self.health_score(rel["neighbor_id"]),
                "neighbor_scenario": neighbor.get("scenario", "unknown"),
            })
        return out

    # -- KPIs -----------------------------------------------------------

    def window(self, cell_id: str, hours: int) -> pd.DataFrame:
        cutoff = self.now - timedelta(hours=hours)
        df = self.kpi_df
        return df[(df.cell_id == cell_id) & (df.timestamp > cutoff)].sort_values("timestamp")

    def get_kpi_series(self, cell_id: str, hours: int = 6, kpis: list[str] | None = None) -> dict:
        df = self.window(cell_id, hours)
        kpi_list = kpis or list(BASELINE.keys())
        series = {}
        summary = {}
        for kpi in kpi_list:
            if kpi not in df.columns:
                continue
            vals = df[kpi]
            series[kpi] = [
                {"timestamp": ts.isoformat(), "value": float(v)}
                for ts, v in zip(df["timestamp"], vals)
            ]
            summary[kpi] = {
                "current": float(vals.iloc[-1]) if len(vals) else None,
                "mean": float(vals.mean()) if len(vals) else None,
                "min": float(vals.min()) if len(vals) else None,
                "max": float(vals.max()) if len(vals) else None,
            }
        return {"cell_id": cell_id, "hours": hours, "series": series, "summary": summary}

    def anomaly(self, cell_id: str, kpi: str, hours: int = 6) -> dict:
        df = self.window(cell_id, hours)
        if df.empty or kpi not in df.columns:
            return {
                "cell_id": cell_id, "kpi": kpi, "hours": hours,
                "current": None, "z_score": 0.0, "deviation_pct": 0.0,
                "severity": "normal", "breached_threshold": False,
            }

        hours_of_day = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60.0
        expected = hours_of_day.apply(lambda h: expected_baseline(kpi, h))
        exp_mean = expected.apply(lambda t: t[0])
        exp_std = expected.apply(lambda t: t[1]).replace(0, 1e-6)

        z = ((df[kpi] - exp_mean) / exp_std)
        current = float(df[kpi].iloc[-1])
        current_z = float(z.iloc[-1])
        mean_z = float(z.abs().mean())
        baseline_now = expected_baseline(kpi, float(hours_of_day.iloc[-1]))
        deviation_pct = (
            0.0 if baseline_now[0] == 0 else round((current - baseline_now[0]) / abs(baseline_now[0]) * 100, 2)
        )

        z_severity = "normal"
        if abs(current_z) >= 3.5 or abs(mean_z) >= 3.0:
            z_severity = "critical"
        elif abs(current_z) >= 2.0 or abs(mean_z) >= 1.5:
            z_severity = "warning"

        threshold_severity = classify_threshold(kpi, current)
        severity = combine_severity(z_severity, threshold_severity)

        return {
            "cell_id": cell_id,
            "kpi": kpi,
            "hours": hours,
            "current": round(current, 3),
            "baseline_mean": round(float(baseline_now[0]), 3),
            "baseline_std": round(float(baseline_now[1]), 3),
            "z_score": round(current_z, 2),
            "mean_abs_z_score": round(mean_z, 2),
            "deviation_pct": deviation_pct,
            "severity": severity,
            "breached_threshold": threshold_severity != "normal",
        }

    # -- status / health -----------------------------------------------------

    def health_score(self, cell_id: str) -> float:
        df = self.window(cell_id, 3)
        if df.empty:
            return 100.0
        penalties = 0.0
        for kpi in ["latency_ms", "packet_loss_pct", "prb_utilization_pct",
                    "drop_rate_pct", "sinr_db", "rsrp_dbm", "handover_success_rate_pct"]:
            result = self.anomaly(cell_id, kpi, hours=3)
            if result["severity"] == "critical":
                penalties += 15
            elif result["severity"] == "warning":
                penalties += 6
        return round(max(0.0, 100.0 - penalties), 1)

    def get_status(self, cell_id: str) -> dict | None:
        cell = self.get_cell(cell_id)
        if not cell:
            return None
        alarms = [
            f"{e['event_type']}"
            for e in self.search_logs(cell_id=cell_id, hours=6, severity="critical", limit=10)
        ]
        health = self.health_score(cell_id)
        oper_state = "up" if health >= 70 else ("degraded" if health >= 40 else "down")
        return {
            "cell_id": cell_id,
            "admin_state": "active",
            "oper_state": oper_state,
            "active_alarms": alarms,
            "health_score": health,
            "scenario": cell["scenario"],
        }

    # -- logs -----------------------------------------------------------

    def search_logs(
        self,
        cell_id: str | None = None,
        query: str | None = None,
        severity: str | None = None,
        hours: int = 6,
        limit: int = 50,
    ) -> list[dict]:
        cutoff = self.now - timedelta(hours=hours)
        out = []
        for e in self.logs:
            if e["timestamp"] <= cutoff:
                continue
            if cell_id and e["cell_id"] != cell_id:
                continue
            if severity and e["severity"] != severity:
                continue
            if query and query.lower() not in e["message"].lower() and query.lower() not in e["event_type"].lower():
                continue
            out.append({**e, "timestamp": e["timestamp"].isoformat()})
        out.sort(key=lambda e: e["timestamp"], reverse=True)
        return out[:limit]


@lru_cache
def get_store() -> NetworkDataStore:
    return NetworkDataStore()
