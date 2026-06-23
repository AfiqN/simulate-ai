from typing import Any, Literal, Optional

from src.llm.client import OllamaClient
from src.llm.json_parse import strip_thought_tags
from src.schema.simulation_schema import SimulationSchema


Valence = Literal["stress", "validation"]
ResilienceVerdict = Literal["Fragile", "Moderate", "Resilient", "Indeterminate"]


def compute_resilience_metrics(
    round2_results: list[dict[str, Any]],
    round3_results: list[dict[str, Any]],
    schema: SimulationSchema,
) -> dict[str, Any]:
    terminal_set = {a.name for a in schema.actions if a.is_terminal}
    r2_by_id = {d["id"]: d for d in round2_results}
    r3_by_id = {d["id"]: d for d in round3_results}

    paired = [
        (r2_by_id[aid], r3_by_id[aid])
        for aid in r2_by_id
        if aid in r3_by_id
        and not r2_by_id[aid].get("error")
        and not r3_by_id[aid].get("error")
    ]

    if not paired:
        return {
            "decision_stability": 0.0,
            "utility_drift_mean": 0.0,
            "terminal_share_r2": 0.0,
            "terminal_share_r3": 0.0,
            "terminal_share_delta": 0.0,
            "verdict": "Indeterminate",
            "rationale": "no paired R2-R3 decisions available",
            "paired_count": 0,
        }

    n = len(paired)
    same_action = sum(1 for r2, r3 in paired if r2.get("action") == r3.get("action"))
    decision_stability = same_action / n

    drift = [r3.get("utility", 0.0) - r2.get("utility", 0.0) for r2, r3 in paired]
    utility_drift_mean = sum(drift) / n

    terminal_r2 = sum(1 for r2, _ in paired if r2.get("action") in terminal_set) / n
    terminal_r3 = sum(1 for _, r3 in paired if r3.get("action") in terminal_set) / n
    terminal_delta = terminal_r3 - terminal_r2

    if decision_stability >= 0.6 and utility_drift_mean >= -0.2 and terminal_delta <= 0.2:
        verdict: ResilienceVerdict = "Resilient"
    elif decision_stability < 0.4 or utility_drift_mean < -0.4 or terminal_delta > 0.4:
        verdict = "Fragile"
    else:
        verdict = "Moderate"

    rationale = (
        f"stability={decision_stability:.2f} ({same_action}/{n} held), "
        f"utility drift={utility_drift_mean:+.2f}, "
        f"terminal share {terminal_r2:.2f}->{terminal_r3:.2f}"
    )

    return {
        "decision_stability": decision_stability,
        "utility_drift_mean": utility_drift_mean,
        "terminal_share_r2": terminal_r2,
        "terminal_share_r3": terminal_r3,
        "terminal_share_delta": terminal_delta,
        "verdict": verdict,
        "rationale": rationale,
        "paired_count": n,
    }


