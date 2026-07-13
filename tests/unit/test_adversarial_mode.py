"""End-to-end tests for adversarial debate mode."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.adversary import ArgumentClaim, AdversarialRoundResult
from src.cli.simulation import _run_adversarial_debate


# --- Helpers ---

class _FakeSchema:
    def __init__(self):
        self.scenario_name = "Test Scenario"
        self.scenario_description = "A test scenario"
        self.verdict_label = "Viability"
        self.evaluation_dimensions = ["impact", "feasibility"]
        self.state_vocabulary = ["optimistic", "skeptical"]
        self.actions = [_FakeAction("SUPPORT", False), _FakeAction("REJECT", True)]

    def action_names(self):
        return [a.name for a in self.actions]


class _FakeAction:
    def __init__(self, name, is_terminal):
        self.name = name
        self.description = f"Action: {name}"
        self.is_terminal = is_terminal


class _FakeAttributes:
    def __init__(self):
        self.aggressiveness = 0.5
        self.risk_tolerance = 0.5
        self.analytical_rigor = 0.7
        self.openness_to_change = 0.5
        self.ideological_commitment = 0.5


class _FakeProfile:
    def __init__(self, agent_id, archetype):
        self.agent_id = agent_id
        self.archetype = archetype
        self.backstory = "Test backstory"
        self.current_internal_state = "neutral"
        self.attributes = _FakeAttributes()


class _FakeAgent:
    def __init__(self, agent_id, archetype):
        self.profile = _FakeProfile(agent_id, archetype)
        self.schema = _FakeSchema()

    async def extract_claims(self, stimulus, r1_decision):
        return [
            {"claim": f"Claim by {self.profile.archetype}", "evidence": "Some evidence"},
            {"claim": f"Second claim by {self.profile.archetype}", "evidence": "More evidence"},
        ]

    async def attack_claims(self, target_claims, target_archetype, stimulus):
        return [
            {"flaw": "This is flawed because...", "counter_evidence": "Counter proof", "severity": "serious"}
            for _ in target_claims
        ]

    async def defend_claim(self, claim, attack_text, severity):
        # First claim rebuts, second concedes
        if "Second" in claim:
            return {"response": "concede", "argument": "", "amended_claim": ""}
        return {"response": "rebut", "argument": "My defense argument", "amended_claim": ""}


def _make_agents(n=3):
    archetypes = ["Innovator", "Skeptic", "Pragmatist", "Regulator", "Consumer"]
    return [_FakeAgent(f"SIM-AGT-{i+1:03d}", archetypes[i % len(archetypes)]) for i in range(n)]


def _make_decisions_r1(agents):
    actions = ["SUPPORT", "REJECT", "SUPPORT", "REJECT", "SUPPORT"]
    return [
        {
            "id": a.profile.agent_id,
            "archetype": a.profile.archetype,
            "action": actions[i % len(actions)],
            "utility": 0.6 - (i * 0.1),
            "utility_dimensions": {"impact": 0.7, "feasibility": 0.5},
            "reasoning_chain": [],
            "monologue": "test",
            "statement": f"Statement from {a.profile.archetype}",
            "new_state": "neutral",
            "duration": 1.0,
        }
        for i, a in enumerate(agents)
    ]


def _make_adversary_map(agents, decisions):
    """Simple round-robin adversary pairing."""
    m = {}
    n = len(agents)
    for i, a in enumerate(agents):
        opponent_idx = (i + 1) % n
        m[a.profile.agent_id] = decisions[opponent_idx]
    return m


# --- Tests ---

class TestArgumentClaim:
    def test_survived_standing(self):
        c = ArgumentClaim(agent_id="A", archetype="X", claim_text="test", evidence="e", status="standing")
        assert c.survived is True

    def test_survived_amended(self):
        c = ArgumentClaim(agent_id="A", archetype="X", claim_text="test", evidence="e", status="amended")
        assert c.survived is True

    def test_defeated(self):
        c = ArgumentClaim(agent_id="A", archetype="X", claim_text="test", evidence="e", status="defeated")
        assert c.survived is False


class TestAdversarialRoundResult:
    def test_survival_rate(self):
        claims = [
            ArgumentClaim(agent_id="A", archetype="X", claim_text="a", evidence="e", status="standing"),
            ArgumentClaim(agent_id="A", archetype="X", claim_text="b", evidence="e", status="defeated"),
            ArgumentClaim(agent_id="B", archetype="Y", claim_text="c", evidence="e", status="amended"),
            ArgumentClaim(agent_id="B", archetype="Y", claim_text="d", evidence="e", status="defeated"),
        ]
        result = AdversarialRoundResult(claims=claims)
        assert result.survival_rate == 0.5
        assert len(result.surviving_claims) == 2
        assert len(result.defeated_claims) == 2

    def test_empty_claims(self):
        result = AdversarialRoundResult(claims=[])
        assert result.survival_rate == 0.0
        assert result.surviving_claims == []
        assert result.defeated_claims == []

    def test_key_defeats_format(self):
        claims = [
            ArgumentClaim(
                agent_id="A", archetype="Skeptic", claim_text="This won't work",
                evidence="e", status="defeated", attack_text="Because it clearly contradicts X"
            ),
        ]
        result = AdversarialRoundResult(claims=claims)
        defeats = result.key_defeats
        assert len(defeats) == 1
        assert "Skeptic" in defeats[0]
        assert "This won't work" in defeats[0]

    def test_to_transcript(self):
        claims = [
            ArgumentClaim(
                agent_id="A", archetype="Innovator", claim_text="This is viable",
                evidence="e", status="standing", attack_text="Maybe not", defense_text="Yes it is"
            ),
            ArgumentClaim(
                agent_id="B", archetype="Skeptic", claim_text="Costs too high",
                evidence="e", status="defeated", attack_text="No data supports this"
            ),
        ]
        result = AdversarialRoundResult(claims=claims)
        transcript = result.to_transcript()
        assert "ADVERSARIAL DEBATE RESULTS" in transcript
        assert "50%" in transcript
        assert "SURVIVING CLAIMS" in transcript
        assert "DEFEATED CLAIMS" in transcript
        assert "Innovator" in transcript
        assert "Skeptic" in transcript


class TestRunAdversarialDebate:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        agents = _make_agents(3)
        decisions_r1 = _make_decisions_r1(agents)
        adversary_map = _make_adversary_map(agents, decisions_r1)
        semaphore = asyncio.Semaphore(5)

        events = []

        decisions_r2, adversarial_result = await _run_adversarial_debate(
            agents=agents,
            decisions_r1=decisions_r1,
            stimulus="Test stimulus for adversarial debate",
            adversary_map=adversary_map,
            semaphore=semaphore,
            depth="standard",
            headless=True,
            progress_callback=lambda msg: None,
            event_callback=lambda e: events.append(e),
        )

        # Verify structure
        assert len(decisions_r2) == 3
        assert isinstance(adversarial_result, AdversarialRoundResult)
        assert len(adversarial_result.claims) > 0

        # Verify decisions have required fields
        for d in decisions_r2:
            assert "id" in d
            assert "archetype" in d
            assert "action" in d
            assert "utility" in d
            assert "statement" in d

        # Verify events were emitted
        event_types = [e["type"] for e in events]
        assert "adversarial_claims" in event_types
        assert "adversarial_result" in event_types

    @pytest.mark.asyncio
    async def test_utility_penalized_on_defeat(self):
        agents = _make_agents(2)
        decisions_r1 = _make_decisions_r1(agents)
        adversary_map = _make_adversary_map(agents, decisions_r1)
        semaphore = asyncio.Semaphore(5)

        decisions_r2, result = await _run_adversarial_debate(
            agents=agents,
            decisions_r1=decisions_r1,
            stimulus="Test",
            adversary_map=adversary_map,
            semaphore=semaphore,
            depth="standard",
            headless=True,
            progress_callback=None,
            event_callback=None,
        )

        # If any claims are defeated, utility should be lower than original
        for i, d in enumerate(decisions_r2):
            original_utility = decisions_r1[i]["utility"]
            # Utility should be <= original (survival_factor <= 1)
            assert d["utility"] <= original_utility + 0.001  # floating point tolerance

    @pytest.mark.asyncio
    async def test_survival_rate_in_range(self):
        agents = _make_agents(4)
        decisions_r1 = _make_decisions_r1(agents)
        adversary_map = _make_adversary_map(agents, decisions_r1)
        semaphore = asyncio.Semaphore(5)

        _, result = await _run_adversarial_debate(
            agents=agents,
            decisions_r1=decisions_r1,
            stimulus="Test scenario",
            adversary_map=adversary_map,
            semaphore=semaphore,
            depth="standard",
            headless=True,
            progress_callback=None,
            event_callback=None,
        )

        assert 0.0 <= result.survival_rate <= 1.0


class TestSimulationRequestModel:
    def test_mode_field_default(self):
        from src.api.models import SimulationRequest
        req = SimulationRequest(stimulus="test scenario")
        assert req.mode == "collaborative"

    def test_mode_field_adversarial(self):
        from src.api.models import SimulationRequest
        req = SimulationRequest(stimulus="test scenario", mode="adversarial")
        assert req.mode == "adversarial"

    def test_mode_field_invalid(self):
        from src.api.models import SimulationRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SimulationRequest(stimulus="test", mode="invalid")
