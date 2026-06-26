"""FastAPI route definitions for SimulateAI API."""

import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from src.api.models import RunListResponse, RunSummary, SimulationRequest, SimulationStatus
from src.api.queue import SimulationJob, enqueue_simulation, get_job
from src.persistence.db import get_run, insert_run, list_runs


router = APIRouter(prefix="/api")

RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "runs"


@router.post("/simulate", response_model=SimulationStatus)
async def start_simulation(req: SimulationRequest, request: Request):
    """Start a new simulation run. Returns immediately with a run ID to poll."""
    db = request.app.state.db
    run_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    job = SimulationJob(
        run_id=run_id,
        stimulus=req.stimulus,
        agent_count=req.agent_count,
        concurrency=req.concurrency,
        model=req.model,
        provider=req.provider,
        crisis_override=req.crisis_override,
        rag_enabled=req.rag_enabled,
    )

    await insert_run(
        db,
        run_id=run_id,
        scenario_name=req.stimulus[:80],
        status="queued",
        agent_count=req.agent_count,
        concurrency=req.concurrency,
        provider=req.provider,
        model=req.model,
        created_at=created_at,
    )

    await enqueue_simulation(job, db)

    return SimulationStatus(id=run_id, status="queued")


@router.get("/simulate/{run_id}", response_model=SimulationStatus)
async def get_simulation_status(run_id: str, request: Request):
    """Poll the status of a running or completed simulation."""
    # Check in-memory first (active jobs)
    job = get_job(run_id)
    if job:
        return SimulationStatus(
            id=job.run_id,
            status=job.status,
            scenario_name=job.scenario_name,
            verdict=job.verdict,
            elapsed_s=job.elapsed_s,
            error=job.error,
            result=job.result,
        )

    # Fall back to database (historical runs)
    db = request.app.state.db
    row = await get_run(db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    # Try to load full result from disk if completed
    result_data = None
    if row["status"] == "completed" and row.get("run_dir"):
        metrics_path = Path(row["run_dir"]) / "metrics.json"
        if metrics_path.exists():
            result_data = json.loads(metrics_path.read_text(encoding="utf-8"))

    return SimulationStatus(
        id=row["id"],
        status=row["status"],
        scenario_name=row["scenario_name"],
        verdict=row.get("verdict"),
        elapsed_s=row.get("elapsed_s"),
        error=row.get("error_message"),
        result=result_data,
    )


@router.get("/runs", response_model=RunListResponse)
async def list_all_runs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    verdict: str | None = None,
):
    """List past simulation runs from the database."""
    db = request.app.state.db
    rows = await list_runs(db, limit=limit, offset=offset, verdict=verdict)

    runs = [
        RunSummary(
            id=r["id"],
            scenario_name=r["scenario_name"],
            status=r["status"],
            verdict=r.get("verdict"),
            agent_count=r.get("agent_count"),
            elapsed_s=r.get("elapsed_s"),
            created_at=r["created_at"],
        )
        for r in rows
    ]
    return RunListResponse(runs=runs, total=len(runs))


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: str, request: Request):
    """Get full metrics for a specific historical run."""
    db = request.app.state.db
    row = await get_run(db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    if not row.get("run_dir"):
        raise HTTPException(status_code=404, detail="Run directory not available.")

    metrics_path = Path(row["run_dir"]) / "metrics.json"
    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="Metrics file not found on disk.")

    return json.loads(metrics_path.read_text(encoding="utf-8"))
