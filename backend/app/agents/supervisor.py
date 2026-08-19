"""Supervisor node: parses the initial query into a plan (once), then on every
return visit checks whether all specialist agents have completed and, if so,
writes the executive summary. Routing itself lives in graph.py's conditional
edge, which reads `plan` / `completed` - this node never routes directly.
"""
from __future__ import annotations

import re

from app.agents.common import Timer, make_event, under_budget
from app.agents.llm import call_llm_json, is_stub_mode
from app.agents.state import InvestigationState
from app.data.store import get_store
from app.logging_conf import get_logger

logger = get_logger("agents.supervisor")

PLAN = ["analyst", "rag", "root_cause", "resolution"]

_CELL_ID_RE = re.compile(r"\b([A-Z]{2,4}-[A-Za-z0-9]{2,4}-\d{2,4})\b")


def _extract_cell_id(query: str) -> str | None:
    m = _CELL_ID_RE.search(query.upper())
    if not m:
        return None
    candidate = m.group(1)
    return candidate if candidate in get_store().cell_ids() else None


def _parse_query_llm(query: str) -> dict | None:
    system = (
        "You extract structured intent from a telecom network investigation "
        "request. Reply with ONLY a JSON object: "
        '{"cell_id": "<cell id or null>", "time_window_hours": <int 1-24>, '
        '"intent": "<one short phrase>"}'
    )
    result = call_llm_json(system, f"Request: {query}", max_tokens=200, temperature=0.0)
    return result if isinstance(result, dict) else None


def supervisor_node(state: InvestigationState) -> dict:
    with Timer() as t:
        if "plan" not in state:
            # First visit: parse the query into cell_id / window / plan.
            query = state["query"]
            regex_cell = _extract_cell_id(query)
            cell_id = state.get("cell_id") or regex_cell
            hours = state.get("time_window_hours") or 6
            llm_calls = 0

            if not is_stub_mode() and under_budget(state.get("llm_calls", 0)):
                parsed = _parse_query_llm(query)
                llm_calls += 1
                if parsed:
                    cell_id = cell_id or parsed.get("cell_id")
                    if cell_id and cell_id not in get_store().cell_ids():
                        cell_id = regex_cell  # don't trust a hallucinated id
                    hours = parsed.get("time_window_hours") or hours

            errors = []
            if not cell_id:
                errors.append(
                    "Could not identify a valid cell_id in the request; "
                    "defaulting is not possible without one."
                )

            event = make_event(
                "supervisor", "completed",
                f"Parsed investigation plan for cell {cell_id or '(unresolved)'}, window={hours}h",
                [], t.elapsed_ms,
            )
            return {
                "plan": PLAN,
                "completed": [],
                "cell_id": cell_id,
                "time_window_hours": hours,
                "agent_events": [event],
                "llm_calls": llm_calls,
                "errors": errors,
                "status": "investigating",
            }

        # Subsequent visits: if all specialists are done, write the summary.
        completed = state.get("completed", [])
        if not all(step in completed for step in PLAN):
            return {}

        summary = _build_summary(state)
        event = make_event("supervisor", "completed", "Investigation complete, summary generated", [], t.elapsed_ms)
        return {"summary": summary, "status": "completed", "agent_events": [event]}


def _build_summary(state: InvestigationState) -> str:
    hypotheses = state.get("hypotheses", [])
    recommendations = state.get("recommendations", [])
    cell_id = state.get("cell_id", "unknown cell")
    top_cause = hypotheses[0] if hypotheses else None
    top_action = recommendations[0] if recommendations else None

    llm_calls_so_far = state.get("llm_calls", 0)
    if not is_stub_mode() and under_budget(llm_calls_so_far):
        system = (
            "You are a senior telecom network operations lead. Write a concise "
            "3-5 sentence executive summary of a network incident investigation "
            "for a technical but time-constrained reader. State the cell, the "
            "top root cause with confidence, and the top recommended action. "
            "Reply with plain text, no markdown headers."
        )
        payload = {
            "cell_id": cell_id,
            "top_hypotheses": hypotheses[:3],
            "top_recommendations": recommendations[:3],
        }
        from app.agents.llm import call_llm, LLMUnavailable
        try:
            text = call_llm(system, str(payload), max_tokens=350, temperature=0.3)
            if text.strip():
                return text.strip()
        except LLMUnavailable as exc:
            logger.warning("summary_llm_failed", error=str(exc))

    # Rule-based fallback (also used directly in stub mode).
    if not top_cause:
        return f"Investigation of {cell_id} completed but no root cause could be determined from available evidence."
    parts = [
        f"Investigation of {cell_id} identified {top_cause['cause']} as the leading root cause "
        f"(confidence {top_cause['confidence']:.0%})."
    ]
    if top_action:
        parts.append(f"Top recommended action: {top_action['action']}.")
    if len(hypotheses) > 1:
        parts.append(f"{len(hypotheses)} candidate causes were evaluated and ranked by supporting evidence.")
    return " ".join(parts)
