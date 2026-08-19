"""Typed shared state threaded through every LangGraph node. Nodes read what
they need and only write their own keys - no node mutates another node's
output list, they append to their own and the supervisor reads the union."""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class AgentEvent(TypedDict):
    agent: str
    status: str  # "started" | "completed" | "failed"
    message: str
    tools_used: list[str]
    duration_ms: float
    timestamp: str


def _keep_last(a, b):
    return b if b is not None else a


class InvestigationState(TypedDict, total=False):
    # input
    investigation_id: str
    query: str
    cell_id: str | None
    time_window_hours: int

    # supervisor
    plan: list[str]
    completed: Annotated[list[str], operator.add]

    # network analyst output
    kpi_snapshot: dict
    anomalies: list[dict]
    log_events: list[dict]
    neighbors: list[dict]
    analyst_findings: str

    # rag agent output
    citations: list[dict]
    rag_findings: str

    # root cause agent output
    hypotheses: list[dict]

    # resolution agent output
    recommendations: list[dict]

    # cross-cutting
    evidence: Annotated[list[dict], operator.add]
    agent_events: Annotated[list[AgentEvent], operator.add]
    errors: Annotated[list[str], operator.add]
    llm_calls: Annotated[int, operator.add]

    # final
    summary: str
    status: str
