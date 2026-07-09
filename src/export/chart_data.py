"""Generate chart-ready data structures from a simulation result."""

from typing import Any


def generate_chart_data(result: dict[str, Any]) -> dict[str, Any]:
    """Transform raw simulation result into frontend-chart-friendly shapes.

    Returns:
        Dict with keys: utility_trajectories, faction_pie, state_sankey, dimension_heatmap
    """
    profiles = result.get("profiles", [])
    rounds_data = {
        "r1": result.get("decisions_r1", []),
        "r2": result.get("decisions_r2", []),
        "r3": result.get("decisions_r3", []),
    }
    # Include r4 if present (deep mode)
    if "decisions_r4" in result:
        rounds_data["r4"] = result["decisions_r4"]

    return {
        "utility_trajectories": _utility_trajectories(rounds_data, profiles),
        "faction_pie": _faction_pie(rounds_data),
        "state_sankey": _state_sankey(rounds_data),
        "dimension_heatmap": _dimension_heatmap(rounds_data, profiles),
    }


def _utility_trajectories(
    rounds: dict[str, list[dict]], profiles: list
) -> list[dict[str, Any]]:
    """Per-agent utility score across rounds.

    Shape: [{agent_id, archetype, values: [{round, utility}]}]
    """
    agent_map: dict[str, dict] = {}
    for p in profiles:
        agent_map[p.agent_id] = {
            "agent_id": p.agent_id,
            "archetype": p.archetype,
            "is_custom": getattr(p, "is_custom", False),
            "values": [],
        }

    for round_key in sorted(rounds.keys()):
        round_num = int(round_key[1:])  # "r1" -> 1
        for d in rounds[round_key]:
            aid = d.get("id", "")
            if aid in agent_map:
                agent_map[aid]["values"].append({
                    "round": round_num,
                    "utility": d.get("utility", 0),
                    "action": d.get("action", ""),
                })

    return list(agent_map.values())


def _faction_pie(rounds: dict[str, list[dict]]) -> dict[str, dict[str, int]]:
    """Per-round action distribution (vote tally).

    Shape: {r1: {ACTION_A: 3, ACTION_B: 2}, r2: ...}
    """
    result = {}
    for round_key in sorted(rounds.keys()):
        tally: dict[str, int] = {}
        for d in rounds[round_key]:
            action = d.get("action", "UNKNOWN")
            tally[action] = tally.get(action, 0) + 1
        result[round_key] = tally
    return result


def _state_sankey(rounds: dict[str, list[dict]]) -> list[dict[str, Any]]:
    """State transitions between rounds as Sankey flows.

    Shape: [{from_round, to_round, from_state, to_state, count}]
    """
    # Build agent_id -> state per round
    states_by_round: dict[str, dict[str, str]] = {}
    for round_key in sorted(rounds.keys()):
        states_by_round[round_key] = {}
        for d in rounds[round_key]:
            states_by_round[round_key][d.get("id", "")] = d.get("new_state", "Unknown")

    flows: list[dict[str, Any]] = []
    sorted_keys = sorted(states_by_round.keys())
    for i in range(len(sorted_keys) - 1):
        from_key = sorted_keys[i]
        to_key = sorted_keys[i + 1]
        from_states = states_by_round[from_key]
        to_states = states_by_round[to_key]

        transition_counts: dict[tuple[str, str], int] = {}
        for agent_id, from_state in from_states.items():
            to_state = to_states.get(agent_id, from_state)
            key = (from_state, to_state)
            transition_counts[key] = transition_counts.get(key, 0) + 1

        for (from_state, to_state), count in transition_counts.items():
            flows.append({
                "from_round": from_key,
                "to_round": to_key,
                "from_state": from_state,
                "to_state": to_state,
                "count": count,
            })

    return flows


def _dimension_heatmap(
    rounds: dict[str, list[dict]], profiles: list
) -> dict[str, list[dict[str, Any]]]:
    """Agent × dimension score matrix per round.

    Shape: {r1: [{agent_id, archetype, dimensions: {dim: score}}], ...}
    """
    result = {}
    for round_key in sorted(rounds.keys()):
        entries = []
        for d in rounds[round_key]:
            entries.append({
                "agent_id": d.get("id", ""),
                "archetype": d.get("archetype", ""),
                "dimensions": d.get("utility_dimensions", {}),
            })
        result[round_key] = entries
    return result
