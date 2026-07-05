"""Tests for src/report/sensitivity.py."""

import pytest

from src.report.sensitivity import (
    compute_sensitivity_analysis,
    _flip_margins,
    _dimension_leverage,
    _coalition_fragility,
    _influence_sensitivity,
    format_sensitivity_block,
)
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decision(agent_id, archetype, action, utility, dims=None):
    d = {
        "id": agent_id,
        "archetype": archetype,
        "action": action,
        "utility": utility,
    }
    if dims:
        d["utility_dimensions"] = dims
    return d


def _profile(agent_id, weight=1.0):
    return SimpleNamespace(agent_id=agent_id, influence_weight=weight)


def _standard_decisions():
    return [
        _decision("a0", "Pragmatist", "SUPPORT", 0.7, {"econ": 0.8, "social": 0.3}),
        _decision("a1", "Idealist", "SUPPORT", 0.5, {"econ": 0.4, "social": 0.7}),
        _decision("a2", "Contrarian", "OPPOSE", -0.2, {"econ": -0.3, "social": 0.1}),
        _decision("a3", "Moderate", "SUPPORT", 0.15, {"econ": 0.2, "social": 0.1}),
        _decision("a4", "Skeptic", "OPPOSE", -0.6, {"econ": -0.5, "social": -0.4}),
    ]


# ---------------------------------------------------------------------------
# Tests: _flip_margins
# ---------------------------------------------------------------------------

def test_flip_margins_sorted_ascending():
    decisions = _standard_decisions()
    margins = _flip_margins(decisions)
    # Should be sorted by margin ascending (most fragile first)
    assert margins[0]["id"] == "a3"  # utility 0.15 → margin 0.15
    assert margins[0]["fragile"] is True
    assert margins[-1]["fragile"] is False


def test_flip_margins_correct_values():
    decisions = [_decision("x", "X", "ACT", 0.1)]
    margins = _flip_margins(decisions)
    assert len(margins) == 1
    assert margins[0]["flip_margin"] == pytest.approx(0.1)
    assert margins[0]["fragile"] is True


def test_flip_margins_skips_errors():
    decisions = [{"id": "x", "error": "failed"}]
    margins = _flip_margins(decisions)
    assert margins == []


# ---------------------------------------------------------------------------
# Tests: _dimension_leverage
# ---------------------------------------------------------------------------

def test_dimension_leverage_returns_all_dims():
    decisions = _standard_decisions()
    leverage = _dimension_leverage(decisions)
    assert "econ" in leverage
    assert "social" in leverage


def test_dimension_leverage_has_stats():
    decisions = _standard_decisions()
    leverage = _dimension_leverage(decisions)
    for dim, stats in leverage.items():
        assert "mean" in stats
        assert "stdev" in stats
        assert "range" in stats
        assert "action_separation" in stats


def test_dimension_leverage_empty_returns_empty():
    assert _dimension_leverage([]) == {}
    assert _dimension_leverage([{"id": "x", "action": "A", "utility": 0.5}]) == {}


# ---------------------------------------------------------------------------
# Tests: _coalition_fragility
# ---------------------------------------------------------------------------

def test_coalition_fragility_standard():
    decisions = _standard_decisions()
    cf = _coalition_fragility(decisions)
    assert cf["majority_action"] == "SUPPORT"
    assert cf["majority_count"] == 3
    assert cf["runner_up_action"] == "OPPOSE"
    assert cf["runner_up_count"] == 2
    assert cf["flips_to_overturn"] == 1  # (3-2)//2 + 1 = 1
    assert 0.0 < cf["fragility_ratio"] <= 1.0


def test_coalition_fragility_unanimous():
    decisions = [
        _decision("a0", "A", "SUPPORT", 0.5),
        _decision("a1", "B", "SUPPORT", 0.6),
        _decision("a2", "C", "SUPPORT", 0.7),
    ]
    cf = _coalition_fragility(decisions)
    assert cf["majority_action"] == "SUPPORT"
    assert cf["flips_to_overturn"] == 2  # (3-0)//2 + 1 = 2


