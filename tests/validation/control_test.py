"""Control test — baseline comparison to detect data contamination.

Runs TWO controls for each validation case:
1. DIRECT PROMPT: Same stimulus → single LLM call "predict what happens" (no pipeline)
2. DECONTAMINATED: Strip identifying names/dates → single LLM call (tests pure reasoning)

Compares control scores vs pipeline scores to measure:
- Pipeline value-add (pipeline_score - direct_score)
- Contamination signal (direct_score - decontaminated_score)

If direct_score ≈ pipeline_score → pipeline adds little, model just recalls
If direct_score >> decontaminated_score → model is recognizing the event, not reasoning
If pipeline_score >> direct_score → pipeline genuinely adds analytical value

Usage:
    py -3 -m tests.validation.control_test [--case svb_collapse] [--model gemma3:4b]
"""

import argparse
import asyncio
import re
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
from tests.validation.models import ValidationCase, DimensionScore, ScoringResult
from tests.validation.scorer import score_simulation, WEIGHTS


CASES_DIR = Path(__file__).resolve().parent / "cases"


# --- Decontamination mappings per case ---
# Maps identifying terms → generic replacements
DECONTAMINATION_MAPS: dict[str, dict[str, str]] = {
    "svb_collapse": {
        "Silicon Valley Bank": "a mid-size regional bank",
        "SVB": "the bank",
        "Founders Fund": "a prominent venture capital firm",
        "Coatue Management": "another major investment firm",
        "FDIC": "the federal deposit insurer",
        "Peter Thiel": "a prominent tech investor",
        "Greg Becker": "the bank's CEO",
        "2023": "recently",
        "March 2023": "recently",
        "March 8": "on Wednesday",
        "March 9": "the following day",
        "March 10": "two days later",
        "$209B": "$200B+",
        "16th largest US bank": "a top-20 US bank",
    },
    "openai_board_crisis": {
        "OpenAI": "a leading AI research company",
        "Sam Altman": "the CEO",
        "Microsoft": "the company's largest investor",
        "Satya Nadella": "the investor's CEO",
        "Ilya Sutskever": "the chief scientist",
        "Mira Murati": "the interim CEO",
        "Greg Brockman": "the president",
        "Emmett Shear": "an external executive",
        "$90B": "$90B",
        "$13B": "$13B",
        "2023": "recently",
        "November 2023": "recently",
        "700 of 770": "over 90%",
    },
    "crowdstrike_outage": {
        "CrowdStrike": "a major cybersecurity vendor",
        "Falcon": "its endpoint protection agent",
        "Channel File 291": "a configuration file",
        "George Kurtz": "the company's CEO",
        "Delta Airlines": "a major airline",
        "Microsoft": "the operating system vendor",
        "Windows": "the dominant desktop OS",
        "July 2024": "recently",
        "July 19": "on Friday",
        "8.5 million": "millions of",
        "29,000": "tens of thousands of",
    },
    "gamestop_squeeze": {
        "GameStop": "a struggling brick-and-mortar retailer",
        "GME": "the stock",
        "Melvin Capital": "a prominent short-selling hedge fund",
        "r/WallStreetBets": "a large retail-investor online forum",
        "Reddit": "a social media platform",
        "Robinhood": "a popular commission-free brokerage",
        "Citadel": "a major market maker",
        "Point72": "another large hedge fund",
        "Keith Gill": "a retail investor influencer",
        "Roaring Kitty": "a retail investor influencer",
        "January 2021": "recently",
        "2021": "recently",
    },
    "tiktok_ban": {
        "TikTok": "a popular short-video social media platform",
        "ByteDance": "the platform's Chinese parent company",
        "Biden": "the current president",
        "Trump": "the incoming president",
        "Supreme Court": "the highest court",
        "Congress": "the national legislature",
        "China": "the parent company's home country",
        "RedNote": "an alternative platform",
        "Lemon8": "a sister app",
        "Oracle": "a US tech company",
        "170 million": "over 150 million",
        "2024": "recently",
        "$225B": "over $200B",
        "April 2024": "recently",
        "January 2025": "months later",
    },
}


