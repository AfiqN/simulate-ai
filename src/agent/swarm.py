import statistics
from typing import Optional

from src.llm.client import OllamaClient
from src.llm.json_parse import parse_json_robustly
from src.agent.profile import AgentProfile, AgentAttributes, ResourceBalance
from src.schema.simulation_schema import SimulationSchema


class SwarmGenerationError(RuntimeError):
    pass


def _resource_block(schema: SimulationSchema) -> str:
    rm = schema.resource_model
    if rm.kind == "none":
        return (
            'For each agent, set "resources": [] (empty array). '
            "This scenario does not track resources."
        )
    lines = ["For each agent, populate \"resources\" with one entry per resource below:"]
    for r in rm.resources:
        default_current = r.initial_default if r.initial_default is not None else 0
        default_max = r.max_default if r.max_default is not None else max(default_current, 1)
        lines.append(
            f'  - name: "{r.name}" ({r.description or "no description"}). '
            f"Reasonable starting balance around {default_current}, ceiling around {default_max}. "
            "Vary per persona to reflect heterogeneity."
        )
    lines.append(
        'Each resource entry is shaped: {"name": str, "current": float, "maximum": float}. '
        "current must be <= maximum and both must be >= 0."
    )
    return "\n".join(lines)


def _cluster_block(schema: SimulationSchema) -> str:
    lines = ["Each agent must be assigned exactly one linguistic_cluster_id from this list:"]
    for c in schema.linguistic_clusters:
        lines.append(f'  - "{c.cluster_id}" — {c.description}')
    return "\n".join(lines)


def _action_coverage_block(schema: SimulationSchema, count: int) -> str:
    required_span = min(count, len(schema.actions))
    lines = [
        "ACTION COVERAGE REQUIREMENT (load-bearing — violation causes automatic rejection):",
        f"The {count} personas must collectively cover at least {required_span} distinct actions in their natural Round 1 reaction. "
        "For EACH of the actions below, design at least one persona whose archetype, attributes "
        "(rationality_index / aggressiveness / risk_tolerance), memories, and starting emotional state make THAT action "
        "their most likely first move:",
    ]
    for a in schema.actions:
        suffix = " (terminal)" if a.is_terminal else ""
        lines.append(f'  - {a.name}{suffix}: {a.description} — who in this scenario would commit to this first?')
    lines.append("")
    lines.append(
        "CRITICAL: Design each persona TO TARGET a specific action. Do NOT design personas first and assign actions later. "
        "Start from the action list, then ask 'what kind of stakeholder would naturally choose THIS action given this scenario?' "
        "For example, if the actions include both ADOPT and OPPOSE, you MUST have at least one persona who would ADOPT "
        "AND at least one who would OPPOSE. A swarm where most personas gravitate toward the same action is INVALID and will "
        "be rejected — it collapses the debate dynamics and produces orphan agents with no cross-faction challengers."
    )
    return "\n".join(lines)


def _build_prompt(schema: SimulationSchema, stimulus: str, count: int, rag_perspectives: dict[str, list[str]] | None = None) -> str:
    rag_block = ""
    if rag_perspectives:
        lines = []
        for cluster in schema.linguistic_clusters:
            facts = rag_perspectives.get(cluster.cluster_id, [])
            if facts:
                facts_str = "\n".join(f"    - {fact}" for fact in facts)
                lines.append(f'  For cluster "{cluster.cluster_id}" ({cluster.description}):\n{facts_str}')
        if lines:
            perspectives = "\n\n".join(lines)
            rag_block = f"""

STAKEHOLDER PERSPECTIVES (real-world attitudes — use to shape each agent's worldview):

{perspectives}

Use these real-world perspectives to shape each agent's memory_vectors and attitudes.
Agents should reflect the genuine sentiments and worldview of their stakeholder group.
Do NOT copy verbatim — synthesize into character-defining beliefs.
"""

    return f"""You are the SimulateAI Swarm Generator. Design exactly {count} distinct agent personas for the scenario "{schema.scenario_name}".

Scenario description: {schema.scenario_description}

Stimulus the agents will react to:
\"\"\"
{stimulus}
\"\"\"

{_action_coverage_block(schema, count)}

Constraints:
- Personas must collectively represent a realistic, contrasting cross-section of stakeholders for THIS scenario. Avoid homogeneity.
- Archetype names must use snake_case (e.g. "skeptical_regulator", "early_stage_investor"). No spaces.
- attributes are floats in [0.0, 1.0]:
  - rationality_index (1.0 = pure logic, 0.0 = pure emotion)
  - aggressiveness (1.0 = dominant/confrontational, 0.0 = passive)
  - risk_tolerance (1.0 = reckless, 0.0 = extremely cautious)
- current_internal_state must be one of: {", ".join(schema.state_vocabulary)}.
- memory_vectors: exactly 2 short, character-defining beliefs or recollections that shape how this agent will evaluate the stimulus.

{_cluster_block(schema)}

{_resource_block(schema)}
{rag_block}
Return ONLY a JSON object of this exact shape (no markdown, no <thought> tags, no preamble):

{{
  "agents": [
    {{
      "agent_id": "SIM-AGT-001",
      "archetype": "snake_case_name",
      "linguistic_cluster_id": "one of the cluster ids above",
      "attributes": {{
        "rationality_index": 0.0,
        "aggressiveness": 0.0,
        "risk_tolerance": 0.0
      }},
      "resources": [],
      "memory_vectors": ["belief one", "belief two"],
      "current_internal_state": "one of the vocabulary entries"
    }}
  ]
}}
"""


