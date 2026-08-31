"""FastAPI routes for simulation lifecycle, sharing, and follow-up analysis."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from src.api.models import (
    RunListResponse,
    RunSummary,
    SchemaApprovalRequest,
    SimulationRequest,
    SimulationStartResponse,
    SimulationStatus,
)
from src.api.queue import SimulationJob, cancel_job, enqueue_simulation, get_job
from src.api.security import (
    generate_token,
    hash_token,
    require_owner,
    require_read_access,
    websocket_has_access,
)
from src.api.websocket import event_bus
from src.export.serialization import load_canonical_result
from src.persistence.db import disable_share, get_run, insert_run, list_runs, update_run

router = APIRouter(prefix="/api")


@router.get("/health")
async def health_check():
    from config import DEFAULT_MODEL, LLM_PROVIDER

    return {"status": "ok", "provider": LLM_PROVIDER, "model": DEFAULT_MODEL}


@router.get("/readiness")
async def readiness_check(request: Request):
    """Check local dependencies without calling a paid model provider."""
    try:
        await (await request.app.state.db.execute("SELECT 1")).fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready.") from exc
    return {"status": "ready", "database": "ok", "storage": "ok"}


@router.post("/simulate", response_model=SimulationStartResponse)
async def start_simulation(req: SimulationRequest, request: Request):
    """Create a background simulation and return its owner capability token."""
    db = request.app.state.db
    run_id = str(uuid.uuid4())
    access_token = generate_token()
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
        schema_approval=req.schema_approval,
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
        owner_token_hash=hash_token(access_token),
    )
    await enqueue_simulation(job, db)
    return SimulationStartResponse(id=run_id, status="queued", access_token=access_token)


@router.get("/simulate/{run_id}", response_model=SimulationStatus)
async def get_simulation_status(run_id: str, request: Request):
    db = request.app.state.db
    row = await get_run(db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    require_read_access(request, row)

    job = get_job(run_id)
    if job:
        status = "schema_pending" if job.schema_pending else job.status
        return SimulationStatus(
            id=job.run_id,
            status=status,
            scenario_name=job.scenario_name,
            verdict=job.verdict,
            elapsed_s=job.elapsed_s,
            error=job.error,
            result=job.result,
            progress=job.progress,
            progress_percent=job.progress_percent,
            stage=job.current_stage,
            schema_pending=job.schema_pending,
            latest_seq=event_bus.latest_sequence(run_id),
        )

    result_data = load_canonical_result(row["run_dir"]) if row.get("run_dir") and row["status"] == "completed" else None
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
async def list_all_runs(request: Request, limit: int = 50, offset: int = 0, verdict: str | None = None):
    """Administrative run index. Disabled publicly unless ADMIN_API_KEY is set and supplied."""
    from config import ADMIN_API_KEY

    if not ADMIN_API_KEY or request.headers.get("x-admin-key") != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Administrative access required.")
    rows = await list_runs(request.app.state.db, limit=limit, offset=offset, verdict=verdict)
    runs = [
        RunSummary(
            id=row["id"], scenario_name=row["scenario_name"], status=row["status"],
            verdict=row.get("verdict"), agent_count=row.get("agent_count"),
            elapsed_s=row.get("elapsed_s"), created_at=row["created_at"],
        )
        for row in rows
    ]
    return RunListResponse(runs=runs, total=len(runs))


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: str, request: Request):
    row = await get_run(request.app.state.db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    require_read_access(request, row)
    if not row.get("run_dir"):
        raise HTTPException(status_code=404, detail="Run result is not available.")
    result = load_canonical_result(row["run_dir"])
    if result is None:
        raise HTTPException(status_code=404, detail="Result file not found.")
    return result


@router.post("/simulate/{run_id}/schema")
async def approve_schema(run_id: str, req: SchemaApprovalRequest, request: Request):
    row = await get_run(request.app.state.db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    require_owner(request, row)
    job = get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail="Run already finished or server restarted.")
    if not job.schema_pending:
        raise HTTPException(status_code=409, detail="Schema is not pending approval.")
    job.schema_overrides = req.overrides if req.approved and req.overrides else None
    job.schema_approval_event.set()
    return {"status": "approved", "run_id": run_id}


@router.post("/simulate/{run_id}/cancel")
async def cancel_simulation(run_id: str, request: Request):
    db = request.app.state.db
    row = await get_run(db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    require_owner(request, row)
    if not await cancel_job(run_id, db):
        raise HTTPException(status_code=409, detail="Run is not cancellable.")
    return {"status": "cancelled", "run_id": run_id}


@router.post("/runs/{run_id}/share")
async def create_share_link(run_id: str, request: Request):
    db = request.app.state.db
    row = await get_run(db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    require_owner(request, row)
    if row["status"] != "completed":
        raise HTTPException(status_code=409, detail="Only completed runs can be shared.")
    token = generate_token()
    await update_run(db, run_id, share_token_hash=hash_token(token), share_enabled=True)
    return {"run_id": run_id, "share_token": token}


@router.delete("/runs/{run_id}/share", status_code=204)
async def revoke_share_link(run_id: str, request: Request):
    db = request.app.state.db
    row = await get_run(db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    require_owner(request, row)
    await disable_share(db, run_id)


@router.websocket("/ws/simulate/{run_id}")
async def websocket_simulate(websocket: WebSocket, run_id: str):
    row = await get_run(websocket.app.state.db, run_id)
    if not row or not websocket_has_access(websocket, row):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    try:
        since = max(0, int(websocket.query_params.get("since", "0")))
    except ValueError:
        since = 0
    queue = event_bus.subscribe(run_id, since=since)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("type") in ("complete", "error", "cancelled"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(run_id, queue)


@router.post("/runs/{run_id}/ask")
async def ask_about_run(run_id: str, request: Request):
    """Owner-only follow-up; shared viewers cannot consume an LLM key."""
    from src.llm.client import UnifiedLLMClient

    db = request.app.state.db
    row = await get_run(db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    require_owner(request, row)
    body = await request.json()
    question = str(body.get("question", "")).strip()
    context_md = str(body.get("context_md", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    if len(question) > 2_000:
        raise HTTPException(status_code=400, detail="Question is too long.")
    if not context_md and row.get("run_dir"):
        report_path = Path(row["run_dir"]) / "report.md"
        if report_path.exists():
            context_md = report_path.read_text(encoding="utf-8")[:8_000]
    if not context_md:
        raise HTTPException(status_code=404, detail="No simulation context is available.")

    client = UnifiedLLMClient(
        model=row.get("model"), provider=row.get("provider"),
        api_key=request.headers.get("x-api-key"),
    )
    system_prompt = (
        "You are an analyst reviewing a multi-agent decision simulation. Answer only from "
        "the report below, cite agents or metrics where useful, and stay concise.\n\n"
        f"--- SIMULATION REPORT ---\n{context_md[:6_000]}\n--- END REPORT ---"
    )
    try:
        answer = await client.chat(messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ])
        return {"answer": answer}
    except Exception:
        raise HTTPException(status_code=502, detail="The selected LLM provider could not answer the question.")
    finally:
        await client.aclose()
