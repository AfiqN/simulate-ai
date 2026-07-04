"""Unit tests for src/report/metrics.py — quantitative report metrics."""

import pytest

from src.report.metrics import (
    compute_quantitative_metrics,
    format_metrics_block,
    _consensus_index,
    _dimension_stats,
    _find_driver_dimension,
    _net_confidence,
    _state_transitions,
    _swing_analysis,
    _vote_tally,
)
from src.schema.simulation_schema import (
    ActionDefinition,
    LinguisticCluster,
    ResourceModel,
    SimulationSchema,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _schema() -> SimulationSchema:
    return SimulationSchema(
        scenario_name="Test Scenario",
        scenario_description="A test",
        verdict_label="Test Verdict",
        actions=[
            ActionDefinition(name="INVEST", description="invest"),
            ActionDefinition(name="PASS", description="pass", is_terminal=True),
            ActionDefinition(name="COUNTER", description="counter"),
        ],
        state_vocabulary=["Optimistic", "Cautious", "Skeptical", "Neutral"],
        resource_model=ResourceModel(kind="none"),
        linguistic_clusters=[
            LinguisticCluster(cluster_id="formal", description="formal", style_prompt="be formal"),
        ],
        macro_context=["test context"],
        crisis_dimensions=["market_crash"],
        evaluation_dimensions=["financial_return", "market_fit", "execution_risk"],
    )


def _decisions_r1():
    return [
        {
            "id": "agent_1",
            "archetype": "VC Partner",
            "action": "INVEST",
            "utility": 0.6,
            "utility_dimensions": {"financial_return": 0.8, "market_fit": 0.5, "execution_risk": 0.5},
            "reasoning_chain": [
                {"dimension": "financial_return", "score": 0.8, "reasoning": "High upside"},
                {"dimension": "market_fit", "score": 0.5, "reasoning": "Decent fit"},
                {"dimension": "execution_risk", "score": 0.5, "reasoning": "Some risk"},
            ],
            "new_state": "Optimistic",
        },
        {
            "id": "agent_2",
            "archetype": "Skeptical Analyst",
            "action": "PASS",
            "utility": -0.3,
            "utility_dimensions": {"financial_return": -0.2, "market_fit": -0.4, "execution_risk": -0.3},
            "reasoning_chain": [
                {"dimension": "financial_return", "score": -0.2, "reasoning": "Unclear returns"},
                {"dimension": "market_fit", "score": -0.4, "reasoning": "Bad fit"},
                {"dimension": "execution_risk", "score": -0.3, "reasoning": "High risk"},
            ],
            "new_state": "Skeptical",
        },
        {
            "id": "agent_3",
            "archetype": "Pragmatist",
            "action": "COUNTER",
            "utility": 0.2,
            "utility_dimensions": {"financial_return": 0.3, "market_fit": 0.2, "execution_risk": 0.1},
            "reasoning_chain": [
                {"dimension": "financial_return", "score": 0.3, "reasoning": "Moderate"},
                {"dimension": "market_fit", "score": 0.2, "reasoning": "Okay"},
                {"dimension": "execution_risk", "score": 0.1, "reasoning": "Manageable"},
            ],
            "new_state": "Cautious",
        },
    ]


def _decisions_r2():
    return [
        {
            "id": "agent_1",
            "archetype": "VC Partner",
            "action": "INVEST",
            "utility": 0.65,
            "utility_dimensions": {"financial_return": 0.85, "market_fit": 0.55, "execution_risk": 0.55},
            "new_state": "Optimistic",
        },
        {
            "id": "agent_2",
            "archetype": "Skeptical Analyst",
            "action": "COUNTER",  # Flipped from PASS
            "utility": 0.1,
            "utility_dimensions": {"financial_return": 0.1, "market_fit": 0.0, "execution_risk": 0.2},
            "new_state": "Cautious",  # State change
        },
        {
            "id": "agent_3",
            "archetype": "Pragmatist",
            "action": "COUNTER",
            "utility": 0.25,
            "utility_dimensions": {"financial_return": 0.35, "market_fit": 0.25, "execution_risk": 0.15},
            "new_state": "Cautious",
        },
    ]


def _decisions_r3():
    return [
        {
            "id": "agent_1",
            "archetype": "VC Partner",
            "action": "COUNTER",  # Flipped from INVEST
            "utility": 0.3,
            "utility_dimensions": {"financial_return": 0.4, "market_fit": 0.3, "execution_risk": 0.2},
            "new_state": "Cautious",  # State change
        },
        {
            "id": "agent_2",
            "archetype": "Skeptical Analyst",
            "action": "PASS",  # Flipped back to PASS
            "utility": -0.2,
            "utility_dimensions": {"financial_return": -0.1, "market_fit": -0.3, "execution_risk": -0.2},
            "new_state": "Skeptical",  # State change
        },
        {
            "id": "agent_3",
            "archetype": "Pragmatist",
            "action": "COUNTER",
            "utility": 0.15,
            "utility_dimensions": {"financial_return": 0.2, "market_fit": 0.15, "execution_risk": 0.1},
            "new_state": "Neutral",  # State change
        },
    ]


# ---------------------------------------------------------------------------
# Tests: Vote Tally
# ---------------------------------------------------------------------------


def test_vote_tally_basic():
    schema = _schema()
    result = _vote_tally(_decisions_r1(), _decisions_r2(), _decisions_r3(), schema)
    assert result["r1"] == {"INVEST": 1, "PASS": 1, "COUNTER": 1}
    assert result["r2"] == {"INVEST": 1, "COUNTER": 2}
    assert result["r3"] == {"COUNTER": 2, "PASS": 1}


def test_vote_tally_filters_errors():
    schema = _schema()
    r1 = [{"id": "a", "action": "INVEST", "error": "timeout"}]
    result = _vote_tally(r1, [], [], schema)
    assert result == {}


# ---------------------------------------------------------------------------
# Tests: Dimension Stats
# ---------------------------------------------------------------------------


def test_dimension_stats_computes_mean_and_range():
    result = _dimension_stats(_decisions_r1(), _decisions_r2(), _decisions_r3())
    r1_stats = result["r1"]
    # financial_return: [0.8, -0.2, 0.3] → mean=0.3, min=-0.2, max=0.8
    assert abs(r1_stats["financial_return"]["mean"] - 0.3) < 0.01
    assert abs(r1_stats["financial_return"]["min"] - (-0.2)) < 0.01
    assert abs(r1_stats["financial_return"]["max"] - 0.8) < 0.01


def test_dimension_stats_empty_dimensions():
    decisions = [{"id": "a", "action": "INVEST", "utility": 0.5, "utility_dimensions": {}}]
    result = _dimension_stats(decisions, [], [])
    assert result == {}


# ---------------------------------------------------------------------------
# Tests: State Transitions
# ---------------------------------------------------------------------------


def test_state_transitions_counts_shifts():
    result = _state_transitions(_decisions_r1(), _decisions_r2(), _decisions_r3())
    # R1→R2: agent_2 Skeptical→Cautious (1 shift out of 3)
    assert result["r1_to_r2"]["shifted_count"] == 1
    assert result["r1_to_r2"]["total"] == 3
    # R2→R3: agent_1 Optimistic→Cautious, agent_2 Cautious→Skeptical, agent_3 Cautious→Neutral (3 shifts)
    assert result["r2_to_r3"]["shifted_count"] == 3
    assert result["r2_to_r3"]["total"] == 3


def test_state_transitions_top_shifts():
    result = _state_transitions(_decisions_r1(), _decisions_r2(), _decisions_r3())
    top = result["r1_to_r2"]["top_shifts"]
    assert len(top) == 1
    assert top[0]["from"] == "Skeptical"
    assert top[0]["to"] == "Cautious"


# ---------------------------------------------------------------------------
# Tests: Swing Analysis
# ---------------------------------------------------------------------------


def test_swing_analysis_identifies_flippers():
    result = _swing_analysis(_decisions_r1(), _decisions_r2(), _decisions_r3())
    # R1→R2: agent_2 flipped PASS→COUNTER
    assert len(result["r1_to_r2"]) == 1
    swing = result["r1_to_r2"][0]
    assert swing["id"] == "agent_2"
    assert swing["from_action"] == "PASS"
    assert swing["to_action"] == "COUNTER"


def test_swing_analysis_driver_dimension():
    result = _swing_analysis(_decisions_r1(), _decisions_r2(), _decisions_r3())
    swing = result["r1_to_r2"][0]
    # agent_2: financial_return went from -0.2 to 0.1 (Δ=0.3), execution_risk from -0.3 to 0.2 (Δ=0.5)
    assert swing["driver_dimension"] == "execution_risk"


def test_swing_analysis_r2_to_r3():
    result = _swing_analysis(_decisions_r1(), _decisions_r2(), _decisions_r3())
    # R2→R3: agent_1 INVEST→COUNTER, agent_2 COUNTER→PASS (2 flippers)
    assert len(result["r2_to_r3"]) == 2


# ---------------------------------------------------------------------------
# Tests: Consensus Index (HHI)
# ---------------------------------------------------------------------------


def test_consensus_index_fragmented():
    result = _consensus_index(_decisions_r1(), _decisions_r2(), _decisions_r3())
    # R1: 3 different actions, each 1/3 → HHI = 3*(1/3)^2 = 1/3 ≈ 0.333
    assert abs(result["r1"] - (1.0 / 3.0)) < 0.01


def test_consensus_index_partial_convergence():
    result = _consensus_index(_decisions_r1(), _decisions_r2(), _decisions_r3())
    # R2: INVEST=1, COUNTER=2 → HHI = (1/3)^2 + (2/3)^2 = 1/9 + 4/9 = 5/9 ≈ 0.556
    assert abs(result["r2"] - (5.0 / 9.0)) < 0.01


def test_consensus_index_unanimous():
    unanimous = [
        {"id": "a", "action": "INVEST", "utility": 0.5},
        {"id": "b", "action": "INVEST", "utility": 0.6},
    ]
    result = _consensus_index(unanimous, [], [])
    assert abs(result["r1"] - 1.0) < 0.01


# ---------------------------------------------------------------------------
# Tests: Net Confidence
# ---------------------------------------------------------------------------


def test_net_confidence_basic():
    result = _net_confidence(_decisions_r1(), _decisions_r2(), _decisions_r3())
    # R1: |0.6| + |-0.3| + |0.2| = 1.1, avg = 1.1/3 ≈ 0.367
    assert abs(result["r1"] - (1.1 / 3.0)) < 0.01


# ---------------------------------------------------------------------------
# Tests: find_driver_dimension
# ---------------------------------------------------------------------------


def test_find_driver_no_dimensions():
    before = {"utility_dimensions": {}}
    after = {"utility_dimensions": {}}
    assert _find_driver_dimension(before, after) == "aggregate"


def test_find_driver_with_dimensions():
    before = {"utility_dimensions": {"a": 0.5, "b": 0.1}}
    after = {"utility_dimensions": {"a": 0.5, "b": 0.9}}  # b shifted most
    assert _find_driver_dimension(before, after) == "b"


# ---------------------------------------------------------------------------
# Tests: Full compute_quantitative_metrics
# ---------------------------------------------------------------------------


def test_compute_quantitative_metrics_returns_all_keys():
    schema = _schema()
    result = compute_quantitative_metrics(
        _decisions_r1(), _decisions_r2(), _decisions_r3(), schema
    )
    assert "vote_tally" in result
    assert "dimension_stats" in result
    assert "state_transitions" in result
    assert "swing_analysis" in result
    assert "consensus_index" in result
    assert "net_confidence" in result


def test_compute_quantitative_metrics_empty_rounds():
    schema = _schema()
    result = compute_quantitative_metrics([], [], [], schema)
    assert result["vote_tally"] == {}
    assert result["consensus_index"] == {}
    assert result["net_confidence"] == {}


# ---------------------------------------------------------------------------
# Tests: format_metrics_block
# ---------------------------------------------------------------------------


def test_format_metrics_block_contains_sections():
    schema = _schema()
    metrics = compute_quantitative_metrics(
        _decisions_r1(), _decisions_r2(), _decisions_r3(), schema
    )
    block = format_metrics_block(metrics)
    assert "PRE-COMPUTED QUANTITATIVE METRICS" in block
    assert "Vote Tally" in block
    assert "Per-Dimension Score Distributions" in block
    assert "State Transitions" in block
    assert "Swing Analysis" in block
    assert "Consensus Index" in block
    assert "Net Confidence" in block


def test_format_metrics_block_empty_graceful():
    schema = _schema()
    metrics = compute_quantitative_metrics([], [], [], schema)
    block = format_metrics_block(metrics)
    assert "PRE-COMPUTED QUANTITATIVE METRICS" in block
    # Should not crash on empty data
    assert "Vote Tally" in block
