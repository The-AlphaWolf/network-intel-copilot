"""Serves eval_results.json produced by `python -m app.eval.run_eval` (stage 6).
Returns a clear "not yet run" response until that file exists."""
from __future__ import annotations

import json

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/latest")
async def latest_evaluation() -> dict:
    settings = get_settings()
    path = settings.data_out_dir / "eval_results.json"
    if not path.exists():
        return {"status": "not_run", "message": "Run `python -m app.eval.run_eval` to generate evaluation metrics."}
    return {"status": "ok", **json.loads(path.read_text(encoding="utf-8"))}
