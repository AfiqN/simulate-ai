import random
import json
from typing import Optional
from src.agent.profile import AgentProfile, AgentAttributes, ResourcePool, AgentState
from src.llm.client import OllamaClient


def get_mock_agents() -> list[AgentProfile]:
    """
    Generate three contrasting pre-defined agent profiles representing a miniature society.
    """
    agent1 = AgentProfile(
        agent_id="SIM-AGT-001",
        archetype="Frugal_College_Student",
        attributes=AgentAttributes(
            rationality_index=0.85,
            aggressiveness=0.30,
            risk_tolerance=0.20,
        ),
        resource_pool=ResourcePool(
            primary_resource_name="Fiat_Currency",
            current_balance=450000.0,
            max_capacity=1500000.0,
        ),
        memory_vectors=[
            "Disappointed in buying cheap items that broke in 2 days.",
            "Loves discount coupons and free shipping.",
        ],
        current_internal_state="Skeptical",
    )

    agent2 = AgentProfile(
        agent_id="SIM-AGT-002",
        archetype="Impulsive_Sultan_Techie",
        attributes=AgentAttributes(
            rationality_index=0.40,
            aggressiveness=0.80,
            risk_tolerance=0.90,
        ),
        resource_pool=ResourcePool(
            primary_resource_name="Fiat_Currency",
            current_balance=8500000.0,
            max_capacity=20000000.0,
        ),
        memory_vectors=[
            "Believes price determines quality.",
            "Always wants to look advanced and premium in front of peers.",
        ],
        current_internal_state="Excited",
    )

    agent3 = AgentProfile(
        agent_id="SIM-AGT-003",
        archetype="Pragmatic_Small_Business_Owner",
        attributes=AgentAttributes(
            rationality_index=0.95,
            aggressiveness=0.60,
            risk_tolerance=0.50,
        ),
        resource_pool=ResourcePool(
            primary_resource_name="Fiat_Currency",
            current_balance=2500000.0,
            max_capacity=10000000.0,
        ),
        memory_vectors=[
            "Strictly calculates ROI (Return on Investment) for every single penny spent.",
            "Needs stable services with guarantees, hates high risk commitments.",
        ],
        current_internal_state="Analytical",
    )

    return [agent1, agent2, agent3]


def generate_custom_swarm(count: int) -> list[AgentProfile]:
    """
    Generate N scalable, unique agent profiles with randomized offsets based on 5 core archetypes.
    This helps stress-test our system concurrently.
    """
    archetypes = [
        ("Frugal_College_Student", "Fiat_Currency", 450000.0, 1500000.0, 0.85, 0.30, 0.20, [
            "Disappointed in buying cheap items that broke in 2 days.",
            "Loves discount coupons and free shipping."
        ]),
        ("Impulsive_Sultan_Techie", "Fiat_Currency", 8500000.0, 20000000.0, 0.40, 0.80, 0.90, [
            "Believes price determines quality.",
            "Always wants to look advanced and premium in front of peers."
        ]),
        ("Pragmatic_Small_Business_Owner", "Fiat_Currency", 2500000.0, 10000000.0, 0.95, 0.60, 0.50, [
            "Strictly calculates ROI (Return on Investment) for every single penny spent.",
            "Needs stable services with guarantees, hates high risk commitments."
        ]),
        ("Skeptical_Senior_Citizen", "Fiat_Currency", 1200000.0, 5000000.0, 0.70, 0.15, 0.10, [
            "Values safety, warranty, and long-term customer service.",
            "Wary of internet scams and modern tech terms."
        ]),
        ("Aggressive_Crypto_Trader", "Fiat_Currency", 6000000.0, 50000000.0, 0.50, 0.95, 0.95, [
            "Obsessed with high risk, high reward plays.",
            "Constantly looking for the next trend to jump on."
        ])
    ]

    profiles = []
    for i in range(count):
        # Pick one base archetype or rotate through the list
        base = archetypes[i % len(archetypes)]

        # Add minor random variations to attributes for natural diversity
        rationality = max(0.0, min(1.0, base[4] + random.uniform(-0.1, 0.1)))
        aggressiveness = max(0.0, min(1.0, base[5] + random.uniform(-0.1, 0.1)))
        risk_tolerance = max(0.0, min(1.0, base[6] + random.uniform(-0.1, 0.1)))

        # Vary the baseline current balance slightly
        balance = base[2] * random.uniform(0.8, 1.2)

        profiles.append(AgentProfile(
            agent_id=f"SIM-AGT-{i+1:03d}",
            archetype=f"{base[0]}_v{i // len(archetypes) + 1}" if i >= len(archetypes) else base[0],
            attributes=AgentAttributes(
                rationality_index=rationality,
                aggressiveness=aggressiveness,
                risk_tolerance=risk_tolerance
            ),
            resource_pool=ResourcePool(
                primary_resource_name=base[1],
                current_balance=round(balance, -2),
                max_capacity=base[3]
            ),
            memory_vectors=base[7].copy(),
            current_internal_state=random.choice(["Neutral", "Inquisitive", "Skeptical", "Excited"])
        ))
    return profiles


