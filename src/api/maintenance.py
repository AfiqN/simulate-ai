"""Periodic cleanup for in-memory jobs, quotas, and expired run bundles."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from config import RUN_RETENTION_DAYS
from src.api.queue import RUNS_DIR, cleanup_finished_jobs
from src.persistence.db import cleanup_usage, delete_run, list_expired_runs

logger = logging.getLogger(__name__)
MAINTENANCE_INTERVAL_SECONDS = 3600


def _safe_run_directory(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    candidate = Path(path_value)
    if candidate.is_symlink():
        return None
    root = RUNS_DIR.resolve()
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if resolved == root or root not in resolved.parents:
        return None
    return resolved


async def run_maintenance(db) -> None:
    """Run one bounded maintenance pass."""
    cleanup_finished_jobs()
    await cleanup_usage(db, time.time() - 2 * 86_400)

    cutoff = datetime.now() - timedelta(days=max(1, RUN_RETENTION_DAYS))
    rows = await list_expired_runs(db, cutoff.isoformat())
    for row in rows:
        path = _safe_run_directory(row.get("run_dir"))
        if row.get("run_dir") and path is None:
            logger.warning("Refusing unsafe retention path for run %s", row["id"])
            continue
        if path and path.exists():
            await asyncio.to_thread(shutil.rmtree, path)
        await delete_run(db, row["id"])


async def maintenance_loop(db) -> None:
    while True:
        try:
            await run_maintenance(db)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Periodic maintenance failed")
        await asyncio.sleep(MAINTENANCE_INTERVAL_SECONDS)
