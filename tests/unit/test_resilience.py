from src.report.compiler import compute_resilience_metrics

from tests.unit.conftest import make_schema


def _decision(agent_id: str, action: str, utility: float) -> dict:
    return {"id": agent_id, "action": action, "utility": utility}


def test_indeterminate_when_no_paired_results():
    schema = make_schema()
    result = compute_resilience_metrics([], [], schema)
    assert result["verdict"] == "Indeterminate"
    assert result["paired_count"] == 0


def test_resilient_when_swarm_holds_under_shock():
    schema = make_schema()
    r2 = [_decision(f"A{i}", "ADOPT", 0.6) for i in range(5)]
    r3 = [_decision(f"A{i}", "ADOPT", 0.65) for i in range(5)]
    result = compute_resilience_metrics(r2, r3, schema)
    assert result["verdict"] == "Resilient"
    assert result["decision_stability"] == 1.0
    assert result["utility_drift_mean"] > 0


def test_fragile_when_utility_drift_collapses():
    schema = make_schema()
    r2 = [_decision(f"A{i}", "ADOPT", 0.5) for i in range(5)]
    r3 = [_decision(f"A{i}", "REJECT", -0.6) for i in range(5)]
    result = compute_resilience_metrics(r2, r3, schema)
    assert result["verdict"] == "Fragile"
    assert result["utility_drift_mean"] < -0.4


def test_fragile_when_terminal_share_jumps():
    schema = make_schema()
    r2 = [_decision(f"A{i}", "ADOPT", 0.3) for i in range(5)]
    r3 = [_decision(f"A{i}", "REJECT", 0.1) for i in range(5)]
    result = compute_resilience_metrics(r2, r3, schema)
    assert result["terminal_share_delta"] == 1.0
    assert result["verdict"] == "Fragile"


def test_moderate_when_partial_flip_and_mild_drift():
    schema = make_schema()
    r2 = [_decision(f"A{i}", "ADOPT", 0.4) for i in range(5)]
    r3 = (
        [_decision(f"A{i}", "ADOPT", 0.35) for i in range(2)]
        + [_decision(f"A{i}", "AMEND", 0.1) for i in range(2, 5)]
    )
    result = compute_resilience_metrics(r2, r3, schema)
    assert result["verdict"] == "Moderate"


def test_error_results_excluded_from_paired_count():
    schema = make_schema()
    r2 = [_decision("A1", "ADOPT", 0.5), _decision("A2", "ADOPT", 0.5)]
    r3 = [
        _decision("A1", "ADOPT", 0.5),
        {"id": "A2", "error": "transient"},
    ]
    result = compute_resilience_metrics(r2, r3, schema)
    assert result["paired_count"] == 1


def test_terminal_share_delta_tracks_action_terminality():
    schema = make_schema()
    r2 = [_decision("A1", "ADOPT", 0.5), _decision("A2", "AMEND", 0.0)]
    r3 = [_decision("A1", "REJECT", -0.5), _decision("A2", "AMEND", 0.0)]
    result = compute_resilience_metrics(r2, r3, schema)
    assert result["terminal_share_r2"] == 0.0
    assert result["terminal_share_r3"] == 0.5
