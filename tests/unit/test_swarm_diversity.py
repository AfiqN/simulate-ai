from src.agent.profile import AgentAttributes, AgentProfile
from src.agent.swarm import _action_coverage_block, _diversity_is_low, _retry_hint

from tests.unit.conftest import make_schema


def _profile(agent_id: str, cluster: str, state: str, rat: float, agg: float, risk: float) -> AgentProfile:
    return AgentProfile(
        agent_id=agent_id,
        archetype="x",
        linguistic_cluster_id=cluster,
        attributes=AgentAttributes(rationality_index=rat, aggressiveness=agg, risk_tolerance=risk),
        current_internal_state=state,
    )


def test_action_coverage_block_lists_every_action():
    schema = make_schema(actions=[("ADOPT", False), ("AMEND", False), ("REJECT", True)])
    block = _action_coverage_block(schema, 5)
    assert "ACTION COVERAGE" in block
    assert "ADOPT" in block
    assert "AMEND" in block
    assert "REJECT" in block
    assert "terminal" in block


def test_diversity_is_low_flags_monoculture():
    schema = make_schema()
    flat = [_profile(f"A{i}", "a", "Neutral", 0.5, 0.5, 0.5) for i in range(5)]
    assert _diversity_is_low(flat, schema) is True


def test_diversity_is_low_accepts_varied_swarm():
    schema = make_schema()
    diverse = [
        _profile("A1", "a", "Neutral", 0.9, 0.2, 0.1),
        _profile("A2", "b", "Skeptical", 0.3, 0.8, 0.9),
        _profile("A3", "c", "Excited", 0.7, 0.5, 0.5),
        _profile("A4", "a", "Cautious", 0.4, 0.7, 0.3),
        _profile("A5", "b", "Resolute", 0.2, 0.3, 0.8),
    ]
    assert _diversity_is_low(diverse, schema) is False


def test_diversity_is_low_short_circuits_small_swarm():
    schema = make_schema()
    small = [_profile(f"A{i}", "a", "Neutral", 0.5, 0.5, 0.5) for i in range(3)]
    assert _diversity_is_low(small, schema) is False


def test_retry_hint_dispatches_on_diversity_error():
    schema = make_schema()
    hint = _retry_hint("diversity_low: clustered", schema)
    assert "action-monoculture" in hint
    for action in schema.action_names():
        assert action in hint


def test_retry_hint_falls_through_for_shape_error():
    schema = make_schema()
    hint = _retry_hint("missing 'agents' key", schema)
    assert "shape" in hint.lower()
    assert "action-monoculture" not in hint
