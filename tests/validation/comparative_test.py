"""Comparative validation runner — collaborative vs adversarial mode.

Runs the same historical cases through both modes and compares:
1. Standard accuracy scores (verdict, behavior, risk, resilience)
2. Adversarial-specific quality scores (claim relevance, attack specificity, etc.)
3. Whether adversarial mode surfaces risks that collaborative misses

Usage:
    py -3 -m tests.validation.comparative_test [--case svb_collapse] [--model gemma3:4b]
"""

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import DEFAULT_MODEL, OLLAMA_HOST, LLM_PROVIDER
from src.llm.client import OllamaClient
from src.cli.simulation import run_simulation_pipeline
from tests.validation.models import ValidationCase
from tests.validation.scorer import score_simulation
from tests.validation.adversarial_scorer import score_adversarial_quality


CASES_DIR = Path(__file__).resolve().parent / "cases"
OUTPUT_DIR = Path(__file__).resolve().parent


@dataclass
class ModeResult:
    """Result from running one mode on one case."""
    mode: str  # "collaborative" or "adversarial"
    accuracy_score: float = 0.0
    accuracy_dimensions: dict[str, float] = field(default_factory=dict)
    adversarial_quality_score: float = 0.0
    adversarial_dimensions: dict[str, float] = field(default_factory=dict)
    survival_rate: float = 0.0
    claims_count: int = 0
    elapsed_s: float = 0.0
    report_md: str = ""
    error: Optional[str] = None


@dataclass
class ComparisonResult:
    """Comparison between collaborative and adversarial for one case."""
    case_id: str
    case_name: str
    domain: str
    collaborative: Optional[ModeResult] = None
    adversarial: Optional[ModeResult] = None

    @property
    def accuracy_delta(self) -> float:
        """Adversarial accuracy - Collaborative accuracy."""
        if not self.collaborative or not self.adversarial:
            return 0.0
        return self.adversarial.accuracy_score - self.collaborative.accuracy_score

    @property
    def risk_delta(self) -> float:
        """Delta in risk_identification dimension."""
        collab_risk = (self.collaborative.accuracy_dimensions.get("risk_identification", 0.0)
                       if self.collaborative else 0.0)
        adv_risk = (self.adversarial.accuracy_dimensions.get("risk_identification", 0.0)
                    if self.adversarial else 0.0)
        return adv_risk - collab_risk


async def run_mode(
    client: OllamaClient,
    case: ValidationCase,
    mode: str,
    model: Optional[str] = None,
) -> ModeResult:
    """Run a single case in a specific mode and score it."""
    result = ModeResult(mode=mode)
    t0 = time.time()

    try:
        sim_result = await run_simulation_pipeline(
            client=client,
            stimulus=case.stimulus,
            agent_count=8,
            concurrency=3,
            headless=True,
            rag_enabled=False,
            depth="standard",
            mode=mode,
        )
        result.elapsed_s = time.time() - t0
    except Exception as e:
        result.elapsed_s = time.time() - t0
        result.error = f"Simulation failed: {e}"
        return result

    result.report_md = sim_result.get("report_md", "")

    # Standard accuracy scoring
    try:
        scoring = await score_simulation(
            client=client,
            simulation_result=sim_result,
            ground_truth=case.ground_truth,
            case_id=f"{case.id}__{mode}",
            run_index=0,
            model=model,
        )
        if not scoring.error:
            result.accuracy_score = scoring.composite_score
            result.accuracy_dimensions = {d.name: d.score for d in scoring.dimensions}
    except Exception as e:
        result.error = f"Accuracy scoring failed: {e}"

    # Adversarial quality scoring (only if adversarial mode produced results)
    adversarial_data = sim_result.get("adversarial_result")
    if adversarial_data is not None:
        from dataclasses import asdict
        # Serialize for scoring
        adv_dict = {
            "claims": [asdict(c) for c in adversarial_data.claims],
            "survival_rate": adversarial_data.survival_rate,
            "surviving_count": len(adversarial_data.surviving_claims),
            "defeated_count": len(adversarial_data.defeated_claims),
            "key_defeats": adversarial_data.key_defeats,
        }
        result.survival_rate = adversarial_data.survival_rate
        result.claims_count = len(adversarial_data.claims)

        try:
            adv_scoring = await score_adversarial_quality(
                client=client,
                stimulus=case.stimulus,
                adversarial_result=adv_dict,
                ground_truth=case.ground_truth,
                case_id=case.id,
                run_index=0,
                model=model,
            )
            if not adv_scoring.get("error"):
                result.adversarial_quality_score = adv_scoring["composite_score"]
                result.adversarial_dimensions = {
                    k: v["score"] for k, v in adv_scoring["dimensions"].items()
                }
        except Exception as e:
            # Non-fatal — we still have accuracy scores
            pass

    return result


