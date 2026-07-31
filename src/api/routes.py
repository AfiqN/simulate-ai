"""FastAPI route definitions for SimulateAI API."""

import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from src.api.models import RunListResponse, RunSummary, SimulationRequest, SimulationStatus, SchemaApprovalRequest
from src.api.queue import SimulationJob, enqueue_simulation, get_job, cancel_job
from src.api.websocket import event_bus
from src.persistence.db import get_run, insert_run, list_runs


router = APIRouter(prefix="/api")

RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "runs"


@router.get("/health")
async def health_check():
    """Health check — verifies the API is up and returns basic status."""
    from config import LLM_PROVIDER, DEFAULT_MODEL
    return {
        "status": "ok",
        "provider": LLM_PROVIDER,
        "model": DEFAULT_MODEL,
    }


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
        depth=req.depth,
        mode=req.mode,
        custom_stakeholders=[s.model_dump() for s in req.custom_stakeholders] if req.custom_stakeholders else None,
        historical_precedents=req.historical_precedents,
        api_key=request.headers.get("x-api-key"),
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
            progress=job.progress,
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


@router.post("/simulate/{run_id}/schema")
async def approve_schema(run_id: str, req: SchemaApprovalRequest):
    """Approve or override the generated schema for a paused simulation.

    The pipeline pauses after schema generation and emits a 'schema_pending' WS event.
    POST to this endpoint to resume. Auto-proceeds after 120s if not called.
    """
    job = get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found or already finished.")
    if not job.schema_pending:
        raise HTTPException(status_code=409, detail="Schema is not pending approval for this run.")

    if req.approved and req.overrides:
        job.schema_overrides = req.overrides
    else:
        job.schema_overrides = None

    job.schema_approval_event.set()
    return {"status": "approved", "run_id": run_id}


@router.post("/simulate/{run_id}/cancel")
async def cancel_simulation(run_id: str, request: Request):
    """Cancel a running or queued simulation."""
    db = request.app.state.db
    success = await cancel_job(run_id, db)
    if not success:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found or not cancellable.")
    return {"status": "cancelled", "run_id": run_id}


@router.websocket("/ws/simulate/{run_id}")
async def websocket_simulate(websocket: WebSocket, run_id: str):
    """Stream simulation events to the client in real-time."""
    await websocket.accept()
    queue = event_bus.subscribe(run_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("type") in ("complete", "error"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(run_id, queue)


@router.post("/runs/{run_id}/ask")
async def ask_about_run(run_id: str, request: Request):
    """Ask a follow-up question about a completed simulation run."""
    from src.llm.client import UnifiedLLMClient

    body = await request.json()
    question = body.get("question", "").strip()
    context_md = body.get("context_md", "").strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    # If no context provided, try to load from disk
    if not context_md:
        db = request.app.state.db
        row = await get_run(db, run_id)
        if row and row.get("run_dir"):
            report_path = Path(row["run_dir"]) / "report.md"
            if report_path.exists():
                context_md = report_path.read_text(encoding="utf-8")[:8000]

    if not context_md:
        raise HTTPException(status_code=404, detail="No simulation context available for this run.")

    # Use user's API key if provided
    api_key = request.headers.get("x-api-key")
    client = UnifiedLLMClient(api_key=api_key)

    system_prompt = (
        "You are an analyst reviewing the results of a multi-agent decision simulation. "
        "The simulation tested a decision by having AI personas debate it across multiple rounds. "
        "Answer the user's question based on the simulation report below. "
        "Be specific, cite agent names or data points when relevant. "
        "Keep your answer concise (2-4 sentences unless the question requires more detail).\n\n"
        f"--- SIMULATION REPORT ---\n{context_md[:6000]}\n--- END REPORT ---"
    )

    try:
        response = await client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ]
        )
        await client.aclose()
        return {"answer": response}
    except Exception as e:
        await client.aclose()
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")

