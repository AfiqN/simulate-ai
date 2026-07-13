"""In-memory background task queue for simulation jobs."""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.cli.simulation import run_simulation_pipeline
from src.export.bundle import write_bundle
from src.llm.client import OllamaClient
from src.persistence.db import update_run

from config import OLLAMA_HOST, DEFAULT_MODEL, MAX_CONCURRENCY


RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "runs"


class SimulationJob:
    """Tracks state of a single simulation run."""

    def __init__(self, run_id: str, stimulus: str, agent_count: int, concurrency: int,
                 model: str | None = None, provider: str | None = None,
                 crisis_override: str | None = None, rag_enabled: bool | None = None,
                 depth: str = "standard", mode: str = "collaborative",
                 custom_stakeholders: list[dict] | None = None,
                 historical_precedents: list[dict] | None = None):
        self.run_id = run_id
        self.stimulus = stimulus
        self.agent_count = agent_count
        self.concurrency = max(1, min(concurrency, MAX_CONCURRENCY))
        self.model = model or DEFAULT_MODEL
        self.provider = provider
        self.crisis_override = crisis_override
        self.rag_enabled = rag_enabled
        self.depth = depth
        self.mode = mode
        self.custom_stakeholders = custom_stakeholders
        self.historical_precedents = historical_precedents
        self.status: str = "queued"
        self.scenario_name: str | None = None
        self.verdict: str | None = None
        self.elapsed_s: float | None = None
        self.error: str | None = None
        self.result: dict[str, Any] | None = None
        self.run_dir: Path | None = None
        self.progress: str | None = None
        # Schema approval gate
        self.schema_pending: bool = False
        self.schema_approval_event: asyncio.Event = asyncio.Event()
        self.schema_overrides: dict[str, Any] | None = None
        # Cancellation
        self.cancelled: bool = False
        self._task: asyncio.Task | None = None


# Global job registry (in-memory — lost on restart)
_jobs: dict[str, SimulationJob] = {}


def get_job(run_id: str) -> Optional[SimulationJob]:
    return _jobs.get(run_id)


def list_jobs() -> list[SimulationJob]:
    return list(_jobs.values())


async def enqueue_simulation(job: SimulationJob, db) -> None:
    """Register the job and spawn a background task to execute it."""
    _jobs[job.run_id] = job
    job._task = asyncio.create_task(_execute_simulation(job, db))


async def cancel_job(run_id: str, db) -> bool:
    """Cancel a running simulation. Returns True if cancelled."""
    job = _jobs.get(run_id)
    if not job or job.status not in ("queued", "running"):
        return False
    job.cancelled = True
    if job._task and not job._task.done():
        job._task.cancel()
    job.status = "cancelled"
    from src.api.websocket import event_bus
    event_bus.emit(run_id, {"type": "error", "message": "Simulation cancelled by user"})
    await update_run(db, run_id, status="cancelled")
    return True


