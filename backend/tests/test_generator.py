from app.data.generator import generate_kpi_dataframe, generate_logs, generate_cells_topology
from app.data.scenarios import CELLS


def test_generation_is_deterministic():
    df1 = generate_kpi_dataframe(42)
    df2 = generate_kpi_dataframe(42)
    assert df1.equals(df2)


def test_generation_differs_with_different_seed():
    df1 = generate_kpi_dataframe(42)
    df2 = generate_kpi_dataframe(43)
    assert not df1.equals(df2)


def test_all_cells_and_points_present():
    df = generate_kpi_dataframe(42)
    assert set(df.cell_id.unique()) == {c.cell_id for c in CELLS}
    assert len(df) == len(CELLS) * 288


def test_congestion_cell_shows_signature():
    df = generate_kpi_dataframe(42)
    sub = df[df.cell_id == "KOL-5G-017"]
    assert sub.prb_utilization_pct.max() > 85
    assert sub.latency_ms.max() > 50
    # RSRP should stay in the normal band - congestion doesn't touch the radio link.
    assert sub.rsrp_dbm.min() > -100


def test_healthy_cell_stays_within_bounds():
    df = generate_kpi_dataframe(42)
    sub = df[df.cell_id == "KOL-5G-002"]
    assert sub.packet_loss_pct.max() < 2.0
    assert sub.handover_success_rate_pct.min() > 95


def test_logs_reference_only_known_cells():
    logs = generate_logs(42)
    cell_ids = {c.cell_id for c in CELLS}
    assert len(logs) > 0
    assert all(e["cell_id"] in cell_ids for e in logs)


def test_topology_has_missing_neighbor_relation():
    topo = generate_cells_topology()
    missing = [r for r in topo["neighbor_relations"] if r["relation_status"] == "missing"]
    assert len(missing) == 1
    assert missing[0]["cell_id"] == "BLR-5G-021"
