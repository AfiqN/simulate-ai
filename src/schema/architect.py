from typing import Optional

from src.llm.client import OllamaClient
from src.llm.json_parse import parse_json_robustly
from src.schema.simulation_schema import SimulationSchema


ARCHITECT_SYSTEM_PROMPT = (
    "You are the SimulateAI Scenario Architect. Your single job is to read a user's stimulus "
    "(a product pitch, policy proposal, hackathon idea, research question, strategic decision, "
    "or any other concept they want simulated) and design the vocabulary and constraints that "
    "the downstream agent swarm will operate under. You output one JSON object matching the "
    "exact schema requested. Do not output prose, markdown, or commentary outside the JSON."
)


def _user_prompt(stimulus: str) -> str:
    return f"""Analyze the following user stimulus and design a SimulationSchema tailored to its domain.

STIMULUS:
\"\"\"
{stimulus}
\"\"\"

Your task is to produce one JSON object that defines the *entire vocabulary* of the simulation. Do not assume the scenario is a consumer market, a product launch, a financial product, or anything specific — derive every field from the stimulus itself.

REQUIRED FIELDS (all required, no extras):

1. "scenario_name" — short title for this simulation (e.g. "Healthcare Policy Reform Debate", "Series A Pitch Review", "Open Source Governance Vote").

2. "scenario_description" — one to three sentences describing what is being simulated and what kind of ecosystem is reacting.

3. "verdict_label" — the headline metric label for the final report (e.g. "Market Acceptance Score", "Approval Likelihood", "Investment Decision Verdict", "Policy Viability Index", "Hackathon Advancement Probability"). Choose what makes sense for THIS stimulus.

4. "actions" — array of 3 to 6 action verbs the agents will commit to. Each action is an object: {{ "name": UPPERCASE_VERB, "description": short explanation, "is_terminal": true if the action effectively ends engagement (REJECT-like) or false if it keeps the agent in the conversation, "affects_resource": null OR the exact name of one resource from resource_model.resources whose balance this action spends/deducts }}. DO NOT default to BUY/REJECT — choose actions native to this scenario. Examples for different domains: a pitch review uses INVEST/PASS/COUNTER_OFFER/REQUEST_MORE_INFO; a policy debate uses SUPPORT/OPPOSE/AMEND/ABSTAIN; a hackathon judging uses ADVANCE/ELIMINATE/SHORTLIST/REQUEST_DEMO; a consumer market uses BUY/REJECT/NEGOTIATE/IGNORE.

5. "state_vocabulary" — array of 6 to 12 emotional/cognitive states agents may adopt during this scenario (free-form strings, single words preferred, no enum constraint). Pick states that are realistic for the domain — a regulator's emotional palette differs from a teenager's.

6. "resource_model" — {{ "kind": one of "none" | "single" | "multi", "resources": [] }}. Use "none" when the scenario has no meaningful resource to spend (e.g. a public opinion poll, a values-debate). Use "single" when there is one obvious resource (e.g. money for consumers, attention-minutes for judges, political-capital for legislators). Use "multi" when agents weigh multiple resources at once. Each resource is {{ "name": SNAKE_CASE, "description": what it represents, "initial_default": typical starting balance, "max_default": typical ceiling }}. If kind is "none", "resources" must be an empty array.

7. "linguistic_clusters" — array of 2 to 5 communication-style groups agents will be classified into. Each cluster is {{ "cluster_id": short_snake_case_id, "description": who falls into this cluster, "style_prompt": a detailed instruction the agent will follow verbatim to speak in that style (tone, register, vocabulary, jargon, what to avoid) }}. Make the styles distinct from each other and natural for the scenario — do not default to formal/informal/aggressive if the scenario calls for something else (e.g. academic/practitioner/activist for a policy debate).

8. "macro_context" — array of 3 to 6 bullet strings describing the real-world environmental anchors agents should evaluate the stimulus against. These are scenario-relevant facts (regulatory climate, market conditions, cultural norms, technical constraints, historical precedents). Be concrete. Do not default to Indonesian macroeconomic indicators unless the stimulus is explicitly Indonesian.

9. "crisis_dimensions" — array of 4 to 8 short labels naming the kinds of shocks that would make sense to inject into THIS scenario in Round 3 (e.g. for a fintech product: "regulatory_freeze", "competitor_price_war", "data_breach"; for a policy debate: "public_backlash", "leaked_document", "opposition_amendment"; for a hackathon: "scope_creep", "team_withdrawal", "judge_skepticism_spike"). The crisis generator will pick one of these later.

10. "evaluation_dimensions" — array of 3 to 5 evaluation dimensions that agents should score independently when computing their utility. Each dimension is a short snake_case label representing a distinct axis of value/risk. Choose dimensions native to this scenario — examples: for a business pitch: "financial_return", "market_fit", "execution_risk", "team_capability"; for a policy debate: "equity_impact", "economic_feasibility", "political_viability"; for a personal decision: "happiness", "career_growth", "financial_security". Do NOT default to generic labels — derive from the stimulus.

OUTPUT FORMAT — return ONLY a valid JSON object with exactly these top-level keys: scenario_name, scenario_description, verdict_label, actions, state_vocabulary, resource_model, linguistic_clusters, macro_context, crisis_dimensions, evaluation_dimensions. No markdown, no preamble, no <thought> tags.
"""


RETRY_USER_HINT = (
    "Your previous response failed validation with this error:\n{error}\n\n"
    "Re-emit the JSON object with ALL required fields present and correctly typed. "
    "Return only the JSON object."
)


class SchemaDesignError(RuntimeError):
    pass


async def design_schema(
    client: OllamaClient,
    stimulus: str,
    model: Optional[str] = None,
) -> SimulationSchema:
    messages = [
        {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT},
        {"role": "user", "content": _user_prompt(stimulus)},
    ]

    last_error: Optional[str] = None
    for attempt in range(2):
        try:
            raw = await client.chat(
                messages,
                model=model,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            raw = ""
            last_error = f"network/client error: {type(e).__name__}: {e}"
            if attempt == 0:
                messages.append({"role": "assistant", "content": ""})
                messages.append({
                    "role": "user",
                    "content": RETRY_USER_HINT.format(error=last_error),
                })
            continue

        parsed = parse_json_robustly(raw)

        if not parsed:
            last_error = "response did not contain a JSON object"
        else:
            try:
                return SimulationSchema.from_dict(parsed)
            except (KeyError, TypeError, ValueError) as e:
                last_error = f"{type(e).__name__}: {e}"

        if attempt == 0:
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": RETRY_USER_HINT.format(error=last_error),
            })

    raise SchemaDesignError(
        f"Architect failed to produce a valid SimulationSchema after 2 attempts. "
        f"Last error: {last_error}"
    )
