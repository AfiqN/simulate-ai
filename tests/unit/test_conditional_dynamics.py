"""Unit tests for the ConditionalEngine (src/dynamics/conditional.py)."""

import pytest

from src.dynamics.conditional import (
    Condition,
    ConditionalEngine,
    TriggerRule,
    TriggerResult,
    default_rules,
)


# --- Helpers ---

def _make_decisions(actions: list[str], utilities: list[float] | None = None) -> list[dict]:
    """Build a decisions list from action strings."""
    if utilities is None:
        utilities = [0.5] * len(actions)
    return [
        {"id": f"agent-{i}", "action": a, "utility": u}
        for i, (a, u) in enumerate(zip(actions, utilities))
    ]


def _consensus_rule(threshold: float = 0.7, fire_once: bool = True, round_min: int = 1) -> TriggerRule:
    return TriggerRule(
        id="test-consensus",
        name="Test Consensus",
        condition=Condition(type="consensus_reached", params={"threshold": threshold}),
        effect="inject_event",
        effect_params={"event_type": "challenge"},
        fire_once=fire_once,
        round_min=round_min,
    )


def _deadlock_rule(max_share: float = 0.4, round_min: int = 1) -> TriggerRule:
    return TriggerRule(
        id="test-deadlock",
        name="Test Deadlock",
        condition=Condition(type="deadlock", params={"max_share": max_share}),
        effect="inject_event",
        effect_params={"event_type": "tie_breaker"},
        fire_once=True,
        round_min=round_min,
    )


# --- Basic rule evaluation ---

class TestBasicRuleEvaluation:
    def test_consensus_fires_when_threshold_met(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.7)])
        decisions = _make_decisions(["BUY", "BUY", "BUY", "REJECT"])  # 75% BUY
        results = engine.evaluate(round_num=1, decisions=decisions)

        assert len(results) == 1
        assert results[0].rule_id == "test-consensus"
        assert results[0].fired is True
        assert results[0].effect == "inject_event"
        assert results[0].context["action"] == "BUY"
        assert results[0].context["ratio"] >= 0.7

    def test_consensus_does_not_fire_below_threshold(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.9)])
        decisions = _make_decisions(["BUY", "BUY", "BUY", "REJECT"])  # 75% < 90%
        results = engine.evaluate(round_num=1, decisions=decisions)

        assert len(results) == 0

    def test_deadlock_fires_when_no_majority(self):
        engine = ConditionalEngine(rules=[_deadlock_rule(max_share=0.4)])
        # 3 distinct actions, each ~33%
        decisions = _make_decisions(["BUY", "REJECT", "HOLD"])
        results = engine.evaluate(round_num=1, decisions=decisions)

        assert len(results) == 1
        assert results[0].rule_id == "test-deadlock"

    def test_deadlock_does_not_fire_when_majority_exists(self):
        engine = ConditionalEngine(rules=[_deadlock_rule(max_share=0.4)])
        decisions = _make_decisions(["BUY", "BUY", "BUY", "REJECT"])  # 75% > 40%
        results = engine.evaluate(round_num=1, decisions=decisions)

        assert len(results) == 0

    def test_result_round_num_matches_input(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.5)])
        decisions = _make_decisions(["BUY", "BUY", "REJECT"])
        results = engine.evaluate(round_num=3, decisions=decisions)

        assert results[0].round_num == 3


# --- fire_once behavior ---

class TestFireOnce:
    def test_fire_once_prevents_second_trigger(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.6, fire_once=True)])
        decisions = _make_decisions(["BUY", "BUY", "BUY", "REJECT"])

        results_r1 = engine.evaluate(round_num=1, decisions=decisions)
        assert len(results_r1) == 1

        results_r2 = engine.evaluate(round_num=2, decisions=decisions)
        assert len(results_r2) == 0

    def test_fire_once_false_allows_repeated_triggers(self):
        rule = TriggerRule(
            id="repeatable",
            name="Repeatable Consensus",
            condition=Condition(type="consensus_reached", params={"threshold": 0.6}),
            effect="notify",
            effect_params={"message": "consensus again"},
            fire_once=False,
            round_min=1,
        )
        engine = ConditionalEngine(rules=[rule])
        decisions = _make_decisions(["BUY", "BUY", "BUY", "REJECT"])

        results_r1 = engine.evaluate(round_num=1, decisions=decisions)
        assert len(results_r1) == 1

        results_r2 = engine.evaluate(round_num=2, decisions=decisions)
        assert len(results_r2) == 1

        # Both recorded in history
        assert len(engine.history) == 2

    def test_fired_flag_set_on_rule_after_trigger(self):
        rule = _consensus_rule(threshold=0.5, fire_once=True)
        engine = ConditionalEngine(rules=[rule])
        decisions = _make_decisions(["BUY", "BUY", "REJECT"])

        assert rule.fired is False
        engine.evaluate(round_num=1, decisions=decisions)
        assert rule.fired is True


# --- round_min gating ---

