"""Pure, unit-testable evaluation metrics. No I/O, no LLM calls here - just
functions over plain lists/dicts so they're trivial to test and reuse from
run_eval.py."""
from __future__ import annotations

import re


def recall_at_k(retrieved_doc_ids: list[str], relevant_doc_ids: list[str], k: int) -> float:
    """Fraction of relevant docs that appear anywhere in the top-k retrieved."""
    if not relevant_doc_ids:
        return 1.0
    top_k = set(retrieved_doc_ids[:k])
    hits = sum(1 for d in relevant_doc_ids if d in top_k)
    return hits / len(relevant_doc_ids)


def precision_at_k(retrieved_doc_ids: list[str], relevant_doc_ids: list[str], k: int) -> float:
    top_k = retrieved_doc_ids[:k]
    if not top_k:
        return 0.0
    relevant = set(relevant_doc_ids)
    hits = sum(1 for d in top_k if d in relevant)
    return hits / len(top_k)


def mean_reciprocal_rank(retrieved_doc_ids: list[str], relevant_doc_ids: list[str]) -> float:
    relevant = set(relevant_doc_ids)
    for i, doc_id in enumerate(retrieved_doc_ids, start=1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def citation_correctness(cited_chunk_ids: list[str], valid_chunk_ids: set[str]) -> float:
    """Fraction of emitted citations that resolve to an actually-retrieved
    chunk_id. 1.0 means no citation was fabricated."""
    if not cited_chunk_ids:
        return 1.0
    valid = sum(1 for c in cited_chunk_ids if c in valid_chunk_ids)
    return valid / len(cited_chunk_ids)


_WORD_RE = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def lexical_faithfulness(claim: str, source_texts: list[str]) -> float:
    """Fallback faithfulness signal (used in LLM_MODE=stub or as a sanity
    check alongside an LLM judge): fraction of the claim's content words that
    also appear somewhere in the cited source passages. Not a substitute for
    a real judge, but a real, deterministic, zero-cost lower bound."""
    claim_words = _words(claim)
    if not claim_words:
        return 1.0
    source_words: set[str] = set()
    for t in source_texts:
        source_words |= _words(t)
    if not source_words:
        return 0.0
    overlap = claim_words & source_words
    return len(overlap) / len(claim_words)


def root_cause_top1_correct(predicted_category: str, acceptable_categories: list[str]) -> bool:
    return predicted_category in acceptable_categories


def root_cause_topk_correct(predicted_categories: list[str], acceptable_categories: list[str], k: int = 3) -> bool:
    return any(c in acceptable_categories for c in predicted_categories[:k])


def action_keyword_hit_rate(actions_text: str, expected_keywords: list[str]) -> float:
    """Fraction of expected keywords/phrases found (case-insensitive
    substring match) anywhere in the concatenated recommendation text."""
    if not expected_keywords:
        return 1.0
    text = actions_text.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in text)
    return hits / len(expected_keywords)
