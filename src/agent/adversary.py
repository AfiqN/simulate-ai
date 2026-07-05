from typing import Any, Optional

from src.agent.agent import Agent


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