class TestRoundMinGating:
    def test_rule_does_not_fire_before_round_min(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.5, round_min=3)])
        decisions = _make_decisions(["BUY", "BUY", "REJECT"])

        results_r1 = engine.evaluate(round_num=1, decisions=decisions)
        assert len(results_r1) == 0

        results_r2 = engine.evaluate(round_num=2, decisions=decisions)
        assert len(results_r2) == 0

    def test_rule_fires_at_round_min(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.5, round_min=3)])
        decisions = _make_decisions(["BUY", "BUY", "REJECT"])

        results = engine.evaluate(round_num=3, decisions=decisions)
        assert len(results) == 1

    def test_rule_fires_after_round_min(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.5, round_min=2, fire_once=False)])
        decisions = _make_decisions(["BUY", "BUY", "REJECT"])

        results = engine.evaluate(round_num=5, decisions=decisions)
        assert len(results) == 1


# --- Multiple rules evaluated at once ---

class TestMultipleRules:
    def test_multiple_rules_can_fire_simultaneously(self):
        consensus_rule = _consensus_rule(threshold=0.6)
        action_majority_rule = TriggerRule(
            id="test-majority",
            name="BUY Majority",
            condition=Condition(type="action_majority", params={"action": "BUY", "threshold": 0.5}),
            effect="notify",
            effect_params={"message": "BUY dominates"},
            fire_once=True,
            round_min=1,
        )
        engine = ConditionalEngine(rules=[consensus_rule, action_majority_rule])
        decisions = _make_decisions(["BUY", "BUY", "BUY", "REJECT"])  # 75% BUY

        results = engine.evaluate(round_num=1, decisions=decisions)
        assert len(results) == 2
        rule_ids = {r.rule_id for r in results}
        assert "test-consensus" in rule_ids
        assert "test-majority" in rule_ids

    def test_only_matching_rules_fire(self):
        consensus_rule = _consensus_rule(threshold=0.9)  # won't fire at 75%
        deadlock_rule = _deadlock_rule(max_share=0.8)  # fires when top <= 80%: 75% <= 80% -> True
        engine = ConditionalEngine(rules=[consensus_rule, deadlock_rule])
        decisions = _make_decisions(["BUY", "BUY", "BUY", "REJECT"])  # 75%

        results = engine.evaluate(round_num=1, decisions=decisions)
        rule_ids = {r.rule_id for r in results}
        assert "test-consensus" not in rule_ids
        assert "test-deadlock" in rule_ids

    def test_add_rule_appends_to_engine(self):
        engine = ConditionalEngine(rules=[])
        assert len(engine.rules) == 0

        engine.add_rule(_consensus_rule())
        assert len(engine.rules) == 1

        engine.add_rule(_deadlock_rule())
        assert len(engine.rules) == 2


# --- get_history() ---

class TestGetHistory:
    def test_get_history_returns_empty_initially(self):
        engine = ConditionalEngine(rules=[_consensus_rule()])
        assert engine.get_history() == []

    def test_get_history_returns_correct_serialized_data(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.5)])
        decisions = _make_decisions(["BUY", "BUY", "REJECT"])

        engine.evaluate(round_num=2, decisions=decisions)
        history = engine.get_history()

        assert len(history) == 1
        entry = history[0]
        assert entry["rule_id"] == "test-consensus"
        assert entry["rule_name"] == "Test Consensus"
        assert entry["round"] == 2
        assert entry["effect"] == "inject_event"
        assert entry["effect_params"] == {"event_type": "challenge"}
        assert "action" in entry["context"]

    def test_get_history_accumulates_across_rounds(self):
        rule = TriggerRule(
            id="repeatable",
            name="Repeatable",
            condition=Condition(type="consensus_reached", params={"threshold": 0.5}),
            effect="notify",
            effect_params={},
            fire_once=False,
            round_min=1,
        )
        engine = ConditionalEngine(rules=[rule])
        decisions = _make_decisions(["BUY", "BUY", "REJECT"])

        engine.evaluate(round_num=1, decisions=decisions)
        engine.evaluate(round_num=2, decisions=decisions)

        history = engine.get_history()
        assert len(history) == 2
        assert history[0]["round"] == 1
        assert history[1]["round"] == 2


# --- default_rules() ---

class TestDefaultRules:
    def test_default_rules_returns_non_empty(self):
        rules = default_rules()
        assert len(rules) > 0

    def test_default_rules_have_valid_structure(self):
        rules = default_rules()
        for rule in rules:
            assert isinstance(rule, TriggerRule)
            assert rule.id
            assert rule.name
            assert rule.condition.type in (
                "consensus_reached", "deadlock", "faction_split",
                "utility_drop", "action_majority", "swing_detected",
            )
            assert rule.effect

    def test_default_rules_are_independent_instances(self):
        rules_a = default_rules()
        rules_b = default_rules()
        # Mutating one set doesn't affect the other
        rules_a[0].fired = True
        assert rules_b[0].fired is False


