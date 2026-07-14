"""LLM-based judge for scoring simulation results against ground truth."""

import json
import re
from typing import Any, Optional

from src.llm.client import OllamaClient
from src.llm.json_parse import parse_json_robustly, strip_thought_tags
from tests.validation.models import DimensionScore, ScoringResult


# Dimension weights
WEIGHTS = {
    "verdict_match": 0.30,
    "behavioral_fidelity": 0.25,
    "risk_identification": 0.25,
    "resilience_accuracy": 0.20,
}

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator assessing how well a multi-agent simulation predicted the outcome of a real-world historical event.

You will receive:
1. SIMULATION OUTPUT — the simulation's report, verdict, and resilience metrics
2. GROUND TRUTH — what actually happened in reality

Score the simulation on these 4 dimensions (each 0-10, where 10 = perfect prediction):

a) verdict_match — Does the simulation's overall conclusion/verdict align with what actually happened? Did the simulation correctly predict success/failure/mixed outcome?

b) behavioral_fidelity — Do the simulated agent behaviors (actions, arguments, concerns raised) match how real-world actors actually behaved? Were the right stakeholder dynamics captured?

c) risk_identification — Were the actual risks that materialized in reality identified by the simulation? Did agents flag the real failure modes?

d) resilience_accuracy — Was the simulation's resilience assessment (Fragile/Moderate/Resilient) correct relative to how the real situation played out?

