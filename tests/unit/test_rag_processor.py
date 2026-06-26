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
    content = "Only one sentence here"
    result = _extract_best_sentence(content, 150)
    assert result == "Only one sentence here"


# --- process_search_results ---

def _make_result(title="T", url="http://x.com", content="Some content here.", score=0.8) -> SearchResult:
    return SearchResult(title=title, url=url, content=content, score=score)


def test_process_filters_low_score_results():
    results = [
        _make_result(score=0.3, content="Low score content."),
        _make_result(score=0.9, content="High score content."),
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
    results = [_make_result(score=0.9, content=f"Unique content number {i}.") for i in range(10)]
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
        _make_result(score=0.6, content="Lower scored item.", url="http://low.com"),
        _make_result(score=0.95, content="Higher scored item.", url="http://high.com"),
    ]
    processed = process_search_results(results, max_facts=4)
    assert processed.citations[0].url == "http://high.com"


def test_process_returns_processed_facts_type():
    results = [_make_result(score=0.7, content="Some fact.")]
    processed = process_search_results(results, max_facts=4)
    assert isinstance(processed, ProcessedFacts)
    assert isinstance(processed.citations[0], Citation)


def test_process_all_below_threshold():
    results = [_make_result(score=0.2), _make_result(score=0.4)]
    processed = process_search_results(results, max_facts=4)
    assert processed.facts == []