async def run_comparative_test(
    case_filter: Optional[str] = None,
    model_override: Optional[str] = None,
) -> list[ComparisonResult]:
    """Run all cases in both modes and generate comparative report."""
    model = model_override or DEFAULT_MODEL

    print(f"\n{'='*60}")
    print(f"  SimulateAI Comparative Validation")
    print(f"  Collaborative vs Adversarial Mode")
    print(f"  Model: {model} | Provider: {LLM_PROVIDER}")
    print(f"{'='*60}\n")

    # Load cases
    cases = []
    yaml_files = sorted(CASES_DIR.glob("*.yaml")) + sorted(CASES_DIR.glob("*.yml"))
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

    if not cases:
        print("[ERROR] No cases found.")
        return []

    print(f"Loaded {len(cases)} case(s): {', '.join(c.id for c in cases)}\n")

    # Connect LLM
    client = OllamaClient(host=OLLAMA_HOST, model=model)
    try:
        available = await client.is_available()
        if not available:
            print("[ERROR] LLM provider not available.")
            return []
        print("LLM provider connected.\n")
    except Exception as e:
        print(f"[ERROR] Failed to connect to LLM: {e}")
        return []

    comparisons = []

    for i, case in enumerate(cases):
        print(f"[{i+1}/{len(cases)}] Case: {case.name} ({case.domain})")
        comparison = ComparisonResult(
            case_id=case.id,
            case_name=case.name,
            domain=case.domain,
        )

        # Run collaborative
        print(f"  Running COLLABORATIVE mode...")
        collab = await run_mode(client, case, "collaborative", model)
        comparison.collaborative = collab
        if collab.error:
            print(f"  Collaborative ERROR: {collab.error}")
        else:
            print(f"  Collaborative: accuracy={collab.accuracy_score:.2f}/10 ({collab.elapsed_s:.1f}s)")

        # Run adversarial
        print(f"  Running ADVERSARIAL mode...")
        adv = await run_mode(client, case, "adversarial", model)
        comparison.adversarial = adv
        if adv.error:
            print(f"  Adversarial ERROR: {adv.error}")
        else:
            print(
                f"  Adversarial: accuracy={adv.accuracy_score:.2f}/10, "
                f"quality={adv.adversarial_quality_score:.2f}/10, "
                f"survival={adv.survival_rate:.0%} ({adv.elapsed_s:.1f}s)"
            )

        # Delta
        print(f"  Δ Accuracy: {comparison.accuracy_delta:+.2f} | Δ Risk ID: {comparison.risk_delta:+.1f}")
        print()

        comparisons.append(comparison)

    await client.aclose()

    # Print summary & write report
    _print_summary(comparisons)
    _write_report(comparisons, model)

    return comparisons


