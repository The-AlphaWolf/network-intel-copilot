"""Runs the ground-truth eval suite end to end through the real LangGraph
investigation pipeline, computes retrieval/citation/faithfulness/root-cause
metrics, logs params+metrics+artifact to MLflow, and writes eval_results.json
for the frontend Evaluation page.

Run directly: `python -m app.eval.run_eval`
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from app.agents.graph import run_investigation
from app.agents.llm import is_stub_mode
from app.config import get_settings
from app.eval.metrics import (
    action_keyword_hit_rate,
    citation_correctness,
    lexical_faithfulness,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    root_cause_top1_correct,
    root_cause_topk_correct,
)
from app.logging_conf import get_logger

logger = get_logger("eval.run_eval")
GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"


def load_ground_truth() -> list[dict]:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def evaluate_case(case: dict) -> dict:
    result = run_investigation(case["query"], cell_id=case.get("cell_id"))

    citations = result.get("citations", [])
    retrieved_doc_ids = [c["doc_id"] for c in citations]  # already score-ordered
    relevant_doc_ids = case["relevant_doc_ids"]

    all_cited_ids = [cid for h in result.get("hypotheses", []) for cid in h.get("citations", [])]
    all_cited_ids += [cid for r in result.get("recommendations", []) for cid in r.get("citations", [])]
    valid_chunk_ids = {c["chunk_id"] for c in citations}

    hypotheses = result.get("hypotheses", [])
    predicted_categories = [h["category"] for h in hypotheses]
    top1 = predicted_categories[0] if predicted_categories else "unknown"

    actions_text = " ".join(r["action"] + " " + r.get("expected_impact", "") for r in result.get("recommendations", []))
    source_texts = [c["snippet"] for c in citations]

    return {
        "id": case["id"],
        "query": case["query"],
        "cell_id_resolved": result.get("cell_id"),
        "cell_id_correct": result.get("cell_id") == case["cell_id"],
        "recall_at_5": recall_at_k(retrieved_doc_ids, relevant_doc_ids, 5),
        "precision_at_5": precision_at_k(retrieved_doc_ids, relevant_doc_ids, 5),
        "mrr": mean_reciprocal_rank(retrieved_doc_ids, relevant_doc_ids),
        "citation_correctness": citation_correctness(all_cited_ids, valid_chunk_ids) if all_cited_ids else 1.0,
        "faithfulness": lexical_faithfulness(result.get("summary", ""), source_texts),
        "root_cause_top1_correct": root_cause_top1_correct(top1, case["acceptable_causes"]),
        "root_cause_top3_correct": root_cause_topk_correct(predicted_categories, case["acceptable_causes"], k=3),
        "action_keyword_hit_rate": action_keyword_hit_rate(actions_text, case["expected_action_keywords"]),
        "errors": result.get("errors", []),
        "duration_ms": result.get("duration_ms", 0.0),
    }


def run_eval() -> dict:
    settings = get_settings()
    cases = load_ground_truth()

    start = time.time()
    per_case = [evaluate_case(c) for c in cases]
    total_duration_ms = round((time.time() - start) * 1000, 1)

    n = len(per_case)
    metrics = {
        "recall_at_5": round(sum(c["recall_at_5"] for c in per_case) / n, 4),
        "precision_at_5": round(sum(c["precision_at_5"] for c in per_case) / n, 4),
        "mrr": round(sum(c["mrr"] for c in per_case) / n, 4),
        "citation_correctness": round(sum(c["citation_correctness"] for c in per_case) / n, 4),
        "faithfulness": round(sum(c["faithfulness"] for c in per_case) / n, 4),
        "root_cause_top1_accuracy": round(sum(c["root_cause_top1_correct"] for c in per_case) / n, 4),
        "root_cause_top3_accuracy": round(sum(c["root_cause_top3_correct"] for c in per_case) / n, 4),
        "cell_id_resolution_accuracy": round(sum(c["cell_id_correct"] for c in per_case) / n, 4),
        "action_keyword_hit_rate": round(sum(c["action_keyword_hit_rate"] for c in per_case) / n, 4),
        "avg_duration_ms": round(sum(c["duration_ms"] for c in per_case) / n, 1),
    }
    params = {
        "embedding_model": settings.embedding_model,
        "embedding_backend": settings.embedding_backend,
        "qdrant_collection": settings.qdrant_collection,
        "llm_mode": settings.llm_mode,
        "llm_model": settings.openai_model if not is_stub_mode() else "stub",
        "num_cases": n,
    }

    output = {
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "params": params,
        "metrics": metrics,
        "total_duration_ms": total_duration_ms,
        "cases": per_case,
    }

    out_path = settings.data_out_dir / "eval_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("eval_complete", **metrics)

    _log_to_mlflow(params, metrics, out_path)
    return output


def _log_to_mlflow(params: dict, metrics: dict, artifact_path: Path) -> None:
    try:
        import mlflow
    except ImportError:
        logger.warning("mlflow_not_installed_skipping_tracking")
        return

    settings = get_settings()
    uri = settings.mlflow_tracking_uri
    if "://" in uri:
        # Already a proper URI - an MLflow tracking server (docker-compose
        # sets this to http://mlflow:5000) or an explicit sqlite:/file: URI.
        mlflow.set_tracking_uri(uri)
    else:
        # Bare local path (the native/no-Docker default) - MLflow 3.x
        # deprecated the plain filesystem store, so point it at a SQLite
        # file under that directory instead.
        mlruns_dir = Path(uri).resolve()
        mlruns_dir.mkdir(parents=True, exist_ok=True)
        mlflow.set_tracking_uri(f"sqlite:///{(mlruns_dir / 'mlflow.db').as_posix()}")
    mlflow.set_experiment(settings.mlflow_experiment)
    with mlflow.start_run(run_name=f"eval-{time.strftime('%Y%m%d-%H%M%S')}"):
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(artifact_path))
    logger.info("mlflow_run_logged", tracking_uri=settings.mlflow_tracking_uri)


if __name__ == "__main__":
    result = run_eval()
    print(json.dumps(result["metrics"], indent=2))
