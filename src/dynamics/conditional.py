"""Conditional Dynamics Engine — evaluate mid-simulation triggers between rounds.

This module provides a rule-based system for injecting dynamic events into the
simulation based on emergent conditions (consensus thresholds, faction splits,
utility drift, etc.). Rules can be user-defined or auto-generated from the schema.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from collections import Counter


@dataclass
class Condition:
    """A single evaluable condition."""
    type: str  # consensus_reached, faction_split, utility_drop, action_majority, deadlock, custom
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class TriggerRule:
    """A conditional trigger: when condition is met, fire the effect."""
    id: str
    name: str
    condition: Condition
    effect: str  # inject_event, modify_agents, add_round, escalate_crisis, notify
    effect_params: dict[str, Any] = field(default_factory=dict)
    fire_once: bool = True  # Only trigger once per simulation
    fired: bool = False
    round_min: int = 1  # Earliest round to evaluate


@dataclass
class TriggerResult:
    """Result of evaluating a trigger."""
    rule_id: str
    rule_name: str
    fired: bool
    effect: str
    effect_params: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)
    round_num: int = 0


class ConditionalEngine:
    """Evaluates trigger rules against simulation state between rounds."""

    def __init__(self, rules: Optional[list[TriggerRule]] = None):
        self.rules: list[TriggerRule] = rules or []
        self.history: list[TriggerResult] = []

    def add_rule(self, rule: TriggerRule) -> None:
        self.rules.append(rule)

    def evaluate(
        self,
        round_num: int,
        decisions: list[dict],
        prev_decisions: Optional[list[dict]] = None,
        faction_data: Optional[dict] = None,
    ) -> list[TriggerResult]:
        """Evaluate all rules against current simulation state.

        Args:
            round_num: The round just completed.
            decisions: Decisions from the current round.
            prev_decisions: Decisions from the previous round (for drift detection).
            faction_data: Current faction state (if tracked).

        Returns:
            List of TriggerResults for rules that fired.
        """
        results: list[TriggerResult] = []

        for rule in self.rules:
            if rule.fired and rule.fire_once:
                continue
            if round_num < rule.round_min:
                continue

            fired, context = self._check_condition(
                rule.condition, round_num, decisions, prev_decisions, faction_data
            )
            if fired:
                rule.fired = True
                tr = TriggerResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    fired=True,
                    effect=rule.effect,
                    effect_params=rule.effect_params,
                    context=context,
                    round_num=round_num,
                )
                results.append(tr)
                self.history.append(tr)

        return results

    def _check_condition(
        self,
        condition: Condition,
        round_num: int,
        decisions: list[dict],
        prev_decisions: Optional[list[dict]],
        faction_data: Optional[dict],
    ) -> tuple[bool, dict[str, Any]]:
        """Evaluate a single condition. Returns (fired, context)."""
        evaluator = _CONDITION_EVALUATORS.get(condition.type)
        if not evaluator:
            return False, {}
        return evaluator(condition.params, round_num, decisions, prev_decisions, faction_data)

    def get_history(self) -> list[dict[str, Any]]:
        """Serializable history of all triggers that fired."""
        return [
            {
                "rule_id": tr.rule_id,
                "rule_name": tr.rule_name,
                "round": tr.round_num,
                "effect": tr.effect,
                "effect_params": tr.effect_params,
                "context": tr.context,
            }
            for tr in self.history
        ]


# --- Condition Evaluators ---

def _eval_consensus_reached(
    params: dict, round_num: int, decisions: list[dict],
    prev: Optional[list[dict]], factions: Optional[dict],
) -> tuple[bool, dict]:
    """Fire when a single action has >= threshold% of votes."""
    threshold = params.get("threshold", 0.7)
    total = len(decisions)
    if total == 0:
        return False, {}
    tally = Counter(d.get("action", "") for d in decisions if "error" not in d)
    if not tally:
        return False, {}
    top_action, top_count = tally.most_common(1)[0]
    ratio = top_count / total
    if ratio >= threshold:
        return True, {"action": top_action, "ratio": round(ratio, 3), "round": round_num}
    return False, {}


def _eval_deadlock(
    params: dict, round_num: int, decisions: list[dict],
    prev: Optional[list[dict]], factions: Optional[dict],
) -> tuple[bool, dict]:
    """Fire when no action has > threshold% — the group is stuck."""
    threshold = params.get("max_share", 0.4)
    total = len(decisions)
    if total == 0:
        return False, {}
    tally = Counter(d.get("action", "") for d in decisions if "error" not in d)
    if not tally:
        return False, {}
    _, top_count = tally.most_common(1)[0]
    if top_count / total <= threshold:
        return True, {"distribution": dict(tally), "round": round_num}
    return False, {}


def _eval_faction_split(
    params: dict, round_num: int, decisions: list[dict],
    prev: Optional[list[dict]], factions: Optional[dict],
) -> tuple[bool, dict]:
    """Fire when factions split into >= N distinct groups."""
    min_factions = params.get("min_factions", 3)
    if not factions:
        # Fall back to action diversity
        tally = Counter(d.get("action", "") for d in decisions if "error" not in d)
        if len(tally) >= min_factions:
            return True, {"faction_count": len(tally), "round": round_num}
        return False, {}
    faction_count = len(factions)
    if faction_count >= min_factions:
        return True, {"faction_count": faction_count, "round": round_num}
    return False, {}


def _eval_utility_drop(
    params: dict, round_num: int, decisions: list[dict],
    prev: Optional[list[dict]], factions: Optional[dict],
) -> tuple[bool, dict]:
    """Fire when mean utility drops by >= threshold between rounds."""
    threshold = params.get("threshold", 0.15)
    if not prev:
        return False, {}

    def _mean_utility(decs: list[dict]) -> float:
        utils = [d.get("utility", 0) for d in decs if "error" not in d]
        return sum(utils) / max(len(utils), 1)

    prev_mean = _mean_utility(prev)
    curr_mean = _mean_utility(decisions)
    if prev_mean == 0:
        return False, {}
    drop = (prev_mean - curr_mean) / abs(prev_mean)
    if drop >= threshold:
        return True, {"prev_mean": round(prev_mean, 3), "curr_mean": round(curr_mean, 3), "drop_pct": round(drop, 3)}
    return False, {}


def _eval_action_majority(
    params: dict, round_num: int, decisions: list[dict],
    prev: Optional[list[dict]], factions: Optional[dict],
) -> tuple[bool, dict]:
    """Fire when a specific named action reaches a vote threshold."""
    target_action = params.get("action", "")
    threshold = params.get("threshold", 0.5)
    total = len(decisions)
    if total == 0:
        return False, {}
    count = sum(1 for d in decisions if d.get("action") == target_action)
    ratio = count / total
    if ratio >= threshold:
        return True, {"action": target_action, "count": count, "total": total, "ratio": round(ratio, 3)}
    return False, {}


def _eval_swing_detected(
    params: dict, round_num: int, decisions: list[dict],
    prev: Optional[list[dict]], factions: Optional[dict],
) -> tuple[bool, dict]:
    """Fire when >= N agents switched their action from the previous round."""
    min_swings = params.get("min_swings", 3)
    if not prev:
        return False, {}
    prev_map = {d.get("id"): d.get("action") for d in prev}
    swings = []
    for d in decisions:
        agent_id = d.get("id", "")
        if agent_id in prev_map and prev_map[agent_id] != d.get("action"):
            swings.append({"agent_id": agent_id, "from": prev_map[agent_id], "to": d.get("action")})
    if len(swings) >= min_swings:
        return True, {"swing_count": len(swings), "swings": swings[:5]}
    return False, {}


# Registry of condition evaluators
_CONDITION_EVALUATORS: dict[str, Callable] = {
    "consensus_reached": _eval_consensus_reached,
    "deadlock": _eval_deadlock,
    "faction_split": _eval_faction_split,
    "utility_drop": _eval_utility_drop,
    "action_majority": _eval_action_majority,
    "swing_detected": _eval_swing_detected,
}


# --- Default rule sets ---

def default_rules() -> list[TriggerRule]:
    """Standard trigger rules applied to every simulation."""
    return [
        TriggerRule(
            id="auto-consensus-early",
            name="Early Consensus",
            condition=Condition(
                type="consensus_reached",
                params={"threshold": 0.8},
                description="80%+ agents converge on a single action before crisis",
            ),
            effect="inject_event",
            effect_params={"event_type": "consensus_challenge", "prompt_hint": "Challenge the emerging groupthink — inject a contrarian scenario"},
            fire_once=True,
            round_min=1,
        ),
        TriggerRule(
            id="auto-deadlock",
            name="Deadlock Detected",
            condition=Condition(
                type="deadlock",
                params={"max_share": 0.35},
                description="No action commands more than 35% — system is stuck",
            ),
            effect="inject_event",
            effect_params={"event_type": "tie_breaker", "prompt_hint": "Introduce a forcing function that demands resolution"},
            fire_once=True,
            round_min=2,
        ),
        TriggerRule(
            id="auto-utility-crash",
            name="Utility Crash",
            condition=Condition(
                type="utility_drop",
                params={"threshold": 0.25},
                description="Mean utility dropped 25%+ between rounds — morale collapse",
            ),
            effect="inject_event",
            effect_params={"event_type": "morale_boost", "prompt_hint": "Inject a positive signal to test if agents recover"},
            fire_once=True,
            round_min=2,
        ),
        TriggerRule(
            id="auto-mass-swing",
            name="Mass Swing",
            condition=Condition(
                type="swing_detected",
                params={"min_swings": 3},
                description="3+ agents changed their stance between rounds",
            ),
            effect="notify",
            effect_params={"message": "Significant position shifts detected — coalition dynamics may have changed."},
            fire_once=False,
            round_min=2,
        ),
    ]
