"""Lightweight SQLite persistence layer for indexing simulation runs."""

import aiosqlite
from pathlib import Path
from typing import Any, Optional


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    scenario_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    verdict TEXT,
    agent_count INTEGER,
    concurrency INTEGER,
    provider TEXT,
    model TEXT,
    created_at TEXT NOT NULL,
    elapsed_s REAL,
    run_dir TEXT,
    error_message TEXT
);
"""

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "simulate.db"


async def init_db(db_path: Path | None = None) -> aiosqlite.Connection:
    """Initialize the database and return an open connection."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(path))
    db.row_factory = aiosqlite.Row
    await db.execute(_CREATE_TABLE)
    await db.commit()
    return db


async def insert_run(
    db: aiosqlite.Connection,
    run_id: str,
    scenario_name: str,
    status: str = "queued",
    agent_count: int = 5,
    concurrency: int = 2,
    provider: str | None = None,
    model: str | None = None,
    created_at: str = "",
    run_dir: str | None = None,
) -> None:
    """Insert a new run record."""
    await db.execute(
        """INSERT INTO runs (id, scenario_name, status, agent_count, concurrency, provider, model, created_at, run_dir)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, scenario_name, status, agent_count, concurrency, provider, model, created_at, run_dir),
    )
    await db.commit()


async def update_run(
    db: aiosqlite.Connection,
    run_id: str,
    *,
    status: str | None = None,
    verdict: str | None = None,
    elapsed_s: float | None = None,
    run_dir: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update fields on an existing run record."""
    updates: list[str] = []
    values: list[Any] = []

    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if verdict is not None:
        updates.append("verdict = ?")
        values.append(verdict)
    if elapsed_s is not None:
        updates.append("elapsed_s = ?")
        values.append(elapsed_s)
    if run_dir is not None:
        updates.append("run_dir = ?")
        values.append(run_dir)
    if error_message is not None:
        updates.append("error_message = ?")
        values.append(error_message)

    if not updates:
        return

    values.append(run_id)
    sql = f"UPDATE runs SET {', '.join(updates)} WHERE id = ?"
    await db.execute(sql, values)
    await db.commit()


async def list_runs(
    db: aiosqlite.Connection,
    limit: int = 50,
    offset: int = 0,
    verdict: str | None = None,
) -> list[dict[str, Any]]:
    """List runs with optional filtering by verdict. Returns newest first."""
    if verdict:
        cursor = await db.execute(
            "SELECT * FROM runs WHERE verdict = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (verdict, limit, offset),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_run(db: aiosqlite.Connection, run_id: str) -> Optional[dict[str, Any]]:
    """Get a single run by ID."""
    cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None
