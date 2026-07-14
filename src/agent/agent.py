from typing import Any, Optional

from src.llm.client import OllamaClient
from src.llm.json_parse import parse_json_robustly
from src.agent.profile import AgentProfile
from src.schema.simulation_schema import SimulationSchema


class Agent:
    def __init__(self, profile: AgentProfile, client: OllamaClient, schema: SimulationSchema):
        self.profile = profile
        self.client = client
        self.schema = schema
        self.decision_threshold = 0.5
        self.historical_context: str = ""  # Injected historical precedent block

    def _linguistic_style_prompt(self) -> str:
        cluster = self.schema.get_cluster(self.profile.linguistic_cluster_id)
        if cluster is not None:
            return cluster.style_prompt
        # Fallback: generic style prompt without keyword-matching on archetype name.
        # This fires only on cluster_id mismatch — a data integrity issue upstream.
        return (
            "Speak with a direct, opinionated voice. Express your biases and emotional "
            "state clearly. Use natural language appropriate to your role in this scenario."
        )

    def _render_actions_block(self) -> str:
        lines = []
        for a in self.schema.actions:
            suffix = []
            if a.is_terminal:
                suffix.append("terminal")
            if a.affects_resource:
                suffix.append(f"spends {a.affects_resource}")
            tag = f" ({', '.join(suffix)})" if suffix else ""
            lines.append(f"- {a.name}{tag}: {a.description}")
        return "\n".join(lines)

    def _render_constraints_block(self) -> str:
        if not self.profile.constraints:
            return "No hard constraints — you may consider any option."
        lines = [f"- {c}" for c in self.profile.constraints]
        lines.append("")
        lines.append(
            "These are NON-NEGOTIABLE. If an action would violate any constraint above, "
            "you MUST NOT choose it regardless of utility calculations."
        )
        return "\n".join(lines)

    def _render_resources_block(self) -> str:
        if self.schema.resource_model.kind == "none" or not self.profile.resources:
            return "This scenario does not track tangible resources for this agent."
        lines = []
        depleted = []
        for r in self.profile.resources:
            pct = (r.current / r.maximum * 100) if r.maximum > 0 else 0
            lines.append(f"- {r.name}: {r.current:,.2f} / {r.maximum:,.2f} ({pct:.0f}%)")
            if r.current <= 0:
                depleted.append(r.name)
            elif pct <= 20:
                depleted.append(f"{r.name} (critically low)")
        if depleted:
            lines.append("")
            lines.append(
                "⚠ RESOURCE CONSTRAINT: " + ", ".join(depleted) + " depleted or critically low. "
                "Maintaining aggressive or high-cost stances without adequate resources is "
                "increasingly untenable — consider whether you can credibly sustain your current "
                "position, or whether pragmatic adaptation (coalition-building, compromise, delay) "
                "better serves your interests given your diminished leverage."
            )
        return "\n".join(lines)

    def _render_decision_logic_prompt(self) -> str:
        if self.schema.evaluation_dimensions:
            dims = ", ".join(self.schema.evaluation_dimensions)
            return (
                f"Evaluate the stimulus across these dimensions: {dims}\n"
                "For each dimension, assign a score in [-1.0, 1.0] where:\n"
                "  -1.0 = extremely negative outcome on this dimension\n"
                "   0.0 = neutral / no impact\n"
                "  +1.0 = extremely positive outcome on this dimension\n"
                "Express each score to exactly 2 decimal places (e.g. 0.35, not 0.3 or 0.4).\n"
                "Reflect genuine nuance — avoid round numbers like 0.50, 0.80, 1.00 unless truly warranted.\n"
                "Include a brief reasoning string (1 sentence) for each dimension.\n"
                "Then compute aggregate_utility as the arithmetic mean of all dimension scores (also 2 decimal places)."
            )
        else:
            return (
                "Compute your utility internally as:\n"
                "  final_utility = perceived_gains - perceived_costs\n"
                "where both inputs are in [0.0, 1.0] and final_utility ends up in [-1.0, 1.0].\n"
                "Express ALL three values to exactly 2 decimal places (e.g. 0.35, not 0.3 or 0.4).\n"
                "Reflect genuine nuance — avoid round numbers like 0.50, 0.80, 1.00 unless truly warranted."
            )

    def _render_response_template(self) -> str:
        if self.schema.resource_model.kind == "none" or not self.profile.resources:
            resource_field = ""
        else:
            resource_field = (
                '\n  "resource_deductions": {  // map of resource_name to numeric amount to deduct '
                '(0 if action does not spend that resource). Numbers only, no symbols or commas.\n'
                + ",\n".join(f'    "{r.name}": 0' for r in self.profile.resources)
                + "\n  },"
            )
        action_names = " | ".join(self.schema.action_names())
        state_examples = ", ".join(self.schema.state_vocabulary[:6])

        # Multi-dimensional utility template when dimensions are defined
        if self.schema.evaluation_dimensions:
            dim_entries = ",\n".join(
                f'      "{d}": {{"score": 0.0, "reasoning": "brief rationale for this dimension"}}'
                for d in self.schema.evaluation_dimensions
            )
            utility_block = f'''"utility_calculation": {{
    "dimensions": {{
{dim_entries}
    }},
    "aggregate_utility": 0.0
  }}'''
        else:
            utility_block = '''"utility_calculation": {{
    "perceived_gains": 0.0,
    "perceived_costs": 0.0,
    "final_utility": 0.0
  }}'''

        return f"""{{
  "internal_reflection": "private thoughts about the stimulus",
  "public_statement": "what you say out loud to peers, in your linguistic style",
  {utility_block},
  "decision": "{action_names}",
  "emotional_state": "one of: {state_examples}, ...",{resource_field}
  "new_memory_to_store": "one short sentence summarizing what you learned"
}}"""

    def build_system_prompt(self, context_summary: str = "", depth: str = "standard") -> str:
        attrs = self.profile.attributes
        memories = "\n".join(f"- {m}" for m in self.profile.memory_vectors) or "- (no prior memories)"

        sections = []
        macro = self.schema.macro_context_text()
        if macro:
            sections.append(macro)
        if context_summary:
            sections.append(context_summary)
        context_block = "\n\n".join(sections) if sections else "Normal operating conditions."

        state_vocab = ", ".join(self.schema.state_vocabulary)

        base = f"""You are an autonomous agent participating in a simulation: "{self.schema.scenario_name}".
Scenario context: {self.schema.scenario_description}

You MUST stay strictly in character — direct, opinionated, biased. Do not sound like an AI assistant.

--- LINGUISTIC STYLE ---
{self._linguistic_style_prompt()}

--- YOUR IDENTITY ---
Agent ID: {self.profile.agent_id}
Archetype: {self.profile.archetype}
Current Internal State: {self.profile.current_internal_state}

--- CHARACTERISTICS ---
- Rationality: {attrs.rationality_index:.2f} (1.0 = pure logic, 0.0 = pure emotion)
- Aggressiveness: {attrs.aggressiveness:.2f} (1.0 = dominant/confrontational, 0.0 = passive)
- Risk Tolerance: {attrs.risk_tolerance:.2f} (1.0 = reckless, 0.0 = extremely cautious)

--- DECISION FRAMEWORK ---
{self.profile.decision_framework or "No specific framework — rely on your archetype instincts."}

--- DOMAIN KNOWLEDGE ---
{self.profile.knowledge_base or "General domain knowledge appropriate to your archetype."}

--- HARD CONSTRAINTS (RED LINES) ---
{self._render_constraints_block()}

--- BACKSTORY ---
{self.profile.backstory or "No specific backstory provided."}

--- RESOURCES ---
{self._render_resources_block()}

--- MEMORIES ---
{memories}

--- SCENARIO ENVIRONMENT ---
{context_block}

--- AVAILABLE ACTIONS ---
You must commit to exactly one of these action verbs:
{self._render_actions_block()}

--- DECISION LOGIC ---
{self._render_decision_logic_prompt()}

--- EMOTIONAL STATE VOCABULARY ---
Pick one state that reflects your shift after this stimulus. Available states: {state_vocab}.

--- OUTPUT FORMAT ---
Return ONLY a valid JSON object matching this template. No prose, no markdown fences, no <thought> tags:

{self._render_response_template()}
"""

        if depth == "quick":
            base += """
--- DEPTH: QUICK ---
Be concise. Your internal_reflection should be 1-2 sentences maximum. Decide fast based on your strongest instinct given your archetype. Do not overthink."""
        elif depth == "deep":
            base += """
--- DEPTH: DEEP ANALYSIS ---
Think step by step. In your internal_reflection, explain your reasoning thoroughly:
1. What are the key dimensions you're evaluating? (e.g. financial, social, risk, feasibility)
2. For each dimension, what's your assessment and why?
3. What's your biggest uncertainty?
4. State your confidence level (low/medium/high) in your final decision.
Your reflection should be a detailed paragraph, not a single sentence."""

        # Inject historical context if available
        if self.historical_context:
            base += f"\n\n{self.historical_context}"

        return base

    def _evaluate_utility_and_transition(self, parsed: dict[str, Any]) -> None:
        calc = parsed.get("utility_calculation") or {}
        if not isinstance(calc, dict):
            calc = {}

        # Multi-dimensional utility parsing
        dimensions = calc.get("dimensions")
        if isinstance(dimensions, dict) and dimensions:
            # Parse per-dimension scores and reasoning
            utility_dimensions = {}
            reasoning_chain = []
            scores = []
            for dim_name, dim_data in dimensions.items():
                if isinstance(dim_data, dict):
                    score = _coerce_float(dim_data.get("score"), 0.0)
                    reasoning = str(dim_data.get("reasoning", "")).strip()
                else:
                    score = _coerce_float(dim_data, 0.0)
                    reasoning = ""
                utility_dimensions[dim_name] = score
                scores.append(score)
                reasoning_chain.append({
                    "dimension": dim_name,
                    "score": score,
                    "reasoning": reasoning,
                })
            parsed["utility_dimensions"] = utility_dimensions
            parsed["reasoning_chain"] = reasoning_chain
            # Aggregate: mean of dimension scores
            utility = _coerce_float(calc.get("aggregate_utility"), sum(scores) / len(scores) if scores else 0.0)
        else:
            # Fallback: flat gains/costs format (backward compat)
            gains = _coerce_float(calc.get("perceived_gains"), 0.0)
            costs = _coerce_float(calc.get("perceived_costs"), 0.0)
            utility = _coerce_float(calc.get("final_utility"), gains - costs)
            parsed["utility_dimensions"] = {}
            parsed["reasoning_chain"] = []

        parsed["utility"] = utility

        action = _normalize_action(parsed.get("decision"), self.schema, utility, self.profile.attributes.aggressiveness, self.decision_threshold)
        parsed["action_decision"] = action

        raw_state = parsed.get("emotional_state")
        state = _normalize_state(raw_state, self.schema.state_vocabulary, fallback=self.profile.current_internal_state)
        parsed["new_internal_state"] = state
        self.profile.current_internal_state = state

        new_memory = parsed.get("new_memory_to_store")
        if isinstance(new_memory, str):
            new_memory = new_memory.strip()
            if new_memory and new_memory not in self.profile.memory_vectors:
                self.profile.memory_vectors.append(new_memory)
                if len(self.profile.memory_vectors) > 10:
                    self.profile.memory_vectors.pop(0)

        self._apply_resource_deductions(parsed, action)

    def _apply_resource_deductions(self, parsed: dict[str, Any], action: str) -> None:
        if self.schema.resource_model.kind == "none" or not self.profile.resources:
            parsed["resource_deductions"] = {}
            return

        action_def = next((a for a in self.schema.actions if a.name == action), None)
        affects = action_def.affects_resource if action_def else None

        raw = parsed.get("resource_deductions") or {}
        if not isinstance(raw, dict):
            raw = {}

        clean: dict[str, float] = {}
        for resource in self.profile.resources:
            amount = _coerce_float(raw.get(resource.name), 0.0)
            if amount < 0:
                amount = 0.0
            if affects is None or resource.name != affects:
                clean[resource.name] = 0.0
                continue
            # Record actual deduction (capped at current balance), not inflated LLM amount
            actual = min(amount, resource.current)
            clean[resource.name] = actual
            resource.current = max(0.0, resource.current - actual)

        parsed["resource_deductions"] = clean

    async def perceive_and_react(self, stimulus: str, model: Optional[str] = None, depth: str = "standard") -> dict[str, Any]:
        return await self._llm_round(
            system=self.build_system_prompt(depth=depth),
            user=f"STIMULUS TO EVALUATE:\n{stimulus}",
            model=model,
        )

    async def debate_and_react(
        self,
        stimulus: str,
        round1_transcript: str,
        adversary: Optional[dict | list[dict]] = None,
        model: Optional[str] = None,
        depth: str = "standard",
        faction_context: Optional[str] = None,
    ) -> dict[str, Any]:
        context_summary = "You are now in ROUND 2 (Debate & Reflection). You have read your peers' initial reactions and must engage with their positions."
        user_prompt = f"""You are now in ROUND 2 (DEBATE & REFLECTION).
Your peers in the swarm have voiced their initial reactions to this stimulus:
"{stimulus}"

--- PEER TRANSCRIPT ---
{round1_transcript}

--- INSTRUCTIONS ---
1. Read your peers' public statements. Identify naive, paranoid, or motivated reasoning.
2. Decide whether to hold your ground, shift your utility perceptions, persuade, or compromise.
3. In your public_statement, address peers directly by archetype where it sharpens the point.
4. Re-evaluate your utility honestly. Commit to one action from the available actions list.
"""
        if faction_context:
            user_prompt += f"\n{faction_context}\n"

        if adversary:
            # Panel mode: multiple challengers
            if isinstance(adversary, list):
                user_prompt += "\n--- PANEL CHALLENGE ---\n"
                user_prompt += "Multiple agents are challenging your position directly:\n\n"
                for i, adv in enumerate(adversary, 1):
                    user_prompt += (
                        f"Challenger {i}: {adv.get('archetype', 'Another agent')} "
                        f"(action: {adv.get('action', '?')}): \"{adv.get('statement', '...')}\"\n\n"
                    )
                user_prompt += (
                    "You MUST address at least TWO of these challengers in your public_statement. "
                    "Defend, concede, or reframe — but engage with the substance of their arguments.\n"
                )
            else:
                # Single adversary (backward compatible)
                user_prompt += f"""
--- DIRECT CHALLENGE ---
{adversary.get('archetype', 'Another agent')} challenged you directly. They took action {adversary.get('action', '?')} and stated: "{adversary.get('statement', '...')}".
You MUST address their stance in your public_statement and internal_reflection. Defend, concede, or reframe — but engage with them by name.
"""
        return await self._llm_round(
            system=self.build_system_prompt(context_summary=context_summary, depth=depth),
            user=user_prompt,
            model=model,
        )

    async def react_to_crisis(
        self,
        crisis: str,
        original_stimulus: str,
        model: Optional[str] = None,
        depth: str = "standard",
    ) -> dict[str, Any]:
        context_summary = f"EXTERNAL EVENTS: {crisis}"
        user_prompt = f"""Two external events have hit the scenario simultaneously — one threatening, one favorable.
Original stimulus: "{original_stimulus}"

{crisis}

Re-evaluate your utility under BOTH new conditions. Weigh which event matters more to your archetype's priorities and constraints. The negative event may threaten your position; the positive event may open opportunities or remove blockers. Both are plausible and happening at the same time.

If the net effect genuinely changes your calculus, update your numbers and action. If one event dominates the other for your perspective, explain why. If they roughly cancel out, hold your previous position — agents who flip without justification look weak. Commit to exactly one action from the available actions list and defend your reasoning in public_statement.
"""
        return await self._llm_round(
            system=self.build_system_prompt(context_summary=context_summary, depth=depth),
            user=user_prompt,
            model=model,
        )

    async def reconcile(
        self,
        stimulus: str,
        full_transcript: str,
        model: Optional[str] = None,
        depth: str = "standard",
    ) -> dict[str, Any]:
        """Round 4 — Reconciliation. Agents seek common ground after the crisis."""
        context_summary = "RECONCILIATION ROUND: After crisis events and three rounds of deliberation, seek the highest-value compromise that respects your constraints."
        user_prompt = f"""You are now in ROUND 4 (RECONCILIATION).

The swarm has been through 3 rounds of deliberation on this stimulus:
"{stimulus}"

--- FULL DEBATE HISTORY ---
{full_transcript}

--- INSTRUCTIONS ---
You've heard everyone's positions harden through debate, and watched the crisis test resolve. Now:

1. Identify the 1-2 points of genuine common ground you share with your adversaries (even partial).
2. Propose a CONCRETE compromise or conditional offer: "I would shift to X IF the following condition were met..."
3. Name the single non-negotiable you REFUSE to yield on (from your hard constraints).
4. In your public_statement, address the full group — not just your adversary. Speak as if drafting a joint communiqué.
5. Your utility should reflect the VALUE OF THE COMPROMISE (not your ideal outcome). A good compromise that has buy-in is worth more than a perfect plan nobody accepts.

If no compromise is possible that respects your constraints, say so explicitly and explain why — but this should be RARE. Most positions have overlapping interests if you look for them.

Commit to exactly one action from the available actions list.
"""
        return await self._llm_round(
            system=self.build_system_prompt(context_summary=context_summary, depth=depth),
            user=user_prompt,
            model=model,
        )

    # --- Adversarial mode methods (R2a, R2b, R2c) ---

    def _adversarial_system_prompt(self) -> str:
        """Lightweight system prompt for adversarial rounds — identity + style only."""
        return (
            f"You are {self.profile.archetype} in a scenario simulation: \"{self.schema.scenario_name}\".\n"
            f"Scenario: {self.schema.scenario_description}\n\n"
            f"Stay in character. Be direct and opinionated.\n\n"
            f"--- LINGUISTIC STYLE ---\n{self._linguistic_style_prompt()}\n\n"
            f"--- YOUR IDENTITY ---\n"
            f"Archetype: {self.profile.archetype}\n"
            f"Decision Framework: {self.profile.decision_framework}\n"
            f"Domain Knowledge: {', '.join(self.profile.knowledge_base[:3])}\n"
            f"Hard Constraints: {', '.join(self.profile.constraints[:3]) if self.profile.constraints else 'None'}\n"
        )

    async def extract_claims(
        self,
        stimulus: str,
        round1_decision: dict[str, Any],
        model: Optional[str] = None,
        depth: str = "standard",
    ) -> list[dict[str, str]]:
        """R2a: Extract 2-3 concrete, falsifiable claims from Round 1 position."""
        action = round1_decision.get("action_decision", round1_decision.get("action", "?"))
        utility = round1_decision.get("utility", 0.0)
        statement = round1_decision.get("public_statement", round1_decision.get("statement", ""))

        user_prompt = f"""You are {self.profile.archetype}. In Round 1, you evaluated the stimulus and took action {action} with utility {utility:.2f}.

Your public statement was: "{statement}"

Now distill your position into exactly 2-3 CONCRETE, FALSIFIABLE claims. Each claim must be:
- Specific enough to be attacked with evidence or logic
- Central to why you chose your action
- Not a tautology or unfalsifiable opinion

Examples of GOOD claims (specific, attackable):
- "The deposit base concentration (93% uninsured) makes a bank run inevitable within 48 hours"
- "Regulatory intervention will come too late because the speed of social-media coordination exceeds traditional response timelines"

Examples of BAD claims (vague, unfalsifiable):
- "This is risky" (too vague)
- "Things could go either way" (unfalsifiable)

Output ONLY valid JSON:
{{"claims": [{{"claim": "your specific claim", "evidence": "why you believe this based on the stimulus"}}]}}"""

        messages = [
            {"role": "system", "content": self._adversarial_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]
        try:
            raw = await self.client.chat(messages, model=model, response_format={"type": "json_object"})
            parsed = parse_json_robustly(raw)
            claims = parsed.get("claims", []) if parsed else []
            # Ensure 2-3 claims max
            return claims[:3] if claims else [{"claim": statement[:200], "evidence": "Based on my initial analysis"}]
        except Exception:
            return [{"claim": statement[:200] if statement else "Position unclear", "evidence": "Based on initial analysis"}]

    async def attack_claims(
        self,
        target_claims: list[dict[str, str]],
        target_archetype: str,
        stimulus: str,
        model: Optional[str] = None,
        depth: str = "standard",
    ) -> list[dict[str, str]]:
        """R2b: Attack specific claims made by an adversary. Be ruthless."""
        claims_text = "\n".join(
            f"  {i+1}. CLAIM: \"{c['claim']}\"\n     EVIDENCE: \"{c.get('evidence', 'none given')}\""
            for i, c in enumerate(target_claims)
        )

        user_prompt = f"""You are {self.profile.archetype}. Your job is to DESTROY the following claims made by {target_archetype}.

SCENARIO CONTEXT: "{stimulus[:300]}"

THEIR CLAIMS:
{claims_text}

For EACH claim, identify:
1. The weakest assumption it relies on
2. A concrete counter-example, contradiction, or logical flaw
3. Why this claim would FAIL under real-world pressure

Be RUTHLESS. Your goal is to expose flawed reasoning. However, if a claim is genuinely airtight, say severity is "minor" — intellectual honesty strengthens your credibility.

Output ONLY valid JSON:
{{"attacks": [{{"target_claim": "the claim you're attacking (quote it)", "flaw": "the core logical/evidential flaw", "counter_evidence": "specific counter-example or contradiction", "severity": "fatal|serious|minor"}}]}}"""

        messages = [
            {"role": "system", "content": self._adversarial_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]
        try:
            raw = await self.client.chat(messages, model=model, response_format={"type": "json_object"})
            parsed = parse_json_robustly(raw)
            attacks = parsed.get("attacks", []) if parsed else []
            return attacks[:len(target_claims)]  # one attack per claim max
        except Exception:
            return [{"target_claim": c["claim"], "flaw": "Unable to generate attack", "counter_evidence": "", "severity": "minor"} for c in target_claims]

    async def defend_claim(
        self,
        claim: str,
        attack_text: str,
        attack_severity: str,
        model: Optional[str] = None,
        depth: str = "standard",
    ) -> dict[str, str]:
        """R2c: Defend a claim that has been attacked. One chance."""
        user_prompt = f"""You are {self.profile.archetype}. Your claim has been attacked:

YOUR CLAIM: "{claim}"

ATTACK: "{attack_text}"
RATED SEVERITY: {attack_severity}

You have ONE chance to respond. Choose honestly:
- REBUT: Provide a counter-argument that neutralizes the attack. You must introduce NEW evidence or logic not already in your original claim. A rebut MUST present new facts, data, or reasoning that the attacker did not consider.
- CONCEDE: Acknowledge the flaw is genuine and your claim does not hold. Honest concession is not weakness — it strengthens your surviving claims and your credibility.
- AMEND: Modify your claim to address the flaw while preserving the core insight. The amended claim must be SUBSTANTIALLY DIFFERENT from the original — not just softer language or hedging.

STRICT RULES — read carefully:
- If the attack severity is "fatal" and you cannot introduce genuinely NEW counter-evidence, you MUST CONCEDE. Amending a fatally flawed claim is not allowed — a fatal flaw means the core logic is broken, not just imprecise.
- If you find yourself writing "the attack is correct" or "the attack lands" or "I cannot defend" — that IS a concession. Do not then amend. Choose CONCEDE.
- AMEND is only valid when: (a) the core insight of your claim remains true, AND (b) the flaw identified is about scope/precision, NOT about the fundamental logic being wrong.
- If the attack exposes that your claim's causal mechanism is wrong (not just overstated), CONCEDE.
- Do NOT use amend as a way to retreat to a weaker version of a broken claim. That is intellectual dishonesty.

Output ONLY valid JSON:
{{"response": "rebut|concede|amend", "argument": "your defense or concession reasoning", "amended_claim": "new version of claim (only if response is amend, otherwise empty string)"}}"""

        messages = [
            {"role": "system", "content": self._adversarial_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]
        try:
            raw = await self.client.chat(messages, model=model, response_format={"type": "json_object"})
            parsed = parse_json_robustly(raw)
            if parsed and "response" in parsed:
                return parsed
            return {"response": "rebut", "argument": "Unable to parse defense", "amended_claim": ""}
        except Exception:
            return {"response": "concede", "argument": "Failed to generate defense", "amended_claim": ""}

    async def _llm_round(self, system: str, user: str, model: Optional[str]) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        raw = ""
        try:
            raw = await self.client.chat(
                messages,
                model=model,
                response_format={"type": "json_object"},
            )
            parsed = parse_json_robustly(raw)
            if not parsed:
                return {
                    "error": "Empty or unparseable LLM response",
                    "raw_response": raw,
                    "action_decision": _terminal_or_first_action(self.schema),
                    "new_internal_state": self.profile.current_internal_state,
                }
            self._evaluate_utility_and_transition(parsed)
            return parsed
        except Exception as e:
            return {
                "error": f"{type(e).__name__}: {e}",
                "raw_response": raw,
                "action_decision": _terminal_or_first_action(self.schema),
                "new_internal_state": self.profile.current_internal_state,
            }


def _coerce_float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        # Handle percentage strings (e.g. "50%")
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1].strip()
            try:
                return float(cleaned) / 100.0
            except ValueError:
                pass
        # Remove commas (thousand separators) and currency symbols
        cleaned = cleaned.replace(",", "").lstrip("$€£¥")
        # Keep only valid float characters, but handle leading/trailing minus properly
        kept = "".join(c for c in cleaned if c.isdigit() or c in (".", "-"))
        # Ensure at most one leading minus
        if kept.startswith("-"):
            kept = "-" + kept[1:].replace("-", "")
        else:
            kept = kept.replace("-", "")
        try:
            return float(kept)
        except ValueError:
            return default
    return default


def _normalize_action(
    raw: Any,
    schema: SimulationSchema,
    utility: float,
    aggressiveness: float,
    threshold: float,
) -> str:
    valid = schema.action_names()
    if isinstance(raw, str):
        candidate = raw.strip().upper()
        if candidate in valid:
            return candidate
    return _utility_to_action(utility, aggressiveness, threshold, schema)


def _utility_to_action(
    utility: float,
    aggressiveness: float,
    threshold: float,
    schema: SimulationSchema,
) -> str:
    non_terminal = [a for a in schema.actions if not a.is_terminal]
    terminal = [a for a in schema.actions if a.is_terminal]

    if utility > threshold and non_terminal:
        return non_terminal[0].name
    if utility < -0.1 and terminal:
        return terminal[0].name
    if non_terminal:
        idx = min(len(non_terminal) - 1, 1 if aggressiveness > 0.6 else 0)
        return non_terminal[idx].name
    return schema.actions[0].name


def _terminal_or_first_action(schema: SimulationSchema) -> str:
    if not schema.actions:
        return "NO_ACTION"
    for a in schema.actions:
        if a.is_terminal:
            return a.name
    return schema.actions[0].name


def _normalize_state(raw: Any, vocabulary: list[str], fallback: str) -> str:
    if not isinstance(raw, str):
        return fallback
    cleaned = raw.strip()
    if not cleaned:
        return fallback
    lower = cleaned.lower()
    for v in vocabulary:
        if v.lower() == lower:
            return v
    return cleaned.title()
