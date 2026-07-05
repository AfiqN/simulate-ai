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
                 depth: str = "standard"):
        self.run_id = run_id
        self.stimulus = stimulus
        self.agent_count = agent_count
        self.concurrency = max(1, min(concurrency, MAX_CONCURRENCY))
        self.model = model or DEFAULT_MODEL
        self.provider = provider
        self.crisis_override = crisis_override
        self.rag_enabled = rag_enabled
        self.depth = depth
        self.status: str = "queued"
        self.scenario_name: str | None = None
        self.verdict: str | None = None
        self.elapsed_s: float | None = None
        self.error: str | None = None
        self.result: dict[str, Any] | None = None
        self.run_dir: Path | None = None
        self.progress: str | None = None


# Global job registry (in-memory — lost on restart)
_jobs: dict[str, SimulationJob] = {}


def get_job(run_id: str) -> Optional[SimulationJob]:
    return _jobs.get(run_id)


def list_jobs() -> list[SimulationJob]:
    return list(_jobs.values())


async def enqueue_simulation(job: SimulationJob, db) -> None:
    """Register the job and spawn a background task to execute it."""
    _jobs[job.run_id] = job
    asyncio.create_task(_execute_simulation(job, db))


async def _execute_simulation(job: SimulationJob, db) -> None:
    """Run the simulation pipeline in the background."""
    job.status = "running"
    job.progress = "Connecting to LLM provider..."
    await update_run(db, job.run_id, status="running")

    client = OllamaClient(host=OLLAMA_HOST, model=job.model, provider=job.provider)
    start = time.time()

    try:
        from src.api.websocket import event_bus

        def _event_cb(event: dict):
            event_bus.emit(job.run_id, event)

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
        )

        job.elapsed_s = time.time() - start
        job.status = "completed"
        job.scenario_name = result["schema"].scenario_name
        job.verdict = result["resilience_metrics"]["verdict"]

        # Write outputs to disk
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        scenario_slug = result["schema"].scenario_name.lower().replace(" ", "_")[:40]
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
        job.result = {
            "scenario_name": job.scenario_name,
            "verdict": job.verdict,
            "resilience_metrics": result["resilience_metrics"],
            "crisis_event": result["crisis_event"],
            "timings": result["timings"],
            "report_md": result["report_md"],
        }

        await update_run(
            db, job.run_id,
            status="completed",
            verdict=job.verdict,
            elapsed_s=job.elapsed_s,
            run_dir=str(out_dir),
        )

        event_bus.emit(job.run_id, {"type": "complete", "result": job.result})

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
    finally:
        await client.aclose()
