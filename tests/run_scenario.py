"""Run swarm simulation scenarios non-interactively and save transcripts.

Usage:
    python tests/run_scenario.py 01                    # by prefix
    python tests/run_scenario.py fintech               # by name fragment
    python tests/run_scenario.py --all                 # every scenario
    python tests/run_scenario.py 02 --agents 5 --concurrency 3
    python tests/run_scenario.py --all --parallel 2    # run 2 scenarios concurrently
    python tests/run_scenario.py 04 --crisis "A massive data breach occurs"
    python tests/run_scenario.py 01 --provider openai --model gpt-4o
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cli import console  # noqa: E402
from src.cli.simulation import check_llm_provider, run_simulation_pipeline  # noqa: E402
from src.llm.client import OllamaClient  # noqa: E402
from config import DEFAULT_MODEL, MAX_CONCURRENCY, OLLAMA_HOST  # noqa: E402
from src.agent.swarm import SwarmGenerationError  # noqa: E402
from src.export.bundle import write_bundle  # noqa: E402
from src.schema.architect import SchemaDesignError  # noqa: E402

SCENARIOS_DIR = ROOT / "tests" / "scenarios"
RUNS_DIR = ROOT / "tests" / "runs"


def resolve_scenarios(spec: str | None, run_all: bool) -> list[Path]:
    available = sorted(SCENARIOS_DIR.glob("*.txt"))
    if run_all:
        return available
    if spec is None:
        names = ", ".join(p.stem for p in available) or "(none found)"
        raise SystemExit(f"Specify a scenario name/prefix or --all. Available: {names}")

    candidate = Path(spec)
    if candidate.is_file():
        return [candidate]

    matches = [p for p in available if spec in p.stem]
    if not matches:
        raise SystemExit(f"No scenario matching '{spec}' in {SCENARIOS_DIR}")
    return sorted(matches)


def serialize_result(result: dict) -> dict:
    schema = result["schema"]
    rounds = {
        f"r{i}": [
            {
                "id": d["id"],
                "archetype": d["archetype"],
                "action": d["action"],
                "utility": d["utility"],
                "new_state": d["new_state"],
                "duration": d.get("duration", 0.0),
            }
            for d in decisions
        ]
        for i, decisions in enumerate(
            [result["decisions_r1"], result["decisions_r2"], result["decisions_r3"]],
            start=1,
        )
    }
    return {
        "scenario_name": schema.scenario_name,
        "verdict_label": schema.verdict_label,
        "actions": [a.name for a in schema.actions],
        "valence": result["valence"],
        "crisis_event": result["crisis_event"],
        "resilience_metrics": result.get("resilience_metrics"),
        "agents": [
            {
                "id": p.agent_id,
                "archetype": p.archetype,
                "linguistic_cluster_id": p.linguistic_cluster_id,
                "final_state": p.current_internal_state,
            }
            for p in result["profiles"]
        ],
        "rounds": rounds,
        "adversary_map": {
            agent_id: (target["id"] if target else None)
            for agent_id, target in result["adversary_map"].items()
        },
        "timings": result["timings"],
    }


async def run_one(
    client: OllamaClient,
    scenario_path: Path,
    agent_count: int,
    concurrency: int,
    crisis_override: str | None = None,
) -> tuple[Path, str]:
    stimulus = scenario_path.read_text(encoding="utf-8").strip()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = RUNS_DIR / f"{timestamp}__{scenario_path.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stimulus.txt").write_text(stimulus, encoding="utf-8")

    console.print(f"\n[bold cyan]══════ Running {scenario_path.stem} ══════[/bold cyan]\n")
    start = time.time()

    try:
        result = await run_simulation_pipeline(
            client, stimulus, agent_count, concurrency,
            crisis_override=crisis_override,
        )
        (out_dir / "report.md").write_text(result["report_md"], encoding="utf-8")
        (out_dir / "metrics.json").write_text(
            json.dumps(serialize_result(result), indent=2, default=str),
            encoding="utf-8",
        )
        # Write shareable export bundle
        write_bundle(result, out_dir)
        status = "ok"
    except (SchemaDesignError, SwarmGenerationError) as e:
        console.print(f"[red]Pipeline failed: {e}[/red]")
        (out_dir / "error.txt").write_text(f"{type(e).__name__}: {e}", encoding="utf-8")
        status = "failed"

    elapsed = time.time() - start

    (out_dir / "transcript.txt").write_text(console.export_text(clear=False), encoding="utf-8")
    (out_dir / "transcript.html").write_text(console.export_html(clear=True), encoding="utf-8")

    console.print(
        f"\n[bold green]✔ {scenario_path.stem} ({status}) in {elapsed:.1f}s → "
        f"{out_dir.relative_to(ROOT)}[/bold green]\n"
    )
    return out_dir, status


def write_batch_summary(results: list[tuple[Path, str]], batch_start: float) -> Path:
    """Write a single summary JSON aggregating all scenario results in this batch."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    entries = []
    for out_dir, status in results:
        entry = {
            "scenario": out_dir.name.split("__", 1)[-1] if "__" in out_dir.name else out_dir.name,
            "status": status,
            "run_dir": str(out_dir.relative_to(ROOT)),
        }
        metrics_path = out_dir / "metrics.json"
        if metrics_path.exists():
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            entry["verdict_label"] = metrics.get("verdict_label")
            entry["resilience_metrics"] = metrics.get("resilience_metrics")
            entry["timings"] = metrics.get("timings")
            entry["crisis_event"] = metrics.get("crisis_event")
            entry["agent_count"] = len(metrics.get("agents", []))
        entries.append(entry)

    summary = {
        "batch_timestamp": timestamp,
        "total_elapsed_s": round(time.time() - batch_start, 1),
        "scenarios_run": len(entries),
        "passed": sum(1 for e in entries if e["status"] == "ok"),
        "failed": sum(1 for e in entries if e["status"] == "failed"),
        "results": entries,
    }
    summary_path = RUNS_DIR / f"summary_{timestamp}.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary_path


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run SimulateAI scenarios non-interactively.")
    parser.add_argument("scenario", nargs="?", help="Scenario name fragment, prefix, or .txt path.")
    parser.add_argument("--all", action="store_true", help="Run every scenario in tests/scenarios/.")
    parser.add_argument("--agents", type=int, default=5, help="Agent count per scenario (default: 5).")
    parser.add_argument("--concurrency", type=int, default=2, help="Max concurrent LLM calls (default: 2).")
    parser.add_argument("--parallel", type=int, default=1, help="Run N scenarios concurrently (default: 1 = sequential).")
    parser.add_argument("--model", type=str, default=None, help="Override LLM model name.")
    parser.add_argument("--provider", type=str, choices=["gemini", "ollama", "openai"], default=None, help="Override LLM provider.")
    parser.add_argument("--crisis", type=str, default=None, help="Inject a custom crisis event for Round 3.")
    args = parser.parse_args()

    # Clamp concurrency
    concurrency = max(1, min(args.concurrency, MAX_CONCURRENCY))

    paths = resolve_scenarios(args.scenario, args.all)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve model/provider overrides
    model = args.model or DEFAULT_MODEL
    provider = args.provider  # None means use config default

    client = OllamaClient(host=OLLAMA_HOST, model=model, provider=provider)
    if not await check_llm_provider(client):
        sys.exit(1)

    batch_start = time.time()
    results: list[tuple[Path, str]] = []

    parallel_count = max(1, min(args.parallel, len(paths)))

    if parallel_count <= 1:
        # Sequential execution (original behavior)
        for path in paths:
            results.append(await run_one(client, path, args.agents, concurrency, crisis_override=args.crisis))
    else:
        # Parallel scenario execution — each scenario gets its own client instance
        sem = asyncio.Semaphore(parallel_count)

        async def _run_with_semaphore(path: Path) -> tuple[Path, str]:
            async with sem:
                # Each parallel scenario gets a fresh client to avoid shared state
                scenario_client = OllamaClient(host=OLLAMA_HOST, model=model, provider=provider)
                try:
                    return await run_one(scenario_client, path, args.agents, concurrency, crisis_override=args.crisis)
                finally:
                    await scenario_client.aclose()

        results = await asyncio.gather(*[_run_with_semaphore(p) for p in paths])
        results = list(results)

    # Write batch summary when running multiple scenarios
    if len(results) > 1:
        summary_path = write_batch_summary(results, batch_start)
        console.print(
            f"\n[bold cyan]Batch summary → {summary_path.relative_to(ROOT)}[/bold cyan]"
        )

    console.print(
        f"\n[bold yellow]All runs saved under {RUNS_DIR.relative_to(ROOT)}/[/bold yellow]"
    )
    for out_dir, status in results:
        marker = "[green]✔[/green]" if status == "ok" else "[red]✗[/red]"
        console.print(f"  {marker} {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
