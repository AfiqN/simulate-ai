"""LLM-based judge for scoring adversarial debate quality.

Evaluates the quality of the adversarial process itself — not just
whether the final verdict matches reality, but whether the debate
mechanism produced rigorous stress-testing of claims.
"""

import json
import re
from typing import Any, Optional

from src.llm.client import OllamaClient
from src.llm.json_parse import parse_json_robustly, strip_thought_tags
from tests.validation.models import DimensionScore


# Dimension weights for adversarial quality scoring
ADVERSARIAL_WEIGHTS = {
    "claim_relevance": 0.20,
    "attack_specificity": 0.25,
    "defense_rigor": 0.20,
    "survival_plausibility": 0.20,
    "insight_delta": 0.15,
}

ADVERSARIAL_JUDGE_SYSTEM = """You are an expert evaluator assessing the quality of an adversarial debate process in a multi-agent simulation.

You will receive:
1. THE STIMULUS — the original scenario being debated
2. ADVERSARIAL RESULTS — claims extracted, attacks made, defenses given, and final statuses
3. GROUND TRUTH — what actually happened in reality (for calibration)

Score the adversarial debate on these 5 dimensions (each 0-10, where 10 = perfect):

a) claim_relevance — Were the extracted claims actually relevant to the scenario's key decision points? Did they capture the core arguments, not peripheral noise?

b) attack_specificity — Were the attacks targeted and substantive? Did they identify real logical weaknesses, evidence gaps, or counterexamples — rather than generic objections?

c) defense_rigor — Did surviving claims earn their survival through genuine evidence and reasoning? Were defenses substantive rather than hand-waving?

d) survival_plausibility — Looking at the ground truth, did the RIGHT claims survive? Were the claims that should have been defeated actually defeated? Does the survival pattern match what reality proved?

e) insight_delta — Did the adversarial process surface insights/risks that would NOT have emerged from a simple collaborative discussion? Did the stress-testing reveal something non-obvious?

Respond ONLY with a JSON object in this exact format:
{
    "claim_relevance": {"score": <0-10>, "reasoning": "<1-2 sentences>"},
    "attack_specificity": {"score": <0-10>, "reasoning": "<1-2 sentences>"},
    "defense_rigor": {"score": <0-10>, "reasoning": "<1-2 sentences>"},
    "survival_plausibility": {"score": <0-10>, "reasoning": "<1-2 sentences>"},
    "insight_delta": {"score": <0-10>, "reasoning": "<1-2 sentences>"}
}"""


def _build_adversarial_judge_prompt(
    stimulus: str,
    adversarial_result: dict[str, Any],
    ground_truth: dict[str, Any],
) -> str:
    """Build the user prompt for adversarial quality judging."""
    # Format claims summary
    claims_text = ""
    for i, claim in enumerate(adversarial_result.get("claims", []), 1):
        status = claim.get("status", "unknown")
        archetype = claim.get("archetype", "unknown")
        claim_text = claim.get("claim_text", "")
        attack = claim.get("attack_text", "N/A")
        defense = claim.get("defense_text", "N/A")
        severity = claim.get("attack_severity", "N/A")

        claims_text += (
            f"\n  Claim {i} [{status.upper()}] (by {archetype}):\n"
            f"    Assertion: \"{claim_text}\"\n"
            f"    Attack ({severity}): {attack}\n"
            f"    Defense: {defense}\n"
        )

    survival_rate = adversarial_result.get("survival_rate", 0)
    key_defeats = adversarial_result.get("key_defeats", [])

    adversarial_section = (
        f"=== ADVERSARIAL RESULTS ===\n\n"
        f"Survival Rate: {survival_rate:.0%}\n"
        f"Surviving: {adversarial_result.get('surviving_count', 0)} | "
        f"Defeated: {adversarial_result.get('defeated_count', 0)}\n\n"
        f"Key Defeats: {'; '.join(key_defeats) if key_defeats else 'None'}\n\n"
        f"Claims:{claims_text}\n"
    )

    truth_section = (
        f"\n=== GROUND TRUTH (WHAT ACTUALLY HAPPENED) ===\n\n"
        f"OUTCOME: {ground_truth.get('outcome', 'N/A')}\n\n"
        f"RISKS THAT MATERIALIZED:\n"
        + "\n".join(f"  - {r}" for r in ground_truth.get("risks_materialized", []))
        + f"\n\nACTUAL RESILIENCE: {ground_truth.get('resilience', ground_truth.get('actual_resilience', 'N/A'))}\n"
    )

    stimulus_section = (
        f"=== STIMULUS ===\n\n"
        f"{stimulus[:3000]}\n"
    )

    return stimulus_section + "\n" + adversarial_section + "\n" + truth_section