def test_coalition_fragility_empty():
    cf = _coalition_fragility([])
    assert cf["majority_action"] is None
    assert cf["flips_to_overturn"] == 0


# ---------------------------------------------------------------------------
# Tests: _influence_sensitivity
# ---------------------------------------------------------------------------

def test_influence_sensitivity_dominated():
    decisions = [
        _decision("a0", "CEO", "SUPPORT", 0.8),
        _decision("a1", "Intern", "OPPOSE", -0.3),
        _decision("a2", "Analyst", "OPPOSE", -0.4),
    ]
    profiles = [
        _profile("a0", weight=3.0),
        _profile("a1", weight=1.0),
        _profile("a2", weight=1.0),
    ]
    # Weighted: SUPPORT=3.0, OPPOSE=2.0 → SUPPORT wins
    # Without CEO: OPPOSE=2.0 → flips
    result = _influence_sensitivity(decisions, profiles)
    assert result["dominated"] is True
    assert result["dominant_agent"]["id"] == "a0"
    assert result["outcome_without_dominant"] == "OPPOSE"


def test_influence_sensitivity_stable():
    decisions = [
        _decision("a0", "A", "SUPPORT", 0.8),
        _decision("a1", "B", "SUPPORT", 0.6),
        _decision("a2", "C", "OPPOSE", -0.4),
    ]
    profiles = [
        _profile("a0", weight=1.5),
        _profile("a1", weight=1.0),
        _profile("a2", weight=1.0),
    ]
    # Weighted: SUPPORT=2.5, OPPOSE=1.0. Without a0: SUPPORT=1.0, OPPOSE=1.0 → tie, but SUPPORT still wins (dict ordering)
    # Actually without a0: remaining is {SUPPORT: 1.0, OPPOSE: 1.0}, max picks first inserted = SUPPORT
    result = _influence_sensitivity(decisions, profiles)
    assert result["dominated"] is False


def test_influence_sensitivity_no_profiles():
    decisions = _standard_decisions()
    result = _influence_sensitivity(decisions, None)
    assert result["dominated"] is False
    assert result["dominant_agent"] is None


# ---------------------------------------------------------------------------
# Tests: compute_sensitivity_analysis (integration)
# ---------------------------------------------------------------------------

def test_compute_sensitivity_analysis_returns_all_keys():
    decisions = _standard_decisions()
    profiles = [_profile(f"a{i}") for i in range(5)]
    result = compute_sensitivity_analysis(decisions, decisions, decisions, profiles=profiles)
    assert "flip_margins" in result
    assert "dimension_leverage" in result
    assert "coalition_fragility" in result
    assert "influence_sensitivity" in result


def test_compute_sensitivity_analysis_empty_rounds():
    result = compute_sensitivity_analysis([], [], [], profiles=None)
    assert result["flip_margins"] == []
    assert result["dimension_leverage"] == {}
    assert result["coalition_fragility"]["majority_action"] is None


# ---------------------------------------------------------------------------
# Tests: format_sensitivity_block
# ---------------------------------------------------------------------------

def test_format_sensitivity_block_contains_sections():
    decisions = _standard_decisions()
    profiles = [_profile(f"a{i}") for i in range(5)]
    analysis = compute_sensitivity_analysis(decisions, decisions, decisions, profiles=profiles)
    block = format_sensitivity_block(analysis)
    assert "SENSITIVITY ANALYSIS" in block
    assert "Decision Stability" in block
    assert "Coalition Fragility" in block


def test_format_sensitivity_block_empty_graceful():
    analysis = compute_sensitivity_analysis([], [], [], profiles=None)
    block = format_sensitivity_block(analysis)
    assert "SENSITIVITY ANALYSIS" in block
    # Should not crash on empty data
