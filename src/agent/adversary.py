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
    return adversary_map
