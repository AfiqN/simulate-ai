"""Unit tests for src.rag.processor."""

import pytest

from src.rag.models import SearchResult, ProcessedFacts, Citation
from src.rag.processor import process_search_results, _jaccard_similarity, _extract_best_sentences as _extract_best_sentence


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


# --- _extract_best_sentence: perspective-first scoring ---

def test_extract_best_sentence_prefers_opinions_over_data():
    content = (
        "Revenue grew 45% in 2024. "
        "Local merchants complain that the new fees are cutting into their thin margins and they refuse to adopt the system."
    )
    result = _extract_best_sentence(content, 200)
    # Should prefer the opinion/complaint sentence over pure data
    assert "complain" in result or "refuse" in result


def test_extract_best_sentence_prefers_attributed_perspectives():
    content = (
        "The regulation was enacted in March 2024. "
        "Drivers say they feel exploited by the commission structure and tend to avoid long-distance rides."
    )
    result = _extract_best_sentence(content, 200)
    assert "say" in result or "feel" in result or "tend to" in result


def test_extract_best_sentence_prefers_behavioral_patterns():
    content = (
        "The GDP growth rate was 5.2% annually. "
        "Rural communities usually prefer cash transactions and are reluctant to trust mobile apps with their savings."
    )
    result = _extract_best_sentence(content, 200)
    assert "usually" in result or "reluctant" in result


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


def test_extract_best_sentence_demotes_pure_regulatory():
    content = (
        "Pursuant to regulation 12/2024, all entities must comply with subsection 3(a) of the mandate. "
        "Workers feel frustrated because the new policy forced them to change their routines overnight."
    )
    result = _extract_best_sentence(content, 200)
    # Should prefer the human perspective over regulatory boilerplate
    assert "frustrated" in result or "forced" in result


# --- process_search_results ---

def _make_result(title="T", url="http://x.com", content="Some content here.", score=0.8) -> SearchResult:
    return SearchResult(title=title, url=url, content=content, score=score)


def test_process_filters_low_score_results():
    results = [
        _make_result(score=0.29, content="Low score content that is filtered out by minimum threshold."),
        _make_result(score=0.9, content="Local vendors say they struggle with the new payment system and often refuse to use it with customers."),
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
        _make_result(score=0.9, content="Merchants complain that QRIS fees are too high and refuse to adopt the new system in their shops."),
        _make_result(score=0.85, content="Young consumers feel frustrated when their favorite warung does not accept digital payments yet."),
    ]
    processed = process_search_results(results, max_facts=4)
    assert len(processed.facts) == 2


def test_process_respects_max_facts():
    contents = [
        "Elderly residents say they feel confused by the smartphone interface and prefer dealing with cash at the local market stalls.",
        "Drivers complain that the commission structure forced them to work longer hours just to maintain their previous income levels.",
        "Students believe the cashback promotions are the main reason they switched from cash and they tend to avoid places without e-wallet.",
        "Small shop owners feel frustrated because customers now expect digital payment but the transaction fees eat into thin profit margins.",
        "Rural farmers usually distrust mobile banking apps because they worry about losing their savings to technical glitches or scams.",
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
        _make_result(score=0.6, content="Workers say they feel exploited by the new gig economy rules and tend to avoid taking short rides.", url="http://low.com"),
        _make_result(score=0.95, content="Community leaders believe the policy forced residents to abandon traditional practices they had relied on for decades.", url="http://high.com"),
    ]
    processed = process_search_results(results, max_facts=4)
    assert processed.citations[0].url == "http://high.com"


def test_process_returns_processed_facts_type():
    results = [_make_result(score=0.7, content="Villagers say they usually refuse to adopt new technology because they worry it will replace their livelihoods.")]
    processed = process_search_results(results, max_facts=4)
    assert isinstance(processed, ProcessedFacts)
    assert isinstance(processed.citations[0], Citation)


def test_process_all_below_threshold():
    results = [_make_result(score=0.2), _make_result(score=0.4)]
    processed = process_search_results(results, max_facts=4)
    assert processed.facts == []
