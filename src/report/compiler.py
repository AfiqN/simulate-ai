from typing import Any, Literal, Optional

from src.llm.client import OllamaClient
from src.llm.json_parse import strip_thought_tags
from src.report.metrics import compute_quantitative_metrics, format_metrics_block
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

    # Per-dimension drift (when multi-dim utility is available)
    per_dimension_drift: dict[str, float] = {}
    all_dims: set[str] = set()
    for r2, r3 in paired:
        all_dims.update((r2.get("utility_dimensions") or {}).keys())
        all_dims.update((r3.get("utility_dimensions") or {}).keys())
    for dim in sorted(all_dims):
        dim_drifts = []
        for r2, r3 in paired:
            r2_score = (r2.get("utility_dimensions") or {}).get(dim)
            r3_score = (r3.get("utility_dimensions") or {}).get(dim)
            if r2_score is not None and r3_score is not None:
                dim_drifts.append(r3_score - r2_score)
        if dim_drifts:
            per_dimension_drift[dim] = sum(dim_drifts) / len(dim_drifts)

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
        "per_dimension_drift": per_dimension_drift,
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
        rag_crisis_facts: Optional[list[str]] = None,
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

        if rag_crisis_facts:
            facts_block = "\n".join(f"- {fact}" for fact in rag_crisis_facts)
            crisis_prompt += f"""

REAL-WORLD PRECEDENTS (use to ground the crisis in actual events):
{facts_block}

Base your crisis event on a real or plausible variation of these precedents."""

        messages = [
            {
                "role": "system",
                "content": "You are an external-event synthesis engine. Output exactly one declarative sentence. No reasoning traces, no commentary, no markup.",
            },
            {"role": "user", "content": crisis_prompt},
        ]

        try:
            raw = await self.client.chat(messages, model=model)
        except Exception as e:
            # Surface the error type so operators can diagnose API/network failures
            return f"An unexpected disruption has occurred ({type(e).__name__}: {e})."

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
        language: Optional[str] = None,
        depth: str = "standard",
        profiles: Optional[list] = None,
        round4_results: Optional[list[dict[str, Any]]] = None,
        faction_metrics: Optional[dict[str, Any]] = None,
        adversarial_result: Optional[Any] = None,
    ) -> str:
        transcript = _build_transcript(round1_results, round2_results, round3_results, profiles=profiles, r4=round4_results)

        # Pre-compute quantitative metrics
        quant_metrics = compute_quantitative_metrics(
            round1_results, round2_results, round3_results or [], self.schema,
            profiles=profiles,
        )
        if faction_metrics:
            quant_metrics["faction_metrics"] = faction_metrics
        quant_block = format_metrics_block(quant_metrics)

        # Adversarial debate section (replaces faction mapping in adversarial mode)
        adversarial_section = ""
        adversarial_report_instruction = ""
        faction_section_fallback = (
            "2. FACTION MAPPING & ALIGNMENT\n"
            "   - Group agents into emergent factions based on the actions they took and the reasoning they revealed.\n"
            "   - Note any agent who shifted position between rounds and why (use the swing analysis above).\n"
        )
        if adversarial_result is not None:
            adversarial_section = f"""
## ARGUMENT SURVIVAL ANALYSIS (Adversarial Debate — pre-computed)
{adversarial_result.to_transcript()}
"""
            adversarial_report_instruction = """
2. ARGUMENT SURVIVAL ANALYSIS
   - Summarize which claims survived adversarial challenge and why they are credible.
   - Which claims were destroyed? What does their defeat reveal about hidden assumptions in the original stimulus?
   - What is the overall signal-to-noise ratio? (survival rate as credibility indicator)
"""

        crisis_section = ""
        if crisis_event:
            if isinstance(crisis_event, dict):
                stress = crisis_event.get("stress", "")
                validation = crisis_event.get("validation", "")
                parts = []
                if stress:
                    parts.append(f'STRESS EVENT: "{stress}"')
                if validation:
                    parts.append(f'VALIDATION EVENT: "{validation}"')
                events_text = "\n".join(parts)
                crisis_section = f"""
## EXTERNAL EVENTS INJECTED (Round 3 — Dual Signals)
The following external events were synthesized and injected into the simulation simultaneously:
{events_text}

Agents were required to weigh BOTH signals and determine which dominates their perspective.
"""
            else:
                crisis_section = f"""
## CRISIS EVENT INJECTED (Round 3 Stress-Test)
The following external crisis was synthesized and injected into the simulation:
> "{crisis_event}"
"""

        if resilience_metrics:
            r = resilience_metrics
            dim_drift = r.get("per_dimension_drift", {})
            dim_drift_line = ""
            if dim_drift:
                dim_drift_line = "- Per-dimension drift (R3 − R2): " + ", ".join(
                    f"{k}={v:+.2f}" for k, v in dim_drift.items()
                ) + "\n"
            resilience_block = f"""
## DETERMINISTIC RESILIENCE METRICS (pre-computed — DO NOT override)
- Verdict: {r['verdict']}
- Decision stability (R2→R3): {r['decision_stability']:.2f} ({r['paired_count']} agents tracked)
- Mean utility drift (R3 − R2): {r['utility_drift_mean']:+.2f}
- Terminal-action share R2 → R3: {r['terminal_share_r2']:.2f} → {r['terminal_share_r3']:.2f} (Δ {r['terminal_share_delta']:+.2f})
{dim_drift_line}- Rationale: {r['rationale']}
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

        if depth == "quick":
            prompt = f"""You are the SimulateAI Chief Behavioral Architect.
