"""Faction tracking for multi-round adversary evolution.

Tracks coalition membership, stability, defections, and swing agents
across simulation rounds. Pure computation — no LLM calls.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FactionInfo:
    """A group of agents who chose the same action in a given round."""

    action: str
    member_ids: list[str]
    size: int
    cohesion: float  # fraction of members who held this action from previous round
    strongest_voice_id: str  # member with highest absolute utility
    mean_utility: float

    @property
    def is_majority(self) -> bool:
        return self._is_majority

    @is_majority.setter
    def is_majority(self, val: bool) -> None:
        self._is_majority = val


@dataclass
class RoundFactions:
    """Snapshot of all factions after one round."""

    round_num: int
    factions: dict[str, FactionInfo]  # action -> FactionInfo
    defections: list[dict[str, str]]  # [{agent_id, from_action, to_action}]
    swing_agent_ids: set[str]  # cumulative: agents who have flipped at least once
    total_agents: int

    @property
    def majority_faction(self) -> Optional[FactionInfo]:
        if not self.factions:
            return None
        return max(self.factions.values(), key=lambda f: f.size)

    @property
    def minority_factions(self) -> list[FactionInfo]:
        majority = self.majority_faction
        if not majority:
            return []
        return [f for f in self.factions.values() if f.action != majority.action]


@dataclass
class FactionTracker:
    """Runtime tracker for coalition dynamics across rounds."""

    history: list[RoundFactions] = field(default_factory=list)
    _all_swing_ids: set[str] = field(default_factory=set)
    _agent_action_history: dict[str, list[str]] = field(default_factory=dict)

    def record_round(self, round_num: int, decisions: list[dict[str, Any]]) -> RoundFactions:
        """Process a round's decisions and record faction state.

        Args:
            round_num: 1-based round number.
            decisions: List of decision dicts with at minimum 'id', 'action', 'utility'.

        Returns:
            The computed RoundFactions snapshot.
        """
        valid = [d for d in decisions if not d.get("error") and d.get("action")]

        # Group by action
        groups: dict[str, list[dict]] = {}
        for d in valid:
            groups.setdefault(d["action"], []).append(d)

        # Get previous round's agent->action mapping
        prev_action_map: dict[str, str] = {}
        if self.history:
            prev = self.history[-1]
            for faction in prev.factions.values():
                for mid in faction.member_ids:
                    prev_action_map[mid] = faction.action

        # Detect defections
        defections: list[dict[str, str]] = []
        for d in valid:
            aid = d["id"]
            prev_action = prev_action_map.get(aid)
            curr_action = d["action"]
            # Track action history
            self._agent_action_history.setdefault(aid, []).append(curr_action)
            if prev_action and prev_action != curr_action:
                defections.append({
                    "agent_id": aid,
                    "from_action": prev_action,
                    "to_action": curr_action,
                })
                self._all_swing_ids.add(aid)

        # Build FactionInfo per action
        factions: dict[str, FactionInfo] = {}
        for action, members in groups.items():
            member_ids = [m["id"] for m in members]
            # Cohesion: fraction of members who were in this same faction last round
            if prev_action_map:
                held = sum(1 for mid in member_ids if prev_action_map.get(mid) == action)
                cohesion = held / len(member_ids) if member_ids else 0.0
            else:
                cohesion = 1.0  # first round: everyone is "stable"

            # Strongest voice: highest absolute utility
            strongest = max(members, key=lambda m: abs(m.get("utility", 0.0)))
            mean_u = sum(m.get("utility", 0.0) for m in members) / len(members)

            factions[action] = FactionInfo(
                action=action,
                member_ids=member_ids,
                size=len(member_ids),
                cohesion=round(cohesion, 3),
                strongest_voice_id=strongest["id"],
                mean_utility=round(mean_u, 4),
            )

        # Mark majority
        if factions:
            max_size = max(f.size for f in factions.values())
            for f in factions.values():
                f.is_majority = (f.size == max_size)

        snapshot = RoundFactions(
            round_num=round_num,
            factions=factions,
            defections=defections,
            swing_agent_ids=set(self._all_swing_ids),
            total_agents=len(valid),
        )
        self.history.append(snapshot)
        return snapshot

    def get_swing_agents(self) -> set[str]:
        """Return IDs of agents who have flipped action at least once."""
        return set(self._all_swing_ids)

    def get_faction_stability(self, agent_id: str) -> float:
        """Return stability score for an agent (fraction of rounds they held position).

        1.0 = never flipped, 0.0 = flipped every round.
        """
        actions = self._agent_action_history.get(agent_id, [])
        if len(actions) <= 1:
            return 1.0
        holds = sum(1 for i in range(1, len(actions)) if actions[i] == actions[i - 1])
        return round(holds / (len(actions) - 1), 3)

    def get_latest(self) -> Optional[RoundFactions]:
        """Return the most recent round's factions, or None if no rounds recorded."""
        return self.history[-1] if self.history else None

    def build_agent_context(self, agent_id: str, decisions: list[dict[str, Any]]) -> str:
        """Build a faction dynamics summary string for injection into agent prompts.

        Args:
            agent_id: The agent receiving this context.
            decisions: Current round's decisions (to find agent's action).

        Returns:
            Formatted string for prompt injection.
        """
        latest = self.get_latest()
        if not latest:
            return ""

        # Find this agent's faction
        agent_action = None
        for faction in latest.factions.values():
            if agent_id in faction.member_ids:
                agent_action = faction.action
                break

        if not agent_action:
            return ""

        my_faction = latest.factions[agent_action]
        majority = latest.majority_faction
        total = latest.total_agents

        lines = ["--- FACTION DYNAMICS ---"]

        # Agent's faction status
        status = "MAJORITY" if my_faction.is_majority else "MINORITY"
        lines.append(
            f"Your faction ({agent_action}): {my_faction.size}/{total} agents. "
            f"You are in the {status}."
        )

        # Other factions
        others = [f for f in latest.factions.values() if f.action != agent_action]
        if others:
            other_parts = [f"{f.action}: {f.size}/{total}" for f in sorted(others, key=lambda x: -x.size)]
            lines.append(f"Opposing: {', '.join(other_parts)}.")

        # Cohesion
        lines.append(
            f"Your faction cohesion: {int(my_faction.cohesion * 100)}% "
            f"({int(my_faction.cohesion * my_faction.size)}/{my_faction.size} held from previous round)."
        )

        # Swing agents
        swing = latest.swing_agent_ids
        if swing:
            # Find archetype names for swing agents from decisions
            swing_names = []
            for d in decisions:
                if d["id"] in swing:
                    swing_names.append(d.get("archetype", d["id"]))
            if swing_names:
                lines.append(f"Swing agents: {', '.join(swing_names[:4])}")

        return "\n".join(lines)

    def compute_metrics(self) -> dict[str, Any]:
        """Compute faction metrics for the final report output."""
        if not self.history:
            return {}

        faction_history = []
        for snapshot in self.history:
            faction_sizes = {action: fi.size for action, fi in snapshot.factions.items()}
            faction_history.append({
                "round": snapshot.round_num,
                "factions": faction_sizes,
            })

        # All alliance events (defections across all rounds)
        alliance_events = []
        for snapshot in self.history:
            for defection in snapshot.defections:
                alliance_events.append({
                    "round": snapshot.round_num,
                    "type": "defection",
                    "agent": defection["agent_id"],
                    "from": defection["from_action"],
                    "to": defection["to_action"],
                })

        # Majority stability: how often the same action held majority across rounds
        majority_actions = [s.majority_faction.action for s in self.history if s.majority_faction]
        if len(majority_actions) > 1:
            holds = sum(
                1 for i in range(1, len(majority_actions))
                if majority_actions[i] == majority_actions[i - 1]
            )
            majority_stability = round(holds / (len(majority_actions) - 1), 3)
        else:
            majority_stability = 1.0

        # Faction count trajectory
        faction_count_trajectory = [len(s.factions) for s in self.history]

        # Swing agent archetypes (we store IDs; pipeline should map to archetypes)
        swing_agents = sorted(self._all_swing_ids)

        return {
            "faction_history": faction_history,
            "swing_agents": swing_agents,
            "alliance_events": alliance_events,
            "majority_stability": majority_stability,
            "faction_count_trajectory": faction_count_trajectory,
        }
