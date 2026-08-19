from app.agents.graph import run_investigation


def test_full_investigation_congestion():
    result = run_investigation("Investigate high latency and packet loss in cell KOL-5G-017")
    assert result["cell_id"] == "KOL-5G-017"
    assert result["status"] == "completed"
    assert result["errors"] == []
    assert result["hypotheses"][0]["category"] == "congestion"
    assert result["llm_calls"] == 0  # stub mode


def test_full_investigation_interference():
    result = run_investigation("SINR is degrading on cell KOL-5G-004, please investigate")
    assert result["cell_id"] == "KOL-5G-004"
    assert result["hypotheses"][0]["category"] == "interference"


def test_full_investigation_backhaul():
    result = run_investigation("High latency and packet loss reported for cell DEL-5G-009")
    assert result["hypotheses"][0]["category"] == "backhaul_degradation"


def test_full_investigation_coverage():
    result = run_investigation("Users complaining about poor signal in cell MUM-5G-012")
    assert result["hypotheses"][0]["category"] == "poor_coverage"


def test_full_investigation_handover():
    result = run_investigation("Handover failures happening on cell BLR-5G-021")
    assert result["hypotheses"][0]["category"] == "handover_problems"


def test_investigation_all_citations_are_valid():
    result = run_investigation("Investigate high latency and packet loss in cell KOL-5G-017")
    valid_ids = {c["chunk_id"] for c in result["citations"]}
    for hyp in result["hypotheses"]:
        assert all(cid in valid_ids for cid in hyp["citations"])
    for rec in result["recommendations"]:
        assert all(cid in valid_ids for cid in rec["citations"])


def test_investigation_unresolvable_cell_records_error():
    result = run_investigation("Investigate this vague network problem with no cell mentioned")
    assert result["cell_id"] is None
    assert len(result["errors"]) > 0
    assert result["status"] == "completed"  # graph still finishes gracefully


def test_investigation_produces_agent_events_for_every_step():
    result = run_investigation("Investigate high latency and packet loss in cell KOL-5G-017")
    agents_seen = {e["agent"] for e in result["agent_events"]}
    assert {"supervisor", "network_analyst", "rag_agent", "root_cause_agent", "resolution_agent"} <= agents_seen
