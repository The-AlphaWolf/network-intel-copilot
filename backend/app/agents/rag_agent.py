"""RAG Agent: turns the anomaly signature into targeted knowledge-base
queries, retrieves cited chunks, and synthesizes a grounded findings note.
Citations are only ever chunk_ids that actually came back from the vector
search - nothing here invents a citation."""
from __future__ import annotations

from app.agents.common import Timer, make_event, under_budget
from app.agents.llm import LLMUnavailable, call_llm, call_llm_json, is_stub_mode
from app.agents.state import InvestigationState
from app.tools.registry import search_knowledge_base

# KPI -> canonical search phrase, used both as the stub-mode query generator
# and as the fallback when the live LLM call fails or is over budget.
_KPI_QUERY_MAP = {
    "prb_utilization_pct": "PRB utilization congestion capacity troubleshooting",
    "active_users": "cell congestion active users capacity",
    "latency_ms": "latency degradation troubleshooting",
    "packet_loss_pct": "packet loss triage troubleshooting",
    "sinr_db": "SINR interference troubleshooting",
    "rsrq_db": "RSRQ interference troubleshooting",
    "rsrp_dbm": "RSRP coverage antenna tilt troubleshooting",
    "handover_success_rate_pct": "handover failure parameter optimization",
    "drop_rate_pct": "drop rate troubleshooting",
    "throughput_mbps": "throughput degradation troubleshooting",
}


def _fallback_queries(anomalies: list[dict]) -> list[str]:
    breached = [a for a in anomalies if a["severity"] != "normal"]
    breached.sort(key=lambda a: {"critical": 0, "warning": 1}.get(a["severity"], 2))
    queries = []
    for a in breached:
        q = _KPI_QUERY_MAP.get(a["kpi"])
        if q and q not in queries:
            queries.append(q)
        if len(queries) >= 3:
            break
    return queries or ["network KPI anomaly troubleshooting"]


def _llm_queries(anomalies: list[dict]) -> list[str] | None:
    system = (
        "Given a list of telecom KPI anomalies for one cell, generate 2-3 short "
        "search queries (a few words each) to look up relevant troubleshooting "
        "documentation. Reply with ONLY a JSON array of strings."
    )
    breached = [a for a in anomalies if a["severity"] != "normal"]
    result = call_llm_json(system, str(breached[:6]), max_tokens=150, temperature=0.2)
    if isinstance(result, list) and all(isinstance(q, str) for q in result):
        return result[:3]
    return None


def _synthesize_findings(anomalies: list[dict], citations: list[dict]) -> str:
    breached = [a["kpi"] for a in anomalies if a["severity"] != "normal"]
    if not citations:
        return "No sufficiently relevant documentation was retrieved for the observed anomaly signature."
    lead_docs = ", ".join(sorted({c["doc_id"] for c in citations[:4]}))
    return (
        f"Retrieved {len(citations)} relevant reference passages for anomalies in "
        f"{', '.join(breached[:4]) or 'the observed KPIs'}, primarily from {lead_docs}."
    )


def rag_agent_node(state: InvestigationState) -> dict:
    with Timer() as t:
        anomalies = state.get("anomalies", [])
        llm_calls = 0

        queries = None
        if not is_stub_mode() and under_budget(state.get("llm_calls", 0)):
            queries = _llm_queries(anomalies)
            llm_calls += 1
        queries = queries or _fallback_queries(anomalies)

        results = []
        for q in queries:
            results.extend(search_knowledge_base(q, top_k=4))

        # Dedupe by chunk_id, keep highest score, sort desc, cap at 8.
        best: dict[str, dict] = {}
        for r in results:
            existing = best.get(r["chunk_id"])
            if not existing or r["score"] > existing["score"]:
                best[r["chunk_id"]] = r
        ranked = sorted(best.values(), key=lambda r: r["score"], reverse=True)[:8]

        citations = [
            {
                "doc_id": r["doc_id"],
                "title": r["title"],
                "section": r["section"],
                "chunk_id": r["chunk_id"],
                "score": round(r["score"], 4),
                "snippet": r["text"][:280],
            }
            for r in ranked
        ]

        findings = None
        if not is_stub_mode() and under_budget(state.get("llm_calls", 0) + llm_calls) and citations:
            system = (
                "You are a RAG synthesis agent for telecom network troubleshooting. "
                "Given retrieved documentation passages, write a 2-4 sentence findings "
                "note that references the source docs by their doc_id in brackets, e.g. "
                "[congestion-triage-runbook]. Only state what the passages support - "
                "never invent a citation not present in the input. Plain text."
            )
            try:
                findings = call_llm(system, str(citations), max_tokens=300, temperature=0.2).strip()
                llm_calls += 1
            except LLMUnavailable:
                findings = None

        if not findings:
            findings = _synthesize_findings(anomalies, citations)

        event = make_event(
            "rag_agent", "completed",
            f"Retrieved {len(citations)} cited passages from {len(queries)} queries",
            ["search_knowledge_base"], t.elapsed_ms,
        )
        return {
            "citations": citations,
            "rag_findings": findings,
            "completed": ["rag"],
            "agent_events": [event],
            "llm_calls": llm_calls,
        }
