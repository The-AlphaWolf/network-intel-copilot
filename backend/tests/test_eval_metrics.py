import pytest

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


def test_recall_at_k_full_hit():
    assert recall_at_k(["a", "b", "c"], ["a", "b"], 5) == 1.0


def test_recall_at_k_partial_hit():
    assert recall_at_k(["a", "x", "y"], ["a", "b"], 5) == 0.5


def test_recall_at_k_respects_k():
    assert recall_at_k(["x", "y", "a"], ["a"], 2) == 0.0


def test_recall_at_k_empty_relevant_is_perfect():
    assert recall_at_k(["a"], [], 5) == 1.0


def test_precision_at_k():
    assert precision_at_k(["a", "b", "x"], ["a", "b"], 3) == pytest.approx(2 / 3)


def test_precision_at_k_empty_retrieved():
    assert precision_at_k([], ["a"], 5) == 0.0


def test_mrr_first_hit():
    assert mean_reciprocal_rank(["a", "b"], ["a"]) == 1.0


def test_mrr_second_hit():
    assert mean_reciprocal_rank(["x", "a"], ["a"]) == 0.5


def test_mrr_no_hit():
    assert mean_reciprocal_rank(["x", "y"], ["a"]) == 0.0


def test_citation_correctness_all_valid():
    assert citation_correctness(["c1", "c2"], {"c1", "c2", "c3"}) == 1.0


def test_citation_correctness_some_invalid():
    assert citation_correctness(["c1", "fake"], {"c1", "c2"}) == 0.5


def test_citation_correctness_empty_is_perfect():
    assert citation_correctness([], {"c1"}) == 1.0


def test_lexical_faithfulness_full_overlap():
    score = lexical_faithfulness("cell congestion prb utilization", ["cell congestion prb utilization high"])
    assert score == 1.0


def test_lexical_faithfulness_no_overlap():
    score = lexical_faithfulness("completely unrelated words here", ["congestion prb utilization"])
    assert score == 0.0


def test_lexical_faithfulness_empty_claim():
    assert lexical_faithfulness("", ["some text"]) == 1.0


def test_root_cause_top1_correct():
    assert root_cause_top1_correct("congestion", ["congestion"]) is True
    assert root_cause_top1_correct("interference", ["congestion"]) is False


def test_root_cause_topk_correct():
    assert root_cause_topk_correct(["backhaul_degradation", "congestion"], ["congestion"], k=3) is True
    assert root_cause_topk_correct(["backhaul_degradation", "poor_coverage"], ["congestion"], k=1) is False


def test_action_keyword_hit_rate():
    text = "Enable carrier aggregation and adjust load balancing parameters"
    assert action_keyword_hit_rate(text, ["carrier aggregation", "load"]) == 1.0
    assert action_keyword_hit_rate(text, ["carrier aggregation", "missing keyword"]) == 0.5


def test_action_keyword_hit_rate_empty_keywords():
    assert action_keyword_hit_rate("anything", []) == 1.0
