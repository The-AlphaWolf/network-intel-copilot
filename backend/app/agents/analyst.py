"""Network Analyst agent: pulls real KPI/log/neighbor data via tools,
computes anomalies, and produces a short evidence-grounded findings note."""
from __future__ import annotations

from app.agents.common import Timer, make_event, under_budget
from app.agents.llm import LLMUnavailable, call_llm, is_stub_mode
from app.agents.state import InvestigationState
from app.tools.registry import (
    ALL_KPI_NAMES,
    calculate_kpi_anomaly,
    get_cell_kpis,
    get_cell_status,
    get_neighbor_cells,
    search_network_logs,
)

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "normal": 2}


def _build_evidence(anomalies: list[dict], logs: list[dict], neighbors: list[dict]) -> list[dict]:
    evidence = []
    for a in anomalies:
        if a["severity"] == "normal":
            continue
        evidence.append({
            "source": "kpi",
            "title": f"{a['kpi']} {a['severity']}",
            "detail": (
                f"{a['kpi']} = {a['current']} (baseline {a['baseline_mean']}, "
                f"z={a['z_score']}, deviation {a['deviation_pct']}%)"
            ),
            "severity": a["severity"],
            "timestamp": None,
        })
    for e in logs:
        if e["severity"] == "info":
            continue
        evidence.append({
            "source": "log",
            "title": e["event_type"],
            "detail": e["message"],
            "severity": e["severity"],
            "timestamp": e["timestamp"],
        })
    for n in neighbors:
        if n["relation_status"] != "active":
            evidence.append({
                "source": "neighbor",
                "title": f"Neighbor relation {n['relation_status']}",
                "detail": f"Relation to {n['neighbor_id']} is {n['relation_status']} ({n['distance_km']} km away)",
                "severity": "warning",
                "timestamp": None,
            })
    evidence.sort(key=lambda e: _SEVERITY_ORDER.get(e["severity"], 3))
    return evidence


def _findings_text(cell_id: str, status: dict, anomalies: list[dict], evidence: list[dict]) -> str:
    breached = [a for a in anomalies if a["severity"] != "normal"]
    if not breached:
        return f"{cell_id} shows no significant KPI anomalies in the analyzed window; health score {status.get('health_score')}."
    lead = ", ".join(f"{a['kpi']} ({a['severity']}, z={a['z_score']})" for a in breached[:5])
    return (
        f"{cell_id} health score {status.get('health_score')}, state {status.get('oper_state')}. "
        f"Anomalous KPIs: {lead}. {len(evidence)} evidence items collected from KPIs, logs, and neighbor relations."
    )


def analyst_node(state: InvestigationState) -> dict:
    with Timer() as t:
        cell_id = state.get("cell_id")
        hours = state.get("time_window_hours", 6)
        tools_used = ["get_cell_status", "get_cell_kpis", "calculate_kpi_anomaly", "search_network_logs", "get_neighbor_cells"]

        if not cell_id:
            event = make_event("network_analyst", "failed", "No cell_id resolved, skipping analysis", [], t.elapsed_ms)
            return {"completed": ["analyst"], "agent_events": [event], "errors": ["analyst: no cell_id"]}

        status = get_cell_status(cell_id)
        kpi_snapshot = get_cell_kpis(cell_id, hours=hours)
        anomalies = [calculate_kpi_anomaly(cell_id, kpi, hours=hours) for kpi in ALL_KPI_NAMES]
        logs = search_network_logs(cell_id=cell_id, hours=max(hours, 24), limit=30)
        neighbors = get_neighbor_cells(cell_id)

        evidence = _build_evidence(anomalies, logs, neighbors)

        llm_calls = 0
        findings = None
        if not is_stub_mode() and under_budget(state.get("llm_calls", 0)):
            system = (
                "You are a telecom network analyst. Given KPI anomalies, log events, "
                "and neighbor relation data for one cell, write a 2-4 sentence factual "
                "findings note. Only state what the data shows - do not diagnose root "
                "cause yet, that is a separate step. Plain text, no markdown."
            )
            payload = {"cell_id": cell_id, "status": status, "anomalies": anomalies, "top_evidence": evidence[:8]}
            try:
                findings = call_llm(system, str(payload), max_tokens=300, temperature=0.2).strip()
                llm_calls += 1
            except LLMUnavailable:
                findings = None

        if not findings:
            findings = _findings_text(cell_id, status, anomalies, evidence)

        event = make_event(
            "network_analyst", "completed",
            f"Analyzed {len(anomalies)} KPIs, {len(logs)} log events, {len(neighbors)} neighbors",
            tools_used, t.elapsed_ms,
        )
        return {
            "kpi_snapshot": kpi_snapshot,
            "anomalies": anomalies,
            "log_events": logs,
            "neighbors": neighbors,
            "analyst_findings": findings,
            "evidence": evidence,
            "completed": ["analyst"],
            "agent_events": [event],
            "llm_calls": llm_calls,
        }
