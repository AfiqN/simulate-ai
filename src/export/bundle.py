"""Export a simulation run as a self-contained shareable bundle."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def write_bundle(result: dict[str, Any], out_dir: Path) -> Path:
    """Write a shareable bundle (manifest + full data + report) to out_dir/bundle/.

    Args:
        result: The dict returned by run_simulation_pipeline (must include
                schema, profiles, decisions_r1/r2/r3, adversary_map, valence,
                crisis_event, resilience_metrics, report_md, timings).
        out_dir: The run output directory (e.g. tests/runs/20260624-112828__04_ai_proctoring).

    Returns:
        Path to the created bundle directory.
    """
    bundle_dir = out_dir / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    schema = result["schema"]

    # --- manifest.json: lightweight metadata for indexing/display ---
    manifest = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "scenario_name": schema.scenario_name,
        "scenario_description": schema.scenario_description,
        "verdict_label": schema.verdict_label,
        "agent_count": len(result["profiles"]),
        "valence": result["valence"],
        "resilience_verdict": result["resilience_metrics"]["verdict"],
        "timings": result["timings"],
    }
    (bundle_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- simulation.json: full structured data ---
    simulation_data = {
        "scenario_name": schema.scenario_name,
        "scenario_description": schema.scenario_description,
        "verdict_label": schema.verdict_label,
        "actions": [a.name for a in schema.actions],
        "state_vocabulary": schema.state_vocabulary,
        "valence": result["valence"],
        "crisis_event": result["crisis_event"],
        "resilience_metrics": result["resilience_metrics"],
        "agents": [
            {
                "id": p.agent_id,
                "archetype": p.archetype,
                "linguistic_cluster_id": p.linguistic_cluster_id,
                "attributes": {
                    "rationality_index": p.attributes.rationality_index,
                    "aggressiveness": p.attributes.aggressiveness,
                    "risk_tolerance": p.attributes.risk_tolerance,
                },
                "final_state": p.current_internal_state,
            }
            for p in result["profiles"]
        ],
        "rounds": {
            "r1": _serialize_decisions(result["decisions_r1"]),
            "r2": _serialize_decisions(result["decisions_r2"]),
            "r3": _serialize_decisions(result["decisions_r3"]),
        },
        "adversary_map": {
            agent_id: (target["id"] if target else None)
            for agent_id, target in result["adversary_map"].items()
        },
        "timings": result["timings"],
        "report_md": result["report_md"],
    }
    (bundle_dir / "simulation.json").write_text(
        json.dumps(simulation_data, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )

    # --- report.md: standalone readable report ---
    (bundle_dir / "report.md").write_text(result["report_md"], encoding="utf-8")

    return bundle_dir


def _serialize_decisions(decisions: list[dict]) -> list[dict]:
    """Serialize decision dicts, keeping only the exportable fields."""
    return [
        {
            "id": d["id"],
            "archetype": d["archetype"],
            "action": d["action"],
            "utility": d["utility"],
            "new_state": d["new_state"],
            "duration": d.get("duration", 0.0),
        }
        for d in decisions
    ]
