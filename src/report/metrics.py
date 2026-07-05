"""Pre-computed quantitative metrics for simulation reports.

All functions are pure (no LLM calls). They compute statistics from decision
dicts and inject them into the report prompt so the LLM references real numbers
instead of inventing its own.
"""

from collections import Counter
from math import sqrt
from typing import Any, Optional

from src.schema.simulation_schema import SimulationSchema


def compute_quantitative_metrics(
    r1: list[dict[str, Any]],
    r2: list[dict[str, Any]],
    r3: list[dict[str, Any]],
    schema: SimulationSchema,
    profiles: Optional[list] = None,
) -> dict[str, Any]:
    """Compute all quantitative metrics from round decisions.

    Returns a dict with:
        vote_tally: per-round action counts
        dimension_stats: per-round per-dimension {mean, stdev, min, max}
        state_transitions: round-over-round state change tracking
        swing_analysis: agents who changed action + dimension that drove the flip
        consensus_index: per-round HHI of action concentration
        weighted_consensus_index: per-round HHI weighted by influence_weight
        net_confidence: per-round average |utility|
    """
    result = {
        "vote_tally": _vote_tally(r1, r2, r3, schema),
        "dimension_stats": _dimension_stats(r1, r2, r3),
        "state_transitions": _state_transitions(r1, r2, r3),
        "swing_analysis": _swing_analysis(r1, r2, r3),
        "consensus_index": _consensus_index(r1, r2, r3),
        "net_confidence": _net_confidence(r1, r2, r3),
    }
    if profiles:
        result["weighted_consensus_index"] = _weighted_consensus_index(r1, r2, r3, profiles)
    return result


