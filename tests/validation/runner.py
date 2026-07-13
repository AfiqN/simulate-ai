"""Main orchestrator for validation/hindsight testing.

Loads YAML case files, runs simulation pipeline for each, scores via LLM judge,
and generates an accuracy report.

Usage:
    py -3 -m tests.validation.runner [--case svb_collapse] [--runs 3] [--model gemma3:4b]
"""

import argparse
import asyncio
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import DEFAULT_MODEL, OLLAMA_HOST, LLM_PROVIDER
from src.llm.client import OllamaClient
from src.cli.simulation import run_simulation_pipeline
from tests.validation.models import CaseResult, ValidationCase, ValidationReport
from tests.validation.scorer import score_simulation
from tests.validation.report import print_console_summary, write_report


CASES_DIR = Path(__file__).resolve().parent / "cases"
OUTPUT_DIR = Path(__file__).resolve().parent


def load_cases(case_filter: Optional[str] = None) -> list[ValidationCase]:
    """Load validation cases from YAML files in the cases/ directory."""
    cases = []
    if not CASES_DIR.exists():
        print(f"[ERROR] Cases directory not found: {CASES_DIR}")
        return cases

    yaml_files = sorted(CASES_DIR.glob("*.yaml")) + sorted(CASES_DIR.glob("*.yml"))
    if not yaml_files:
        print(f"[WARNING] No YAML case files found in {CASES_DIR}")
        return cases

    for yaml_path in yaml_files:
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data is None:
                continue
            case = ValidationCase.from_dict(data, filename=yaml_path.stem)
            if case_filter and case.id != case_filter:
                continue
            cases.append(case)
        except Exception as e:
            print(f"[ERROR] Failed to load {yaml_path.name}: {e}")

    return cases


async def run_single_case(
    client: OllamaClient,
    case: ValidationCase,
    run_index: int,
    model: Optional[str] = None,
    mode: str = "collaborative",
) -> dict[str, Any]:
    """Run a single simulation for a validation case. Returns the pipeline result dict."""
    result = await run_simulation_pipeline(
        client=client,
        stimulus=case.stimulus,
        agent_count=8,
        concurrency=3,
        headless=True,
        rag_enabled=False,
        depth="standard",
        mode=mode,
    )
    return result


async def evaluate_case(
    client: OllamaClient,
    case: ValidationCase,
    num_runs: int,
    model: Optional[str] = None,
    mode: str = "collaborative",
) -> CaseResult:
    """Run a case N times, score each run, return aggregated CaseResult."""
    case_result = CaseResult(
        case_id=case.id,
        case_name=case.name,
        domain=case.domain,
    )

    for run_idx in range(num_runs):
        run_label = f"[{case.id}] Run {run_idx + 1}/{num_runs}"
        print(f"  {run_label}: Simulating ({mode})...")
        t0 = time.time()

        try:
            sim_result = await run_single_case(client, case, run_idx, model, mode)
            elapsed = time.time() - t0
            print(f"  {run_label}: Simulation complete ({elapsed:.1f}s). Scoring...")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  {run_label}: Simulation FAILED ({elapsed:.1f}s) — {e}")
            traceback.print_exc()
            case_result.simulation_error = str(e)
            continue

        # Score this run
        try:
            scoring = await score_simulation(
                client=client,
                simulation_result=sim_result,
                ground_truth=case.ground_truth,
                case_id=case.id,
                run_index=run_idx,
                model=model,
            )
            case_result.runs.append(scoring)

            if scoring.error:
                print(f"  {run_label}: Scoring error — {scoring.error}")
            else:
                print(f"  {run_label}: Score = {scoring.composite_score:.2f}/10")
        except Exception as e:
            print(f"  {run_label}: Scoring FAILED — {e}")
            traceback.print_exc()

    return case_result


async def run_validation(
    case_filter: Optional[str] = None,
    num_runs: int = 3,
    model_override: Optional[str] = None,
    mode: str = "collaborative",
) -> ValidationReport:
    """Main validation entry point — load cases, run sims, score, report."""
    model = model_override or DEFAULT_MODEL
    print(f"\n{'='*60}")
    print(f"  SimulateAI Hindsight Validation Runner")
    print(f"  Model: {model} | Provider: {LLM_PROVIDER}")
    print(f"  Mode: {mode}")
    print(f"  Runs per case: {num_runs}")
    if case_filter:
        print(f"  Filter: {case_filter}")
    print(f"{'='*60}\n")

    # Load cases
    cases = load_cases(case_filter)
    if not cases:
        if case_filter:
            print(f"[ERROR] No case found with id '{case_filter}'")
            print(f"  Available cases in: {CASES_DIR}")
        else:
            print(f"[ERROR] No validation cases found.")
            print(f"  Add YAML case files to: {CASES_DIR}")
        return ValidationReport(timestamp=datetime.now().isoformat(), model_used=model)

    print(f"Loaded {len(cases)} case(s): {', '.join(c.id for c in cases)}\n")

    # Initialize LLM client
    client = OllamaClient(host=OLLAMA_HOST, model=model)
    try:
        available = await client.is_available()
        if not available:
            print(f"[ERROR] LLM provider not available. Check config.py settings.")
            return ValidationReport(timestamp=datetime.now().isoformat(), model_used=model)
        print(f"LLM provider connected.\n")
    except Exception as e:
        print(f"[ERROR] Failed to connect to LLM: {e}")
        return ValidationReport(timestamp=datetime.now().isoformat(), model_used=model)

    # Evaluate each case
    report = ValidationReport(
        model_used=model,
        runs_per_case=num_runs,
        timestamp=datetime.now().isoformat(),
    )

    for i, case in enumerate(cases):
        print(f"[{i+1}/{len(cases)}] Case: {case.name} ({case.domain})")
        if case.description:
            print(f"  Description: {case.description}")

        case_result = await evaluate_case(client, case, num_runs, model, mode)
        report.cases.append(case_result)

        if case_result.runs:
            print(f"  Median score: {case_result.median_score:.2f}/10\n")
        else:
            print(f"  No successful runs.\n")

    # Close client
    await client.aclose()

    # Generate report
    report_path = write_report(report, str(OUTPUT_DIR))
    print(f"\nReport written to: {report_path}")

    # Console summary
    print_console_summary(report)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="SimulateAI Hindsight Validation Runner",
        prog="py -3 -m tests.validation.runner",
    )
    parser.add_argument(
        "--case",
        type=str,
        default=None,
        help="Run a specific case by ID (e.g. svb_collapse). Omit to run all.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs per case (default: 3). Median score is taken.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=f"Override the LLM model (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="collaborative",
        choices=["collaborative", "adversarial"],
        help="Simulation mode (default: collaborative).",
    )
    args = parser.parse_args()

    asyncio.run(run_validation(
        case_filter=args.case,
        num_runs=args.runs,
        model_override=args.model,
        mode=args.mode,
    ))


if __name__ == "__main__":
    main()