Compile a brief diagnostic summary based on the multi-agent simulation below.

Scenario: {self.schema.scenario_name}
Scenario description: {self.schema.scenario_description}
Verdict label for this scenario: {self.schema.verdict_label}
Action vocabulary used by agents: {action_vocab}

User stimulus:
\"\"\"
{stimulus}
\"\"\"
{crisis_section}{resilience_block}
{quant_block}
Raw simulation transcript:
{transcript}

Write a concise Markdown report with ONLY these 3 sections:

1. VERDICT & SUMMARY
   - State the {self.schema.verdict_label} as one of: High / Mixed / Low (or domain-appropriate equivalent).
   - 2-3 sentences of synthesis. Reference the vote tally and consensus index above.

2. KEY CONCERNS
   - Top 3 risks or objections surfaced by agents, as bullets.

3. ONE RECOMMENDATION
   - Single most impactful modification to the original stimulus.

Rules:
- Reference the pre-computed metrics above when citing numbers. Do NOT invent statistics.
- Do not output <thought> blocks, scratch reasoning, or section drafts. Output only the final report.
- Do not wrap the report in code fences or quote it.
- Keep the entire output under 300 words.
"""
        else:
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
{quant_block}
{adversarial_section}Raw simulation transcript:
{transcript}

Write a professional Markdown report with these sections, in this order. Adapt the wording to the scenario domain — do not assume this is a consumer market unless it actually is.

1. EXECUTIVE SUMMARY & VERDICT
   - State the {self.schema.verdict_label} as one of: High / Mixed / Low (or domain-appropriate equivalent).
   - One paragraph of brutally honest synthesis. No sycophancy.
   - Reference the vote tally and consensus index from the metrics above.

{adversarial_report_instruction if adversarial_result else faction_section_fallback}
3. STRUCTURAL BLIND SPOTS (RED-TEAMING)
   - Pull concrete flaws, frictions, or skepticism from the agents' private monologues and public statements.
   - List them as bullets with the evidence (which agent surfaced which concern).

4. SYSTEM STABILITY & CONSENSUS INDEX
   - Is the swarm polarized, converging, or fragmented? Reference the HHI values and state transitions above.
   - Cite specific transitions you observed.

5. CRISIS RESILIENCE VERDICT
{resilience_instruction}

6. STRATEGIC PIVOT RECOMMENDATIONS
   - Three concrete, actionable modifications to the original stimulus that would address the strongest objections surfaced in the swarm.

Rules:
- Reference the pre-computed metrics above when citing numbers. Do NOT invent statistics.
- Do not output <thought> blocks, scratch reasoning, or section drafts. Output only the final report.
- Do not wrap the report in code fences or quote it.
- Use Markdown headers (## and ###), bullet lists, and bold sparingly. Do not use backticks for paths or filenames.
"""
            if depth == "deep":
                prompt += """
7. MINORITY REPORT
   - Identify the single strongest dissenting voice in the simulation.
   - Reconstruct their full argument: what did they see that the majority missed?
   - Assess whether their concern represents a tail risk, a fundamental flaw, or a solvable friction.
   - If their argument were correct, what would the consequences be?
"""

        if language:
            prompt += f"\n\nIMPORTANT: Write the entire report in {language}. All section headers, analysis, and recommendations must be in {language}."

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
        # Take the FIRST non-empty line (the event sentence), not the last
        # (which may be a trailing LLM caveat or explanation).
        for line in cleaned.splitlines():
            line = line.strip().strip('"').strip("'").strip()
            if line:
                cleaned = line
                break
    return cleaned


