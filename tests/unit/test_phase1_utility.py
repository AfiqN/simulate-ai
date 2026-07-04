"""Unit tests for Phase 1 features: multi-dimensional utility, reasoning chain,
_coerce_float, _normalize_action, _utility_to_action, _normalize_state, and depth tiers."""

import pytest

from src.agent.agent import (
    Agent,
    _coerce_float,
    _normalize_action,
    _normalize_state,
    _terminal_or_first_action,
    _utility_to_action,
)
from src.agent.profile import AgentAttributes, AgentProfile, ResourceBalance
from src.schema.simulation_schema import (
    ActionDefinition,
    LinguisticCluster,
    ResourceModel,
    SimulationSchema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_schema(
    evaluation_dimensions: list[str] | None = None,
    actions: list[tuple[str, bool]] | None = None,
    resource_kind: str = "none",
) -> SimulationSchema:
    action_defs = [
        ActionDefinition(name=name, description=name.lower(), is_terminal=terminal)
        for name, terminal in (actions or [("INVEST", False), ("COUNTER", False), ("PASS", True)])
    ]
    return SimulationSchema(
        scenario_name="Test Scenario",
        scenario_description="A test scenario",
        verdict_label="Test Verdict",
        actions=action_defs,
        state_vocabulary=["Optimistic", "Cautious", "Skeptical", "Neutral"],
        resource_model=ResourceModel(kind=resource_kind),
        linguistic_clusters=[
            LinguisticCluster(cluster_id="formal", description="formal tone", style_prompt="Speak formally."),
        ],
        macro_context=["test context"],
        crisis_dimensions=["market_crash"],
        evaluation_dimensions=evaluation_dimensions or [],
    )


def _make_profile(resources: list[ResourceBalance] | None = None) -> AgentProfile:
    return AgentProfile(
        agent_id="agent_test",
        archetype="Test Analyst",
        linguistic_cluster_id="formal",
        attributes=AgentAttributes(
            rationality_index=0.7,
            aggressiveness=0.4,
            risk_tolerance=0.5,
        ),
        resources=resources or [],
        memory_vectors=["Prior observation one"],
        current_internal_state="Neutral",
    )


def _make_agent(schema: SimulationSchema | None = None, profile: AgentProfile | None = None) -> Agent:
    s = schema or _make_schema(evaluation_dimensions=["financial_return", "market_fit", "execution_risk"])
    p = profile or _make_profile()
    # Agent requires a client but we won't call LLM in unit tests
    return Agent(profile=p, client=None, schema=s)


# ---------------------------------------------------------------------------
# Tests: _coerce_float
# ---------------------------------------------------------------------------


class TestCoerceFloat:
    def test_int_value(self):
        assert _coerce_float(5, 0.0) == 5.0

    def test_float_value(self):
        assert _coerce_float(0.75, 0.0) == 0.75

    def test_negative_float(self):
        assert _coerce_float(-0.3, 0.0) == -0.3

    def test_string_number(self):
        assert _coerce_float("0.65", 0.0) == 0.65

    def test_string_negative(self):
        assert _coerce_float("-0.42", 0.0) == -0.42

    def test_percentage_string(self):
        assert _coerce_float("50%", 0.0) == 0.5

    def test_percentage_with_space(self):
        assert _coerce_float("75 %", 0.0) == pytest.approx(0.75)

    def test_currency_dollar(self):
        assert _coerce_float("$100", 0.0) == 100.0

    def test_currency_euro(self):
        assert _coerce_float("€42.5", 0.0) == 42.5

    def test_thousand_separator(self):
        assert _coerce_float("1,500", 0.0) == 1500.0

    def test_empty_string_returns_default(self):
        assert _coerce_float("", 99.0) == 99.0

    def test_none_returns_default(self):
        assert _coerce_float(None, -1.0) == -1.0

    def test_garbage_string_returns_default(self):
        assert _coerce_float("not a number", 0.5) == 0.5

    def test_list_returns_default(self):
        assert _coerce_float([1, 2, 3], 0.0) == 0.0

    def test_bool_treated_as_int(self):
        # bool is subclass of int in Python
        assert _coerce_float(True, 0.0) == 1.0
        assert _coerce_float(False, 0.0) == 0.0

    def test_whitespace_string(self):
        assert _coerce_float("  0.33  ", 0.0) == 0.33


# ---------------------------------------------------------------------------
# Tests: _normalize_action
# ---------------------------------------------------------------------------


class TestNormalizeAction:
    def setup_method(self):
        self.schema = _make_schema()

    def test_valid_action_returned(self):
        assert _normalize_action("INVEST", self.schema, 0.5, 0.4, 0.0) == "INVEST"

    def test_valid_action_case_insensitive(self):
        assert _normalize_action("invest", self.schema, 0.5, 0.4, 0.0) == "INVEST"

    def test_valid_action_with_whitespace(self):
        assert _normalize_action("  COUNTER  ", self.schema, 0.5, 0.4, 0.0) == "COUNTER"

    def test_invalid_action_falls_back_to_utility(self):
        # Invalid action + positive utility above threshold → first non-terminal
        result = _normalize_action("INVALID", self.schema, 0.5, 0.4, 0.0)
        assert result == "INVEST"

    def test_none_action_falls_back(self):
        result = _normalize_action(None, self.schema, 0.5, 0.4, 0.0)
        assert result == "INVEST"

    def test_numeric_action_falls_back(self):
        result = _normalize_action(42, self.schema, -0.5, 0.4, 0.0)
        assert result == "PASS"  # negative utility → terminal


# ---------------------------------------------------------------------------
# Tests: _utility_to_action
# ---------------------------------------------------------------------------


class TestUtilityToAction:
    def setup_method(self):
        self.schema = _make_schema()

    def test_positive_utility_returns_first_non_terminal(self):
        assert _utility_to_action(0.5, 0.4, 0.0, self.schema) == "INVEST"

    def test_very_negative_returns_terminal(self):
        assert _utility_to_action(-0.5, 0.4, 0.0, self.schema) == "PASS"

    def test_mildly_negative_but_above_threshold_returns_non_terminal(self):
        # utility = -0.05, threshold = -0.1 → utility > threshold so first non-terminal
        # Wait: threshold is 0.0 by default. utility = -0.05 < threshold but > -0.1
        # So it goes to the middle branch (aggressiveness check)
        result = _utility_to_action(-0.05, 0.4, 0.0, self.schema)
        # -0.05 is NOT > threshold (0.0) and NOT < -0.1, so falls to aggressiveness branch
        # aggressiveness 0.4 <= 0.6 → idx=0 → INVEST
        assert result == "INVEST"

    def test_high_aggressiveness_picks_second_non_terminal(self):
        # utility in middle zone, aggressiveness > 0.6 → idx=1 → COUNTER
        result = _utility_to_action(-0.05, 0.8, 0.0, self.schema)
        assert result == "COUNTER"

    def test_no_terminal_actions_returns_non_terminal(self):
        schema = _make_schema(actions=[("ACT_A", False), ("ACT_B", False)])
        # Very negative utility but no terminal action available
        result = _utility_to_action(-0.9, 0.4, 0.0, schema)
        # No terminal → fall to aggressiveness branch
        assert result in ("ACT_A", "ACT_B")


# ---------------------------------------------------------------------------
# Tests: _normalize_state
# ---------------------------------------------------------------------------


class TestNormalizeState:
    def setup_method(self):
        self.vocab = ["Optimistic", "Cautious", "Skeptical", "Neutral"]

    def test_exact_match(self):
        assert _normalize_state("Optimistic", self.vocab, "Neutral") == "Optimistic"

    def test_case_insensitive_match(self):
        assert _normalize_state("SKEPTICAL", self.vocab, "Neutral") == "Skeptical"

    def test_lowercase_match(self):
        assert _normalize_state("cautious", self.vocab, "Neutral") == "Cautious"

    def test_unknown_state_title_cased(self):
        assert _normalize_state("angry", self.vocab, "Neutral") == "Angry"

    def test_none_returns_fallback(self):
        assert _normalize_state(None, self.vocab, "Neutral") == "Neutral"

    def test_empty_string_returns_fallback(self):
        assert _normalize_state("", self.vocab, "Neutral") == "Neutral"

    def test_non_string_returns_fallback(self):
        assert _normalize_state(123, self.vocab, "Neutral") == "Neutral"

    def test_whitespace_only_returns_fallback(self):
        assert _normalize_state("   ", self.vocab, "Neutral") == "Neutral"


# ---------------------------------------------------------------------------
# Tests: _terminal_or_first_action
# ---------------------------------------------------------------------------


class TestTerminalOrFirstAction:
    def test_returns_terminal_when_available(self):
        schema = _make_schema(actions=[("INVEST", False), ("REJECT", True)])
        assert _terminal_or_first_action(schema) == "REJECT"

    def test_returns_first_action_when_no_terminal(self):
        schema = _make_schema(actions=[("ACT_A", False), ("ACT_B", False)])
        assert _terminal_or_first_action(schema) == "ACT_A"

    def test_empty_actions_returns_no_action(self):
        schema = _make_schema(actions=[])
        schema.actions = []
        assert _terminal_or_first_action(schema) == "NO_ACTION"


# ---------------------------------------------------------------------------
# Tests: Multi-dimensional utility parsing (_evaluate_utility_and_transition)
# ---------------------------------------------------------------------------


class TestEvaluateUtilityMultiDim:
    def setup_method(self):
        self.agent = _make_agent()

    def test_parses_dimensions_correctly(self):
        parsed = {
            "utility_calculation": {
                "dimensions": {
                    "financial_return": {"score": 0.8, "reasoning": "Strong returns"},
                    "market_fit": {"score": 0.5, "reasoning": "Decent fit"},
                    "execution_risk": {"score": -0.3, "reasoning": "Some risk"},
                },
                "aggregate_utility": 0.33,
            },
            "decision": "INVEST",
            "emotional_state": "Optimistic",
            "new_memory_to_store": "Looks promising",
        }
        self.agent._evaluate_utility_and_transition(parsed)

        assert parsed["utility_dimensions"] == {
            "financial_return": 0.8,
            "market_fit": 0.5,
            "execution_risk": -0.3,
        }
        assert len(parsed["reasoning_chain"]) == 3
        assert parsed["reasoning_chain"][0] == {
            "dimension": "financial_return",
            "score": 0.8,
            "reasoning": "Strong returns",
        }
        assert parsed["utility"] == 0.33
        assert parsed["action_decision"] == "INVEST"
        assert parsed["new_internal_state"] == "Optimistic"

    def test_computes_aggregate_as_mean_when_not_provided(self):
        parsed = {
            "utility_calculation": {
                "dimensions": {
                    "financial_return": {"score": 0.6, "reasoning": ""},
                    "market_fit": {"score": 0.4, "reasoning": ""},
                },
            },
            "decision": "INVEST",
            "emotional_state": "Neutral",
        }
        self.agent._evaluate_utility_and_transition(parsed)
        # Mean of 0.6 and 0.4 = 0.5
        assert parsed["utility"] == pytest.approx(0.5)

    def test_bare_number_dimensions(self):
        """When LLM returns dimension as bare number instead of {score, reasoning}."""
        parsed = {
            "utility_calculation": {
                "dimensions": {
                    "financial_return": 0.7,
                    "market_fit": -0.2,
                },
            },
            "decision": "COUNTER",
            "emotional_state": "Cautious",
        }
        self.agent._evaluate_utility_and_transition(parsed)

        assert parsed["utility_dimensions"] == {"financial_return": 0.7, "market_fit": -0.2}
        assert parsed["reasoning_chain"][0]["reasoning"] == ""
        assert parsed["reasoning_chain"][0]["score"] == 0.7

    def test_string_scores_in_dimensions(self):
        """LLM returns scores as strings."""
        parsed = {
            "utility_calculation": {
                "dimensions": {
                    "financial_return": {"score": "0.65", "reasoning": "Good"},
                },
            },
            "decision": "INVEST",
            "emotional_state": "Optimistic",
        }
        self.agent._evaluate_utility_and_transition(parsed)
        assert parsed["utility_dimensions"]["financial_return"] == 0.65

    def test_empty_dimensions_triggers_fallback(self):
        """Empty dimensions dict → fall back to flat utility."""
        parsed = {
            "utility_calculation": {
                "dimensions": {},
                "perceived_gains": 0.7,
                "perceived_costs": 0.2,
                "final_utility": 0.5,
            },
            "decision": "INVEST",
            "emotional_state": "Optimistic",
        }
        self.agent._evaluate_utility_and_transition(parsed)
        assert parsed["utility"] == 0.5
        assert parsed["utility_dimensions"] == {}
        assert parsed["reasoning_chain"] == []

    def test_no_utility_calculation_key(self):
        """Missing utility_calculation entirely → uses defaults."""
        parsed = {
            "decision": "PASS",
            "emotional_state": "Skeptical",
        }
        self.agent._evaluate_utility_and_transition(parsed)
        assert parsed["utility"] == 0.0  # gains(0) - costs(0)
        assert parsed["utility_dimensions"] == {}
        assert parsed["reasoning_chain"] == []

    def test_non_dict_utility_calculation(self):
        """utility_calculation is a string or number instead of dict."""
        parsed = {
            "utility_calculation": "broken",
            "decision": "INVEST",
            "emotional_state": "Neutral",
        }
        self.agent._evaluate_utility_and_transition(parsed)
        assert parsed["utility"] == 0.0
        assert parsed["utility_dimensions"] == {}


# ---------------------------------------------------------------------------
# Tests: Flat utility fallback (backward compatibility)
# ---------------------------------------------------------------------------


class TestEvaluateUtilityFlat:
    def setup_method(self):
        # Schema without evaluation_dimensions triggers flat utility in prompting,
        # but _evaluate_utility_and_transition looks at the response structure, not the schema
        self.agent = _make_agent()

    def test_gains_minus_costs(self):
        parsed = {
            "utility_calculation": {
                "perceived_gains": 0.8,
                "perceived_costs": 0.3,
                "final_utility": 0.5,
            },
            "decision": "INVEST",
            "emotional_state": "Optimistic",
        }
        self.agent._evaluate_utility_and_transition(parsed)
        assert parsed["utility"] == 0.5

    def test_uses_computed_fallback_when_final_missing(self):
        parsed = {
            "utility_calculation": {
                "perceived_gains": 0.7,
                "perceived_costs": 0.4,
            },
            "decision": "COUNTER",
            "emotional_state": "Cautious",
        }
        self.agent._evaluate_utility_and_transition(parsed)
        # gains - costs = 0.3
        assert parsed["utility"] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Tests: Memory management in _evaluate_utility_and_transition
# ---------------------------------------------------------------------------


class TestMemoryManagement:
    def test_appends_new_memory(self):
        agent = _make_agent()
        initial_count = len(agent.profile.memory_vectors)
        parsed = {
            "utility_calculation": {"perceived_gains": 0.5, "perceived_costs": 0.2, "final_utility": 0.3},
            "decision": "INVEST",
            "emotional_state": "Neutral",
            "new_memory_to_store": "A new insight",
        }
        agent._evaluate_utility_and_transition(parsed)
        assert "A new insight" in agent.profile.memory_vectors
        assert len(agent.profile.memory_vectors) == initial_count + 1

    def test_does_not_duplicate_memory(self):
        agent = _make_agent()
        agent.profile.memory_vectors = ["Already known"]
        parsed = {
            "utility_calculation": {"perceived_gains": 0.5, "perceived_costs": 0.2, "final_utility": 0.3},
            "decision": "INVEST",
            "emotional_state": "Neutral",
            "new_memory_to_store": "Already known",
        }
        agent._evaluate_utility_and_transition(parsed)
        assert agent.profile.memory_vectors.count("Already known") == 1

    def test_evicts_oldest_when_over_10(self):
        agent = _make_agent()
        agent.profile.memory_vectors = [f"memory_{i}" for i in range(10)]
        parsed = {
            "utility_calculation": {"perceived_gains": 0.5, "perceived_costs": 0.2, "final_utility": 0.3},
            "decision": "INVEST",
            "emotional_state": "Neutral",
            "new_memory_to_store": "memory_new",
        }
        agent._evaluate_utility_and_transition(parsed)
        assert len(agent.profile.memory_vectors) == 10
        assert "memory_0" not in agent.profile.memory_vectors
        assert "memory_new" in agent.profile.memory_vectors


# ---------------------------------------------------------------------------
# Tests: Depth tiers (build_system_prompt)
# ---------------------------------------------------------------------------


class TestDepthTiers:
    def setup_method(self):
        self.agent = _make_agent()

    def test_standard_no_depth_section(self):
        prompt = self.agent.build_system_prompt(depth="standard")
        assert "DEPTH: QUICK" not in prompt
        assert "DEPTH: DEEP ANALYSIS" not in prompt

    def test_quick_adds_quick_section(self):
        prompt = self.agent.build_system_prompt(depth="quick")
        assert "DEPTH: QUICK" in prompt
        assert "Be concise" in prompt
        assert "DEPTH: DEEP ANALYSIS" not in prompt

    def test_deep_adds_deep_section(self):
        prompt = self.agent.build_system_prompt(depth="deep")
        assert "DEPTH: DEEP ANALYSIS" in prompt
        assert "Think step by step" in prompt
        assert "DEPTH: QUICK" not in prompt

    def test_prompt_contains_evaluation_dimensions(self):
        prompt = self.agent.build_system_prompt()
        assert "financial_return" in prompt
        assert "market_fit" in prompt
        assert "execution_risk" in prompt

    def test_prompt_without_dimensions_uses_flat_format(self):
        schema = _make_schema(evaluation_dimensions=[])
        agent = _make_agent(schema=schema)
        prompt = agent.build_system_prompt()
        assert "perceived_gains" in prompt
        assert "perceived_costs" in prompt
        assert "dimensions" not in prompt.split("DECISION LOGIC")[0] if "DECISION LOGIC" in prompt else True


# ---------------------------------------------------------------------------
# Tests: Resource deductions
# ---------------------------------------------------------------------------


class TestResourceDeductions:
    def test_no_resources_schema_none(self):
        agent = _make_agent()
        parsed = {
            "utility_calculation": {"perceived_gains": 0.6, "perceived_costs": 0.1, "final_utility": 0.5},
            "decision": "INVEST",
            "emotional_state": "Optimistic",
            "resource_deductions": {"Budget": 100},
        }
        agent._evaluate_utility_and_transition(parsed)
        assert parsed["resource_deductions"] == {}

    def test_deduction_applied_to_matching_resource(self):
        schema = _make_schema(
            resource_kind="single",
            actions=[("INVEST", False), ("PASS", True)],
        )
        schema.actions[0].affects_resource = "Budget"
        profile = _make_profile(resources=[ResourceBalance(name="Budget", current=1000.0, maximum=2000.0)])
        agent = _make_agent(schema=schema, profile=profile)

        parsed = {
            "utility_calculation": {"perceived_gains": 0.6, "perceived_costs": 0.1, "final_utility": 0.5},
            "decision": "INVEST",
            "emotional_state": "Optimistic",
            "resource_deductions": {"Budget": 200},
        }
        agent._evaluate_utility_and_transition(parsed)
        assert parsed["resource_deductions"]["Budget"] == 200.0
        assert agent.profile.resources[0].current == 800.0

    def test_deduction_capped_at_balance(self):
        schema = _make_schema(
            resource_kind="single",
            actions=[("INVEST", False), ("PASS", True)],
        )
        schema.actions[0].affects_resource = "Budget"
        profile = _make_profile(resources=[ResourceBalance(name="Budget", current=50.0, maximum=1000.0)])
        agent = _make_agent(schema=schema, profile=profile)

        parsed = {
            "utility_calculation": {"perceived_gains": 0.6, "perceived_costs": 0.1, "final_utility": 0.5},
            "decision": "INVEST",
            "emotional_state": "Optimistic",
            "resource_deductions": {"Budget": 200},
        }
        agent._evaluate_utility_and_transition(parsed)
        assert parsed["resource_deductions"]["Budget"] == 50.0
        assert agent.profile.resources[0].current == 0.0
