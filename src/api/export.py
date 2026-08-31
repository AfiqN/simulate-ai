"""Export API routes — structured JSON export and run comparison."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from src.api.security import require_read_access, token_matches
from src.export.comparison import compare_runs, load_run_data
from src.persistence.db import get_run


router = APIRouter(prefix="/api")


@router.get("/runs/{run_id}/export")
async def export_run(run_id: str, request: Request):
    """Export full structured JSON for a completed run, including chart_data."""
    db = request.app.state.db
    row = await get_run(db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    require_read_access(request, row)
    if row["status"] != "completed":
        raise HTTPException(status_code=409, detail="Run is not completed yet.")
    if not row.get("run_dir"):
        raise HTTPException(status_code=404, detail="Run directory not available.")

    run_dir = Path(row["run_dir"])

    # Load simulation.json from bundle if available
    bundle_sim = run_dir / "bundle" / "simulation.json"
    if bundle_sim.exists():
        data = json.loads(bundle_sim.read_text(encoding="utf-8"))
    else:
        # Fallback to metrics.json
        metrics_path = run_dir / "metrics.json"
        if not metrics_path.exists():
            raise HTTPException(status_code=404, detail="No exportable data found.")
        data = json.loads(metrics_path.read_text(encoding="utf-8"))

    # Include chart_data if present in bundle
    chart_data_path = run_dir / "bundle" / "chart_data.json"
    if chart_data_path.exists():
        data["chart_data"] = json.loads(chart_data_path.read_text(encoding="utf-8"))

    return data


@router.get("/compare")
async def compare_two_runs(run_a: str, run_b: str, request: Request):
    """Compare two completed simulation runs.

    Query params: ?run_a={id}&run_b={id}
    """
    db = request.app.state.db

    row_a = await get_run(db, run_a)
    if not row_a:
        raise HTTPException(status_code=404, detail=f"Run A '{run_a}' not found.")
    token_a = request.headers.get("x-run-a-token")
    if row_a.get("owner_token_hash") and not token_matches(token_a, row_a.get("owner_token_hash")):
        raise HTTPException(status_code=403, detail="Owner token for Run A is required.")
    if row_a["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Run A is not completed (status: {row_a['status']}).")
    if not row_a.get("run_dir"):
        raise HTTPException(status_code=404, detail="Run A directory not available.")

    row_b = await get_run(db, run_b)
    if not row_b:
        raise HTTPException(status_code=404, detail=f"Run B '{run_b}' not found.")
    token_b = request.headers.get("x-run-b-token")
    if row_b.get("owner_token_hash") and not token_matches(token_b, row_b.get("owner_token_hash")):
        raise HTTPException(status_code=403, detail="Owner token for Run B is required.")
    if row_b["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Run B is not completed (status: {row_b['status']}).")
    if not row_b.get("run_dir"):
        raise HTTPException(status_code=404, detail="Run B directory not available.")

    try:
        data_a = load_run_data(row_a["run_dir"])
        data_b = load_run_data(row_b["run_dir"])
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return compare_runs(data_a, data_b)
