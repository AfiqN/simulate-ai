"""Unit tests for SimulationSchema — focus on evaluation_dimensions and from_dict/to_dict."""

import pytest

from src.schema.simulation_schema import (
    ActionDefinition,
    LinguisticCluster,
    ResourceDefinition,
    ResourceModel,
    SimulationSchema,
    _optional_float,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_schema_dict(**overrides) -> dict:
    base = {
        "scenario_name": "Test",
        "scenario_description": "A test scenario",
        "verdict_label": "Verdict",
        "actions": [
            {"name": "SUPPORT", "description": "support the proposal"},
            {"name": "OPPOSE", "description": "oppose", "is_terminal": True},
        ],
        "state_vocabulary": ["Neutral", "Excited", "Wary"],
        "resource_model": {"kind": "none", "resources": []},
        "linguistic_clusters": [
            {"cluster_id": "formal", "description": "formal", "style_prompt": "be formal"},
        ],
        "macro_context": ["context line"],
        "crisis_dimensions": ["economic_shock"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests: evaluation_dimensions field
# ---------------------------------------------------------------------------


class TestEvaluationDimensions:
    def test_default_empty_list(self):
        schema = SimulationSchema(
            scenario_name="X",
            scenario_description="X",
            verdict_label="X",
            actions=[ActionDefinition(name="A", description="a")],
            state_vocabulary=["Neutral"],
            resource_model=ResourceModel(kind="none"),
            linguistic_clusters=[LinguisticCluster(cluster_id="c", description="", style_prompt="")],
            macro_context=[],
            crisis_dimensions=["x"],
        )
        assert schema.evaluation_dimensions == []

    def test_set_dimensions(self):
        schema = SimulationSchema(
            scenario_name="X",
            scenario_description="X",
            verdict_label="X",
            actions=[ActionDefinition(name="A", description="a")],
            state_vocabulary=["Neutral"],
            resource_model=ResourceModel(kind="none"),
            linguistic_clusters=[LinguisticCluster(cluster_id="c", description="", style_prompt="")],
            macro_context=[],
            crisis_dimensions=["x"],
            evaluation_dimensions=["cost", "impact", "feasibility"],
        )
        assert schema.evaluation_dimensions == ["cost", "impact", "feasibility"]


# ---------------------------------------------------------------------------
# Tests: from_dict
# ---------------------------------------------------------------------------


class TestFromDict:
    def test_from_dict_with_evaluation_dimensions(self):
        data = _minimal_schema_dict(evaluation_dimensions=["financial", "social", "risk"])
        schema = SimulationSchema.from_dict(data)
        assert schema.evaluation_dimensions == ["financial", "social", "risk"]

    def test_from_dict_without_evaluation_dimensions(self):
        data = _minimal_schema_dict()
        # No evaluation_dimensions key at all
        schema = SimulationSchema.from_dict(data)
        assert schema.evaluation_dimensions == []

    def test_from_dict_action_names_uppercased(self):
        data = _minimal_schema_dict(actions=[
            {"name": "invest", "description": "invest in it"},
            {"name": "pass", "description": "skip", "is_terminal": True},
        ])
        schema = SimulationSchema.from_dict(data)
        assert schema.action_names() == ["INVEST", "PASS"]

    def test_from_dict_action_is_terminal(self):
        data = _minimal_schema_dict()
        schema = SimulationSchema.from_dict(data)
        assert schema.actions[0].is_terminal is False
        assert schema.actions[1].is_terminal is True

    def test_from_dict_resource_model_kind(self):
        data = _minimal_schema_dict()
        data["resource_model"] = {"kind": "Single", "resources": [
            {"name": "Budget", "description": "money", "initial_default": 1000, "max_default": 5000}
        ]}
        schema = SimulationSchema.from_dict(data)
        assert schema.resource_model.kind == "single"  # lowercased
        assert len(schema.resource_model.resources) == 1
        assert schema.resource_model.resources[0].name == "Budget"
        assert schema.resource_model.resources[0].initial_default == 1000.0

    def test_from_dict_linguistic_clusters(self):
        data = _minimal_schema_dict()
        schema = SimulationSchema.from_dict(data)
        assert schema.cluster_ids() == ["formal"]
        assert schema.get_cluster("formal").style_prompt == "be formal"

    def test_from_dict_state_vocabulary_as_strings(self):
        data = _minimal_schema_dict(state_vocabulary=[1, 2, "Three"])
        schema = SimulationSchema.from_dict(data)
        assert schema.state_vocabulary == ["1", "2", "Three"]


# ---------------------------------------------------------------------------
# Tests: to_dict round-trip
# ---------------------------------------------------------------------------


class TestToDict:
    def test_roundtrip_preserves_evaluation_dimensions(self):
        data = _minimal_schema_dict(evaluation_dimensions=["a", "b", "c"])
        schema = SimulationSchema.from_dict(data)
        exported = schema.to_dict()
        assert exported["evaluation_dimensions"] == ["a", "b", "c"]

    def test_roundtrip_preserves_actions(self):
        data = _minimal_schema_dict()
        schema = SimulationSchema.from_dict(data)
        exported = schema.to_dict()
        assert len(exported["actions"]) == 2
        assert exported["actions"][0]["name"] == "SUPPORT"
        assert exported["actions"][1]["is_terminal"] is True

    def test_roundtrip_empty_dimensions(self):
        data = _minimal_schema_dict()
        schema = SimulationSchema.from_dict(data)
        exported = schema.to_dict()
        assert exported["evaluation_dimensions"] == []


# ---------------------------------------------------------------------------
# Tests: action_names helper
# ---------------------------------------------------------------------------


class TestActionNames:
    def test_returns_names_in_order(self):
        data = _minimal_schema_dict(actions=[
            {"name": "ACT_A", "description": "a"},
            {"name": "ACT_B", "description": "b"},
            {"name": "ACT_C", "description": "c"},
        ])
        schema = SimulationSchema.from_dict(data)
        assert schema.action_names() == ["ACT_A", "ACT_B", "ACT_C"]


# ---------------------------------------------------------------------------
# Tests: get_cluster
# ---------------------------------------------------------------------------


class TestGetCluster:
    def test_found(self):
        data = _minimal_schema_dict()
        schema = SimulationSchema.from_dict(data)
        cluster = schema.get_cluster("formal")
        assert cluster is not None
        assert cluster.cluster_id == "formal"

    def test_not_found(self):
        data = _minimal_schema_dict()
        schema = SimulationSchema.from_dict(data)
        assert schema.get_cluster("nonexistent") is None


# ---------------------------------------------------------------------------
# Tests: _optional_float
# ---------------------------------------------------------------------------


class TestOptionalFloat:
    def test_none_returns_none(self):
        assert _optional_float(None) is None

    def test_int_value(self):
        assert _optional_float(100) == 100.0

    def test_float_value(self):
        assert _optional_float(3.14) == 3.14

    def test_string_number(self):
        assert _optional_float("42.5") == 42.5

    def test_invalid_string_returns_none(self):
        assert _optional_float("not a number") is None

    def test_empty_string_returns_none(self):
        assert _optional_float("") is None
