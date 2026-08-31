"""Sensitivity analysis — measure outcome stability under parameter perturbation.

Rather than re-running the full LLM pipeline (expensive), this module performs
analytical sensitivity analysis on the existing decision data:

1. Flip Margin: How much utility shift would flip each agent's action?
2. Dimension Leverage: Which evaluation dimensions most strongly predict the final action?
3. Coalition Fragility: How many agents would need to flip to change the majority verdict?
4. Influence Sensitivity: How outcome changes if high-influence agents are removed.
"""

from typing import Any, Optional
from collections import Counter


def compute_sensitivity_analysis(
    decisions_r1: list[dict[str, Any]],
    decisions_r2: list[dict[str, Any]],
    decisions_r3: list[dict[str, Any]],
    profiles: Optional[list] = None,
) -> dict[str, Any]:
    """Compute full sensitivity report from round decisions.

    Returns:
        flip_margins: per-agent distance to decision boundary
        dimension_leverage: which dimensions correlate most with action choice
        coalition_fragility: votes needed to flip majority
        influence_sensitivity: outcome change if top influencer removed
    """
    # Use the latest decisive round
    final_decisions = decisions_r3 if decisions_r3 else decisions_r2 if decisions_r2 else decisions_r1

    return {
        "flip_margins": _flip_margins(final_decisions),
        "dimension_leverage": _dimension_leverage(final_decisions),
        "coalition_fragility": _coalition_fragility(final_decisions),
        "influence_sensitivity": _influence_sensitivity(final_decisions, profiles),
    }


