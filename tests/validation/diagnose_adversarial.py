"""Diagnostic: trace adversarial debate for CrowdStrike case.

Runs the adversarial pipeline with detailed logging at each phase to understand
why 100% survival occurs and how it impacts accuracy.

Usage:
    py -3 -u -m tests.validation.diagnose_adversarial --case crowdstrike_outage
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import DEFAULT_MODEL, OLLAMA_HOST, LLM_PROVIDER
from src.llm.client import OllamaClient
from src.agent.adversary import compute_adversary_map, ArgumentClaim, AdversarialRoundResult
from src.agent.agent import Agent
from src.agent.swarm import generate_llm_swarm
from src.schema.architect import design_schema
from src.cli.simulation import run_simulation_pipeline
from tests.validation.models import ValidationCase

CASES_DIR = Path(__file__).resolve().parent / "cases"


def load_case(case_id: str) -> Optional[ValidationCase]:
    yaml_files = sorted(CASES_DIR.glob("*.yaml")) + sorted(CASES_DIR.glob("*.yml"))
    for yaml_path in yaml_files:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            continue
        case = ValidationCase.from_dict(data, filename=yaml_path.stem)
        if case.id == case_id:
            return case
    return None


async def diagnose(case_id: str, model_override: Optional[str] = None):
    model = model_override or DEFAULT_MODEL
    case = load_case(case_id)
    if not case:
        print(f"[ERROR] Case '{case_id}' not found")
        return

    print(f"\n{'='*70}")
    print(f"  ADVERSARIAL DIAGNOSTIC: {case.name}")
    print(f"  Model: {model} | Domain: {case.domain}")
    print(f"{'='*70}\n")

    client = OllamaClient(host=OLLAMA_HOST, model=model)
    available = await client.is_available()
    if not available:
        print("[ERROR] LLM provider not available.")
        return

    # Collect events during the run
    events: list[dict] = []

    def event_collector(event: dict):
        events.append(event)

    print("Running adversarial simulation with event capture...\n")

    result = await run_simulation_pipeline(
        client=client,
        stimulus=case.stimulus,
        agent_count=8,
        concurrency=3,
        headless=True,
        rag_enabled=False,
        depth="standard",
        mode="adversarial",
        event_callback=event_collector,
    )

    await client.aclose()

    # --- Analyze events ---
    print(f"\n{'='*70}")
    print("  DIAGNOSTIC ANALYSIS")
    print(f"{'='*70}\n")

    # 1. Round 1 actions — did agents converge?
    r1_event = next((e for e in events if e.get("type") == "round_summary" and e.get("round") == 1), None)
    if r1_event:
        decisions = r1_event.get("data", {}).get("decisions", [])
        actions = [d.get("action", "?") for d in decisions]
        action_counts = {}
        for a in actions:
            action_counts[a] = action_counts.get(a, 0) + 1
        print("1. ROUND 1 ACTION DISTRIBUTION:")
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            print(f"   {action}: {count} agents ({count/len(actions)*100:.0f}%)")
        print(f"   Consensus level: {'HIGH' if max(action_counts.values()) >= 6 else 'MODERATE' if max(action_counts.values()) >= 4 else 'LOW'}")
        print()

        # Utility spread
        utilities = [d.get("utility", 0) for d in decisions]
        if utilities:
            print(f"   Utility spread: min={min(utilities):.2f}, max={max(utilities):.2f}, range={max(utilities)-min(utilities):.2f}")
            print()

    # 2. Adversarial claims event
    claims_event = next((e for e in events if e.get("type") == "adversarial_claims"), None)
    if claims_event:
        print(f"2. CLAIMS EXTRACTED: {claims_event.get('total', 0)} total")
        per_agent = claims_event.get("per_agent", {})
        for aid, count in per_agent.items():
            print(f"   {aid}: {count} claims")
        print()

    # 3. Adversarial result
    adv_event = next((e for e in events if e.get("type") == "adversarial_result"), None)
    if adv_event:
        print(f"3. ADVERSARIAL OUTCOME:")
        print(f"   Total claims: {adv_event.get('total_claims', 0)}")
        print(f"   Survived: {adv_event.get('survived', 0)}")
        print(f"   Defeated: {adv_event.get('defeated', 0)}")
        survival_rate = adv_event.get("survival_rate", 0)
        print(f"   Survival rate: {survival_rate:.0%}")
        print()

    # 4. Check adversarial_result object for detailed claim analysis
    adv_result = result.get("adversarial_result")
    if adv_result and hasattr(adv_result, "claims"):
        print("4. DETAILED CLAIM ANALYSIS:")
        print(f"   {'Status':<10} {'Archetype':<20} {'Claim (truncated)':<50} {'Attack Sev.':<12}")
        print(f"   {'-'*10} {'-'*20} {'-'*50} {'-'*12}")
        for claim in adv_result.claims:
            status_icon = "ALIVE" if claim.survived else "DEAD"
            claim_short = claim.claim_text[:48] + ".." if len(claim.claim_text) > 50 else claim.claim_text
            sev = claim.attack_severity or "none"
            print(f"   {status_icon:<10} {claim.archetype:<20} {claim_short:<50} {sev:<12}")
        print()

        # 5. Attack/defense breakdown
        print("5. ATTACK & DEFENSE DETAIL:")
        for i, claim in enumerate(adv_result.claims):
            print(f"\n   --- Claim {i+1} [{claim.status}] by {claim.archetype} ---")
            print(f"   Claim: \"{claim.claim_text[:100]}\"")
            if claim.attack_text:
                print(f"   Attack ({claim.attack_severity}): \"{claim.attack_text[:120]}\"")
            else:
                print(f"   Attack: NONE (not attacked)")
            if claim.defense_text:
                print(f"   Defense ({claim.defense_response}): \"{claim.defense_text[:120]}\"")
            else:
                print(f"   Defense: N/A")

        # 6. Key pattern analysis
        print(f"\n\n6. PATTERN ANALYSIS:")
        attacked_claims = [c for c in adv_result.claims if c.attack_text]
        unattacked = [c for c in adv_result.claims if not c.attack_text]
        rebuts = [c for c in attacked_claims if c.defense_response == "rebut"]
        concedes = [c for c in attacked_claims if c.defense_response == "concede"]
        amends = [c for c in attacked_claims if c.defense_response == "amend"]

        print(f"   Attacked: {len(attacked_claims)} / {len(adv_result.claims)} claims")
        print(f"   Unattacked (auto-survive): {len(unattacked)}")
        print(f"   Rebuttals: {len(rebuts)}")
        print(f"   Concessions: {len(concedes)}")
        print(f"   Amendments: {len(amends)}")

        severities = [c.attack_severity for c in attacked_claims if c.attack_severity]
        if severities:
            sev_counts = {}
            for s in severities:
                sev_counts[s] = sev_counts.get(s, 0) + 1
            print(f"   Attack severities: {sev_counts}")

        # Diagnosis
        print(f"\n7. DIAGNOSIS:")
        if len(unattacked) > len(adv_result.claims) * 0.3:
            print(f"   [!] HIGH UNATTACKED RATE: {len(unattacked)}/{len(adv_result.claims)} claims were never attacked.")
            print(f"       Cause: adversary_map doesn't cover all agents, or claims_by_agent is empty for some.")
        if not concedes:
            print(f"   [!] ZERO CONCESSIONS: No agent conceded any claim.")
            if all(c.defense_response == "rebut" for c in attacked_claims):
                print(f"       All {len(attacked_claims)} attacked claims were successfully rebutted.")
                print(f"       Possible causes:")
                print(f"         a) Scenario is too clear-cut; all positions are defensible")
                print(f"         b) Attacks are generic/weak (not targeting real weaknesses)")
                print(f"         c) Defense prompt too lenient (allows easy rebuttals)")
            if rebuts and severities:
                fatal_rebuts = [c for c in attacked_claims if c.attack_severity == "fatal" and c.defense_response == "rebut"]
                if fatal_rebuts:
                    print(f"   [!] {len(fatal_rebuts)} 'fatal' attacks were rebutted — defense may be too easy")
        if r1_event:
            decisions = r1_event.get("data", {}).get("decisions", [])
            actions = [d.get("action", "?") for d in decisions]
            if len(set(actions)) == 1:
                print(f"   [!] UNANIMOUS CONSENSUS: All agents chose '{actions[0]}'")
                print(f"       With no cross-faction disagreement, adversary_map pairs same-faction agents.")
                print(f"       Same-faction attacks are inherently weaker — attacking allies is harder.")

    print(f"\n{'='*70}")
    print("  END DIAGNOSTIC")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose adversarial debate behavior for a specific case",
        prog="py -3 -u -m tests.validation.diagnose_adversarial",
    )
    parser.add_argument(
        "--case", type=str, default="crowdstrike_outage",
        help="Case ID to diagnose (default: crowdstrike_outage)",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help=f"Override the LLM model (default: {DEFAULT_MODEL}).",
    )
    args = parser.parse_args()

    asyncio.run(diagnose(args.case, args.model))


if __name__ == "__main__":
    main()
