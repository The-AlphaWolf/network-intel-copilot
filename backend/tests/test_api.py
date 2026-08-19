import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_system(client):
    r = client.get("/api/v1/health/system")
    assert r.status_code == 200
    names = {c["name"] for c in r.json()["components"]}
    assert {"data_store", "qdrant", "embedder", "llm"} <= names


def test_list_cells(client):
    r = client.get("/api/v1/cells")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 14


def test_get_cell_known(client):
    r = client.get("/api/v1/cells/KOL-5G-017")
    assert r.status_code == 200
    assert r.json()["cell_id"] == "KOL-5G-017"


def test_get_cell_unknown_returns_404(client):
    r = client.get("/api/v1/cells/NOPE-999")
    assert r.status_code == 404


def test_cell_kpis(client):
    r = client.get("/api/v1/cells/KOL-5G-017/kpis?hours=6")
    assert r.status_code == 200
    assert "prb_utilization_pct" in r.json()["series"]


def test_topology(client):
    r = client.get("/api/v1/topology")
    assert r.status_code == 200
    assert len(r.json()["cells"]) == 14


def test_overview(client):
    r = client.get("/api/v1/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["cells_monitored"] == 14
    assert body["active_incidents"] == 5


def test_knowledge_documents(client):
    r = client.get("/api/v1/knowledge/documents")
    assert r.status_code == 200
    assert len(r.json()) == 12


def test_knowledge_search(client):
    r = client.post("/api/v1/knowledge/search", json={"query": "congestion", "top_k": 3})
    assert r.status_code == 200
    assert len(r.json()) <= 3


def test_agents(client):
    r = client.get("/api/v1/agents")
    assert r.status_code == 200
    assert len(r.json()["architecture"]) == 5


def test_investigate_returns_structured_result(client):
    r = client.post("/api/v1/investigate", json={"query": "Investigate high latency and packet loss in cell KOL-5G-017"})
    assert r.status_code == 200
    body = r.json()
    assert body["cell_id"] == "KOL-5G-017"
    assert body["status"] == "completed"
    assert body["root_causes"][0]["category"] == "congestion"
    assert body["metrics"]["llm_calls"] == 0


def test_get_investigation_by_id_roundtrip(client):
    r1 = client.post("/api/v1/investigate", json={"query": "Handover failures on BLR-5G-021"})
    inv_id = r1.json()["investigation_id"]
    r2 = client.get(f"/api/v1/investigate/{inv_id}")
    assert r2.status_code == 200
    assert r2.json()["investigation_id"] == inv_id


def test_get_investigation_unknown_id_404(client):
    r = client.get("/api/v1/investigate/does-not-exist")
    assert r.status_code == 404


def test_list_investigations(client):
    client.post("/api/v1/investigate", json={"query": "Investigate cell KOL-5G-017"})
    r = client.get("/api/v1/investigations?limit=5")
    assert r.status_code == 200
    assert len(r.json()) >= 1