def _flip_margins(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For each agent, compute how far their utility is from zero (decision boundary).

    Agents near zero utility are "on the edge" — small perturbations could flip them.
    Returns sorted by margin ascending (most fragile first).
    """
    margins = []
    for d in decisions:
        if d.get("error"):
            continue
        utility = d.get("utility", 0.0)
        margins.append({
            "id": d.get("id"),
            "archetype": d.get("archetype"),
            "action": d.get("action"),
            "utility": utility,
            "flip_margin": abs(utility),
            "fragile": abs(utility) < 0.25,
        })
    return sorted(margins, key=lambda m: m["flip_margin"])


def _dimension_leverage(decisions: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Compute per-dimension statistics to identify which dimensions drive divergence.

    Returns per-dimension: {mean, stdev, range, action_correlation}.
    action_correlation: how strongly this dimension separates the majority action from others.
    """
    valid = [d for d in decisions if not d.get("error") and d.get("utility_dimensions")]
    if not valid:
        return {}

    # Collect all dimension keys
    all_dims: set[str] = set()
    for d in valid:
        all_dims.update(d["utility_dimensions"].keys())

    # Find majority action
    action_counts = Counter(d["action"] for d in valid)
    majority_action = action_counts.most_common(1)[0][0] if action_counts else None

    result: dict[str, dict[str, float]] = {}
    for dim in sorted(all_dims):
        values = [d["utility_dimensions"].get(dim, 0.0) for d in valid]
        n = len(values)
        if n == 0:
            continue

        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n if n > 1 else 0.0
        stdev = variance ** 0.5
        val_range = max(values) - min(values) if values else 0.0

        # Action correlation: mean for majority vs mean for minority
        majority_vals = [
            d["utility_dimensions"].get(dim, 0.0)
            for d in valid if d["action"] == majority_action
        ]
        minority_vals = [
            d["utility_dimensions"].get(dim, 0.0)
            for d in valid if d["action"] != majority_action
        ]
        maj_mean = sum(majority_vals) / len(majority_vals) if majority_vals else 0.0
        min_mean = sum(minority_vals) / len(minority_vals) if minority_vals else 0.0
        separation = maj_mean - min_mean  # positive = dimension favors majority

        result[dim] = {
            "mean": round(mean, 4),
            "stdev": round(stdev, 4),
            "range": round(val_range, 4),
            "action_separation": round(separation, 4),
        }

    return result


def _coalition_fragility(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """How many agents would need to flip to change the majority outcome?

    Lower number = more fragile coalition.
    """
    valid = [d for d in decisions if not d.get("error")]
    if not valid:
        return {"majority_action": None, "majority_count": 0, "flips_to_overturn": 0, "fragility_ratio": 0.0}

    action_counts = Counter(d["action"] for d in valid)
    ranked = action_counts.most_common()
    majority_action = ranked[0][0]
    majority_count = ranked[0][1]
    runner_up_count = ranked[1][1] if len(ranked) > 1 else 0
    total = len(valid)

    # Flips needed: majority loses if (majority_count - x) < (runner_up_count + x)
    # Solve: majority_count - x < runner_up_count + x → x > (majority_count - runner_up_count) / 2
    flips_needed = (majority_count - runner_up_count) // 2 + 1

    return {
        "majority_action": majority_action,
        "majority_count": majority_count,
        "runner_up_action": ranked[1][0] if len(ranked) > 1 else None,
        "runner_up_count": runner_up_count,
        "flips_to_overturn": flips_needed,
        "fragility_ratio": round(flips_needed / total, 3) if total > 0 else 0.0,
    }


def _influence_sensitivity(
    decisions: list[dict[str, Any]],
    profiles: Optional[list],
) -> dict[str, Any]:
    """Check if removing the highest-influence agent changes the outcome.

    This reveals whether the result is dominated by a single powerful voice.
    """
    valid = [d for d in decisions if not d.get("error")]
    if not valid or not profiles:
        return {"dominated": False, "dominant_agent": None}

    weight_map = {p.agent_id: getattr(p, "influence_weight", 1.0) for p in profiles}

    # Find majority action with weights
    action_weights: dict[str, float] = {}
    for d in valid:
        w = weight_map.get(d.get("id", ""), 1.0)
        action = d.get("action", "UNKNOWN")
        action_weights[action] = action_weights.get(action, 0.0) + w

    majority_action = max(action_weights, key=action_weights.get) if action_weights else None

    # Find highest-influence agent in majority coalition
    majority_agents = [(d, weight_map.get(d.get("id", ""), 1.0)) for d in valid if d.get("action") == majority_action]
    if not majority_agents:
        return {"dominated": False, "dominant_agent": None}

    top_agent, top_weight = max(majority_agents, key=lambda x: x[1])

    # Recompute without top agent
    remaining_weights: dict[str, float] = {}
    for d in valid:
        if d.get("id") == top_agent.get("id"):
            continue
        w = weight_map.get(d.get("id", ""), 1.0)
        action = d.get("action", "UNKNOWN")
        remaining_weights[action] = remaining_weights.get(action, 0.0) + w

    new_majority = max(remaining_weights, key=remaining_weights.get) if remaining_weights else None
    outcome_flipped = new_majority != majority_action

    return {
        "dominated": outcome_flipped,
        "dominant_agent": {
            "id": top_agent.get("id"),
            "archetype": top_agent.get("archetype"),
            "influence_weight": top_weight,
            "action": top_agent.get("action"),
        },
        "outcome_without_dominant": new_majority,
        "original_outcome": majority_action,
    }


def format_sensitivity_block(analysis: dict[str, Any]) -> str:
    """Format sensitivity analysis into a human-readable markdown block."""
    lines = ["## SENSITIVITY ANALYSIS", ""]

    # Flip margins
    margins = analysis.get("flip_margins", [])
    fragile = [m for m in margins if m.get("fragile")]
    lines.append("### Decision Stability")
    lines.append(f"- Agents on the edge (utility < 0.25): {len(fragile)}/{len(margins)}")
    if fragile:
        for m in fragile[:3]:
            lines.append(f"  - {m['archetype']} ({m['action']}): margin {m['flip_margin']:.3f}")
    lines.append("")

    # Coalition fragility
    cf = analysis.get("coalition_fragility", {})
    if cf.get("majority_action"):
        lines.append("### Coalition Fragility")
        lines.append(f"- Majority: {cf['majority_action']} ({cf['majority_count']} agents)")
        if cf.get("runner_up_action"):
            lines.append(f"- Runner-up: {cf['runner_up_action']} ({cf['runner_up_count']} agents)")
        lines.append(f"- Flips needed to overturn: {cf['flips_to_overturn']} ({cf['fragility_ratio']:.0%} of swarm)")
        lines.append("")

    # Dimension leverage
    dims = analysis.get("dimension_leverage", {})
    if dims:
        lines.append("### Dimension Leverage (drives action divergence)")
        sorted_dims = sorted(dims.items(), key=lambda x: abs(x[1].get("action_separation", 0)), reverse=True)
        for dim, stats in sorted_dims[:5]:
            sep = stats.get("action_separation", 0)
            direction = "favors majority" if sep > 0 else "favors minority"
            lines.append(f"- {dim}: separation={sep:+.3f} ({direction}), spread={stats.get('range', 0):.3f}")
        lines.append("")

    # Influence sensitivity
    inf = analysis.get("influence_sensitivity", {})
    if inf.get("dominant_agent"):
        da = inf["dominant_agent"]
        lines.append("### Influence Sensitivity")
        if inf["dominated"]:
            lines.append(f"- ⚠️ OUTCOME DOMINATED: removing {da['archetype']} (weight {da['influence_weight']:.1f}x) flips result from {inf['original_outcome']} → {inf['outcome_without_dominant']}")
        else:
            lines.append(f"- Outcome stable: removing top influencer ({da['archetype']}, {da['influence_weight']:.1f}x) does not flip result")
        lines.append("")

    return "\n".join(lines)