def format_metrics_block(metrics: dict[str, Any]) -> str:
    """Format pre-computed metrics as a markdown block for the report prompt."""
    lines: list[str] = []
    lines.append("## PRE-COMPUTED QUANTITATIVE METRICS (authoritative — DO NOT invent different numbers)")
    lines.append("")

    # Vote tally
    vt = metrics["vote_tally"]
    lines.append("### Vote Tally")
    for round_key, label in [("r1", "Round 1"), ("r2", "Round 2"), ("r3", "Round 3")]:
        counts = vt.get(round_key, {})
        if counts:
            tally_str = ", ".join(f"{action}={count}" for action, count in sorted(counts.items(), key=lambda x: -x[1]))
            total = sum(counts.values())
            lines.append(f"- {label} ({total} agents): {tally_str}")
    lines.append("")

    # Dimension stats
    ds = metrics["dimension_stats"]
    if any(ds.get(rk) for rk in ("r1", "r2", "r3")):
        lines.append("### Per-Dimension Score Distributions")
        for round_key, label in [("r1", "Round 1"), ("r2", "Round 2"), ("r3", "Round 3")]:
            round_dims = ds.get(round_key, {})
            if round_dims:
                lines.append(f"- {label}:")
                for dim, stats in sorted(round_dims.items()):
                    lines.append(
                        f"    {dim}: mean={stats['mean']:+.2f}, "
                        f"stdev={stats['stdev']:.2f}, "
                        f"range=[{stats['min']:+.2f}, {stats['max']:+.2f}]"
                    )
        lines.append("")

    # State transitions
    st = metrics["state_transitions"]
    if st.get("r1_to_r2") or st.get("r2_to_r3"):
        lines.append("### State Transitions")
        for trans_key, label in [("r1_to_r2", "R1→R2"), ("r2_to_r3", "R2→R3")]:
            transitions = st.get(trans_key, {})
            if transitions:
                shifted = transitions["shifted_count"]
                total = transitions["total"]
                lines.append(f"- {label}: {shifted}/{total} agents shifted state")
                if transitions["top_shifts"]:
                    for shift in transitions["top_shifts"][:5]:
                        lines.append(f"    {shift['from']} → {shift['to']} ({shift['count']}x)")
        lines.append("")

    # Swing analysis
    sa = metrics["swing_analysis"]
    if sa.get("r1_to_r2") or sa.get("r2_to_r3"):
        lines.append("### Swing Analysis (agents who changed action)")
        for swing_key, label in [("r1_to_r2", "R1→R2"), ("r2_to_r3", "R2→R3")]:
            swings = sa.get(swing_key, [])
            if swings:
                lines.append(f"- {label}: {len(swings)} agent(s) flipped")
                for s in swings[:5]:
                    driver = s.get("driver_dimension", "unknown")
                    lines.append(
                        f"    {s['archetype']}: {s['from_action']}→{s['to_action']} "
                        f"(driver: {driver}, Δutility={s['utility_delta']:+.2f})"
                    )
        lines.append("")

    # Consensus index
    ci = metrics["consensus_index"]
    lines.append("### Consensus Index (HHI: 0=fragmented, 1=unanimous)")
    for round_key, label in [("r1", "Round 1"), ("r2", "Round 2"), ("r3", "Round 3")]:
        val = ci.get(round_key)
        if val is not None:
            lines.append(f"- {label}: {val:.3f}")
    # Weighted consensus (influence-adjusted)
    wci = metrics.get("weighted_consensus_index")
    if wci:
        lines.append("- Influence-weighted:")
        for round_key, label in [("r1", "R1"), ("r2", "R2"), ("r3", "R3")]:
            val = wci.get(round_key)
            if val is not None:
                lines.append(f"    {label}: {val:.3f}")
    lines.append("")

    # Net confidence
    nc = metrics["net_confidence"]
    lines.append("### Net Confidence (avg |utility| — conviction strength)")
    for round_key, label in [("r1", "Round 1"), ("r2", "Round 2"), ("r3", "Round 3")]:
        val = nc.get(round_key)
        if val is not None:
            lines.append(f"- {label}: {val:.3f}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal computation helpers
# ---------------------------------------------------------------------------


def _valid(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out error entries."""
    return [d for d in decisions if not d.get("error")]


def _vote_tally(
    r1: list[dict], r2: list[dict], r3: list[dict], schema: SimulationSchema
) -> dict[str, dict[str, int]]:
    result = {}
    for round_key, decisions in [("r1", r1), ("r2", r2), ("r3", r3)]:
        valid = _valid(decisions)
        if valid:
            result[round_key] = dict(Counter(d.get("action", "UNKNOWN") for d in valid))
    return result


def _dimension_stats(
    r1: list[dict], r2: list[dict], r3: list[dict]
) -> dict[str, dict[str, dict[str, float]]]:
    result = {}
    for round_key, decisions in [("r1", r1), ("r2", r2), ("r3", r3)]:
        valid = _valid(decisions)
        # Gather all dimension names seen in this round
        all_dims: set[str] = set()
        for d in valid:
            dims = d.get("utility_dimensions") or {}
            all_dims.update(dims.keys())

        if not all_dims:
            continue

        round_stats: dict[str, dict[str, float]] = {}
        for dim in sorted(all_dims):
            scores = [
                d["utility_dimensions"][dim]
                for d in valid
                if dim in (d.get("utility_dimensions") or {})
            ]
            if scores:
                n = len(scores)
                mean = sum(scores) / n
                variance = sum((s - mean) ** 2 for s in scores) / n if n > 1 else 0.0
                round_stats[dim] = {
                    "mean": mean,
                    "stdev": sqrt(variance),
                    "min": min(scores),
                    "max": max(scores),
                }
        if round_stats:
            result[round_key] = round_stats
    return result


def _state_transitions(
    r1: list[dict], r2: list[dict], r3: list[dict]
) -> dict[str, Any]:
    result = {}

    def _compute_transitions(before: list[dict], after: list[dict]) -> Optional[dict]:
        before_by_id = {d["id"]: d for d in _valid(before)}
        after_by_id = {d["id"]: d for d in _valid(after)}
        paired_ids = set(before_by_id.keys()) & set(after_by_id.keys())
        if not paired_ids:
            return None

        shifts: list[tuple[str, str]] = []
        for aid in paired_ids:
            s_before = before_by_id[aid].get("new_state", "")
            s_after = after_by_id[aid].get("new_state", "")
            if s_before != s_after:
                shifts.append((s_before, s_after))

        shift_counts = Counter(shifts)
        top_shifts = [
            {"from": pair[0], "to": pair[1], "count": count}
            for pair, count in shift_counts.most_common(5)
        ]

        return {
            "total": len(paired_ids),
            "shifted_count": len(shifts),
            "top_shifts": top_shifts,
        }

    t12 = _compute_transitions(r1, r2)
    if t12:
        result["r1_to_r2"] = t12
    t23 = _compute_transitions(r2, r3)
    if t23:
        result["r2_to_r3"] = t23
    return result


def _swing_analysis(
    r1: list[dict], r2: list[dict], r3: list[dict]
) -> dict[str, list[dict[str, Any]]]:
    result = {}

    def _find_swings(before: list[dict], after: list[dict]) -> list[dict[str, Any]]:
        before_by_id = {d["id"]: d for d in _valid(before)}
        after_by_id = {d["id"]: d for d in _valid(after)}
        swings = []
        for aid in set(before_by_id.keys()) & set(after_by_id.keys()):
            b = before_by_id[aid]
            a = after_by_id[aid]
            if b.get("action") != a.get("action"):
                # Find the dimension with the largest absolute shift
                driver = _find_driver_dimension(b, a)
                swings.append({
                    "id": aid,
                    "archetype": a.get("archetype", "?"),
                    "from_action": b.get("action"),
                    "to_action": a.get("action"),
                    "utility_delta": (a.get("utility", 0.0) - b.get("utility", 0.0)),
                    "driver_dimension": driver,
                })
        # Sort by magnitude of utility change (biggest swings first)
        swings.sort(key=lambda s: abs(s["utility_delta"]), reverse=True)
        return swings

    s12 = _find_swings(r1, r2)
    if s12:
        result["r1_to_r2"] = s12
    s23 = _find_swings(r2, r3)
    if s23:
        result["r2_to_r3"] = s23
    return result


def _find_driver_dimension(before: dict, after: dict) -> str:
    """Identify the dimension with the largest absolute score change."""
    dims_b = before.get("utility_dimensions") or {}
    dims_a = after.get("utility_dimensions") or {}
    all_dims = set(dims_b.keys()) | set(dims_a.keys())
    if not all_dims:
        return "aggregate"

    max_delta = 0.0
    driver = "aggregate"
    for dim in all_dims:
        delta = abs((dims_a.get(dim, 0.0)) - (dims_b.get(dim, 0.0)))
        if delta > max_delta:
            max_delta = delta
            driver = dim
    return driver


def _consensus_index(
    r1: list[dict], r2: list[dict], r3: list[dict]
) -> dict[str, float]:
    """Compute Herfindahl-Hirschman Index per round (0=fragmented, 1=unanimous)."""
    result = {}
    for round_key, decisions in [("r1", r1), ("r2", r2), ("r3", r3)]:
        valid = _valid(decisions)
        if not valid:
            continue
        n = len(valid)
        counts = Counter(d.get("action", "UNKNOWN") for d in valid)
        hhi = sum((count / n) ** 2 for count in counts.values())
        result[round_key] = hhi
    return result


def _net_confidence(
    r1: list[dict], r2: list[dict], r3: list[dict]
) -> dict[str, float]:
    """Compute average |utility| per round as a proxy for conviction strength."""
    result = {}
    for round_key, decisions in [("r1", r1), ("r2", r2), ("r3", r3)]:
        valid = _valid(decisions)
        if not valid:
            continue
        avg_abs = sum(abs(d.get("utility", 0.0)) for d in valid) / len(valid)
        result[round_key] = avg_abs
    return result


def _weighted_consensus_index(
    r1: list[dict], r2: list[dict], r3: list[dict],
    profiles: list,
) -> dict[str, float]:
    """Compute influence-weighted HHI per round.

    Each agent's vote is weighted by their influence_weight. Higher influence
    agents contribute more to consensus measurement.
    """
    weight_map = {p.agent_id: getattr(p, "influence_weight", 1.0) for p in profiles}

    result = {}
    for round_key, decisions in [("r1", r1), ("r2", r2), ("r3", r3)]:
        valid = _valid(decisions)
        if not valid:
            continue
        # Accumulate weighted votes per action
        action_weights: dict[str, float] = {}
        total_weight = 0.0
        for d in valid:
            w = weight_map.get(d.get("id", ""), 1.0)
            action = d.get("action", "UNKNOWN")
            action_weights[action] = action_weights.get(action, 0.0) + w
            total_weight += w
        if total_weight > 0:
            hhi = sum((w / total_weight) ** 2 for w in action_weights.values())
            result[round_key] = hhi
    return result