async def _execute_simulation(job: SimulationJob, db) -> None:
    """Run the simulation pipeline in the background."""
    job.status = "running"
    job.progress = "Connecting to LLM provider..."
    await update_run(db, job.run_id, status="running")

    from src.api.webhooks import dispatch_webhook_event
    await dispatch_webhook_event("simulation.started", {
        "stimulus": job.stimulus,
        "agent_count": job.agent_count,
        "depth": job.depth,
    }, run_id=job.run_id)

    client = OllamaClient(host=OLLAMA_HOST, model=job.model, provider=job.provider)
    start = time.time()

    try:
        from src.api.websocket import event_bus

        def _event_cb(event: dict):
            event_bus.emit(job.run_id, event)

        async def _schema_approval_cb(schema):
            """Pause pipeline, emit schema_pending, wait for approval or 120s timeout."""
            job.schema_pending = True
            job.schema_approval_event.clear()
            schema_data = {
                "scenario_name": schema.scenario_name,
                "actions": [{"name": a.name, "description": a.description, "is_terminal": a.is_terminal} for a in schema.actions],
                "evaluation_dimensions": schema.evaluation_dimensions,
                "state_vocabulary": schema.state_vocabulary,
            }
            event_bus.emit(job.run_id, {"type": "schema_pending", "schema": schema_data})

            try:
                await asyncio.wait_for(job.schema_approval_event.wait(), timeout=120.0)
            except asyncio.TimeoutError:
                pass  # Auto-approve after 120s

            job.schema_pending = False
            event_bus.emit(job.run_id, {"type": "schema_approved"})
            return job.schema_overrides  # None means no changes

        result = await run_simulation_pipeline(
            client,
            job.stimulus,
            job.agent_count,
            job.concurrency,
            crisis_override=job.crisis_override,
            headless=True,
            rag_enabled=job.rag_enabled,
            progress_callback=lambda msg: setattr(job, 'progress', msg),
            event_callback=_event_cb,
            depth=job.depth,
            mode=job.mode,
            schema_approval_callback=_schema_approval_cb,
            custom_stakeholders=job.custom_stakeholders,
            historical_precedents=job.historical_precedents,
        )

        job.elapsed_s = time.time() - start
        job.status = "completed"
        job.scenario_name = result["schema"].scenario_name
        job.verdict = result["resilience_metrics"]["verdict"]

        # Write outputs to disk
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        scenario_slug = result["schema"].scenario_name.lower().replace(" ", "_")[:40]
        # Remove characters invalid in Windows paths
        scenario_slug = "".join(c for c in scenario_slug if c not in r'<>:"/\|?*')
        out_dir = RUNS_DIR / f"{timestamp}__{scenario_slug}"
        out_dir.mkdir(parents=True, exist_ok=True)

        (out_dir / "stimulus.txt").write_text(job.stimulus, encoding="utf-8")
        (out_dir / "report.md").write_text(result["report_md"], encoding="utf-8")

        # Serialize result for metrics.json
        from tests.run_scenario import serialize_result
        (out_dir / "metrics.json").write_text(
            json.dumps(serialize_result(result), indent=2, default=str),
            encoding="utf-8",
        )
        write_bundle(result, out_dir)

        job.run_dir = out_dir
        # Serialize adversarial result if present
        adversarial_raw = result.get("adversarial_result")
        adversarial_data = None
        if adversarial_raw is not None:
            from dataclasses import asdict
            adversarial_data = {
                "claims": [asdict(c) for c in adversarial_raw.claims],
                "survival_rate": adversarial_raw.survival_rate,
                "surviving_count": len(adversarial_raw.surviving_claims),
                "defeated_count": len(adversarial_raw.defeated_claims),
                "key_defeats": adversarial_raw.key_defeats,
            }

        job.result = {
            "scenario_name": job.scenario_name,
            "verdict": job.verdict,
            "resilience_metrics": result["resilience_metrics"],
            "crisis_event": result["crisis_event"],
            "timings": result["timings"],
            "report_md": result["report_md"],
            "quantitative_metrics": result.get("quantitative_metrics"),
            "faction_metrics": result.get("faction_metrics"),
            "conditional_dynamics": result.get("conditional_dynamics"),
            "historical_context": result.get("historical_context"),
            "adversarial_result": adversarial_data,
        }

        await update_run(
            db, job.run_id,
            status="completed",
            verdict=job.verdict,
            elapsed_s=job.elapsed_s,
            run_dir=str(out_dir),
        )

        event_bus.emit(job.run_id, {"type": "complete", "result": job.result})

        await dispatch_webhook_event("simulation.completed", {
            "scenario_name": job.scenario_name,
            "verdict": job.verdict,
            "elapsed_s": job.elapsed_s,
            "agent_count": job.agent_count,
        }, run_id=job.run_id)

    except Exception as e:
        job.elapsed_s = time.time() - start
        job.status = "failed"
        job.error = f"{type(e).__name__}: {e}"
        event_bus.emit(job.run_id, {"type": "error", "message": job.error})
        await update_run(
            db, job.run_id,
            status="failed",
            elapsed_s=job.elapsed_s,
            error_message=job.error,
        )
        await dispatch_webhook_event("simulation.failed", {
            "error": job.error,
            "elapsed_s": job.elapsed_s,
        }, run_id=job.run_id)
    finally:
        await client.aclose()