def _diversity_is_low(profiles: list[AgentProfile], schema: SimulationSchema) -> bool:
    if len(profiles) < 4:
        return False

    distinct_clusters = len({p.linguistic_cluster_id for p in profiles})
    cluster_target = min(3, len(schema.linguistic_clusters))
    if cluster_target >= 2 and distinct_clusters < cluster_target:
        return True

    distinct_states = len({p.current_internal_state.lower() for p in profiles})
    state_target = min(3, len(schema.state_vocabulary))
    if state_target >= 2 and distinct_states < state_target:
        return True

    rat = [p.attributes.rationality_index for p in profiles]
    agg = [p.attributes.aggressiveness for p in profiles]
    risk = [p.attributes.risk_tolerance for p in profiles]
    max_spread = max(statistics.pstdev(rat), statistics.pstdev(agg), statistics.pstdev(risk))
    return max_spread < 0.15


def _retry_hint(last_error: str, schema: SimulationSchema) -> str:
    if last_error.startswith("diversity_low"):
        actions_list = ", ".join(a.name for a in schema.actions)
        return (
            "Your previous swarm is action-monoculture: persona attributes, linguistic clusters, "
            "and starting emotional states are too clustered, which predicts most agents will commit "
            "to the same Round 1 action. "
            "DISCARD the previous swarm entirely — do NOT base the new personas on your prior response. "
            "Design from scratch with EXPLICIT heterogeneity — each persona "
            "must be designed to gravitate toward a DIFFERENT action from this list: "
            f"{actions_list}. Spread rationality_index, aggressiveness, risk_tolerance, "
            "linguistic_cluster_id, and current_internal_state widely across the personas. "
            "Return only the JSON object."
        )
    return (
        f"Your previous response failed validation: {last_error}. "
        "Re-emit the JSON object with the exact required shape. Return only JSON."
    )


async def generate_llm_swarm(
    client: OllamaClient,
    schema: SimulationSchema,
    stimulus: str,
    count: int,
    model: Optional[str] = None,
    rag_perspectives: Optional[dict[str, list[str]]] = None,
) -> list[AgentProfile]:
    prompt = _build_prompt(schema, stimulus, count, rag_perspectives=rag_perspectives)
    messages = [
        {
            "role": "system",
            "content": "You output a single JSON object matching the requested schema. No prose, no markdown fences, no <thought> tags.",
        },
        {"role": "user", "content": prompt},
    ]

    last_error: Optional[str] = None
    last_profiles: Optional[list[AgentProfile]] = None

    for attempt in range(2):
        try:
            raw = await client.chat(messages, model=model, response_format={"type": "json_object"})
        except Exception as e:
            raw = ""
            last_error = f"network/client error: {type(e).__name__}: {e}"
            if attempt == 0:
                messages.append({"role": "assistant", "content": ""})
                messages.append({"role": "user", "content": _retry_hint(last_error, schema)})
            continue

        parsed = parse_json_robustly(raw)

        if not parsed or "agents" not in parsed:
            last_error = "missing 'agents' key in response"
        else:
            try:
                profiles = _materialize(parsed["agents"], schema, count)
                if not profiles:
                    last_error = "no valid agent objects produced"
                elif _diversity_is_low(profiles, schema):
                    last_profiles = profiles
                    last_error = "diversity_low: attributes/clusters/states too clustered"
                else:
                    return profiles
            except (KeyError, TypeError, ValueError) as e:
                last_error = f"{type(e).__name__}: {e}"

        if attempt == 0:
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": _retry_hint(last_error, schema)})

    if last_profiles is not None:
        return last_profiles

    raise SwarmGenerationError(
        f"Swarm generator failed after 2 attempts. Last error: {last_error}"
    )


