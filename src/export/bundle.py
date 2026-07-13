"""Export a simulation run as a self-contained shareable bundle."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.export.chart_data import generate_chart_data


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
        "crisis_event": result["crisis_event"],
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
        "crisis_event": result["crisis_event"],
        "resilience_metrics": result["resilience_metrics"],
        "quantitative_metrics": result.get("quantitative_metrics"),
        "rag_metadata": result.get("rag_metadata"),
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
                "decision_framework": p.decision_framework,
                "knowledge_base": p.knowledge_base,
                "constraints": p.constraints,
                "influence_weight": p.influence_weight,
                "backstory": p.backstory,
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
        "adversarial_result": _serialize_adversarial_result(result.get("adversarial_result")),
        "timings": result["timings"],
        "report_md": result["report_md"],
    }
    (bundle_dir / "simulation.json").write_text(
        json.dumps(simulation_data, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )

    # --- report.md: standalone readable report ---
    (bundle_dir / "report.md").write_text(result["report_md"], encoding="utf-8")

    # --- chart_data.json: pre-computed chart-ready structures ---
    try:
        chart_data = generate_chart_data(result)
        (bundle_dir / "chart_data.json").write_text(
            json.dumps(chart_data, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
    except (KeyError, TypeError):
        pass  # Non-fatal: chart data is optional

    return bundle_dir


def _serialize_decisions(decisions: list[dict]) -> list[dict]:
    """Serialize decision dicts, keeping only the exportable fields."""
    return [
        {
            "id": d["id"],
            "archetype": d["archetype"],
            "action": d["action"],
            "utility": d["utility"],
            "utility_dimensions": d.get("utility_dimensions", {}),
            "reasoning_chain": d.get("reasoning_chain", []),
            "new_state": d["new_state"],
            "duration": d.get("duration", 0.0),
        }
        for d in decisions
    ]


def _serialize_adversarial_result(adversarial_raw) -> dict | None:
    """Serialize AdversarialRoundResult dataclass to a plain dict for export."""
    if adversarial_raw is None:
        return None
    from dataclasses import asdict
    return {
        "claims": [asdict(c) for c in adversarial_raw.claims],
        "survival_rate": adversarial_raw.survival_rate,
        "surviving_count": len(adversarial_raw.surviving_claims),
        "defeated_count": len(adversarial_raw.defeated_claims),
        "key_defeats": adversarial_raw.key_defeats,
    }
