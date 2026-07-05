"""Tests for src/export/bundle.py."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.export.bundle import write_bundle, _serialize_decisions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_attrs(rationality=0.7, aggressiveness=0.5, risk_tolerance=0.4):
    return SimpleNamespace(
        rationality_index=rationality,
        aggressiveness=aggressiveness,
        risk_tolerance=risk_tolerance,
    )


def _make_profile(agent_id, archetype, cluster_id, state="Neutral"):
    return SimpleNamespace(
        agent_id=agent_id,
        archetype=archetype,
        linguistic_cluster_id=cluster_id,
        attributes=_make_attrs(),
        current_internal_state=state,
    )


def _make_action(name):
    return SimpleNamespace(name=name)


def _make_schema(
    scenario_name="Policy Debate",
    scenario_description="A debate on fiscal policy.",
    verdict_label="CONTESTED",
    action_names=("SUPPORT", "OPPOSE", "AMEND"),
    state_vocab=("Neutral", "Skeptical", "Resolute"),
):
    return SimpleNamespace(
        scenario_name=scenario_name,
        scenario_description=scenario_description,
        verdict_label=verdict_label,
        actions=[_make_action(n) for n in action_names],
        state_vocabulary=list(state_vocab),
    )


def _make_decision(agent_id, archetype, action, utility, new_state, duration=1.2):
    return {
        "id": agent_id,
        "archetype": archetype,
        "action": action,
        "utility": utility,
        "new_state": new_state,
        "duration": duration,
    }


def _make_result(out_dir: Path):
    profiles = [
        _make_profile("agent_0", "Pragmatist", "cluster_a", "Neutral"),
        _make_profile("agent_1", "Idealist", "cluster_b", "Skeptical"),
    ]
    decisions = [
        _make_decision("agent_0", "Pragmatist", "SUPPORT", 0.7, "Resolute"),
        _make_decision("agent_1", "Idealist", "OPPOSE", -0.3, "Skeptical"),
    ]
    return {
        "schema": _make_schema(),
        "profiles": profiles,
        "decisions_r1": decisions,
        "decisions_r2": decisions,
        "decisions_r3": decisions,
        "adversary_map": {
            "agent_0": {"id": "agent_1"},
            "agent_1": {"id": "agent_0"},
        },
        "crisis_event": {"stress": "Sudden budget freeze announced.", "validation": "Major partner publicly endorses the initiative."},
        "resilience_metrics": {"verdict": "RESILIENT", "score": 0.8},
        "report_md": "# Executive Report\n\nAll clear.",
        "timings": {"r1": 5.1, "r2": 6.3, "r3": 4.8, "total": 16.2},
    }


# ---------------------------------------------------------------------------
# Tests: directory and file creation
# ---------------------------------------------------------------------------

def test_write_bundle_creates_bundle_directory(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    assert bundle_dir.is_dir()
    assert bundle_dir.name == "bundle"


def test_write_bundle_creates_required_files(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    assert (bundle_dir / "manifest.json").exists()
    assert (bundle_dir / "simulation.json").exists()
    assert (bundle_dir / "report.md").exists()


def test_write_bundle_returns_bundle_path(tmp_path):
    result = _make_result(tmp_path)
    returned = write_bundle(result, tmp_path)
    assert returned == tmp_path / "bundle"


def test_write_bundle_is_idempotent(tmp_path):
    """Calling write_bundle twice on the same out_dir should not raise."""
    result = _make_result(tmp_path)
    write_bundle(result, tmp_path)
    write_bundle(result, tmp_path)
    assert (tmp_path / "bundle" / "manifest.json").exists()


# ---------------------------------------------------------------------------
# Tests: manifest.json content
# ---------------------------------------------------------------------------

def test_manifest_required_keys(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    for key in ("version", "exported_at", "scenario_name", "scenario_description",
                "verdict_label", "agent_count", "crisis_event", "resilience_verdict", "timings"):
        assert key in manifest, f"Missing key: {key}"


def test_manifest_version(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.0"


def test_manifest_scenario_name(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scenario_name"] == "Policy Debate"


def test_manifest_agent_count(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["agent_count"] == 2


def test_manifest_crisis_event(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["crisis_event"]["stress"] == "Sudden budget freeze announced."
    assert manifest["crisis_event"]["validation"] == "Major partner publicly endorses the initiative."


def test_manifest_resilience_verdict(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["resilience_verdict"] == "RESILIENT"


def test_manifest_timings(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["timings"]["total"] == pytest.approx(16.2)


# ---------------------------------------------------------------------------
# Tests: simulation.json content
# ---------------------------------------------------------------------------

def test_simulation_json_top_level_keys(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    sim = json.loads((bundle_dir / "simulation.json").read_text(encoding="utf-8"))
    for key in ("scenario_name", "scenario_description", "verdict_label", "actions",
                "state_vocabulary", "crisis_event", "resilience_metrics",
                "agents", "rounds", "adversary_map", "timings", "report_md"):
        assert key in sim, f"Missing key: {key}"


def test_simulation_json_actions_list(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    sim = json.loads((bundle_dir / "simulation.json").read_text(encoding="utf-8"))
    assert sim["actions"] == ["SUPPORT", "OPPOSE", "AMEND"]


def test_simulation_json_agent_structure(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    sim = json.loads((bundle_dir / "simulation.json").read_text(encoding="utf-8"))
    agent = sim["agents"][0]
    assert agent["id"] == "agent_0"
    assert agent["archetype"] == "Pragmatist"
    assert agent["linguistic_cluster_id"] == "cluster_a"
    assert "attributes" in agent
    assert "rationality_index" in agent["attributes"]
    assert "aggressiveness" in agent["attributes"]
    assert "risk_tolerance" in agent["attributes"]
    assert "final_state" in agent


def test_simulation_json_rounds_present(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    sim = json.loads((bundle_dir / "simulation.json").read_text(encoding="utf-8"))
    assert set(sim["rounds"].keys()) == {"r1", "r2", "r3"}


def test_simulation_json_adversary_map_values(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    sim = json.loads((bundle_dir / "simulation.json").read_text(encoding="utf-8"))
    # Values should be plain IDs (strings), not nested dicts
    assert sim["adversary_map"]["agent_0"] == "agent_1"
    assert sim["adversary_map"]["agent_1"] == "agent_0"


def test_simulation_json_adversary_map_none_value(tmp_path):
    result = _make_result(tmp_path)
    result["adversary_map"]["agent_0"] = None
    bundle_dir = write_bundle(result, tmp_path)
    sim = json.loads((bundle_dir / "simulation.json").read_text(encoding="utf-8"))
    assert sim["adversary_map"]["agent_0"] is None


# ---------------------------------------------------------------------------
# Tests: report.md content
# ---------------------------------------------------------------------------

def test_report_md_content(tmp_path):
    result = _make_result(tmp_path)
    bundle_dir = write_bundle(result, tmp_path)
    text = (bundle_dir / "report.md").read_text(encoding="utf-8")
    assert text == "# Executive Report\n\nAll clear."


# ---------------------------------------------------------------------------
# Tests: _serialize_decisions
# ---------------------------------------------------------------------------

def test_serialize_decisions_fields():
    decisions = [
        _make_decision("agent_0", "Pragmatist", "SUPPORT", 0.7, "Resolute", duration=2.5),
    ]
    serialized = _serialize_decisions(decisions)
    assert len(serialized) == 1
    row = serialized[0]
    assert row["id"] == "agent_0"
    assert row["archetype"] == "Pragmatist"
    assert row["action"] == "SUPPORT"
    assert row["utility"] == pytest.approx(0.7)
    assert row["new_state"] == "Resolute"
    assert row["duration"] == pytest.approx(2.5)


def test_serialize_decisions_duration_defaults_to_zero():
    decision = {
        "id": "agent_0",
        "archetype": "X",
        "action": "SUPPORT",
        "utility": 0.5,
        "new_state": "Neutral",
        # no "duration" key
    }
    serialized = _serialize_decisions([decision])
    assert serialized[0]["duration"] == pytest.approx(0.0)


def test_serialize_decisions_multiple():
    decisions = [
        _make_decision(f"agent_{i}", "Arch", "OPPOSE", -0.1 * i, "Skeptical")
        for i in range(4)
    ]
    serialized = _serialize_decisions(decisions)
    assert len(serialized) == 4
    assert [r["id"] for r in serialized] == ["agent_0", "agent_1", "agent_2", "agent_3"]


def test_serialize_decisions_empty():
    assert _serialize_decisions([]) == []
