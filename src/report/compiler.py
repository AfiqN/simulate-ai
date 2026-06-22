from typing import Any, Literal, Optional

from src.llm.client import OllamaClient
from src.llm.json_parse import strip_thought_tags
from src.schema.simulation_schema import SimulationSchema


Valence = Literal["stress", "validation"]


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
{crisis_section}
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
   - Did the crisis cause cascading rejection or did agents adapt?
   - Rate resilience: Fragile / Moderate / Resilient.
   - Identify the most risk-sensitive pivot-point archetype.

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