def _materialize(
    agent_dicts: list,
    schema: SimulationSchema,
    count: int,
) -> list[AgentProfile]:
    valid_clusters = set(schema.cluster_ids())
    valid_states = {s.lower(): s for s in schema.state_vocabulary}
    fallback_cluster = schema.linguistic_clusters[0].cluster_id if schema.linguistic_clusters else "default"
    fallback_state = schema.state_vocabulary[0] if schema.state_vocabulary else "Neutral"

    profiles: list[AgentProfile] = []
    for i, raw in enumerate(agent_dicts[:count]):
        if not isinstance(raw, dict):
            continue
        attrs_raw = raw.get("attributes") or {}
        attributes = AgentAttributes(
            rationality_index=_clamp01(attrs_raw.get("rationality_index", 0.5)),
            aggressiveness=_clamp01(attrs_raw.get("aggressiveness", 0.5)),
            risk_tolerance=_clamp01(attrs_raw.get("risk_tolerance", 0.5)),
        )

        cluster_id = str(raw.get("linguistic_cluster_id", fallback_cluster))
        if cluster_id not in valid_clusters:
            cluster_id = fallback_cluster

        state_raw = str(raw.get("current_internal_state", fallback_state))
        state = valid_states.get(state_raw.lower(), state_raw if state_raw else fallback_state)

        memories = list(raw.get("memory_vectors", []))[:5]
        memories = [str(m) for m in memories if str(m).strip()]
        if not memories:
            memories = [
                "Approaches new proposals through personal context.",
                "Weighs perceived gains against perceived costs.",
            ]

        resources = _materialize_resources(raw.get("resources", []), schema)

        profiles.append(AgentProfile(
            agent_id=f"SIM-AGT-{i + 1:03d}",
            archetype=str(raw.get("archetype", f"dynamic_archetype_{i + 1}")),
            linguistic_cluster_id=cluster_id,
            attributes=attributes,
            resources=resources,
            memory_vectors=memories,
            current_internal_state=state,
        ))
    return profiles


def _materialize_resources(raw_list, schema: SimulationSchema) -> list[ResourceBalance]:
    if schema.resource_model.kind == "none":
        return []
    if not isinstance(raw_list, list):
        return _default_resources(schema)

    declared = {r.name for r in schema.resource_model.resources}
    out: list[ResourceBalance] = []
    seen: set[str] = set()
    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name or name not in declared or name in seen:
            continue
        current = max(0.0, _coerce_float(entry.get("current"), 0.0))
        maximum = max(current, _coerce_float(entry.get("maximum"), current))
        out.append(ResourceBalance(name=name, current=current, maximum=maximum))
        seen.add(name)

    for r in schema.resource_model.resources:
        if r.name not in seen:
            current = r.initial_default if r.initial_default is not None else 0.0
            maximum = r.max_default if r.max_default is not None else max(current, 1.0)
            out.append(ResourceBalance(name=r.name, current=current, maximum=maximum))

    return out


def _default_resources(schema: SimulationSchema) -> list[ResourceBalance]:
    out: list[ResourceBalance] = []
    for r in schema.resource_model.resources:
        current = r.initial_default if r.initial_default is not None else 0.0
        maximum = r.max_default if r.max_default is not None else max(current, 1.0)
        out.append(ResourceBalance(name=r.name, current=current, maximum=maximum))
    return out


def _clamp01(value) -> float:
    return max(0.0, min(1.0, _coerce_float(value, 0.5)))


def _coerce_float(value, default: float) -> float:
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
        # Keep only valid float characters, handle leading/trailing minus properly
        kept = "".join(c for c in cleaned if c.isdigit() or c in (".", "-"))
        if kept.startswith("-"):
            kept = "-" + kept[1:].replace("-", "")
        else:
            kept = kept.replace("-", "")
        try:
            return float(kept)
        except ValueError:
            return default
    return default
