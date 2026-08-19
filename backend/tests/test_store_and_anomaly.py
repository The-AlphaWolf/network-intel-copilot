from app.data.store import classify_threshold, combine_severity, get_store


def test_classify_threshold_lower_is_worse():
    assert classify_threshold("rsrp_dbm", -80) == "normal"
    assert classify_threshold("rsrp_dbm", -108) == "warning"
    assert classify_threshold("rsrp_dbm", -120) == "critical"


def test_classify_threshold_higher_is_worse():
    assert classify_threshold("latency_ms", 10) == "normal"
    assert classify_threshold("latency_ms", 60) == "warning"
    assert classify_threshold("latency_ms", 150) == "critical"


def test_classify_threshold_no_bands_defined():
    assert classify_threshold("active_users", 999) == "normal"


def test_combine_severity_takes_worse():
    assert combine_severity("normal", "critical") == "critical"
    assert combine_severity("warning", "normal") == "warning"
    assert combine_severity("critical", "critical") == "critical"


def test_congestion_cell_anomaly_critical():
    store = get_store()
    result = store.anomaly("KOL-5G-017", "prb_utilization_pct", hours=6)
    assert result["severity"] == "critical"
    assert result["current"] > 70


def test_healthy_cell_anomaly_normal():
    store = get_store()
    result = store.anomaly("KOL-5G-002", "prb_utilization_pct", hours=6)
    assert result["severity"] == "normal"


def test_unknown_kpi_returns_neutral_result():
    store = get_store()
    result = store.anomaly("KOL-5G-017", "not_a_real_kpi", hours=6)
    assert result["severity"] == "normal"
    assert result["current"] is None


def test_health_score_lower_for_incident_cell():
    store = get_store()
    assert store.health_score("KOL-5G-017") < store.health_score("KOL-5G-002")


def test_get_status_unknown_cell_returns_none():
    store = get_store()
    assert store.get_status("NOPE-999") is None


def test_neighbors_include_missing_relation():
    store = get_store()
    neighbors = store.get_neighbors("BLR-5G-021")
    statuses = {n["neighbor_id"]: n["relation_status"] for n in neighbors}
    assert statuses.get("BLR-5G-010") == "missing"