class ExecutiveCompiler:
    def __init__(self, client: OllamaClient, schema: SimulationSchema):
        self.client = client
        self.schema = schema

    async def generate_crisis_event(
        self,
        stimulus: str,
        debate_transcript: str,
        valence: Valence = "stress",
        model: Optional[str] = None,
    ) -> str:
        crisis_axes = ", ".join(self.schema.crisis_dimensions) or "any plausible external shock"
        macro = self.schema.macro_context_text() or "(no specific environmental anchors)"

        if valence == "validation":
            framing = (
                "Identify the single most dominant ASSUMPTION, FEAR, or BLOCKER voiced in the Round 2 debate transcript below, "
                "then synthesize ONE realistic external event that UNEXPECTEDLY VALIDATES the stimulus or REMOVES that blocker. "
                "The event should be plausible vindication or favorable shift (e.g. a regulator endorses, a competitor exits, "
                "a key risk is empirically debunked, a major partner signals support). It must still fit one of the allowed "
                "crisis dimensions, treated as an inverted/positive realization of that dimension "
                "(e.g. \"regulatory_crackdown\" → \"regulatory sandbox approval\"; "
                "\"competitor_counter_demo\" → \"competitor publicly withdraws comparable product\")."
            )
        else:
            framing = (
                "Identify the single most dominant concern, fear, or structural complaint voiced in the Round 2 debate transcript below, "
                "then synthesize ONE realistic external crisis event that hits that concern."
            )

        crisis_prompt = f"""You are the SimulateAI External Event Catalyst for the scenario "{self.schema.scenario_name}".
{framing}

Scenario context:
{self.schema.scenario_description}

Macro environment anchors:
{macro}

Allowed crisis dimensions for this scenario: {crisis_axes}.
The event MUST fall under one of those dimensions.

Original stimulus:
\"\"\"
{stimulus}
\"\"\"

Round 2 debate transcript:
{debate_transcript}

Output ONLY one short sentence describing the event. Do not include explanation, preamble, quotation marks, markdown, or <thought> tags. One declarative sentence, nothing else."""

        messages = [
            {
                "role": "system",
                "content": "You are an external-event synthesis engine. Output exactly one declarative sentence. No reasoning traces, no commentary, no markup.",
            },
            {"role": "user", "content": crisis_prompt},
        ]

        try:
            raw = await self.client.chat(messages, model=model)
        except Exception:
            return "An unexpected disruption has occurred that directly impacts the viability of the proposed concept."

        return _clean_single_sentence(raw)

    async def compile_report(
        self,
        stimulus: str,
        round1_results: list[dict[str, Any]],
        round2_results: list[dict[str, Any]],
        round3_results: Optional[list[dict[str, Any]]] = None,
        crisis_event: Optional[str] = None,
        resilience_metrics: Optional[dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> str:
        transcript = _build_transcript(round1_results, round2_results, round3_results)
        crisis_section = ""
        if crisis_event:
            crisis_section = f"""
## CRISIS EVENT INJECTED (Round 3 Stress-Test)
The following external crisis was synthesized and injected into the simulation:
> "{crisis_event}"
"""

        if resilience_metrics:
            r = resilience_metrics
            resilience_block = f"""
## DETERMINISTIC RESILIENCE METRICS (pre-computed — DO NOT override)
- Verdict: {r['verdict']}
- Decision stability (R2→R3): {r['decision_stability']:.2f} ({r['paired_count']} agents tracked)
- Mean utility drift (R3 − R2): {r['utility_drift_mean']:+.2f}
- Terminal-action share R2 → R3: {r['terminal_share_r2']:.2f} → {r['terminal_share_r3']:.2f} (Δ {r['terminal_share_delta']:+.2f})
- Rationale: {r['rationale']}
"""
            resilience_instruction = (
                f"   - The resilience verdict is **{r['verdict']}** — this is pre-computed from the metrics above and is authoritative. "
                "Do NOT invent a different rating. Your job is to explain WHY the metrics produced this verdict using evidence from the transcript "
                "(which agents held, which flipped, magnitude of utility shifts) and to identify the most risk-sensitive pivot-point archetype."
            )
        else:
            resilience_block = ""
            resilience_instruction = (
                "   - Did the crisis cause cascading rejection or did agents adapt?\n"
                "   - Rate resilience: Fragile / Moderate / Resilient.\n"
                "   - Identify the most risk-sensitive pivot-point archetype."
            )

        action_vocab = ", ".join(self.schema.action_names())
        prompt = f"""You are the SimulateAI Chief Behavioral Architect & Diagnostic Director.
Compile a sharp, objective, actionable Executive Diagnostic Report based on the multi-agent simulation below.

Scenario: {self.schema.scenario_name}
Scenario description: {self.schema.scenario_description}
Verdict label for this scenario: {self.schema.verdict_label}
Action vocabulary used by agents: {action_vocab}

User stimulus:
\"\"\"
{stimulus}
\"\"\"
{crisis_section}{resilience_block}
Raw simulation transcript:
{transcript}

Write a professional Markdown report with these sections, in this order. Adapt the wording to the scenario domain — do not assume this is a consumer market unless it actually is.

1. EXECUTIVE SUMMARY & VERDICT
   - State the {self.schema.verdict_label} as one of: High / Mixed / Low (or domain-appropriate equivalent).
   - One paragraph of brutally honest synthesis. No sycophancy.

2. FACTION MAPPING & ALIGNMENT
   - Group agents into emergent factions based on the actions they took and the reasoning they revealed.
   - Note any agent who shifted position between rounds and why.

3. STRUCTURAL BLIND SPOTS (RED-TEAMING)
   - Pull concrete flaws, frictions, or skepticism from the agents' private monologues and public statements.
   - List them as bullets with the evidence (which agent surfaced which concern).

4. SYSTEM STABILITY & CONSENSUS INDEX
   - Is the swarm polarized, converging, or fragmented?
   - Cite specific transitions you observed.

5. CRISIS RESILIENCE VERDICT
{resilience_instruction}

6. STRATEGIC PIVOT RECOMMENDATIONS
   - Three concrete, actionable modifications to the original stimulus that would address the strongest objections surfaced in the swarm.

Rules:
- Do not output <thought> blocks, scratch reasoning, or section drafts. Output only the final report.
- Do not wrap the report in code fences or quote it.
- Use Markdown headers (## and ###), bullet lists, and bold sparingly. Do not use backticks for paths or filenames.
"""

        messages = [
            {
                "role": "system",
                "content": "You are a behavioral economist and diagnostic intelligence analyst. Output the final report only. Never expose chain-of-thought, never wrap output in fences.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            raw = await self.client.chat(messages, model=model)
        except Exception as e:
            return f"Error compiling diagnostic report: {e}"

        return strip_thought_tags(raw)


def _clean_single_sentence(text: str) -> str:
    cleaned = strip_thought_tags(text).strip()
    if not cleaned:
        return "An unexpected disruption has occurred that directly impacts the viability of the proposed concept."
    cleaned = cleaned.strip().strip('"').strip("'").strip()
    if "\n" in cleaned:
        for line in reversed(cleaned.splitlines()):
            line = line.strip().strip('"').strip("'").strip()
            if line:
                cleaned = line
                break
    return cleaned


def _build_transcript(
    r1: list[dict[str, Any]],
    r2: list[dict[str, Any]],
    r3: Optional[list[dict[str, Any]]],
) -> str:
    parts: list[str] = []
    for i, a in enumerate(r1):
        b = r2[i] if i < len(r2) else {}
        c = r3[i] if r3 and i < len(r3) else {}

        block = (
            f"Agent: {a.get('archetype', '?')} (ID: {a.get('id', '?')})\n"
            f"- Round 1 Action: {a.get('action')} (Utility: {a.get('utility', 0.0):.4f})\n"
            f"- Round 1 Inner Monologue: \"{a.get('monologue', '')}\"\n"
            f"- Round 1 Public Statement: \"{a.get('statement', '')}\"\n"
        )
        if b and not b.get("error"):
            block += (
                f"- Round 2 Action: {b.get('action')} (Utility: {b.get('utility', 0.0):.4f})\n"
                f"- Round 2 Inner Monologue: \"{b.get('monologue', '')}\"\n"
                f"- Round 2 Public Statement: \"{b.get('statement', '')}\"\n"
                f"- State after Round 2: {b.get('new_state')}\n"
            )
        if c and not c.get("error"):
            block += (
                f"- Round 3 Action: {c.get('action')} (Utility: {c.get('utility', 0.0):.4f})\n"
                f"- Round 3 Inner Monologue: \"{c.get('monologue', '')}\"\n"
                f"- Round 3 Public Statement: \"{c.get('statement', '')}\"\n"
                f"- State after Round 3: {c.get('new_state')}\n"
            )
        parts.append(block)
    return "\n---\n".join(parts)
