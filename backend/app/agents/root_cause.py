"""Root Cause Agent: correlates KPI/log/neighbor evidence and retrieved
documentation into ranked hypotheses. Confidence blends the LLM's judgment
with a deterministic rule-based signature score, so ranking is never pure
LLM vibes - and citations are validated against what RAG actually retrieved,
never trusted blindly from the model output."""
from __future__ import annotations

from app.agents.common import Timer, make_event, under_budget
from app.agents.llm import LLMUnavailable, call_llm, call_llm_json, is_stub_mode
from app.agents.state import InvestigationState

CATEGORY_LABELS = {
    "congestion": "Cell congestion (capacity exhaustion)",
    "interference": "Uplink/downlink interference (possible PIM)",
    "backhaul_degradation": "Backhaul / transport degradation",
    "poor_coverage": "Poor coverage (RF/antenna issue)",
    "handover_problems": "Handover configuration problem",
}


def _sev(anomalies: dict[str, dict], kpi: str) -> float:
    return {"critical": 1.0, "warning": 0.5, "normal": 0.0}.get(
        anomalies.get(kpi, {}).get("severity", "normal"), 0.0
    )


def rule_scores(anomalies: list[dict]) -> dict[str, float]:
    """Deterministic KPI-pattern -> root-cause-category scores, 0-1. Mirrors
    the discriminator logic in the knowledge base docs (e.g. congestion =
    high PRB with normal RSRP/SINR; interference = SINR/RSRQ down with RSRP
    stable). Independent of any hidden ground-truth label."""
    by_kpi = {a["kpi"]: a for a in anomalies}
    prb, users, latency, loss = (_sev(by_kpi, k) for k in
        ("prb_utilization_pct", "active_users", "latency_ms", "packet_loss_pct"))
    sinr, rsrq, rsrp, drop = (_sev(by_kpi, k) for k in
        ("sinr_db", "rsrq_db", "rsrp_dbm", "drop_rate_pct"))
    ho, throughput = _sev(by_kpi, "handover_success_rate_pct"), _sev(by_kpi, "throughput_mbps")

    scores = {
        "congestion": max(0.0, (0.45 * prb + 0.25 * users + 0.15 * latency + 0.15 * loss) * (1 - 0.4 * rsrp)),
        "interference": max(0.0, (0.45 * sinr + 0.3 * rsrq + 0.25 * drop) * (1 - 0.3 * prb)),
        "backhaul_degradation": max(0.0, (0.4 * latency + 0.4 * loss + 0.2 * throughput) * (1 - 0.5 * prb) * (1 - 0.3 * sinr)),
        "poor_coverage": max(0.0, 0.5 * rsrp + 0.25 * rsrq + 0.25 * ho),
        "handover_problems": max(0.0, 0.7 * ho + 0.3 * drop) * (1 - 0.2 * rsrp),
    }
    return {k: round(min(v, 1.0), 3) for k, v in scores.items()}


def _match_category(cause_text: str) -> str | None:
    text = cause_text.lower()
    if any(w in text for w in ["congest", "capacity", "prb", "resource"]):
        return "congestion"
    if any(w in text for w in ["interfer", "pim", "sinr", "noise"]):
        return "interference"
    if any(w in text for w in ["backhaul", "transport", "jitter"]):
        return "backhaul_degradation"
    if any(w in text for w in ["coverage", "rsrp", "antenna", "tilt"]):
        return "poor_coverage"
    if any(w in text for w in ["handover", "neighbor", "mobility"]):
        return "handover_problems"
    return None


def _rule_based_hypotheses(anomalies: list[dict], evidence: list[dict], citations: list[dict]) -> list[dict]:
    scores = rule_scores(anomalies)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    hypotheses = []
    for rank, (category, score) in enumerate(ranked[:3], start=1):
        if score <= 0.05:
            continue
        cat_citations = [c["chunk_id"] for c in citations if category.split("_")[0] in c["doc_id"]]
        hypotheses.append({
            "rank": rank,
            "cause": CATEGORY_LABELS[category],
            "category": category,
            "confidence": round(score, 2),
            "explanation": f"KPI signature matches {category.replace('_', ' ')} pattern with rule-score {score:.2f}.",
            "supporting_evidence": [e["title"] for e in evidence if e["severity"] != "normal"][:5],
            "citations": cat_citations[:3],
        })
    if not hypotheses:
        hypotheses.append({
            "rank": 1, "cause": "Inconclusive - no strong KPI signature",
            "category": "unknown", "confidence": 0.1,
            "explanation": "No KPI breached severity thresholds strongly enough to support a specific hypothesis.",
            "supporting_evidence": [], "citations": [],
        })
    return hypotheses


def _validate_citations(cited: list, valid_chunk_ids: set[str]) -> list[str]:
    if not isinstance(cited, list):
        return []
    return [c for c in cited if isinstance(c, str) and c in valid_chunk_ids]


def root_cause_node(state: InvestigationState) -> dict:
    with Timer() as t:
        anomalies = state.get("anomalies", [])
        evidence = state.get("evidence", [])
        citations = state.get("citations", [])
        valid_chunk_ids = {c["chunk_id"] for c in citations}
        rule = rule_scores(anomalies)

        llm_calls = 0
        hypotheses = None
        if not is_stub_mode() and under_budget(state.get("llm_calls", 0)):
            system = (
                "You are a root-cause analysis agent for telecom network incidents. "
                "Given KPI anomalies, evidence, and cited documentation, propose up to "
                "3 ranked root-cause hypotheses. Reply with ONLY a JSON array, each item: "
                '{"cause": str, "category": one of ["congestion","interference",'
                '"backhaul_degradation","poor_coverage","handover_problems"], '
                '"confidence": float 0-1, "explanation": str, '
                '"citations": [chunk_id, ...]}. Only use chunk_ids present in the input citations list.'
            )
            payload = {
                "anomalies": [a for a in anomalies if a["severity"] != "normal"],
                "evidence": evidence[:10],
                "citations": citations,
                "rule_based_scores": rule,
            }
            result = call_llm_json(system, str(payload), max_tokens=700, temperature=0.3)
            llm_calls += 1
            if isinstance(result, list) and result:
                hypotheses = []
                for item in result[:3]:
                    if not isinstance(item, dict) or "cause" not in item:
                        continue
                    category = item.get("category") if item.get("category") in rule else _match_category(item["cause"])
                    rule_score = rule.get(category, 0.0) if category else 0.0
                    llm_conf = float(item.get("confidence", 0.5)) if isinstance(item.get("confidence"), (int, float)) else 0.5
                    blended = round(0.6 * llm_conf + 0.4 * rule_score, 2)
                    hypotheses.append({
                        "cause": item["cause"],
                        "category": category or "unknown",
                        "confidence": blended,
                        "explanation": str(item.get("explanation", ""))[:500],
                        "supporting_evidence": [e["title"] for e in evidence if e["severity"] != "normal"][:5],
                        "citations": _validate_citations(item.get("citations", []), valid_chunk_ids),
                    })
                hypotheses.sort(key=lambda h: h["confidence"], reverse=True)
                for i, h in enumerate(hypotheses, start=1):
                    h["rank"] = i

        if not hypotheses:
            hypotheses = _rule_based_hypotheses(anomalies, evidence, citations)

        event = make_event(
            "root_cause_agent", "completed",
            f"Ranked {len(hypotheses)} hypotheses, top: {hypotheses[0]['cause']} ({hypotheses[0]['confidence']:.0%})",
            [], t.elapsed_ms,
        )
        return {"hypotheses": hypotheses, "completed": ["root_cause"], "agent_events": [event], "llm_calls": llm_calls}
