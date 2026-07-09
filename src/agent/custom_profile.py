"""Build full AgentProfiles from user-defined custom stakeholders via LLM."""

from typing import Optional

from src.llm.client import OllamaClient
from src.llm.json_parse import parse_json_robustly
from src.agent.profile import AgentProfile, AgentAttributes, ResourceBalance
from src.schema.simulation_schema import SimulationSchema


def _build_custom_prompt(stakeholders: list[dict], schema: SimulationSchema, stimulus: str) -> str:
    """Build LLM prompt to convert user-defined stakeholders into full AgentProfiles."""
    clusters_desc = "\n".join(
        f'  - "{c.cluster_id}" — {c.description}' for c in schema.linguistic_clusters
    )
    states_list = ", ".join(schema.state_vocabulary)
    actions_list = ", ".join(a.name for a in schema.actions)

    stakeholder_blocks = []
    for i, s in enumerate(stakeholders):
        focus = ", ".join(s.get("focus_areas") or []) or "not specified"
        constraints = ", ".join(s.get("constraints") or []) or "not specified"
        stakeholder_blocks.append(
            f"  {i + 1}. Role: {s['role']}\n"
            f"     Description: {s['description']}\n"
            f"     Focus areas: {focus}\n"
            f"     Constraints: {constraints}"
        )
    stakeholders_text = "\n".join(stakeholder_blocks)

    resource_block = ""
    if schema.resource_model.kind != "none":
        res_lines = []
        for r in schema.resource_model.resources:
            default_current = r.initial_default if r.initial_default is not None else 0
            default_max = r.max_default if r.max_default is not None else max(default_current, 1)
            res_lines.append(
                f'  - "{r.name}" (initial ~{default_current}, max ~{default_max})'
            )
        resource_block = (
            "Resources to assign (set appropriate levels for each stakeholder's position):\n"
            + "\n".join(res_lines)
        )

    return f"""You are the SimulateAI Custom Stakeholder Adapter. Convert user-defined stakeholders into full agent profiles that fit the simulation schema.

Scenario: {schema.scenario_name}
Description: {schema.scenario_description}

Stimulus:
\"\"\"{stimulus}\"\"\"

Available actions: {actions_list}
State vocabulary: {states_list}

Linguistic clusters:
{clusters_desc}

{resource_block}

User-defined stakeholders to convert:
{stakeholders_text}

For EACH stakeholder, generate a full agent profile JSON. Requirements:
- archetype: snake_case derived from role (e.g. "chief_financial_officer", "senior_regulator")
- linguistic_cluster_id: pick the cluster that best matches their communication style
- attributes: rationality_index, aggressiveness, risk_tolerance (floats 0.0-1.0) inferred from description
- current_internal_state: pick from the state vocabulary that fits their stance
- memory_vectors: 2-3 beliefs derived from their description and focus areas
- decision_framework: infer from description (e.g. "conservative, prioritizes cash preservation and ROI")
- knowledge_base: 1 sentence about their domain expertise inferred from role
- constraints: use user-provided constraints, or infer 1-2 from description
- influence_weight: 1.5-2.5 for senior/executive roles, 1.0-1.5 for mid-level
- backstory: 2-3 sentences grounding the persona based on role and description
- resources: appropriate levels for their position (if applicable)

Return ONLY a JSON object:
{{
  "profiles": [
    {{
      "archetype": "snake_case_name",
      "linguistic_cluster_id": "cluster_id",
      "attributes": {{
        "rationality_index": 0.0,
        "aggressiveness": 0.0,
        "risk_tolerance": 0.0
      }},
      "resources": [],
      "memory_vectors": ["belief 1", "belief 2"],
      "current_internal_state": "state",
      "decision_framework": "...",
      "knowledge_base": "...",
      "constraints": ["..."],
      "influence_weight": 1.5,
      "backstory": "..."
    }}
  ]
}}
"""


async def build_custom_profiles(
    stakeholders: list[dict],
    schema: SimulationSchema,
    stimulus: str,
    client: OllamaClient,
    start_index: int = 0,
    model: Optional[str] = None,
) -> list[AgentProfile]:
    """Convert user-defined stakeholders into full AgentProfiles via LLM.

    Args:
        stakeholders: list of dicts with keys: role, description, focus_areas?, constraints?
        schema: the simulation schema (for vocabulary, clusters, resources)
        stimulus: the scenario stimulus text
        client: LLM client
        start_index: starting agent ID number (for SIM-AGT-XXX numbering)
        model: optional model override

    Returns:
        List of AgentProfile objects marked with is_custom=True
    """
    if not stakeholders:
        return []

    prompt = _build_custom_prompt(stakeholders, schema, stimulus)
    messages = [
        {
            "role": "system",
            "content": "You output a single JSON object matching the requested schema. No prose, no markdown fences.",
        },
        {"role": "user", "content": prompt},
    ]

    raw = await client.chat(messages, model=model, response_format={"type": "json_object"})
    parsed = parse_json_robustly(raw)

    if not parsed or "profiles" not in parsed:
        # Fallback: build minimal profiles without LLM
        return _build_fallback_profiles(stakeholders, schema, start_index)

    profiles = _materialize_custom(parsed["profiles"], stakeholders, schema, start_index)
    if not profiles:
        return _build_fallback_profiles(stakeholders, schema, start_index)

    return profiles