def _print_summary(comparisons: list[ComparisonResult]):
    """Print comparative summary to console."""
    print(f"\n{'='*60}")
    print(f"  COMPARATIVE SUMMARY")
    print(f"{'='*60}\n")

    print(f"{'Case':<25} {'Collab':<8} {'Advers':<8} {'Δ Acc':<8} {'Δ Risk':<8} {'Quality':<8} {'Surv%':<6}")
    print(f"{'-'*25} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*5}")

    for comp in comparisons:
        collab_s = f"{comp.collaborative.accuracy_score:.1f}" if comp.collaborative else "ERR"
        adv_s = f"{comp.adversarial.accuracy_score:.1f}" if comp.adversarial else "ERR"
        delta = f"{comp.accuracy_delta:+.1f}" if comp.collaborative and comp.adversarial else "N/A"
        risk_d = f"{comp.risk_delta:+.1f}" if comp.collaborative and comp.adversarial else "N/A"
        quality = f"{comp.adversarial.adversarial_quality_score:.1f}" if comp.adversarial else "N/A"
        surv = f"{comp.adversarial.survival_rate:.0%}" if comp.adversarial else "N/A"

        print(f"{comp.case_id:<25} {collab_s:<8} {adv_s:<8} {delta:<8} {risk_d:<8} {quality:<8} {surv:<6}")

    # Averages
    valid = [c for c in comparisons if c.collaborative and c.adversarial]
    if valid:
        avg_collab = sum(c.collaborative.accuracy_score for c in valid) / len(valid)
        avg_adv = sum(c.adversarial.accuracy_score for c in valid) / len(valid)
        avg_quality = sum(c.adversarial.adversarial_quality_score for c in valid) / len(valid)
        avg_delta = avg_adv - avg_collab

        print(f"\n--- Averages ---")
        print(f"Collaborative: {avg_collab:.2f}/10")
        print(f"Adversarial:   {avg_adv:.2f}/10")
        print(f"Δ Accuracy:    {avg_delta:+.2f}")
        print(f"Adv. Quality:  {avg_quality:.2f}/10")

        # Interpretation
        print(f"\n--- Interpretation ---")
        if avg_delta > 0.5:
            print("[+] Adversarial mode produces MORE ACCURATE predictions.")
            print("    Stress-testing claims improves final verdict quality.")
        elif avg_delta > -0.5:
            print("[=] Both modes produce COMPARABLE accuracy.")
            print("    Adversarial mode adds depth/rigor without harming accuracy.")
        else:
            print("[-] Adversarial mode produces LESS ACCURATE predictions.")
            print("    The debate process may be overly aggressive, defeating valid claims.")

        avg_risk_delta = sum(c.risk_delta for c in valid) / len(valid)
        if avg_risk_delta > 1.0:
            print(f"\n[+] Adversarial mode identifies SIGNIFICANTLY MORE risks (Δ={avg_risk_delta:+.1f})")
        elif avg_risk_delta > 0:
            print(f"\n[+] Adversarial mode identifies slightly more risks (Δ={avg_risk_delta:+.1f})")


