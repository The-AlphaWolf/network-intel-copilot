"""Small shared helpers for agent nodes: event construction, timing."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from app.agents.state import AgentEvent
from app.config import get_settings


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_event(agent: str, status: str, message: str, tools_used: list[str], duration_ms: float) -> AgentEvent:
    return AgentEvent(
        agent=agent,
        status=status,
        message=message,
        tools_used=tools_used,
        duration_ms=round(duration_ms, 1),
        timestamp=now_iso(),
    )


def under_budget(llm_calls_so_far: int) -> bool:
    return llm_calls_so_far < get_settings().llm_max_calls_per_investigation


class Timer:
    """Usable both inside the `with` block (elapsed_ms is live) and after it
    exits (elapsed_ms is frozen at the final value)."""

    def __enter__(self):
        self._start = time.time()
        self._frozen: float | None = None
        return self

    def __exit__(self, *exc):
        self._frozen = (time.time() - self._start) * 1000

    @property
    def elapsed_ms(self) -> float:
        return self._frozen if self._frozen is not None else (time.time() - self._start) * 1000
