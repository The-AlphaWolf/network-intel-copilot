"""Resolution Agent: turns the top-ranked root cause into prioritized,
actionable remediation steps, grounded in the retrieved runbook citations."""
from __future__ import annotations

from app.agents.common import Timer, make_event, under_budget
from app.agents.llm import LLMUnavailable, call_llm_json, is_stub_mode
from app.agents.state import InvestigationState

_TEMPLATES: dict[str, list[dict]] = {
    "congestion": [
        {"action": "Enable/expand carrier aggregation for CA-capable UEs on the cell", "category": "immediate", "priority": "P2", "expected_impact": "Reduces primary-carrier PRB load without mobility risk", "risk": "low", "owner_team": "RAN Operations", "estimated_time": "< 1 hour"},
        {"action": "Trigger load-balancing mobility parameter adjustment toward underutilized neighbors", "category": "immediate", "priority": "P2", "expected_impact": "Shifts demand off the congested cell", "risk": "medium", "owner_team": "RAN Operations", "estimated_time": "1-2 hours"},
        {"action": "Escalate to RAN Planning for capacity expansion if congestion recurs", "category": "structural", "priority": "P3", "expected_impact": "Addresses root capacity shortfall", "risk": "low", "owner_team": "RAN Planning", "estimated_time": "planning cycle"},
    ],
    "interference": [
        {"action": "Dispatch field technician to inspect connectors and run a PIM sweep", "category": "immediate", "priority": "P2", "expected_impact": "Resolves PIM source if physical fault confirmed", "risk": "low", "owner_team": "RF Engineering", "estimated_time": "4-8 hours"},
        {"action": "Coordinate spectrum monitoring to locate external interference source", "category": "immediate", "priority": "P3", "expected_impact": "Identifies and enables removal of external jammer", "risk": "low", "owner_team": "RF Engineering", "estimated_time": "1-2 days"},
        {"action": "Review neighbor cell azimuth/power for co-channel reuse conflict", "category": "structural", "priority": "P3", "expected_impact": "Reduces intra-system interference", "risk": "medium", "owner_team": "RF Engineering", "estimated_time": "planning cycle"},
    ],
    "backhaul_degradation": [
        {"action": "Engage transport provider to inspect link (fiber/microwave/leased line)", "category": "immediate", "priority": "P1", "expected_impact": "Resolves physical transport fault", "risk": "low", "owner_team": "Transport Engineering", "estimated_time": "2-6 hours"},
        {"action": "Fail over to redundant backhaul path if available", "category": "immediate", "priority": "P1", "expected_impact": "Restores service while primary link is repaired", "risk": "low", "owner_team": "Transport Engineering", "estimated_time": "< 1 hour"},
        {"action": "Apply QoS shaping at the site router to protect latency-sensitive traffic", "category": "immediate", "priority": "P2", "expected_impact": "Mitigates user impact during repair window", "risk": "low", "owner_team": "Transport Engineering", "estimated_time": "< 1 hour"},
    ],
    "poor_coverage": [
        {"action": "Dispatch field team to inspect antenna/feeder for physical fault", "category": "immediate", "priority": "P2", "expected_impact": "Resolves fault if physical cause confirmed", "risk": "low", "owner_team": "RF Engineering", "estimated_time": "4-8 hours"},
        {"action": "Incrementally reduce electrical downtilt and re-measure", "category": "immediate", "priority": "P3", "expected_impact": "Extends effective coverage radius", "risk": "medium", "owner_team": "RF Engineering", "estimated_time": "1-2 hours"},
        {"action": "Restore transmit power to engineered design value if reduced", "category": "immediate", "priority": "P3", "expected_impact": "Restores designed coverage footprint", "risk": "low", "owner_team": "RF Engineering", "estimated_time": "< 1 hour"},
    ],
    "handover_problems": [
        {"action": "Add missing bidirectional neighbor relation for the affected cell pair", "category": "immediate", "priority": "P2", "expected_impact": "Resolves handover failures in the affected direction", "risk": "low", "owner_team": "RAN Performance Engineering", "estimated_time": "< 1 hour"},
        {"action": "Retune TTT/hysteresis for the affected cell pair if ping-pong is observed", "category": "immediate", "priority": "P3", "expected_impact": "Reduces unnecessary handover churn", "risk": "low", "owner_team": "RAN Performance Engineering", "estimated_time": "1-2 hours"},
        {"action": "Review A3 offset if failures correlate with cell-edge RSRP", "category": "structural", "priority": "P3", "expected_impact": "Improves handover trigger timing at cell edge", "risk": "medium", "owner_team": "RAN Performance Engineering", "estimated_time": "planning cycle"},
    ],
    "unknown": [
        {"action": "Continue monitoring and re-run investigation once more evidence accumulates", "category": "immediate", "priority": "P3", "expected_impact": "Avoids acting on an inconclusive diagnosis", "risk": "low", "owner_team": "Network Operations Center", "estimated_time": "ongoing"},
    ],
}


def _rule_based_recommendations(category: str, citations: list[dict]) -> list[dict]:
    templates = _TEMPLATES.get(category, _TEMPLATES["unknown"])
    cat_citation_ids = [c["chunk_id"] for c in citations if category.split("_")[0] in c["doc_id"]][:2]
    return [{**tmpl, "citations": cat_citation_ids} for tmpl in templates]


def resolution_node(state: InvestigationState) -> dict:
    with Timer() as t:
        hypotheses = state.get("hypotheses", [])
        citations = state.get("citations", [])
        valid_chunk_ids = {c["chunk_id"] for c in citations}
        top = hypotheses[0] if hypotheses else {"category": "unknown", "cause": "unknown"}
        category = top.get("category", "unknown")

        llm_calls = 0
        recommendations = None
        if not is_stub_mode() and under_budget(state.get("llm_calls", 0)):
            system = (
                "You are a network remediation planning agent. Given the top root-cause "
                "hypothesis and cited documentation, produce up to 4 prioritized remediation "
                'actions. Reply with ONLY a JSON array, each item: {"action": str, '
                '"category": "immediate"|"structural", "priority": "P1"|"P2"|"P3", '
                '"expected_impact": str, "risk": "low"|"medium"|"high", "owner_team": str, '
                '"estimated_time": str, "citations": [chunk_id, ...]}. Only use chunk_ids '
                "present in the input citations list."
            )
            payload = {"top_hypothesis": top, "citations": citations}
            result = call_llm_json(system, str(payload), max_tokens=700, temperature=0.3)
            llm_calls += 1
            if isinstance(result, list) and result:
                recommendations = []
                for item in result[:4]:
                    if not isinstance(item, dict) or "action" not in item:
                        continue
                    recommendations.append({
                        "action": str(item["action"])[:300],
                        "category": item.get("category", "immediate"),
                        "priority": item.get("priority", "P3"),
                        "expected_impact": str(item.get("expected_impact", ""))[:300],
                        "risk": item.get("risk", "medium"),
                        "owner_team": item.get("owner_team", "Network Operations Center"),
                        "estimated_time": str(item.get("estimated_time", "TBD")),
                        "citations": [c for c in item.get("citations", []) if c in valid_chunk_ids],
                    })

        if not recommendations:
            recommendations = _rule_based_recommendations(category, citations)

        event = make_event(
            "resolution_agent", "completed",
            f"Generated {len(recommendations)} recommendations for {top.get('cause', 'unknown cause')}",
            [], t.elapsed_ms,
        )
        return {"recommendations": recommendations, "completed": ["resolution"], "agent_events": [event], "llm_calls": llm_calls}
