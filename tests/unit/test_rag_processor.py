"""Unit tests for src.rag.processor."""

import pytest

from src.rag.models import SearchResult, ProcessedFacts, Citation
from src.rag.processor import process_search_results, _jaccard_similarity, _extract_best_sentence


# --- _jaccard_similarity ---

def test_jaccard_identical_texts():
    assert _jaccard_similarity("hello world", "hello world") == 1.0


def test_jaccard_completely_different():
    assert _jaccard_similarity("cat dog", "fish bird") == 0.0


def test_jaccard_partial_overlap():
    sim = _jaccard_similarity("the cat sat", "the dog sat")
    # intersection: {the, sat} = 2, union: {the, cat, sat, dog} = 4 → 0.5
    assert sim == pytest.approx(0.5)


def test_jaccard_empty_string_returns_zero():
    assert _jaccard_similarity("", "hello") == 0.0
    assert _jaccard_similarity("hello", "") == 0.0
    assert _jaccard_similarity("", "") == 0.0


def test_jaccard_case_insensitive():
    assert _jaccard_similarity("Hello World", "hello world") == 1.0


# --- _extract_best_sentence ---

def test_extract_best_sentence_prefers_numbers():
    content = "This is a vague statement. Revenue grew 45% in 2024. Another filler."
    result = _extract_best_sentence(content, 150)
    assert "45%" in result or "2024" in result


def test_extract_best_sentence_respects_max_chars():
    content = "A very long sentence that goes on forever " * 10
    result = _extract_best_sentence(content, 50)
    assert len(result) <= 50


def test_extract_best_sentence_empty_content():
    result = _extract_best_sentence("", 150)
    assert result == ""


def test_extract_best_sentence_single_sentence():
    content = "Only one sentence here but it needs to be long enough to pass filters"
    result = _extract_best_sentence(content, 150)
    assert result == "Only one sentence here but it needs to be long enough to pass filters"


# --- process_search_results ---

def _make_result(title="T", url="http://x.com", content="Some content here.", score=0.8) -> SearchResult:
    return SearchResult(title=title, url=url, content=content, score=score)


def test_process_filters_low_score_results():
    results = [
        _make_result(score=0.3, content="Low score content that is filtered out by minimum threshold."),
        _make_result(score=0.9, content="According to a 2024 KFF poll, two-thirds of insured adults believe claim denials are a major problem."),
    ]
    processed = process_search_results(results, max_facts=4)
    assert len(processed.facts) == 1
    assert len(processed.citations) == 1


def test_process_deduplicates_similar_content():
    results = [
        _make_result(score=0.9, content="The quick brown fox jumps over the lazy dog today"),
        _make_result(score=0.8, content="The quick brown fox jumps over the lazy dog today"),
    ]
    processed = process_search_results(results, max_facts=4)
    assert len(processed.facts) == 1


def test_process_keeps_distinct_content():
    results = [
        _make_result(score=0.9, content="Indonesia fintech regulation update 2024."),
        _make_result(score=0.85, content="Global semiconductor shortage impacts manufacturing."),
    ]
    processed = process_search_results(results, max_facts=4)
    assert len(processed.facts) == 2


def test_process_respects_max_facts():
    contents = [
        "According to the CDC, childhood obesity rates increased by 15% between 2019 and 2023 in the United States.",
        "The Federal Reserve raised interest rates to 5.25% in 2024, the highest level since 2001 according to official data.",
        "A 2025 WHO report found that global vaccination coverage declined by 8% during the pandemic recovery period.",
        "Research from MIT indicates that renewable energy costs fell by 40% between 2020 and 2025 in developed nations.",
        "The European GDPR regulation resulted in 2.1 billion euros in fines issued across member states by end of 2024.",
    ]
    results = [_make_result(score=0.9, content=c, url=f"http://x{i}.com") for i, c in enumerate(contents)]
    processed = process_search_results(results, max_facts=3)
    assert len(processed.facts) == 3
    assert len(processed.citations) == 3


def test_process_returns_empty_for_no_results():
    processed = process_search_results([], max_facts=4)
    assert processed.facts == []
    assert processed.citations == []
    assert processed.raw_results == []


def test_process_sorts_by_score_descending():
    results = [
        _make_result(score=0.6, content="A 2023 study found that lower-priority policies reduced compliance by 12% across the sector.", url="http://low.com"),
        _make_result(score=0.95, content="According to the FDA, the regulation required manufacturers to report 95% of adverse events within 30 days.", url="http://high.com"),
    ]
    processed = process_search_results(results, max_facts=4)
    assert processed.citations[0].url == "http://high.com"


def test_process_returns_processed_facts_type():
    results = [_make_result(score=0.7, content="Research indicates that the policy led to a 25% reduction in processing delays across federal agencies.")]
    processed = process_search_results(results, max_facts=4)
    assert isinstance(processed, ProcessedFacts)
    assert isinstance(processed.citations[0], Citation)


def test_process_all_below_threshold():
    results = [_make_result(score=0.2), _make_result(score=0.4)]
    processed = process_search_results(results, max_facts=4)
    assert processed.facts == []
