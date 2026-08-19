"""Test environment setup. Runs at collection time (before any test module
imports app.config), so env vars here take effect for every test: fake
embedder (no model download, no network) and an isolated Qdrant path/
collection so tests never touch the dev database."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="nic_test_")
os.environ["LLM_MODE"] = "stub"
os.environ["EMBEDDING_BACKEND"] = "fake"
os.environ["QDRANT_PATH"] = os.path.join(_tmp, "qdrant")
os.environ["QDRANT_COLLECTION"] = "test_knowledge"
os.environ["MLFLOW_TRACKING_URI"] = os.path.join(_tmp, "mlruns")

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _ingest_test_knowledge_base():
    """Ingest the real knowledge docs into the isolated test collection once
    per test session, using the fake embedder (fast, deterministic, no
    network)."""
    from app.rag.ingest import ingest

    ingest(recreate=True)
