"""In-memory investigation result store (single-process, demo-scale). Keeps
insertion order; trimmed to the most recent MAX_HISTORY entries."""
from __future__ import annotations

MAX_HISTORY = 100
_investigations: dict[str, dict] = {}


def save(investigation_id: str, result: dict) -> None:
    _investigations[investigation_id] = result
    if len(_investigations) > MAX_HISTORY:
        oldest = next(iter(_investigations))
        del _investigations[oldest]


def get(investigation_id: str) -> dict | None:
    return _investigations.get(investigation_id)


def recent(limit: int = 20) -> list[dict]:
    return list(reversed(list(_investigations.values())))[:limit]
