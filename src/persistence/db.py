"""Lightweight SQLite persistence for simulation runs and demo usage."""

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
    error_message TEXT,
    owner_token_hash TEXT,
    share_token_hash TEXT,
    share_enabled INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_USAGE_TABLE = """
CREATE TABLE IF NOT EXISTS usage_events (
    identity_hash TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""

_MIGRATIONS = {
    "owner_token_hash": "ALTER TABLE runs ADD COLUMN owner_token_hash TEXT",
    "share_token_hash": "ALTER TABLE runs ADD COLUMN share_token_hash TEXT",
    "share_enabled": "ALTER TABLE runs ADD COLUMN share_enabled INTEGER NOT NULL DEFAULT 0",
}

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "simulate.db"


async def init_db(db_path: Path | None = None) -> aiosqlite.Connection:
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(path))
    db.row_factory = aiosqlite.Row
    await db.execute(_CREATE_TABLE)
    columns = {row[1] for row in await (await db.execute("PRAGMA table_info(runs)")).fetchall()}
    for name, sql in _MIGRATIONS.items():
        if name not in columns:
            await db.execute(sql)
    await db.execute(_CREATE_USAGE_TABLE)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_usage_identity_time ON usage_events(identity_hash, created_at)")
    await db.execute(
        "UPDATE runs SET status = 'failed', error_message = 'Server restarted' "
        "WHERE status IN ('queued', 'running')"
    )
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
    owner_token_hash: str | None = None,
) -> None:
    await db.execute(
        """INSERT INTO runs
           (id, scenario_name, status, agent_count, concurrency, provider, model,
            created_at, run_dir, owner_token_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, scenario_name, status, agent_count, concurrency, provider, model,
         created_at, run_dir, owner_token_hash),
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
    share_token_hash: str | None = None,
    share_enabled: bool | None = None,
) -> None:
    updates: list[str] = []
    values: list[Any] = []
    for column, value in (
        ("status", status), ("verdict", verdict), ("elapsed_s", elapsed_s),
        ("run_dir", run_dir), ("error_message", error_message),
        ("share_token_hash", share_token_hash),
    ):
        if value is not None:
            updates.append(f"{column} = ?")
            values.append(value)
    if share_enabled is not None:
        updates.append("share_enabled = ?")
        values.append(1 if share_enabled else 0)
    if not updates:
        return
    values.append(run_id)
    await db.execute(f"UPDATE runs SET {', '.join(updates)} WHERE id = ?", values)
    await db.commit()


async def disable_share(db: aiosqlite.Connection, run_id: str) -> None:
    await db.execute(
        "UPDATE runs SET share_enabled = 0, share_token_hash = NULL WHERE id = ?",
        (run_id,),
    )
    await db.commit()


async def list_runs(
    db: aiosqlite.Connection,
    limit: int = 50,
    offset: int = 0,
    verdict: str | None = None,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
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
    return [dict(row) for row in await cursor.fetchall()]


async def get_run(db: aiosqlite.Connection, run_id: str) -> Optional[dict[str, Any]]:
    cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def count_recent_usage(db: aiosqlite.Connection, identity_hash: str, since: float) -> int:
    cursor = await db.execute(
        "SELECT COUNT(*) FROM usage_events WHERE identity_hash = ? AND created_at >= ?",
        (identity_hash, since),
    )
    row = await cursor.fetchone()
    return int(row[0])


async def record_usage(db: aiosqlite.Connection, identity_hash: str, created_at: float) -> None:
    await db.execute(
        "INSERT INTO usage_events(identity_hash, created_at) VALUES (?, ?)",
        (identity_hash, created_at),
    )
    await db.commit()


async def cleanup_usage(db: aiosqlite.Connection, before: float) -> None:
    await db.execute("DELETE FROM usage_events WHERE created_at < ?", (before,))
    await db.commit()


async def list_expired_runs(db: aiosqlite.Connection, before_iso: str) -> list[dict[str, Any]]:
    cursor = await db.execute(
        "SELECT * FROM runs WHERE status IN ('completed', 'failed', 'cancelled') "
        "AND created_at != '' AND created_at < ?",
        (before_iso,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def delete_run(db: aiosqlite.Connection, run_id: str) -> None:
    await db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
    await db.commit()
