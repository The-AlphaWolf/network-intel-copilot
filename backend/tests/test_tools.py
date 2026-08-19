from app.tools.registry import (
    calculate_kpi_anomaly,
    get_cell_kpis,
    get_cell_status,
    get_neighbor_cells,
    search_knowledge_base,
    search_network_logs,
)


def test_get_cell_kpis_shape():
    result = get_cell_kpis("KOL-5G-017", hours=6)
    assert result["cell_id"] == "KOL-5G-017"
    assert "prb_utilization_pct" in result["series"]
    assert "prb_utilization_pct" in result["summary"]
    assert len(result["series"]["prb_utilization_pct"]) > 0


def test_get_cell_status_known_cell():
    result = get_cell_status("KOL-5G-017")
    assert result["cell_id"] == "KOL-5G-017"
    assert "error" not in result


def test_get_cell_status_unknown_cell():
    result = get_cell_status("NOPE-999")
    assert "error" in result


def test_search_network_logs_filters_by_cell():
    logs = search_network_logs(cell_id="KOL-5G-017", hours=24, limit=50)
    assert len(logs) > 0
    assert all(e["cell_id"] == "KOL-5G-017" for e in logs)


def test_search_network_logs_filters_by_severity():
    logs = search_network_logs(hours=24, severity="critical", limit=100)
    assert all(e["severity"] == "critical" for e in logs)


def test_get_neighbor_cells_returns_relations():
    neighbors = get_neighbor_cells("KOL-5G-017")
    assert len(neighbors) == 3
    assert all("neighbor_health_score" in n for n in neighbors)


def test_calculate_kpi_anomaly_returns_expected_fields():
    result = calculate_kpi_anomaly("KOL-5G-017", "latency_ms", hours=6)
    assert set(["cell_id", "kpi", "current", "z_score", "severity"]).issubset(result)


def test_search_knowledge_base_returns_scored_chunks():
    results = search_knowledge_base("congestion troubleshooting", top_k=3)
    assert len(results) <= 3
    for r in results:
        assert "chunk_id" in r and "doc_id" in r and "score" in r
