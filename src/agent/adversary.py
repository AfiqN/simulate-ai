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
