"""LangGraph supervisor wiring. Any node exception is caught here so one
agent's failure never crashes the whole investigation - it's recorded in
`errors` and the graph moves on with a partial result.

Run directly: `python -m app.agents.graph --query "Investigate high latency and packet loss in cell KOL-5G-017"`
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

from langgraph.graph import END, START, StateGraph

from app.agents.analyst import analyst_node
from app.agents.common import make_event
from app.agents.rag_agent import rag_agent_node
from app.agents.resolution import resolution_node
from app.agents.root_cause import root_cause_node
from app.agents.state import InvestigationState
from app.agents.supervisor import PLAN, supervisor_node
from app.logging_conf import get_logger

logger = get_logger("agents.graph")


def _safe(name: str, fn: Callable[[InvestigationState], dict]) -> Callable[[InvestigationState], dict]:
    def wrapped(state: InvestigationState) -> dict:
        try:
            return fn(state)
        except Exception as exc:  # noqa: BLE001 - node failure must not crash the graph
            logger.exception("node_failed", node=name, error=str(exc))
            event = make_event(name, "failed", f"{type(exc).__name__}: {exc}", [], 0.0)
            out: dict = {"errors": [f"{name}: {exc}"], "agent_events": [event]}
            if name in PLAN:
                out["completed"] = [name]
            return out
    return wrapped


def _route_after_supervisor(state: InvestigationState) -> str:
    plan = state.get("plan", [])
    completed = state.get("completed", [])
    for step in plan:
        if step not in completed:
            return step
    return END


def build_graph():
    builder = StateGraph(InvestigationState)
    builder.add_node("supervisor", _safe("supervisor", supervisor_node))
    builder.add_node("analyst", _safe("analyst", analyst_node))
    builder.add_node("rag", _safe("rag", rag_agent_node))
    builder.add_node("root_cause", _safe("root_cause", root_cause_node))
    builder.add_node("resolution", _safe("resolution", resolution_node))

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {"analyst": "analyst", "rag": "rag", "root_cause": "root_cause", "resolution": "resolution", END: END},
    )
    builder.add_edge("analyst", "supervisor")
    builder.add_edge("rag", "supervisor")
    builder.add_edge("root_cause", "supervisor")
    builder.add_edge("resolution", "supervisor")

    return builder.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def run_investigation(query: str, cell_id: str | None = None, time_window_hours: int | None = None) -> dict:
    graph = get_graph()
    investigation_id = str(uuid.uuid4())
    initial: InvestigationState = {
        "investigation_id": investigation_id,
        "query": query,
        "cell_id": cell_id,
        "time_window_hours": time_window_hours or 6,
        "llm_calls": 0,
    }
    start = time.time()
    final_state = graph.invoke(initial, config={"recursion_limit": 20})
    final_state["duration_ms"] = round((time.time() - start) * 1000, 1)
    return final_state


if __name__ == "__main__":
    import argparse
    import json as _json

    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--cell-id", default=None)
    parser.add_argument("--hours", type=int, default=None)
    args = parser.parse_args()

    result = run_investigation(args.query, cell_id=args.cell_id, time_window_hours=args.hours)
    print(_json.dumps(result, indent=2, default=str))