DIRECT_PREDICT_PROMPT = """You are a geopolitical and market analyst. Given the following situation description, predict what will happen next. Be specific about:
1. The most likely outcome (what happens to the main entity/situation)
2. How key stakeholders will behave
3. What risks are most likely to materialize
4. How resilient or fragile the situation is (rate as Fragile, Moderate, or Resilient)

Provide your analysis in a structured format.

SITUATION:
{stimulus}

PREDICTION:"""


DIRECT_PREDICT_SYSTEM = """You are an expert analyst making predictions about real-world events based ONLY on the information provided. Do NOT reference any specific real-world events you may know about. Reason purely from the structural dynamics described.

Provide your prediction as a structured analysis covering:
- VERDICT: What is the most likely outcome? (1-2 sentences)
- KEY BEHAVIORS: How will each major actor likely behave? (list each actor and predicted action)
- RISKS: What are the top 3-5 risks most likely to materialize?
- RESILIENCE: Rate the situation as Fragile, Moderate, or Resilient and explain why.
- TIMELINE: How quickly will this unfold?"""


@dataclass
class ControlResult:
    """Result from a single control test."""
    case_id: str
    mode: str  # "direct" or "decontaminated"
    scoring: Optional[ScoringResult] = None
    raw_prediction: str = ""
    error: Optional[str] = None


@dataclass
class ControlComparison:
    """Comparison between pipeline and control scores."""
    case_id: str
    case_name: str
    domain: str
    direct_score: float = 0.0
    decontaminated_score: float = 0.0
    pipeline_value_add: float = 0.0  # pipeline - direct
    contamination_signal: float = 0.0  # direct - decontaminated
    direct_dimensions: dict[str, float] = field(default_factory=dict)
    decontaminated_dimensions: dict[str, float] = field(default_factory=dict)


def decontaminate_stimulus(stimulus: str, case_id: str) -> str:
    """Strip identifying info from stimulus to prevent model recall."""
    mappings = DECONTAMINATION_MAPS.get(case_id, {})
    result = stimulus
    # Sort by length descending so longer matches replace first
    for original, replacement in sorted(mappings.items(), key=lambda x: -len(x[0])):
        result = result.replace(original, replacement)
    return result


def _build_sim_result_from_prediction(raw_prediction: str) -> dict[str, Any]:
    """Wrap a raw LLM prediction into the format score_simulation expects."""
    # Extract resilience rating from the prediction text
    resilience = "Unknown"
    for label in ["Fragile", "Moderate", "Resilient"]:
        if label.lower() in raw_prediction.lower():
            resilience = label
            break

    return {
        "report_md": raw_prediction,
        "resilience_metrics": {
            "verdict": _extract_verdict(raw_prediction),
            "rationale": raw_prediction[:500],
            "pre_crisis_consensus": "N/A (control test)",
            "post_crisis_consensus": "N/A (control test)",
            "stability_index": "N/A",
        },
    }