def _materialize_custom(
    profile_dicts: list,
    stakeholders: list[dict],
    schema: SimulationSchema,
    start_index: int,
) -> list[AgentProfile]:
    """Convert LLM output into AgentProfile objects."""
    valid_clusters = set(schema.cluster_ids())
    valid_states = {s.lower(): s for s in schema.state_vocabulary}
    fallback_cluster = schema.linguistic_clusters[0].cluster_id if schema.linguistic_clusters else "default"
    fallback_state = schema.state_vocabulary[0] if schema.state_vocabulary else "Neutral"

    profiles: list[AgentProfile] = []
    for i, raw in enumerate(profile_dicts[:len(stakeholders)]):
        if not isinstance(raw, dict):
            continue

        attrs_raw = raw.get("attributes") or {}
        attributes = AgentAttributes(
            rationality_index=_clamp01(attrs_raw.get("rationality_index", 0.7)),
            aggressiveness=_clamp01(attrs_raw.get("aggressiveness", 0.5)),
            risk_tolerance=_clamp01(attrs_raw.get("risk_tolerance", 0.4)),
        )

        cluster_id = str(raw.get("linguistic_cluster_id", fallback_cluster))
        if cluster_id not in valid_clusters:
            cluster_id = fallback_cluster

        state_raw = str(raw.get("current_internal_state", fallback_state))
        state = valid_states.get(state_raw.lower(), state_raw if state_raw else fallback_state)

        memories = [str(m) for m in raw.get("memory_vectors", []) if str(m).strip()][:5]
        if not memories:
            stakeholder = stakeholders[i] if i < len(stakeholders) else {}
            memories = [
                f"Focused on: {stakeholder.get('description', 'strategic outcomes')}",
                f"Role demands: {stakeholder.get('role', 'leadership')} perspective",
            ]

        resources = _materialize_resources(raw.get("resources", []), schema)

        # Use user-provided constraints if LLM didn't produce good ones
        llm_constraints = [str(c) for c in raw.get("constraints", []) if str(c).strip()]
        stakeholder = stakeholders[i] if i < len(stakeholders) else {}
        user_constraints = stakeholder.get("constraints") or []
        constraints = llm_constraints if llm_constraints else user_constraints

        influence = max(0.5, min(3.0, _coerce_float(raw.get("influence_weight", 1.5), 1.5)))

        profiles.append(AgentProfile(
            agent_id=f"SIM-AGT-{start_index + i + 1:03d}",
            archetype=str(raw.get("archetype", f"custom_{stakeholder.get('role', 'stakeholder').lower().replace(' ', '_')}")),
            linguistic_cluster_id=cluster_id,
            attributes=attributes,
            resources=resources,
            memory_vectors=memories,
            current_internal_state=state,
            decision_framework=str(raw.get("decision_framework", "")),
            knowledge_base=str(raw.get("knowledge_base", "")),
            constraints=constraints,
            influence_weight=influence,
            backstory=str(raw.get("backstory", "")),
            is_custom=True,
        ))

    return profiles


def _build_fallback_profiles(
    stakeholders: list[dict],
    schema: SimulationSchema,
    start_index: int,
) -> list[AgentProfile]:
    """Build minimal profiles without LLM when the LLM call fails."""
    fallback_cluster = schema.linguistic_clusters[0].cluster_id if schema.linguistic_clusters else "default"
    fallback_state = schema.state_vocabulary[0] if schema.state_vocabulary else "Neutral"

    profiles: list[AgentProfile] = []
    for i, s in enumerate(stakeholders):
        role_slug = s["role"].lower().replace(" ", "_").replace("-", "_")
        archetype = f"custom_{role_slug}"

        profiles.append(AgentProfile(
            agent_id=f"SIM-AGT-{start_index + i + 1:03d}",
            archetype=archetype,
            linguistic_cluster_id=fallback_cluster,
            attributes=AgentAttributes(
                rationality_index=0.7,
                aggressiveness=0.5,
                risk_tolerance=0.4,
            ),
            resources=_default_resources(schema),
            memory_vectors=[
                f"Core focus: {s['description'][:80]}",
                f"Role: {s['role']} with strong domain conviction",
            ],
            current_internal_state=fallback_state,
            decision_framework=s["description"][:120],
            knowledge_base=f"Deep expertise as {s['role']}",
            constraints=s.get("constraints") or [],
            influence_weight=1.5,
            backstory=f"A seasoned {s['role']} who {s['description'][:100]}.",
            is_custom=True,
        ))

    return profiles


def _materialize_resources(raw_list, schema: SimulationSchema) -> list[ResourceBalance]:
    """Materialize resource entries from LLM output."""
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

    # Fill missing resources with defaults
    for r in schema.resource_model.resources:
        if r.name not in seen:
            current = r.initial_default if r.initial_default is not None else 0.0
            maximum = r.max_default if r.max_default is not None else max(current, 1.0)
            out.append(ResourceBalance(name=r.name, current=current, maximum=maximum))

    return out


def _default_resources(schema: SimulationSchema) -> list[ResourceBalance]:
    """Build default resources from schema."""
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
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default