async def generate_llm_swarm(
    client: OllamaClient, stimulus: str, count: int, model: Optional[str] = None
) -> list[AgentProfile]:
    """
    Generate N scalable, unique agent profiles tailored to the stimulus using an LLM.
    Falls back to generate_custom_swarm in case of LLM or parsing errors.
    """
    valid_states = ["Neutral", "Skeptical", "Excited", "Angry", "Satisfied", "Bored", "Aggressive", "Paranoid", "Analytical", "Inquisitive"]
    
    prompt = f"""You are the SimulateAI Swarm Generator. Your task is to analyze the following user concept stimulus and generate exactly {count} distinct, realistic, and contrasting agent profiles that are relevant to simulating how an ecosystem, market, or target audience reacts to this concept.

STIMULUS TO SIMULATE:
"{stimulus}"

Number of agents to generate: {count}

For each agent, you must design:
1. An `archetype` name (e.g., "Thrifty_Student", "Strict_Academic_Judge", "Tech_Early_Adopter", "Regulatory_Officer") that makes sense for testing this specific stimulus. Archetype names should use underscores instead of spaces.
2. Characteristics & attributes:
   - `rationality_index`: scale 0.0 to 1.0 (How logical they are)
   - `aggressiveness`: scale 0.0 to 1.0 (How confrontational/assertive they are)
   - `risk_tolerance`: scale 0.0 to 1.0 (How willing they are to take risks/safety compromises)
3. A relevant resource pool:
   - `primary_resource_name`: what resource they care about (e.g., "Fiat_Currency" for consumers, "Time_Budget_Hours" for busy professionals, "Cloud_Credits" for developers, etc.)
   - `current_balance`: starting resource balance
   - `max_capacity`: resource maximum capacity (must be >= current_balance)
4. `memory_vectors`: a list of exactly 2 short, character-appropriate memories or core beliefs that shape how they evaluate this specific stimulus.
5. `current_internal_state`: starting emotional/internal state, selected ONLY from this list: {valid_states}

Return ONLY a valid JSON object matching the schema below. Do not output any conversational text, markdown formatting other than the JSON block, or preamble.

Expected JSON schema:
{{
  "agents": [
    {{
      "agent_id": "SIM-AGT-001",
      "archetype": "archetype_name",
      "attributes": {{
        "rationality_index": 0.85,
        "aggressiveness": 0.30,
        "risk_tolerance": 0.20
      }},
      "resource_pool": {{
        "primary_resource_name": "Fiat_Currency",
        "current_balance": 450000.0,
        "max_capacity": 1500000.0
      }},
      "memory_vectors": [
        "Memory line 1 description.",
        "Memory line 2 description."
      ],
      "current_internal_state": "Skeptical"
    }}
  ]
}}
"""
    messages = [
        {"role": "system", "content": "You are a swarm synthesis engine that outputs raw JSON matching the requested schema. Do not output any notes, conversational text or markdown codeblocks except the requested JSON block."},
        {"role": "user", "content": prompt}
    ]

    try:
        raw_response = await client.chat(messages, model=model)
        
        # Robust JSON parsing
        cleaned = raw_response.strip()
        parsed_data = None
        
        try:
            parsed_data = json.loads(cleaned)
        except Exception:
            # Try cleaning standard markdown code blocks
            if "```" in cleaned:
                parts = cleaned.split("```")
                for part in parts:
                    part_stripped = part.strip()
                    if part_stripped.startswith("json"):
                        part_stripped = part_stripped[4:].strip()
                    if part_stripped.startswith("{") and part_stripped.endswith("}"):
                        try:
                            parsed_data = json.loads(part_stripped)
                            break
                        except Exception:
                            pass
            
            if not parsed_data:
                # Failover search for the first '{' and the last '}'
                start_idx = cleaned.find("{")
                end_idx = cleaned.rfind("}")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    substring = cleaned[start_idx:end_idx + 1]
                    try:
                        parsed_data = json.loads(substring)
                    except Exception:
                        pass
        
        if not parsed_data or "agents" not in parsed_data:
            raise ValueError("Parsed JSON is missing 'agents' key or is empty")
            
        agents = []
        for i, agent_data in enumerate(parsed_data["agents"]):
            # Normalize agent_id if LLM got it wrong
            agent_id = f"SIM-AGT-{i+1:03d}"
            
            # Extract state and ensure it's valid
            raw_state = agent_data.get("current_internal_state", "Neutral")
            state_enum = AgentState.from_str(raw_state)
            
            attr_data = agent_data.get("attributes", {})
            attributes = AgentAttributes(
                rationality_index=max(0.0, min(1.0, float(attr_data.get("rationality_index", 0.5)))),
                aggressiveness=max(0.0, min(1.0, float(attr_data.get("aggressiveness", 0.5)))),
                risk_tolerance=max(0.0, min(1.0, float(attr_data.get("risk_tolerance", 0.5)))),
            )
            
            res_data = agent_data.get("resource_pool", {})
            current_balance = float(res_data.get("current_balance", 100.0))
            max_capacity = float(res_data.get("max_capacity", max(current_balance, 100.0)))
            if max_capacity < current_balance:
                max_capacity = current_balance
                
            resource_pool = ResourcePool(
                primary_resource_name=str(res_data.get("primary_resource_name", "Fiat_Currency")),
                current_balance=current_balance,
                max_capacity=max_capacity
            )
            
            memories = list(agent_data.get("memory_vectors", []))
            if not memories:
                memories = ["Evaluates the stimulus based on personal needs.", "Considers resource tradeoffs."]
            
            agents.append(AgentProfile(
                agent_id=agent_id,
                archetype=str(agent_data.get("archetype", f"Dynamic_Archetype_{i+1}")),
                attributes=attributes,
                resource_pool=resource_pool,
                memory_vectors=memories,
                current_internal_state=state_enum
            ))
            
        if len(agents) < count:
            # If we got fewer agents than requested, generate additional custom ones to fill the gap
            gap = count - len(agents)
            fallback_agents = generate_custom_swarm(gap)
            for j, fb_agent in enumerate(fallback_agents):
                fb_agent.agent_id = f"SIM-AGT-{len(agents)+1:03d}"
                agents.append(fb_agent)
                
        # Trim if we got more agents than requested
        return agents[:count]
        
    except Exception as e:
        # Fallback console print to indicate fallback mode was triggered
        print(f"\n[yellow]LLM swarm generation failed ({str(e)}). Falling back to randomized custom swarm.[/yellow]")
        return generate_custom_swarm(count)