def _extract_verdict(text: str) -> str:
    """Extract the verdict/outcome line from a prediction."""
    # Look for VERDICT: line
    match = re.search(r"VERDICT[:\s]*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: first sentence
    sentences = text.split(".")
    return sentences[0].strip() if sentences else "Unknown"


async def run_direct_prediction(
    client: OllamaClient,
    stimulus: str,
    model: Optional[str] = None,
) -> str:
    """Run a single direct LLM prediction (no pipeline)."""
    messages = [
        {"role": "system", "content": DIRECT_PREDICT_SYSTEM},
        {"role": "user", "content": DIRECT_PREDICT_PROMPT.format(stimulus=stimulus)},
    ]
    response = await client.chat(messages, model=model, timeout=120.0)
    return response


async def run_control_for_case(
    client: OllamaClient,
    case: ValidationCase,
    mode: str,  # "direct" or "decontaminated"
    model: Optional[str] = None,
) -> ControlResult:
    """Run a control test (direct or decontaminated) for one case."""
    if mode == "decontaminated":
        stimulus = decontaminate_stimulus(case.stimulus, case.id)
    else:
        stimulus = case.stimulus

    try:
        raw_prediction = await run_direct_prediction(client, stimulus, model)
    except Exception as e:
        return ControlResult(
            case_id=case.id, mode=mode, error=f"Prediction failed: {e}"
        )

    # Wrap into sim-result format for scoring
    sim_result = _build_sim_result_from_prediction(raw_prediction)

    # Score against ground truth
    try:
        scoring = await score_simulation(
            client=client,
            simulation_result=sim_result,
            ground_truth=case.ground_truth,
            case_id=f"{case.id}__{mode}",
            run_index=0,
            model=model,
        )
    except Exception as e:
        return ControlResult(
            case_id=case.id,
            mode=mode,
            raw_prediction=raw_prediction,
            error=f"Scoring failed: {e}",
        )

    return ControlResult(
        case_id=case.id,
        mode=mode,
        scoring=scoring,
        raw_prediction=raw_prediction,
    )


async def run_control_tests(
    case_filter: Optional[str] = None,
    model_override: Optional[str] = None,
    pipeline_scores: Optional[dict[str, float]] = None,
) -> list[ControlComparison]:
    """Run control tests for all cases and compare with pipeline scores."""
    model = model_override or DEFAULT_MODEL

    print(f"\n{'='*60}")
    print(f"  SimulateAI Control Test — Data Contamination Check")
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

        # Show decontaminated stimulus preview
        decontaminated = decontaminate_stimulus(case.stimulus, case.id)
        print(f"  Decontaminated preview: {decontaminated[:80].strip()}...")

        # Run direct prediction
        print(f"  Running DIRECT prediction...")
        t0 = time.time()
        direct_result = await run_control_for_case(client, case, "direct", model)
        t1 = time.time()
        print(f"  Direct done ({t1-t0:.1f}s)")

        # Run decontaminated prediction
        print(f"  Running DECONTAMINATED prediction...")
        decontam_result = await run_control_for_case(client, case, "decontaminated", model)
        t2 = time.time()
        print(f"  Decontaminated done ({t2-t1:.1f}s)")

        # Build comparison
        comp = ControlComparison(
            case_id=case.id,
            case_name=case.name,
            domain=case.domain,
        )

        if direct_result.scoring and not direct_result.scoring.error:
            comp.direct_score = direct_result.scoring.composite_score
            comp.direct_dimensions = {
                d.name: d.score for d in direct_result.scoring.dimensions
            }

        if decontam_result.scoring and not decontam_result.scoring.error:
            comp.decontaminated_score = decontam_result.scoring.composite_score
            comp.decontaminated_dimensions = {
                d.name: d.score for d in decontam_result.scoring.dimensions
            }

        # Get pipeline score if available
        pipeline_score = (pipeline_scores or {}).get(case.id, 0.0)
        comp.pipeline_value_add = pipeline_score - comp.direct_score
        comp.contamination_signal = comp.direct_score - comp.decontaminated_score

        comparisons.append(comp)

        print(f"  Direct score: {comp.direct_score:.2f}/10")
        print(f"  Decontaminated score: {comp.decontaminated_score:.2f}/10")
        if pipeline_score > 0:
            print(f"  Pipeline score: {pipeline_score:.2f}/10")
            print(f"  Pipeline value-add: {comp.pipeline_value_add:+.2f}")
        print(f"  Contamination signal: {comp.contamination_signal:+.2f}")
        print()

    await client.aclose()

    # Print summary
    _print_control_summary(comparisons, pipeline_scores)

    # Write report
    _write_control_report(comparisons, model, pipeline_scores)

    return comparisons


def _print_control_summary(
    comparisons: list[ControlComparison],
    pipeline_scores: Optional[dict[str, float]] = None,
):
    """Print control test summary to console."""
    print(f"\n{'='*60}")
    print(f"  CONTROL TEST SUMMARY")
    print(f"{'='*60}\n")

    print(f"{'Case':<25} {'Direct':<8} {'Decontam':<10} {'Contam.Signal':<15} {'Pipeline':<10} {'Value-Add':<10}")
    print(f"{'-'*25} {'-'*7} {'-'*9} {'-'*14} {'-'*9} {'-'*9}")

    for comp in comparisons:
        pipeline = (pipeline_scores or {}).get(comp.case_id, 0.0)
        pipeline_str = f"{pipeline:.1f}" if pipeline > 0 else "N/A"
        value_add_str = f"{comp.pipeline_value_add:+.1f}" if pipeline > 0 else "N/A"
        print(
            f"{comp.case_id:<25} "
            f"{comp.direct_score:<8.1f} "
            f"{comp.decontaminated_score:<10.1f} "
            f"{comp.contamination_signal:<+15.1f} "
            f"{pipeline_str:<10} "
            f"{value_add_str:<10}"
        )

    # Interpretation
    avg_contam = sum(c.contamination_signal for c in comparisons) / len(comparisons) if comparisons else 0
    avg_direct = sum(c.direct_score for c in comparisons) / len(comparisons) if comparisons else 0
    avg_decontam = sum(c.decontaminated_score for c in comparisons) / len(comparisons) if comparisons else 0

    print(f"\n--- Interpretation ---")
    print(f"Avg Direct Score: {avg_direct:.2f}/10")
    print(f"Avg Decontaminated Score: {avg_decontam:.2f}/10")
    print(f"Avg Contamination Signal: {avg_contam:+.2f}")

    if avg_contam > 2.0:
        print("\n[!] HIGH contamination signal — model is likely recognizing events from training data.")
        print("    Decontaminated scores represent truer 'reasoning from structure' ability.")
    elif avg_contam > 1.0:
        print("\n[~] MODERATE contamination signal — some recall, but structural reasoning contributes.")
    else:
        print("\n[OK] LOW contamination signal — model appears to reason from structure, not recall.")

    if pipeline_scores:
        avg_pipeline = sum(pipeline_scores.values()) / len(pipeline_scores)
        avg_value = avg_pipeline - avg_direct
        if avg_value > 1.5:
            print(f"\n[+] Pipeline adds SIGNIFICANT value ({avg_value:+.1f}) over direct prompting.")
            print("    Multi-agent debate genuinely improves prediction quality.")
        elif avg_value > 0.5:
            print(f"\n[+] Pipeline adds MODERATE value ({avg_value:+.1f}) over direct prompting.")
        else:
            print(f"\n[-] Pipeline adds MINIMAL value ({avg_value:+.1f}) over direct prompting.")
            print("    Consider whether the pipeline overhead is justified.")


def _write_control_report(
    comparisons: list[ControlComparison],
    model: str,
    pipeline_scores: Optional[dict[str, float]] = None,
):
    """Write control test results to markdown file."""
    output_path = Path(__file__).resolve().parent / "control_report.md"

    lines = [
        "# SimulateAI Control Test — Data Contamination Analysis",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Model:** `{model}`",
        "",
        "---",
        "",
        "## Methodology",
        "",
        "Two controls per case to isolate pipeline value from model recall:",
        "",
        "| Mode | What it tests |",
        "|------|--------------|",
        "| **Direct** | Same stimulus → single LLM call (no pipeline). Measures raw model prediction ability. |",
        "| **Decontaminated** | Identifying names/dates stripped → single LLM call. Measures pure structural reasoning. |",
        "",
        "**Key Metrics:**",
        "- `Pipeline Value-Add` = pipeline_score - direct_score (positive = pipeline helps)",
        "- `Contamination Signal` = direct_score - decontaminated_score (positive = model recognizes event)",
        "",
        "---",
        "",
        "## Results",
        "",
        "| Case | Direct | Decontaminated | Contam. Signal | Pipeline | Value-Add |",
        "|------|--------|----------------|----------------|----------|-----------|",
    ]

    for comp in comparisons:
        pipeline = (pipeline_scores or {}).get(comp.case_id, 0.0)
        pipeline_str = f"{pipeline:.1f}" if pipeline > 0 else "N/A"
        value_add_str = f"{comp.pipeline_value_add:+.1f}" if pipeline > 0 else "N/A"
        lines.append(
            f"| {comp.case_id} | {comp.direct_score:.1f} | "
            f"{comp.decontaminated_score:.1f} | {comp.contamination_signal:+.1f} | "
            f"{pipeline_str} | {value_add_str} |"
        )

    # Averages
    avg_direct = sum(c.direct_score for c in comparisons) / len(comparisons) if comparisons else 0
    avg_decontam = sum(c.decontaminated_score for c in comparisons) / len(comparisons) if comparisons else 0
    avg_contam = sum(c.contamination_signal for c in comparisons) / len(comparisons) if comparisons else 0
    lines.append(
        f"| **Average** | **{avg_direct:.1f}** | **{avg_decontam:.1f}** | "
        f"**{avg_contam:+.1f}** | | |"
    )

    lines.extend([
        "",
        "---",
        "",
        "## Interpretation",
        "",
    ])

    if avg_contam > 2.0:
        lines.append("**HIGH contamination detected.** The model is likely recognizing these events from training data. "
                     "Decontaminated scores better represent the system's structural reasoning ability.")
    elif avg_contam > 1.0:
        lines.append("**MODERATE contamination.** Some event recall is occurring, but structural reasoning "
                     "also contributes to prediction accuracy.")
    else:
        lines.append("**LOW contamination.** The model appears to reason primarily from structural dynamics, "
                     "not from recall of specific events.")

    if pipeline_scores:
        avg_pipeline = sum(pipeline_scores.values()) / len(pipeline_scores)
        avg_value = avg_pipeline - avg_direct
        lines.extend([
            "",
            f"**Pipeline Value-Add: {avg_value:+.1f}**",
            "",
        ])
        if avg_value > 1.5:
            lines.append("The multi-agent pipeline adds **significant** analytical value beyond raw model prediction.")
        elif avg_value > 0.5:
            lines.append("The multi-agent pipeline adds **moderate** value over direct prompting.")
        else:
            lines.append("The multi-agent pipeline adds **minimal** value over direct prompting for these cases.")

    lines.extend([
        "",
        "---",
        "",
        "## Per-Dimension Breakdown",
        "",
        "| Case | Mode | Verdict | Behavior | Risk | Resilience |",
        "|------|------|---------|----------|------|------------|",
    ])

    for comp in comparisons:
        dd = comp.direct_dimensions
        de = comp.decontaminated_dimensions
        lines.append(
            f"| {comp.case_id} | Direct | "
            f"{dd.get('verdict_match', 0):.1f} | {dd.get('behavioral_fidelity', 0):.1f} | "
            f"{dd.get('risk_identification', 0):.1f} | {dd.get('resilience_accuracy', 0):.1f} |"
        )
        lines.append(
            f"| {comp.case_id} | Decontam | "
            f"{de.get('verdict_match', 0):.1f} | {de.get('behavioral_fidelity', 0):.1f} | "
            f"{de.get('risk_identification', 0):.1f} | {de.get('resilience_accuracy', 0):.1f} |"
        )

    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nControl report written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="SimulateAI Control Test — Data Contamination Check",
        prog="py -3 -m tests.validation.control_test",
    )
    parser.add_argument(
        "--case", type=str, default=None,
        help="Run a specific case by ID (e.g. svb_collapse). Omit to run all.",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help=f"Override the LLM model (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--pipeline-scores", type=str, default=None,
        help="Comma-separated case_id:score pairs from previous pipeline run (e.g. svb_collapse:8.7,crowdstrike_outage:6.2)",
    )
    args = parser.parse_args()

    # Parse pipeline scores if provided
    pipeline_scores = None
    if args.pipeline_scores:
        pipeline_scores = {}
        for pair in args.pipeline_scores.split(","):
            k, v = pair.strip().split(":")
            pipeline_scores[k.strip()] = float(v.strip())

    asyncio.run(run_control_tests(
        case_filter=args.case,
        model_override=args.model,
        pipeline_scores=pipeline_scores,
    ))


if __name__ == "__main__":
    main()