Respond ONLY with a JSON object in this exact format:
{
    "verdict_match": {"score": <0-10>, "reasoning": "<1-2 sentences>"},
    "behavioral_fidelity": {"score": <0-10>, "reasoning": "<1-2 sentences>"},
    "risk_identification": {"score": <0-10>, "reasoning": "<1-2 sentences>"},
    "resilience_accuracy": {"score": <0-10>, "reasoning": "<1-2 sentences>"}
}"""


def _build_judge_prompt(
    report_md: str,
    verdict: str,
    resilience_metrics: dict[str, Any],
    ground_truth: dict[str, Any],
) -> str:
    """Build the user prompt for the judge LLM (blind — no case name)."""
    sim_section = (
        f"=== SIMULATION OUTPUT ===\n\n"
        f"VERDICT: {verdict}\n\n"
        f"RESILIENCE METRICS:\n"
        f"- Overall Verdict: {resilience_metrics.get('verdict', 'N/A')}\n"
        f"- Rationale: {resilience_metrics.get('rationale', 'N/A')}\n"
        f"- Pre-crisis Consensus: {resilience_metrics.get('pre_crisis_consensus', 'N/A')}\n"
        f"- Post-crisis Consensus: {resilience_metrics.get('post_crisis_consensus', 'N/A')}\n"
        f"- Stability Index: {resilience_metrics.get('stability_index', 'N/A')}\n\n"
        f"FULL REPORT:\n{report_md[:6000]}\n"  # Truncate to avoid token overflow
    )

    truth_section = (
        f"\n=== GROUND TRUTH (WHAT ACTUALLY HAPPENED) ===\n\n"
        f"OUTCOME: {ground_truth.get('outcome', 'N/A')}\n\n"
        f"ACTUAL BEHAVIORS:\n{_format_list(ground_truth.get('actual_behaviors', []))}\n\n"
        f"RISKS THAT MATERIALIZED:\n{_format_list(ground_truth.get('risks_materialized', []))}\n\n"
        f"ACTUAL RESILIENCE: {ground_truth.get('resilience', ground_truth.get('actual_resilience', 'N/A'))}\n"
    )

    if ground_truth.get("additional_context"):
        truth_section += f"\nADDITIONAL CONTEXT: {ground_truth['additional_context']}\n"

    return sim_section + truth_section


def _format_list(items: list) -> str:
    if not items:
        return "  (none specified)"
    return "\n".join(f"  - {item}" for item in items)


def _parse_scores(raw: str) -> Optional[dict[str, dict[str, Any]]]:
    """Parse judge response as JSON, with regex fallback."""
    cleaned = strip_thought_tags(raw)

    # Try JSON parse
    parsed = parse_json_robustly(cleaned)
    if parsed and "verdict_match" in parsed:
        return parsed

    # Regex fallback: extract individual dimension scores
    result = {}
    for dim in WEIGHTS.keys():
        pattern = rf'"{dim}"\s*:\s*\{{\s*"score"\s*:\s*(\d+(?:\.\d+)?)'
        match = re.search(pattern, cleaned)
        if match:
            score_val = float(match.group(1))
            # Try to get reasoning too
            reasoning_pattern = rf'"{dim}"[^{{]*\{{[^}}]*"reasoning"\s*:\s*"([^"]*)"'
            reasoning_match = re.search(reasoning_pattern, cleaned)
            reasoning = reasoning_match.group(1) if reasoning_match else ""
            result[dim] = {"score": score_val, "reasoning": reasoning}

    if len(result) >= 3:  # Accept if at least 3 of 4 dimensions parsed
        # Fill missing with 5.0
        for dim in WEIGHTS.keys():
            if dim not in result:
                result[dim] = {"score": 5.0, "reasoning": "parse failure — default score"}
        return result

    return None


async def score_simulation(
    client: OllamaClient,
    simulation_result: dict[str, Any],
    ground_truth: dict[str, Any],
    case_id: str,
    run_index: int,
    model: Optional[str] = None,
) -> ScoringResult:
    """Score a simulation result against ground truth using an LLM judge.

    Args:
        client: LLM client for the judge call.
        simulation_result: Output from run_simulation_pipeline.
        ground_truth: Ground truth dict from the YAML case file.
        case_id: Identifier for the case (for tracking only).
        run_index: Which run number this is.
        model: Override model for the judge LLM.

    Returns:
        ScoringResult with per-dimension scores.
    """
    report_md = simulation_result.get("report_md", "")
    resilience_metrics = simulation_result.get("resilience_metrics", {})
    verdict = resilience_metrics.get("verdict", "Unknown")

    user_prompt = _build_judge_prompt(report_md, verdict, resilience_metrics, ground_truth)

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw_response = await client.chat(
            messages,
            model=model,
            timeout=120.0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        return ScoringResult(
            case_id=case_id,
            run_index=run_index,
            verdict_match=DimensionScore("verdict_match", 0, WEIGHTS["verdict_match"]),
            behavioral_fidelity=DimensionScore("behavioral_fidelity", 0, WEIGHTS["behavioral_fidelity"]),
            risk_identification=DimensionScore("risk_identification", 0, WEIGHTS["risk_identification"]),
            resilience_accuracy=DimensionScore("resilience_accuracy", 0, WEIGHTS["resilience_accuracy"]),
            raw_llm_response="",
            error=f"LLM judge call failed: {e}",
        )

    scores = _parse_scores(raw_response)
    if scores is None:
        return ScoringResult(
            case_id=case_id,
            run_index=run_index,
            verdict_match=DimensionScore("verdict_match", 0, WEIGHTS["verdict_match"]),
            behavioral_fidelity=DimensionScore("behavioral_fidelity", 0, WEIGHTS["behavioral_fidelity"]),
            risk_identification=DimensionScore("risk_identification", 0, WEIGHTS["risk_identification"]),
            resilience_accuracy=DimensionScore("resilience_accuracy", 0, WEIGHTS["resilience_accuracy"]),
            raw_llm_response=raw_response,
            error=f"Failed to parse judge response",
        )

    def _make_dim(name: str) -> DimensionScore:
        dim_data = scores.get(name, {})
        raw_score = dim_data.get("score", 0)
        # Clamp to 0-10
        clamped = max(0.0, min(10.0, float(raw_score)))
        return DimensionScore(
            name=name,
            score=clamped,
            weight=WEIGHTS[name],
            reasoning=dim_data.get("reasoning", ""),
        )

    return ScoringResult(
        case_id=case_id,
        run_index=run_index,
        verdict_match=_make_dim("verdict_match"),
        behavioral_fidelity=_make_dim("behavioral_fidelity"),
        risk_identification=_make_dim("risk_identification"),
        resilience_accuracy=_make_dim("resilience_accuracy"),
        raw_llm_response=raw_response,
    )