def _build_transcript(
    r1: list[dict[str, Any]],
    r2: list[dict[str, Any]],
    r3: Optional[list[dict[str, Any]]],
    profiles: Optional[list] = None,
    r4: Optional[list[dict[str, Any]]] = None,
) -> str:
    # Align by agent ID to prevent cross-contamination when a round has missing/failed entries
    r2_by_id = {d.get("id"): d for d in r2}
    r3_by_id = {d.get("id"): d for d in (r3 or [])}
    r4_by_id = {d.get("id"): d for d in (r4 or [])}
    profile_by_id = {p.agent_id: p for p in (profiles or [])}

    parts: list[str] = []
    for a in r1:
        aid = a.get("id")
        b = r2_by_id.get(aid, {})
        c = r3_by_id.get(aid, {})
        profile = profile_by_id.get(aid)

        block = (
            f"Agent: {a.get('archetype', '?')} (ID: {aid})\n"
        )
        # Include persona context when available
        if profile:
            if profile.influence_weight != 1.0:
                block += f"- Influence Weight: {profile.influence_weight:.1f}x\n"
            if profile.decision_framework:
                block += f"- Decision Framework: {profile.decision_framework}\n"
            if profile.constraints:
                block += f"- Hard Constraints: {'; '.join(profile.constraints)}\n"

        block += (
            f"- Round 1 Action: {a.get('action')} (Utility: {a.get('utility', 0.0):.4f})\n"
            f"- Round 1 Inner Monologue: \"{a.get('monologue', '')}\"\n"
            f"- Round 1 Public Statement: \"{a.get('statement', '')}\"\n"
        )
        dims_r1 = a.get("utility_dimensions")
        if dims_r1:
            block += "- Round 1 Dimension Scores: " + ", ".join(f"{k}={v:+.2f}" for k, v in dims_r1.items()) + "\n"
        chain_r1 = a.get("reasoning_chain")
        if chain_r1:
            block += "- Round 1 Reasoning:\n" + "".join(
                f"    {entry['dimension']}: {entry['reasoning']}\n" for entry in chain_r1 if entry.get("reasoning")
            )

        if b and not b.get("error"):
            block += (
                f"- Round 2 Action: {b.get('action')} (Utility: {b.get('utility', 0.0):.4f})\n"
                f"- Round 2 Inner Monologue: \"{b.get('monologue', '')}\"\n"
                f"- Round 2 Public Statement: \"{b.get('statement', '')}\"\n"
                f"- State after Round 2: {b.get('new_state')}\n"
            )
            dims_r2 = b.get("utility_dimensions")
            if dims_r2:
                block += "- Round 2 Dimension Scores: " + ", ".join(f"{k}={v:+.2f}" for k, v in dims_r2.items()) + "\n"
            chain_r2 = b.get("reasoning_chain")
            if chain_r2:
                block += "- Round 2 Reasoning:\n" + "".join(
                    f"    {entry['dimension']}: {entry['reasoning']}\n" for entry in chain_r2 if entry.get("reasoning")
                )

        if c and not c.get("error"):
            block += (
                f"- Round 3 Action: {c.get('action')} (Utility: {c.get('utility', 0.0):.4f})\n"
                f"- Round 3 Inner Monologue: \"{c.get('monologue', '')}\"\n"
                f"- Round 3 Public Statement: \"{c.get('statement', '')}\"\n"
                f"- State after Round 3: {c.get('new_state')}\n"
            )
            dims_r3 = c.get("utility_dimensions")
            if dims_r3:
                block += "- Round 3 Dimension Scores: " + ", ".join(f"{k}={v:+.2f}" for k, v in dims_r3.items()) + "\n"
            chain_r3 = c.get("reasoning_chain")
            if chain_r3:
                block += "- Round 3 Reasoning:\n" + "".join(
                    f"    {entry['dimension']}: {entry['reasoning']}\n" for entry in chain_r3 if entry.get("reasoning")
                )

        e = r4_by_id.get(aid, {})
        if e and not e.get("error"):
            block += (
                f"- Round 4 (Reconciliation) Action: {e.get('action')} (Utility: {e.get('utility', 0.0):.4f})\n"
                f"- Round 4 Inner Monologue: \"{e.get('monologue', '')}\"\n"
                f"- Round 4 Public Statement: \"{e.get('statement', '')}\"\n"
                f"- State after Round 4: {e.get('new_state')}\n"
            )
            dims_r4 = e.get("utility_dimensions")
            if dims_r4:
                block += "- Round 4 Dimension Scores: " + ", ".join(f"{k}={v:+.2f}" for k, v in dims_r4.items()) + "\n"
            chain_r4 = e.get("reasoning_chain")
            if chain_r4:
                block += "- Round 4 Reasoning:\n" + "".join(
                    f"    {entry['dimension']}: {entry['reasoning']}\n" for entry in chain_r4 if entry.get("reasoning")
                )

        parts.append(block)
    return "\n---\n".join(parts)
