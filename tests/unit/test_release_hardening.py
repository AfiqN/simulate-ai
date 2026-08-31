"""Regression tests for Portfolio v1 security and reliability boundaries."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from src.agent.profile import AgentAttributes, AgentProfile
from src.api.maintenance import _safe_run_directory
from src.api.security import generate_token, hash_token, require_read_access, token_matches
from src.api.webhooks import validate_webhook_url
from src.api.websocket import SimulationEventBus
from src.export.serialization import load_canonical_result, serialize_simulation_result
from src.persistence.db import count_recent_usage, init_db, record_usage


def _request(*, bearer: str | None = None, share: str | None = None) -> Request:
    headers = []
    if bearer:
        headers.append((b"authorization", f"Bearer {bearer}".encode()))
    query = f"share={share}".encode() if share else b""
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": query,
        "headers": headers,
        "client": ("127.0.0.1", 1234),
    })


def test_capability_token_is_hashed_and_constant_contract():
    token = generate_token()
    assert token not in hash_token(token)
    assert token_matches(token, hash_token(token))
    assert not token_matches(token + "x", hash_token(token))


def test_owner_and_share_read_access():
    owner = generate_token()
    share = generate_token()
    row = {
        "owner_token_hash": hash_token(owner),
        "share_enabled": 1,
        "share_token_hash": hash_token(share),
    }
    assert require_read_access(_request(bearer=owner), row) == "owner"
    assert require_read_access(_request(share=share), row) == "shared"
    with pytest.raises(Exception):
        require_read_access(_request(share="wrong"), row)


def test_event_bus_replays_only_events_after_sequence():
    bus = SimulationEventBus(history_size=4)
    first = bus.emit("run", {"type": "stage", "stage": "schema"})
    second = bus.emit("run", {"type": "stage", "stage": "swarm"})
    queue = bus.subscribe("run", since=first["seq"])
    assert queue.get_nowait() == second
    assert bus.latest_sequence("run") == 2
    bus.clear("run")
    assert bus.latest_sequence("run") == 0


def test_load_canonical_result_prefers_result_json(tmp_path):
    (tmp_path / "result.json").write_text('{"version":"1.0","id":"new"}', encoding="utf-8")
    (tmp_path / "metrics.json").write_text('{"id":"old"}', encoding="utf-8")
    assert load_canonical_result(tmp_path)["id"] == "new"


def test_load_canonical_result_marks_legacy(tmp_path):
    (tmp_path / "metrics.json").write_text('{"id":"old"}', encoding="utf-8")
    assert load_canonical_result(tmp_path)["version"] == "legacy"


def test_canonical_serializer_preserves_round4_and_never_accepts_api_key():
    schema = SimpleNamespace(scenario_name="Scenario", to_dict=lambda: {"scenario_name": "Scenario"})
    profile = AgentProfile(
        agent_id="A1", archetype="operator", linguistic_cluster_id="ops",
        attributes=AgentAttributes(rationality_index=0.7, aggressiveness=0.2, risk_tolerance=0.3),
        decision_framework="evidence", knowledge_base="operations", constraints=[],
        influence_weight=1.0, backstory="", current_internal_state="Neutral",
    )
    decision = {"id": "A1", "action": "ADOPT", "utility": 0.5, "new_state": "Ready"}
    payload = serialize_simulation_result(
        {"schema": schema, "profiles": [profile], "decisions_r4": [decision], "report_md": "ok"},
        run_id="run", stimulus="proposal", config={"provider": "openai"},
    )
    assert payload["rounds"]["r4"][0]["action"] == "ADOPT"
    assert "api_key" not in str(payload).lower()


@pytest.mark.asyncio
async def test_usage_counter_is_durable_in_sqlite(tmp_path):
    db_path = tmp_path / "usage.db"
    db = await init_db(db_path)
    await record_usage(db, "identity", 100.0)
    await db.close()
    reopened = await init_db(db_path)
    assert await count_recent_usage(reopened, "identity", 99.0) == 1
    await reopened.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "http://example.com/hook",
    "https://localhost/hook",
    "https://127.0.0.1/hook",
    "https://169.254.169.254/latest/meta-data",
    "https://user:pass@example.com/hook",
])
async def test_webhook_rejects_unsafe_targets(url):
    with pytest.raises(ValueError):
        await validate_webhook_url(url)


def test_retention_path_rejects_outside_root_and_symlink(tmp_path, monkeypatch):
    import src.api.maintenance as maintenance

    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setattr(maintenance, "RUNS_DIR", root)
    assert _safe_run_directory(str(tmp_path / "outside")) is None
    target = root / "target"
    target.mkdir()
    link = root / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks unavailable on this platform")
    assert _safe_run_directory(str(link)) is None