def _parse_adversarial_scores(raw: str) -> Optional[dict[str, dict[str, Any]]]:
    """Parse adversarial judge response as JSON, with regex fallback."""
    cleaned = strip_thought_tags(raw)

    parsed = parse_json_robustly(cleaned)
    if parsed and "claim_relevance" in parsed:
        return parsed

    # Regex fallback
    result = {}
    for dim in ADVERSARIAL_WEIGHTS.keys():
        pattern = rf'"{dim}"\s*:\s*\{{\s*"score"\s*:\s*(\d+(?:\.\d+)?)'
        match = re.search(pattern, cleaned)
        if match:
            score_val = float(match.group(1))
            reasoning_pattern = rf'"{dim}"[^{{]*\{{[^}}]*"reasoning"\s*:\s*"([^"]*)"'
            reasoning_match = re.search(reasoning_pattern, cleaned)
            reasoning = reasoning_match.group(1) if reasoning_match else ""
            result[dim] = {"score": score_val, "reasoning": reasoning}

    if len(result) >= 4:
        for dim in ADVERSARIAL_WEIGHTS.keys():
            if dim not in result:
                result[dim] = {"score": 5.0, "reasoning": "parse failure — default score"}
        return result

    return None


async def score_adversarial_quality(
    client: OllamaClient,
    stimulus: str,
    adversarial_result: dict[str, Any],
    ground_truth: dict[str, Any],
    case_id: str,
    run_index: int,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """Score the quality of an adversarial debate process.

    Returns:
        Dict with per-dimension scores, composite score, and raw response.
    """
    if not adversarial_result or not adversarial_result.get("claims"):
        return {
            "case_id": case_id,
            "run_index": run_index,
            "composite_score": 0.0,
            "dimensions": {},
            "error": "No adversarial result or claims to evaluate",
        }

    user_prompt = _build_adversarial_judge_prompt(stimulus, adversarial_result, ground_truth)

    messages = [
        {"role": "system", "content": ADVERSARIAL_JUDGE_SYSTEM},
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
        return {
            "case_id": case_id,
            "run_index": run_index,
            "composite_score": 0.0,
            "dimensions": {},
            "raw_response": "",
            "error": f"LLM judge call failed: {e}",
        }

    scores = _parse_adversarial_scores(raw_response)
    if scores is None:
        return {
            "case_id": case_id,
            "run_index": run_index,
            "composite_score": 0.0,
            "dimensions": {},
            "raw_response": raw_response,
            "error": "Failed to parse adversarial judge response",
        }

    # Build dimension scores
    dimensions = {}
    composite = 0.0
    for dim_name, weight in ADVERSARIAL_WEIGHTS.items():
        dim_data = scores.get(dim_name, {})
        raw_score = max(0.0, min(10.0, float(dim_data.get("score", 0))))
        dimensions[dim_name] = {
            "score": raw_score,
            "weight": weight,
            "weighted": raw_score * weight,
            "reasoning": dim_data.get("reasoning", ""),
        }
        composite += raw_score * weight

    return {
        "case_id": case_id,
        "run_index": run_index,
        "composite_score": composite,
        "dimensions": dimensions,
        "raw_response": raw_response,
        "error": None,
    }
