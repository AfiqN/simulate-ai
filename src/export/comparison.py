"""Compare two simulation runs and produce a structured diff."""

import json
from pathlib import Path
from typing import Any


def compare_runs(run_a_data: dict[str, Any], run_b_data: dict[str, Any]) -> dict[str, Any]:
    """Compare two simulation results and return a structured diff.

    Args:
        run_a_data: Full metrics.json content for run A
        run_b_data: Full metrics.json content for run B

    Returns:
        Structured comparison with verdict diff, metric deltas, vote diffs, etc.
    """
    return {
        "verdict": _compare_verdicts(run_a_data, run_b_data),
        "stability": _compare_stability(run_a_data, run_b_data),
        "vote_tally": _compare_votes(run_a_data, run_b_data),
        "dimension_stats": _compare_dimensions(run_a_data, run_b_data),
        "timings": _compare_timings(run_a_data, run_b_data),
        "meta": {
            "run_a_scenario": run_a_data.get("scenario_name", "Unknown"),
            "run_b_scenario": run_b_data.get("scenario_name", "Unknown"),
            "run_a_agents": run_a_data.get("agent_count") or _count_agents(run_a_data),
            "run_b_agents": run_b_data.get("agent_count") or _count_agents(run_b_data),
        },
    }


def _compare_verdicts(a: dict, b: dict) -> dict[str, Any]:
    metrics_a = a.get("resilience_metrics") or {}
    metrics_b = b.get("resilience_metrics") or {}
    verdict_a = metrics_a.get("verdict", "Unknown")
    verdict_b = metrics_b.get("verdict", "Unknown")
    return {
        "run_a": verdict_a,
        "run_b": verdict_b,
        "changed": verdict_a != verdict_b,
    }


def _compare_stability(a: dict, b: dict) -> dict[str, Any]:
    metrics_a = a.get("resilience_metrics") or {}
    metrics_b = b.get("resilience_metrics") or {}
    stability_a = metrics_a.get("decision_stability", 0)
    stability_b = metrics_b.get("decision_stability", 0)
    drift_a = metrics_a.get("utility_drift_mean", 0)
    drift_b = metrics_b.get("utility_drift_mean", 0)
    return {
        "decision_stability": {
            "run_a": stability_a,
            "run_b": stability_b,
            "delta": round(stability_b - stability_a, 4),
        },
        "utility_drift_mean": {
            "run_a": drift_a,
            "run_b": drift_b,
            "delta": round(drift_b - drift_a, 4),
        },
    }


def _compare_votes(a: dict, b: dict) -> dict[str, Any]:
    """Compare vote tallies across rounds."""
    qm_a = a.get("quantitative_metrics") or {}
    qm_b = b.get("quantitative_metrics") or {}
    tally_a = qm_a.get("vote_tally", {})
    tally_b = qm_b.get("vote_tally", {})

    all_rounds = sorted(set(list(tally_a.keys()) + list(tally_b.keys())))
    comparison = {}
    for round_key in all_rounds:
        ra = tally_a.get(round_key, {})
        rb = tally_b.get(round_key, {})
        all_actions = sorted(set(list(ra.keys()) + list(rb.keys())))
        comparison[round_key] = {
            action: {
                "run_a": ra.get(action, 0),
                "run_b": rb.get(action, 0),
                "delta": rb.get(action, 0) - ra.get(action, 0),
            }
            for action in all_actions
        }
    return comparison


def _compare_dimensions(a: dict, b: dict) -> dict[str, Any]:
    """Compare dimension stats (mean scores per dimension per round)."""
    qm_a = a.get("quantitative_metrics") or {}
    qm_b = b.get("quantitative_metrics") or {}
    dims_a = qm_a.get("dimension_stats", {})
    dims_b = qm_b.get("dimension_stats", {})

    all_rounds = sorted(set(list(dims_a.keys()) + list(dims_b.keys())))
    comparison = {}
    for round_key in all_rounds:
        da = dims_a.get(round_key, {})
        db = dims_b.get(round_key, {})
        all_dims = sorted(set(list(da.keys()) + list(db.keys())))
        comparison[round_key] = {}
        for dim in all_dims:
            mean_a = (da.get(dim) or {}).get("mean", 0)
            mean_b = (db.get(dim) or {}).get("mean", 0)
            comparison[round_key][dim] = {
                "run_a_mean": round(mean_a, 3),
                "run_b_mean": round(mean_b, 3),
                "delta": round(mean_b - mean_a, 3),
            }
    return comparison


def _compare_timings(a: dict, b: dict) -> dict[str, Any]:
    ta = a.get("timings") or {}
    tb = b.get("timings") or {}
    return {
        "run_a_total": ta.get("total", 0),
        "run_b_total": tb.get("total", 0),
        "delta": round((tb.get("total", 0) - ta.get("total", 0)), 2),
    }


def _count_agents(data: dict) -> int:
    """Estimate agent count from available data."""
    if "profiles" in data and isinstance(data["profiles"], list):
        return len(data["profiles"])
    qm = data.get("quantitative_metrics") or {}
    tally = qm.get("vote_tally", {})
    if "r1" in tally:
        return sum(tally["r1"].values())
    return 0


def load_run_data(run_dir: str | Path) -> dict[str, Any]:
    """Load a run's metrics.json from its directory."""
    metrics_path = Path(run_dir) / "metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"metrics.json not found in {run_dir}")
    return json.loads(metrics_path.read_text(encoding="utf-8"))
