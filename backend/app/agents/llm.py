"""LLM call machinery: one client factory, one retrying call function, one
tolerant JSON extractor. Domain-specific stub output lives in each agent node
(the template needs the node's own tool data), not here - this module only
decides *whether* to call a live model and how to parse what comes back.
"""
from __future__ import annotations

import json
import re
import time

from app.config import Settings, get_settings
from app.logging_conf import get_logger

logger = get_logger("agents.llm")

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def is_stub_mode(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return settings.llm_mode.lower() == "stub" or not settings.openai_api_key


class LLMUnavailable(Exception):
    """Raised when a live call fails after retries - callers should fall
    back to a rule-based result rather than let the investigation fail."""


_client = None


def _get_client(settings: Settings):
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    return _client


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 900,
    temperature: float = 0.2,
    retries: int = 2,
) -> str:
    """One chat completion call against the configured OpenAI-compatible
    endpoint. Raises LLMUnavailable after exhausting retries - callers
    (agent nodes) must catch this and fall back to a rule-based result."""
    settings = get_settings()
    client = _get_client(settings)

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=settings.llm_timeout_seconds,
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                return content
            # Reasoning models sometimes emit only a `reasoning` field and
            # truncate content at the token budget - treat as retryable.
            raise ValueError("empty completion content")
        except Exception as exc:  # noqa: BLE001 - deliberately broad, we retry/fallback
            last_err = exc
            logger.warning("llm_call_failed", attempt=attempt, error=str(exc))
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))

    raise LLMUnavailable(str(last_err))


def extract_json(text: str) -> dict | list | None:
    """Pull a JSON object/array out of LLM output that may be wrapped in
    markdown fences, prefixed with prose, or otherwise not-quite-clean."""
    candidates = []
    fence_matches = _JSON_FENCE_RE.findall(text)
    candidates.extend(fence_matches)
    candidates.append(text)

    for candidate in candidates:
        candidate = candidate.strip()
        # Try direct parse first.
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        # Try slicing to the outermost {...} or [...] block.
        for open_c, close_c in (("{", "}"), ("[", "]")):
            start = candidate.find(open_c)
            end = candidate.rfind(close_c)
            if start != -1 and end != -1 and end > start:
                snippet = candidate[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    continue
    return None


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 900,
    temperature: float = 0.2,
) -> dict | list | None:
    """call_llm + extract_json, returns None on any failure (call or parse)
    so the caller's rule-based fallback path takes over."""
    try:
        raw = call_llm(system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature)
    except LLMUnavailable as exc:
        logger.warning("llm_unavailable_using_fallback", error=str(exc))
        return None
    parsed = extract_json(raw)
    if parsed is None:
        logger.warning("llm_json_parse_failed", raw_preview=raw[:200])
    return parsed
