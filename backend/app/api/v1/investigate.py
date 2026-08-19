"""POST /investigate (sync, full result) and GET /investigate/stream (SSE,
live agent timeline) - both run the same LangGraph investigation, just with
different delivery. Also GET /investigate/{id} and GET /investigations."""
from __future__ import annotations

import asyncio
import json
import threading
import uuid

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agents.graph import get_graph
from app.api.investigation_store import get as get_investigation
from app.api.investigation_store import recent as recent_investigations
from app.api.investigation_store import save as save_investigation
from app.logging_conf import get_logger
from app.schemas.investigation import InvestigateRequest, InvestigationResult

router = APIRouter(prefix="/investigate", tags=["investigate"])
logger = get_logger("api.investigate")


def _initial_state(investigation_id: str, req: InvestigateRequest) -> dict:
    return {
        "investigation_id": investigation_id,
        "query": req.query,
        "cell_id": req.cell_id,
        "time_window_hours": req.time_window_hours or 6,
        "llm_calls": 0,
    }


def _to_result(state: dict) -> dict:
    anomalies = [a for a in state.get("anomalies", []) if a.get("current") is not None]
    agent_events = state.get("agent_events", [])
    tools_called = sum(len(e.get("tools_used", [])) for e in agent_events)

    return {
        "investigation_id": state["investigation_id"],
        "query": state.get("query", ""),
        "cell_id": state.get("cell_id"),
        "status": state.get("status", "failed"),
        "summary": state.get("summary") or "Investigation did not complete.",
        "kpi_anomalies": [
            {
                "kpi": a["kpi"], "current": a.get("current"), "baseline_mean": a.get("baseline_mean"),
                "z_score": a.get("z_score", 0.0), "deviation_pct": a.get("deviation_pct", 0.0),
                "severity": a.get("severity", "normal"), "breached_threshold": a.get("breached_threshold", False),
            }
            for a in anomalies
        ],
        "evidence": state.get("evidence", []),
        "root_causes": state.get("hypotheses", []),
        "recommendations": state.get("recommendations", []),
        "citations": state.get("citations", []),
        "agent_execution": agent_events,
        "errors": state.get("errors", []),
        "metrics": {
            "llm_calls": state.get("llm_calls", 0),
            "tools_called": tools_called,
            "retrieval_hits": len(state.get("citations", [])),
            "duration_ms": state.get("duration_ms", 0.0),
        },
    }


@router.post("", response_model=InvestigationResult)
async def investigate(req: InvestigateRequest) -> dict:
    import time

    investigation_id = str(uuid.uuid4())
    graph = get_graph()
    start = time.time()
    final_state = await asyncio.to_thread(
        graph.invoke, _initial_state(investigation_id, req), {"recursion_limit": 20}
    )
    final_state["duration_ms"] = round((time.time() - start) * 1000, 1)
    result = _to_result(final_state)
    save_investigation(investigation_id, result)
    return result


@router.get("/stream")
async def investigate_stream(query: str, cell_id: str | None = None, time_window_hours: int | None = None):
    import time

    investigation_id = str(uuid.uuid4())
    req = InvestigateRequest(query=query, cell_id=cell_id, time_window_hours=time_window_hours)
    graph = get_graph()
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def worker():
        start = time.time()
        state: dict = dict(_initial_state(investigation_id, req))
        try:
            for update in graph.stream(state, {"recursion_limit": 20}, stream_mode="updates"):
                for _node_name, partial in update.items():
                    if not partial:
                        continue
                    for key, value in partial.items():
                        if key in ("completed", "evidence", "agent_events", "errors"):
                            state[key] = state.get(key, []) + value
                        else:
                            state[key] = value
                    for ev in partial.get("agent_events", []):
                        loop.call_soon_threadsafe(
                            queue.put_nowait, {"event": "agent_event", "data": json.dumps(ev)}
                        )
            state["duration_ms"] = round((time.time() - start) * 1000, 1)
            result = _to_result(state)
            save_investigation(investigation_id, result)
            loop.call_soon_threadsafe(
                queue.put_nowait, {"event": "result", "data": json.dumps(result, default=str)}
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("stream_worker_failed", error=str(exc))
            loop.call_soon_threadsafe(
                queue.put_nowait, {"event": "error", "data": json.dumps({"error": str(exc)})}
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, {"event": "done", "data": "{}"})

    threading.Thread(target=worker, daemon=True).start()

    async def event_gen():
        yield {"event": "started", "data": json.dumps({"investigation_id": investigation_id})}
        while True:
            item = await queue.get()
            yield item
            if item["event"] in ("done",):
                break

    return EventSourceResponse(event_gen())


@router.get("/{investigation_id}", response_model=InvestigationResult)
async def get_investigation_by_id(investigation_id: str) -> dict:
    result = get_investigation(investigation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="investigation not found")
    return result


investigations_router = APIRouter(tags=["investigate"])


@investigations_router.get("/investigations")
async def list_investigations(limit: int = 20) -> list[dict]:
    return recent_investigations(limit)
