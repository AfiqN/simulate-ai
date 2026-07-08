from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from src.agent.agent import Agent

if TYPE_CHECKING:
    from src.agent.factions import FactionTracker


def compute_adversary_map(decisions: list[dict[str, Any]], agents: list[Agent]) -> dict[str, Optional[dict[str, Any]]]:
    adversary_map: dict[str, Optional[dict[str, Any]]] = {}
    for i, dec_a in enumerate(decisions):
        u_a = dec_a.get("utility", 0.0)
        action_a = dec_a.get("action", "")

        cross_faction = [
            (j, d) for j, d in enumerate(decisions)
            if j != i and d.get("action", "") != action_a
        ]
        candidates = cross_faction if cross_faction else [
            (j, d) for j, d in enumerate(decisions) if j != i
        ]

        if not candidates:
            adversary_map[dec_a["id"]] = None
            continue

        max_delta = max(abs(u_a - d.get("utility", 0.0)) for _, d in candidates)
        tied = [(j, d) for j, d in candidates if abs(u_a - d.get("utility", 0.0)) == max_delta]
        if len(tied) > 1:
            _, chosen = max(tied, key=lambda x: agents[x[0]].profile.attributes.aggressiveness)
        else:
            _, chosen = tied[0]
        adversary_map[dec_a["id"]] = chosen

    _rebalance_incoming(adversary_map, decisions)
    return adversary_map


def evolve_adversary_map(
    prev_map: dict[str, Optional[dict[str, Any]]],
    prev_decisions: list[dict[str, Any]],
    curr_decisions: list[dict[str, Any]],
    agents: list[Agent],
) -> dict[str, Optional[dict[str, Any]]]:
    """Re-compute adversary pairings after a new round.

    Agents who flipped actions get re-paired based on new positions.
    Agents whose position held keep their existing adversary UNLESS their
    adversary flipped to the same faction (in which case they also get re-paired).
    """
    prev_by_id = {d["id"]: d for d in prev_decisions}
    curr_by_id = {d["id"]: d for d in curr_decisions}

    # Identify who flipped and who stayed
    flipped_ids: set[str] = set()
    for d in curr_decisions:
        aid = d["id"]
        prev = prev_by_id.get(aid)
        if prev and prev.get("action") != d.get("action"):
            flipped_ids.add(aid)

    # Start from fresh computation on current decisions
    new_map = compute_adversary_map(curr_decisions, agents)

    # For stable agents whose adversary didn't flip and is still cross-faction,
    # preserve the prior pairing for narrative continuity
    for aid, old_target in prev_map.items():
        if aid in flipped_ids:
            continue  # re-paired already
        if old_target is None:
            continue
        old_target_id = old_target["id"]
        if old_target_id in flipped_ids:
            continue  # adversary flipped, need new pairing

        # Check if old adversary is still cross-faction
        curr_agent = curr_by_id.get(aid)
        curr_target = curr_by_id.get(old_target_id)
        if curr_agent and curr_target and curr_agent.get("action") != curr_target.get("action"):
            new_map[aid] = curr_target  # preserve continuity

    _rebalance_incoming(new_map, curr_decisions)
    return new_map


def _rebalance_incoming(
    adversary_map: dict[str, Optional[dict[str, Any]]],
    decisions: list[dict[str, Any]],
) -> None:
    by_id = {d["id"]: d for d in decisions}

    def incoming_counts() -> dict[str, int]:
        counts = {d["id"]: 0 for d in decisions}
        for target in adversary_map.values():
            if target is not None:
                counts[target["id"]] = counts.get(target["id"], 0) + 1
        return counts

    counts = incoming_counts()
    zero_targets = [d for d in decisions if counts[d["id"]] == 0]

    for orphan in zero_targets:
        orphan_id = orphan["id"]
        orphan_action = orphan.get("action", "")

        oversubscribed = sorted(
            (cid for cid, n in counts.items() if n >= 2 and cid != orphan_id),
            key=lambda cid: -counts[cid],
        )

        redirected = False
        for over_id in oversubscribed:
            for challenger_id, target in adversary_map.items():
                if target is None or target["id"] != over_id or challenger_id == orphan_id:
                    continue
                challenger_action = by_id[challenger_id].get("action", "")
                if challenger_action == orphan_action:
                    continue
                adversary_map[challenger_id] = orphan
                counts[over_id] -= 1
                counts[orphan_id] = counts.get(orphan_id, 0) + 1
                redirected = True
                break
            if redirected:
                break


