"""Canonical, versioned serialization for simulation results.

The same payload is used by the API, persisted result.json, exports, examples,
and frontend hydration. Keep this module independent from tests and FastAPI.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

RESULT_VERSION = "1.0"


def _serialize_decisions(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "id", "archetype", "action", "utility", "utility_dimensions",
        "reasoning_chain", "new_state", "duration", "monologue", "statement",
    )
    return [{key: decision.get(key) for key in fields} for decision in decisions]


def _serialize_profiles(profiles: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": profile.agent_id,
            "archetype": profile.archetype,
            "linguistic_cluster_id": profile.linguistic_cluster_id,
            "attributes": asdict(profile.attributes),
            "decision_framework": profile.decision_framework,
            "knowledge_base": profile.knowledge_base,
            "constraints": profile.constraints,
            "influence_weight": profile.influence_weight,
            "backstory": profile.backstory,
            "final_state": profile.current_internal_state,
        }
        for profile in profiles
    ]


def _serialize_adversarial(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    return {
        "claims": [asdict(claim) for claim in value.claims],
        "survival_rate": value.survival_rate,
        "surviving_count": len(value.surviving_claims),
        "defeated_count": len(value.defeated_claims),
        "key_defeats": value.key_defeats,
    }


def serialize_simulation_result(
    result: dict[str, Any],
    *,
    run_id: str | None = None,
    stimulus: str = "",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the canonical JSON-safe result payload."""
    schema = result["schema"]
    rounds = {
        "r1": _serialize_decisions(result.get("decisions_r1", [])),
        "r2": _serialize_decisions(result.get("decisions_r2", [])),
        "r3": _serialize_decisions(result.get("decisions_r3", [])),
        "r4": _serialize_decisions(result.get("decisions_r4", [])),
    }
    return {
        "version": RESULT_VERSION,
        "id": run_id,
        "stimulus": stimulus,
        "config": config or {},
        "scenario_name": schema.scenario_name,
        "schema": schema.to_dict(),
        "profiles": _serialize_profiles(result.get("profiles", [])),
        "rounds": rounds,
        "crisis_event": result.get("crisis_event"),
        "resilience_metrics": result.get("resilience_metrics"),
        "quantitative_metrics": result.get("quantitative_metrics"),
        "sensitivity_analysis": result.get("sensitivity_analysis"),
        "faction_metrics": result.get("faction_metrics"),
        "conditional_dynamics": result.get("conditional_dynamics"),
        "historical_context": result.get("historical_context"),
        "adversarial_result": _serialize_adversarial(result.get("adversarial_result")),
        "report_md": result.get("report_md", ""),
        "timings": result.get("timings", {}),
        "rag_metadata": result.get("rag_metadata"),
    }


def load_canonical_result(run_dir) -> dict[str, Any] | None:
    """Load canonical data, with backward-compatible fallbacks for old runs."""
    import json
    from pathlib import Path

    root = Path(run_dir)
    candidates = (
        root / "result.json",
        root / "bundle" / "simulation.json",
        root / "metrics.json",
    )
    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data.setdefault("version", "legacy")
            return data
    return None
