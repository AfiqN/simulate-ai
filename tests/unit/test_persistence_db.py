"""Tests for src/persistence/db.py."""

import pytest
import pytest_asyncio

from src.persistence.db import init_db, insert_run, update_run, get_run, list_runs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _insert(db, run_id, scenario_name="Test Scenario", status="queued",
                  agent_count=5, concurrency=2, provider="gemini",
                  model="gemini-2.0-flash", created_at="2026-06-26T10:00:00"):
    await insert_run(
        db,
        run_id=run_id,
        scenario_name=scenario_name,
        status=status,
        agent_count=agent_count,
        concurrency=concurrency,
        provider=provider,
        model=model,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# Tests: init_db
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_init_db_creates_file(tmp_path):
    db_path = tmp_path / "simulate.db"
    assert not db_path.exists()
    db = await init_db(db_path)
    await db.close()
    assert db_path.exists()


@pytest.mark.asyncio
async def test_init_db_creates_runs_table(tmp_path):
    db_path = tmp_path / "simulate.db"
    db = await init_db(db_path)
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='runs'"
    )
    row = await cursor.fetchone()
    await db.close()
    assert row is not None
    assert row[0] == "runs"


@pytest.mark.asyncio
async def test_init_db_is_idempotent(tmp_path):
    """Calling init_db twice on the same path should not raise."""
    db_path = tmp_path / "simulate.db"
    db1 = await init_db(db_path)
    await db1.close()
    db2 = await init_db(db_path)
    await db2.close()


@pytest.mark.asyncio
async def test_init_db_creates_parent_dirs(tmp_path):
    db_path = tmp_path / "nested" / "deep" / "simulate.db"
    db = await init_db(db_path)
    await db.close()
    assert db_path.exists()


# ---------------------------------------------------------------------------
# Tests: insert_run + get_run round-trip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insert_and_get_run(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-001", scenario_name="Fintech Pitch")
    row = await get_run(db, "run-001")
    await db.close()
    assert row is not None
    assert row["id"] == "run-001"
    assert row["scenario_name"] == "Fintech Pitch"


