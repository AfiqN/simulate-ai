"""Tests for src/api/models.py."""

import pytest
from pydantic import ValidationError

from src.api.models import SimulationRequest, SimulationStatus, RunSummary, RunListResponse


# ---------------------------------------------------------------------------
# Tests: SimulationRequest defaults
# ---------------------------------------------------------------------------

def test_simulation_request_defaults():
    req = SimulationRequest(stimulus="Should we ban single-use plastics?")
    assert req.agent_count == 5
    assert req.concurrency == 2
    assert req.model is None
    assert req.provider is None
    assert req.crisis_override is None


def test_simulation_request_accepts_valid_stimulus():
    req = SimulationRequest(stimulus="A policy debate about universal basic income.")
    assert req.stimulus == "A policy debate about universal basic income."


def test_simulation_request_accepts_all_fields():
    req = SimulationRequest(
        stimulus="Evaluate this startup pitch.",
        agent_count=10,
        concurrency=4,
        model="gemini-2.0-flash",
        provider="gemini",
        crisis_override="Sudden regulatory freeze.",
    )
    assert req.agent_count == 10
    assert req.concurrency == 4
    assert req.model == "gemini-2.0-flash"
    assert req.provider == "gemini"
    assert req.crisis_override == "Sudden regulatory freeze."


# ---------------------------------------------------------------------------
# Tests: SimulationRequest stimulus validation
# ---------------------------------------------------------------------------

def test_simulation_request_empty_stimulus_raises():
    with pytest.raises(ValidationError):
        SimulationRequest(stimulus="")


def test_simulation_request_missing_stimulus_raises():
    with pytest.raises(ValidationError):
        SimulationRequest()


# ---------------------------------------------------------------------------
# Tests: SimulationRequest agent_count bounds
# ---------------------------------------------------------------------------

def test_simulation_request_agent_count_minimum():
    req = SimulationRequest(stimulus="Test", agent_count=1)
    assert req.agent_count == 1


def test_simulation_request_agent_count_maximum():
    req = SimulationRequest(stimulus="Test", agent_count=20)
    assert req.agent_count == 20


def test_simulation_request_agent_count_below_minimum_raises():
    with pytest.raises(ValidationError):
        SimulationRequest(stimulus="Test", agent_count=0)


def test_simulation_request_agent_count_above_maximum_raises():
    with pytest.raises(ValidationError):
        SimulationRequest(stimulus="Test", agent_count=21)


def test_simulation_request_agent_count_negative_raises():
    with pytest.raises(ValidationError):
        SimulationRequest(stimulus="Test", agent_count=-1)


# ---------------------------------------------------------------------------
# Tests: SimulationRequest concurrency bounds
# ---------------------------------------------------------------------------

def test_simulation_request_concurrency_minimum():
    req = SimulationRequest(stimulus="Test", concurrency=1)
    assert req.concurrency == 1


def test_simulation_request_concurrency_maximum():
    req = SimulationRequest(stimulus="Test", concurrency=5)
    assert req.concurrency == 5


def test_simulation_request_concurrency_below_minimum_raises():
    with pytest.raises(ValidationError):
        SimulationRequest(stimulus="Test", concurrency=0)


def test_simulation_request_concurrency_above_maximum_raises():
    with pytest.raises(ValidationError):
        SimulationRequest(stimulus="Test", concurrency=6)


# ---------------------------------------------------------------------------
# Tests: SimulationStatus
# ---------------------------------------------------------------------------

def test_simulation_status_required_fields():
    s = SimulationStatus(id="run-001", status="queued")
    assert s.id == "run-001"
    assert s.status == "queued"


def test_simulation_status_optional_fields_default_none():
    s = SimulationStatus(id="run-001", status="running")
    assert s.scenario_name is None
    assert s.verdict is None
    assert s.elapsed_s is None
    assert s.error is None
    assert s.result is None


def test_simulation_status_accepts_all_fields():
    s = SimulationStatus(
        id="run-002",
        status="completed",
        scenario_name="Fintech Pitch",
        verdict="ADOPTED",
        elapsed_s=18.7,
        error=None,
        result={"valence": 0.6},
    )
    assert s.scenario_name == "Fintech Pitch"
    assert s.verdict == "ADOPTED"
    assert s.elapsed_s == pytest.approx(18.7)
    assert s.result == {"valence": 0.6}


def test_simulation_status_missing_id_raises():
    with pytest.raises(ValidationError):
        SimulationStatus(status="queued")


def test_simulation_status_missing_status_raises():
    with pytest.raises(ValidationError):
        SimulationStatus(id="run-001")


# ---------------------------------------------------------------------------
# Tests: RunSummary
# ---------------------------------------------------------------------------

def test_run_summary_required_fields():
    r = RunSummary(
        id="run-003",
        scenario_name="Healthcare Policy",
        status="completed",
        created_at="2026-06-26T10:00:00",
    )
    assert r.id == "run-003"
    assert r.scenario_name == "Healthcare Policy"
    assert r.status == "completed"
    assert r.created_at == "2026-06-26T10:00:00"


def test_run_summary_optional_fields_default_none():
    r = RunSummary(
        id="run-004",
        scenario_name="X",
        status="queued",
        created_at="2026-06-26T10:00:00",
    )
    assert r.verdict is None
    assert r.agent_count is None
    assert r.elapsed_s is None


def test_run_summary_missing_required_field_raises():
    with pytest.raises(ValidationError):
        RunSummary(id="run-005", status="queued", created_at="2026-06-26T10:00:00")
        # scenario_name is missing


# ---------------------------------------------------------------------------
# Tests: RunListResponse
# ---------------------------------------------------------------------------

def test_run_list_response_structure():
    summaries = [
        RunSummary(
            id=f"run-{i:03d}",
            scenario_name="Test",
            status="completed",
            created_at="2026-06-26T10:00:00",
        )
        for i in range(3)
    ]
    resp = RunListResponse(runs=summaries, total=3)
    assert resp.total == 3
    assert len(resp.runs) == 3


def test_run_list_response_empty_runs():
    resp = RunListResponse(runs=[], total=0)
    assert resp.runs == []
    assert resp.total == 0


def test_run_list_response_missing_total_raises():
    with pytest.raises(ValidationError):
        RunListResponse(runs=[])
