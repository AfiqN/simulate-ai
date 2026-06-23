from src.agent.adversary import compute_adversary_map


class _FakeAttrs:
    def __init__(self, aggressiveness: float):
        self.aggressiveness = aggressiveness


class _FakeProfile:
    def __init__(self, aggressiveness: float):
        self.attributes = _FakeAttrs(aggressiveness)


class _FakeAgent:
    def __init__(self, aggressiveness: float):
        self.profile = _FakeProfile(aggressiveness)


def _setup(specs: list[tuple[str, str, float, float]]):
    decisions = [
        {"id": agent_id, "action": action, "utility": utility}
        for agent_id, action, utility, _ in specs
    ]
    agents = [_FakeAgent(agg) for _, _, _, agg in specs]
    return decisions, agents


def test_cross_faction_preferred_over_same_action():
    decisions, agents = _setup([
        ("A", "BUY", 0.8, 0.5),
        ("B", "BUY", 0.7, 0.5),
        ("C", "REJECT", -0.5, 0.5),
    ])
    result = compute_adversary_map(decisions, agents)
    assert result["A"]["id"] == "C"
    assert result["B"]["id"] == "C"


def test_flat_collapse_when_all_same_action():
    decisions, agents = _setup([
        ("A", "BUY", 0.8, 0.5),
        ("B", "BUY", 0.2, 0.5),
        ("C", "BUY", -0.3, 0.5),
    ])
    result = compute_adversary_map(decisions, agents)
    for target in result.values():
        assert target is not None


def test_aggressiveness_tie_breaker():
    decisions, agents = _setup([
        ("A", "BUY", 0.5, 0.5),
        ("B", "REJECT", -0.5, 0.3),
        ("C", "REJECT", -0.5, 0.9),
    ])
    result = compute_adversary_map(decisions, agents)
    assert result["A"]["id"] == "C"


def test_rebalance_redirects_orphan_when_swap_valid():
    decisions, agents = _setup([
        ("A", "BUY", 0.8, 0.5),
        ("B", "BUY", 0.7, 0.5),
        ("C", "BUY", 0.6, 0.5),
        ("D", "BUY", 0.5, 0.5),
        ("E", "REJECT", -0.7, 0.5),
    ])
    result = compute_adversary_map(decisions, agents)
    incoming = {d["id"]: 0 for d in decisions}
    for target in result.values():
        if target is not None:
            incoming[target["id"]] += 1
    assert incoming["E"] >= 1


def test_single_agent_has_no_adversary():
    decisions, agents = _setup([("A", "BUY", 0.5, 0.5)])
    result = compute_adversary_map(decisions, agents)
    assert result["A"] is None