@pytest.mark.asyncio
async def test_insert_run_default_status(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-002")
    row = await get_run(db, "run-002")
    await db.close()
    assert row["status"] == "queued"


@pytest.mark.asyncio
async def test_insert_run_stores_agent_count(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-003", agent_count=8)
    row = await get_run(db, "run-003")
    await db.close()
    assert row["agent_count"] == 8


@pytest.mark.asyncio
async def test_insert_run_stores_provider_and_model(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-004", provider="ollama", model="qwen2.5:3b")
    row = await get_run(db, "run-004")
    await db.close()
    assert row["provider"] == "ollama"
    assert row["model"] == "qwen2.5:3b"


@pytest.mark.asyncio
async def test_get_run_returns_none_for_missing_id(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    row = await get_run(db, "does-not-exist")
    await db.close()
    assert row is None


@pytest.mark.asyncio
async def test_insert_run_verdict_initially_null(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-005")
    row = await get_run(db, "run-005")
    await db.close()
    assert row["verdict"] is None


# ---------------------------------------------------------------------------
# Tests: update_run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_run_status(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-010")
    await update_run(db, "run-010", status="running")
    row = await get_run(db, "run-010")
    await db.close()
    assert row["status"] == "running"


@pytest.mark.asyncio
async def test_update_run_verdict(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-011")
    await update_run(db, "run-011", verdict="CONTESTED")
    row = await get_run(db, "run-011")
    await db.close()
    assert row["verdict"] == "CONTESTED"


@pytest.mark.asyncio
async def test_update_run_elapsed_s(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-012")
    await update_run(db, "run-012", elapsed_s=42.5)
    row = await get_run(db, "run-012")
    await db.close()
    assert row["elapsed_s"] == pytest.approx(42.5)


@pytest.mark.asyncio
async def test_update_run_run_dir(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-013")
    await update_run(db, "run-013", run_dir="/some/path/to/run")
    row = await get_run(db, "run-013")
    await db.close()
    assert row["run_dir"] == "/some/path/to/run"


@pytest.mark.asyncio
async def test_update_run_error_message(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-014")
    await update_run(db, "run-014", error_message="LLM timed out")
    row = await get_run(db, "run-014")
    await db.close()
    assert row["error_message"] == "LLM timed out"


@pytest.mark.asyncio
async def test_update_run_multiple_fields(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-015")
    await update_run(db, "run-015", status="completed", verdict="ADOPTED", elapsed_s=18.3)
    row = await get_run(db, "run-015")
    await db.close()
    assert row["status"] == "completed"
    assert row["verdict"] == "ADOPTED"
    assert row["elapsed_s"] == pytest.approx(18.3)


@pytest.mark.asyncio
async def test_update_run_no_fields_is_noop(tmp_path):
    """Calling update_run with no kwargs should not raise and leave the row unchanged."""
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-016", status="queued")
    await update_run(db, "run-016")
    row = await get_run(db, "run-016")
    await db.close()
    assert row["status"] == "queued"


# ---------------------------------------------------------------------------
# Tests: list_runs ordering and pagination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_runs_newest_first(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-A", created_at="2026-06-26T08:00:00")
    await _insert(db, "run-B", created_at="2026-06-26T09:00:00")
    await _insert(db, "run-C", created_at="2026-06-26T10:00:00")
    rows = await list_runs(db)
    await db.close()
    ids = [r["id"] for r in rows]
    assert ids == ["run-C", "run-B", "run-A"]


@pytest.mark.asyncio
async def test_list_runs_limit(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    for i in range(5):
        await _insert(db, f"run-{i:02d}", created_at=f"2026-06-26T0{i}:00:00")
    rows = await list_runs(db, limit=3)
    await db.close()
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_list_runs_offset(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    for i in range(4):
        await _insert(db, f"run-{i:02d}", created_at=f"2026-06-26T0{i}:00:00")
    # Newest-first: run-03, run-02, run-01, run-00
    all_rows = await list_runs(db)
    offset_rows = await list_runs(db, limit=10, offset=2)
    await db.close()
    assert offset_rows == all_rows[2:]


@pytest.mark.asyncio
async def test_list_runs_empty_db(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    rows = await list_runs(db)
    await db.close()
    assert rows == []


# ---------------------------------------------------------------------------
# Tests: list_runs with verdict filter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_runs_verdict_filter(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-X", created_at="2026-06-26T08:00:00")
    await _insert(db, "run-Y", created_at="2026-06-26T09:00:00")
    await _insert(db, "run-Z", created_at="2026-06-26T10:00:00")
    await update_run(db, "run-X", verdict="ADOPTED")
    await update_run(db, "run-Y", verdict="REJECTED")
    await update_run(db, "run-Z", verdict="ADOPTED")

    adopted = await list_runs(db, verdict="ADOPTED")
    await db.close()
    assert len(adopted) == 2
    assert all(r["verdict"] == "ADOPTED" for r in adopted)


@pytest.mark.asyncio
async def test_list_runs_verdict_filter_no_match(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-P", created_at="2026-06-26T08:00:00")
    await update_run(db, "run-P", verdict="ADOPTED")
    rows = await list_runs(db, verdict="CONTESTED")
    await db.close()
    assert rows == []


@pytest.mark.asyncio
async def test_list_runs_verdict_filter_newest_first(tmp_path):
    db = await init_db(tmp_path / "simulate.db")
    await _insert(db, "run-M", created_at="2026-06-26T08:00:00")
    await _insert(db, "run-N", created_at="2026-06-26T09:00:00")
    await update_run(db, "run-M", verdict="REJECTED")
    await update_run(db, "run-N", verdict="REJECTED")
    rows = await list_runs(db, verdict="REJECTED")
    await db.close()
    assert rows[0]["id"] == "run-N"
    assert rows[1]["id"] == "run-M"