# --- Edge cases ---

class TestEdgeCases:
    def test_empty_decisions_list(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.5)])
        results = engine.evaluate(round_num=1, decisions=[])

        assert len(results) == 0

    def test_no_faction_data_faction_split_uses_action_diversity(self):
        rule = TriggerRule(
            id="test-split",
            name="Faction Split",
            condition=Condition(type="faction_split", params={"min_factions": 3}),
            effect="notify",
            effect_params={},
            fire_once=True,
            round_min=1,
        )
        engine = ConditionalEngine(rules=[rule])
        # 3 distinct actions should trigger faction_split fallback
        decisions = _make_decisions(["BUY", "REJECT", "HOLD"])
        results = engine.evaluate(round_num=1, decisions=decisions, faction_data=None)

        assert len(results) == 1
        assert results[0].context["faction_count"] == 3

    def test_no_previous_decisions_utility_drop_does_not_fire(self):
        rule = TriggerRule(
            id="test-drop",
            name="Utility Drop",
            condition=Condition(type="utility_drop", params={"threshold": 0.1}),
            effect="notify",
            effect_params={},
            fire_once=True,
            round_min=1,
        )
        engine = ConditionalEngine(rules=[rule])
        decisions = _make_decisions(["BUY", "BUY"], utilities=[0.2, 0.3])
        results = engine.evaluate(round_num=1, decisions=decisions, prev_decisions=None)

        assert len(results) == 0

    def test_no_previous_decisions_swing_detected_does_not_fire(self):
        rule = TriggerRule(
            id="test-swing",
            name="Swing",
            condition=Condition(type="swing_detected", params={"min_swings": 1}),
            effect="notify",
            effect_params={},
            fire_once=True,
            round_min=1,
        )
        engine = ConditionalEngine(rules=[rule])
        decisions = _make_decisions(["BUY", "REJECT"])
        results = engine.evaluate(round_num=1, decisions=decisions, prev_decisions=None)

        assert len(results) == 0

    def test_decisions_with_error_entries_are_excluded(self):
        engine = ConditionalEngine(rules=[_consensus_rule(threshold=0.7)])
        decisions = [
            {"id": "a0", "action": "BUY", "utility": 0.5},
            {"id": "a1", "action": "BUY", "utility": 0.6},
            {"id": "a2", "action": "BUY", "utility": 0.4},
            {"id": "a3", "error": "LLM timeout"},  # excluded from tally
        ]
        # 3 BUY out of 4 total = 75% >= 70% threshold
        results = engine.evaluate(round_num=1, decisions=decisions)
        assert len(results) == 1

    def test_unknown_condition_type_does_not_fire(self):
        rule = TriggerRule(
            id="test-unknown",
            name="Unknown",
            condition=Condition(type="nonexistent_evaluator", params={}),
            effect="notify",
            effect_params={},
            fire_once=True,
            round_min=1,
        )
        engine = ConditionalEngine(rules=[rule])
        decisions = _make_decisions(["BUY", "BUY", "BUY"])
        results = engine.evaluate(round_num=1, decisions=decisions)

        assert len(results) == 0

    def test_utility_drop_fires_with_significant_drop(self):
        rule = TriggerRule(
            id="test-drop",
            name="Utility Drop",
            condition=Condition(type="utility_drop", params={"threshold": 0.2}),
            effect="inject_event",
            effect_params={"event_type": "morale_boost"},
            fire_once=True,
            round_min=1,
        )
        engine = ConditionalEngine(rules=[rule])
        prev = _make_decisions(["BUY", "BUY"], utilities=[0.8, 0.8])
        curr = _make_decisions(["BUY", "BUY"], utilities=[0.4, 0.4])

        results = engine.evaluate(round_num=2, decisions=curr, prev_decisions=prev)
        assert len(results) == 1
        assert results[0].context["drop_pct"] == 0.5  # (0.8-0.4)/0.8 = 0.5

    def test_swing_detected_fires_when_agents_change_action(self):
        rule = TriggerRule(
            id="test-swing",
            name="Swing",
            condition=Condition(type="swing_detected", params={"min_swings": 2}),
            effect="notify",
            effect_params={},
            fire_once=True,
            round_min=1,
        )
        engine = ConditionalEngine(rules=[rule])
        prev = [
            {"id": "agent-0", "action": "BUY", "utility": 0.5},
            {"id": "agent-1", "action": "BUY", "utility": 0.5},
            {"id": "agent-2", "action": "REJECT", "utility": 0.3},
        ]
        curr = [
            {"id": "agent-0", "action": "REJECT", "utility": 0.3},  # swung
            {"id": "agent-1", "action": "REJECT", "utility": 0.3},  # swung
            {"id": "agent-2", "action": "REJECT", "utility": 0.3},  # stayed
        ]
        results = engine.evaluate(round_num=2, decisions=curr, prev_decisions=prev)
        assert len(results) == 1
        assert results[0].context["swing_count"] == 2