def evolve_adversary_map_v2(
    prev_map: dict[str, Optional[dict[str, Any]]],
    prev_decisions: list[dict[str, Any]],
    curr_decisions: list[dict[str, Any]],
    agents: list[Agent],
    faction_tracker: "FactionTracker",
) -> dict[str, Optional[dict[str, Any]]]:
    """Enhanced adversary re-pairing using faction intelligence.

    Improvements over v1:
    - Swing agents get paired with the minority's strongest voice
    - Majority's weakest member gets the most aggressive minority challenger
    - Echo chamber breaker: agents paired same-faction for 2+ rounds get forced cross-faction
    """
    curr_by_id = {d["id"]: d for d in curr_decisions}
    latest = faction_tracker.get_latest()
    if not latest:
        # Fallback to basic evolution if no faction data
        return evolve_adversary_map(prev_map, prev_decisions, curr_decisions, agents)

    swing_ids = faction_tracker.get_swing_agents()
    majority = latest.majority_faction
    minority_factions = latest.minority_factions

    # Build agent lookup
    agent_by_id = {a.profile.agent_id: a for a in agents}

    # Start with basic v1 map as foundation
    new_map = evolve_adversary_map(prev_map, prev_decisions, curr_decisions, agents)

    if not majority or not minority_factions:
        return new_map  # homogeneous swarm, nothing to enhance

    # Collect minority strongest voices (sorted by abs utility descending)
    minority_members: list[dict[str, Any]] = []
    for mf in minority_factions:
        for mid in mf.member_ids:
            if mid in curr_by_id:
                minority_members.append(curr_by_id[mid])
    minority_members.sort(key=lambda d: abs(d.get("utility", 0.0)), reverse=True)

    if not minority_members:
        return new_map

    # --- Strategy 1: Swing agents get minority's strongest voice ---
    minority_strongest = minority_members[0] if minority_members else None
    for sid in swing_ids:
        if sid not in curr_by_id:
            continue
        agent_action = curr_by_id[sid].get("action", "")
        # Only re-pair if the swing agent is in the majority (interesting tension)
        if agent_action == majority.action and minority_strongest:
            if minority_strongest["id"] != sid:  # don't self-pair
                new_map[sid] = minority_strongest

    # --- Strategy 2: Majority's weakest member gets most aggressive minority challenger ---
    majority_members = [curr_by_id[mid] for mid in majority.member_ids if mid in curr_by_id]
    if majority_members:
        weakest = min(majority_members, key=lambda d: abs(d.get("utility", 0.0)))
        # Find most aggressive minority agent
        most_aggressive = None
        best_aggro = -1.0
        for mm in minority_members:
            a = agent_by_id.get(mm["id"])
            if a and a.profile.attributes.aggressiveness > best_aggro:
                best_aggro = a.profile.attributes.aggressiveness
                most_aggressive = mm
        if most_aggressive and most_aggressive["id"] != weakest["id"]:
            new_map[weakest["id"]] = most_aggressive

    # --- Strategy 3: Echo chamber breaker ---
    # If an agent has had the same adversary for 2+ rounds AND that adversary
    # is now same-faction, force a cross-faction pairing
    if len(faction_tracker.history) >= 2:
        for aid, target in list(new_map.items()):
            if target is None:
                continue
            # Check if same pairing existed in previous map
            prev_target = prev_map.get(aid)
            if prev_target and prev_target["id"] == target["id"]:
                # Same pairing for 2 rounds — check if same faction
                agent_action = curr_by_id.get(aid, {}).get("action", "")
                target_action = target.get("action", "")
                if agent_action == target_action:
                    # Echo chamber! Find a cross-faction alternative
                    cross = [m for m in minority_members if m["id"] != aid]
                    if not cross:
                        cross = [m for m in majority_members if m["id"] != aid and m.get("action") != agent_action]
                    if cross:
                        new_map[aid] = cross[0]

    _rebalance_incoming(new_map, curr_decisions)
    return new_map


def compute_panel_challenges(
    faction_tracker: "FactionTracker",
    decisions: list[dict[str, Any]],
    agents: list[Agent],
    max_challengers: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """Compute panel debate assignments for deep mode.

    Majority faction members each get 2-3 minority challengers.
    Minority's strongest voices are distributed across majority targets.

    Returns:
        dict mapping agent_id to a list of adversary decision dicts.
    """
    latest = faction_tracker.get_latest()
    if not latest:
        return {}

    majority = latest.majority_faction
    minority_factions = latest.minority_factions
    if not majority or not minority_factions:
        return {}

    curr_by_id = {d["id"]: d for d in decisions}
    agent_by_id = {a.profile.agent_id: a for a in agents}

    # Collect all minority members sorted by influence (abs utility × aggressiveness)
    minority_pool: list[dict[str, Any]] = []
    for mf in minority_factions:
        for mid in mf.member_ids:
            if mid in curr_by_id:
                minority_pool.append(curr_by_id[mid])

    def _challenge_strength(d: dict) -> float:
        a = agent_by_id.get(d["id"])
        aggro = a.profile.attributes.aggressiveness if a else 0.5
        return abs(d.get("utility", 0.0)) * (0.5 + aggro)

    minority_pool.sort(key=_challenge_strength, reverse=True)

    if not minority_pool:
        return {}

    # Rank majority members by vulnerability (low stability + low utility = more vulnerable)
    swing_ids = faction_tracker.get_swing_agents()
    majority_targets = []
    for mid in majority.member_ids:
        if mid in curr_by_id:
            stability = faction_tracker.get_faction_stability(mid)
            is_swing = mid in swing_ids
            vuln_score = (1.0 - stability) + (0.3 if is_swing else 0.0)
            majority_targets.append((mid, vuln_score))
    majority_targets.sort(key=lambda x: -x[1])  # most vulnerable first

    # Assign challengers: distribute minority pool across majority targets
    panel_map: dict[str, list[dict[str, Any]]] = {}
    challenger_idx = 0

    for target_id, _ in majority_targets:
        challengers = []
        for _ in range(min(max_challengers, len(minority_pool))):
            if challenger_idx >= len(minority_pool):
                challenger_idx = 0  # wrap around — minority voices can challenge multiple targets
            challenger = minority_pool[challenger_idx]
            if challenger["id"] != target_id:  # don't self-challenge
                challengers.append(challenger)
            challenger_idx += 1
        if challengers:
            panel_map[target_id] = challengers

    # Minority members get 1 majority challenger each (strongest majority voice)
    majority_pool = [curr_by_id[mid] for mid in majority.member_ids if mid in curr_by_id]
    majority_pool.sort(key=_challenge_strength, reverse=True)

    for mp in minority_pool:
        if mp["id"] not in panel_map:
            # Give minority agent the strongest majority challenger
            challengers = [m for m in majority_pool[:2] if m["id"] != mp["id"]]
            if challengers:
                panel_map[mp["id"]] = challengers

    return panel_map