def _write_report(comparisons: list[ComparisonResult], model: str):
    """Write comparative results to markdown."""
    output_path = OUTPUT_DIR / "comparative_report.md"

    lines = [
        "# SimulateAI Comparative Validation — Collaborative vs Adversarial",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Model:** `{model}`",
        "",
        "---",
        "",
        "## Methodology",
        "",
        "Each historical case is run through both modes with identical parameters:",
        "- 8 agents, concurrency 3, standard depth, no RAG",
        "- Scored by an LLM judge against ground truth (same dimensions)",
        "- Adversarial mode additionally scored on debate quality",
        "",
        "---",
        "",
        "## Results",
        "",
        "| Case | Collaborative | Adversarial | Δ Accuracy | Δ Risk ID | Adv. Quality | Survival |",
        "|------|--------------|-------------|------------|-----------|--------------|----------|",
    ]

    for comp in comparisons:
        collab_s = f"{comp.collaborative.accuracy_score:.1f}" if comp.collaborative else "ERR"
        adv_s = f"{comp.adversarial.accuracy_score:.1f}" if comp.adversarial else "ERR"
        delta = f"{comp.accuracy_delta:+.1f}" if comp.collaborative and comp.adversarial else "N/A"
        risk_d = f"{comp.risk_delta:+.1f}" if comp.collaborative and comp.adversarial else "N/A"
        quality = f"{comp.adversarial.adversarial_quality_score:.1f}" if comp.adversarial else "N/A"
        surv = f"{comp.adversarial.survival_rate:.0%}" if comp.adversarial else "N/A"
        lines.append(f"| {comp.case_id} | {collab_s} | {adv_s} | {delta} | {risk_d} | {quality} | {surv} |")

    # Averages row
    valid = [c for c in comparisons if c.collaborative and c.adversarial]
    if valid:
        avg_collab = sum(c.collaborative.accuracy_score for c in valid) / len(valid)
        avg_adv = sum(c.adversarial.accuracy_score for c in valid) / len(valid)
        avg_quality = sum(c.adversarial.adversarial_quality_score for c in valid) / len(valid)
        avg_delta = avg_adv - avg_collab
        avg_risk = sum(c.risk_delta for c in valid) / len(valid)
        lines.append(
            f"| **Average** | **{avg_collab:.1f}** | **{avg_adv:.1f}** | "
            f"**{avg_delta:+.1f}** | **{avg_risk:+.1f}** | **{avg_quality:.1f}** | |"
        )

    lines.extend(["", "---", "", "## Adversarial Quality Breakdown", ""])

    if any(c.adversarial and c.adversarial.adversarial_dimensions for c in comparisons):
        lines.extend([
            "| Case | Claim Rel. | Attack Spec. | Defense Rigor | Survival Plaus. | Insight Δ |",
            "|------|-----------|-------------|--------------|-----------------|-----------|",
        ])
        for comp in comparisons:
            if comp.adversarial and comp.adversarial.adversarial_dimensions:
                d = comp.adversarial.adversarial_dimensions
                lines.append(
                    f"| {comp.case_id} | "
                    f"{d.get('claim_relevance', 0):.1f} | "
                    f"{d.get('attack_specificity', 0):.1f} | "
                    f"{d.get('defense_rigor', 0):.1f} | "
                    f"{d.get('survival_plausibility', 0):.1f} | "
                    f"{d.get('insight_delta', 0):.1f} |"
                )
    else:
        lines.append("No adversarial quality data available.")

    # Interpretation
    lines.extend(["", "---", "", "## Interpretation", ""])

    if valid:
        avg_delta = sum(c.accuracy_delta for c in valid) / len(valid)
        avg_risk = sum(c.risk_delta for c in valid) / len(valid)
        avg_quality = sum(c.adversarial.adversarial_quality_score for c in valid) / len(valid)

        if avg_delta > 0.5:
            lines.append("**Adversarial mode improves prediction accuracy.** "
                        "Stress-testing claims leads to better-calibrated verdicts.")
        elif avg_delta > -0.5:
            lines.append("**Both modes produce comparable accuracy.** "
                        "Adversarial adds analytical depth without harming predictive power.")
        else:
            lines.append("**Adversarial mode slightly reduces accuracy.** "
                        "The debate may be too aggressive — valid claims are being defeated.")

        if avg_risk > 1.0:
            lines.append(f"\n**Risk identification is significantly better in adversarial mode** (Δ={avg_risk:+.1f}). "
                        "The stress-testing surfaces risks that collaborative consensus overlooks.")

        if avg_quality >= 7.0:
            lines.append(f"\n**Adversarial debate quality is high** ({avg_quality:.1f}/10). "
                        "Claims, attacks, and defenses are substantive and relevant.")
        elif avg_quality >= 5.0:
            lines.append(f"\n**Adversarial debate quality is moderate** ({avg_quality:.1f}/10). "
                        "Some attacks/defenses are generic; room for prompt improvement.")
        else:
            lines.append(f"\n**Adversarial debate quality needs improvement** ({avg_quality:.1f}/10). "
                        "Consider refining attack/defense prompts for more specificity.")

    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nComparative report written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="SimulateAI Comparative Validation — Collaborative vs Adversarial",
        prog="py -3 -m tests.validation.comparative_test",
    )
    parser.add_argument(
        "--case", type=str, default=None,
        help="Run a specific case by ID (e.g. svb_collapse). Omit to run all.",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help=f"Override the LLM model (default: {DEFAULT_MODEL}).",
    )
    args = parser.parse_args()

    asyncio.run(run_comparative_test(
        case_filter=args.case,
        model_override=args.model,
    ))


if __name__ == "__main__":
    main()
