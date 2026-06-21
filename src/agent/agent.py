import json
from typing import Dict, Any, List, Optional
import httpx

from src.llm.client import OllamaClient
from src.agent.profile import AgentProfile, AgentState


class Agent:
    """
    Unified Agent controller wrapping its Profile, Memory, and LLM reasoning.
    Grounds LLM opinions in mathematical utility attributes & persistent state.
    """

    def __init__(self, profile: AgentProfile, client: OllamaClient):
        self.profile = profile
        self.client = client
        # Decision threshold (theta). If Utility > theta, execute action.
        self.decision_threshold = 0.5

    def build_system_prompt(self, context_summary: str = "") -> str:
        """
        Create a dynamic system prompt representing this agent's identity,
        personality, bias weights, and current state.
        """
        attributes = self.profile.attributes
        resources = self.profile.resource_pool
        memories = "\n".join([f"- {m}" for m in self.profile.memory_vectors])

        system_prompt = f"""You are simulating an autonomous agent of a social colony.
You MUST think and act strictly according to your defined archetype and internal state.
Do NOT break character or sound like an AI assistant. Be direct, opinionated, and show biases.

--- YOUR IDENTITY ---
Agent ID: {self.profile.agent_id}
Archetype/Profile: {self.profile.archetype}
Current Emotional/Internal State: {self.profile.current_internal_state}

--- CHARACTERISTICS & BIASES ---
- Rationality Index: {attributes.rationality_index:.2f} (1.0 = purely logical, 0.0 = purely emotional)
- Aggressiveness: {attributes.aggressiveness:.2f} (1.0 = highly dominant/confrontational, 0.0 = passive/avoidant)
- Risk Tolerance: {attributes.risk_tolerance:.2f} (1.0 = reckless gambler, 0.0 = extremely paranoid safety seeker)

--- ECONOMIC STATUS & RESOURCES ---
- Primary Resource: {resources.primary_resource_name}
- Current Balance: {resources.current_balance:.2f} / {resources.max_capacity:.2f}

--- PERSISTENT MEMORIES ---
{memories if memories else "- (No past memories recorded yet)"}

--- CURRENT SIMULATION CONTEXT ---
{context_summary if context_summary else "Normal daily operations."}

--- DECISION LOGIC (UTILITY EVALUATION) ---
You evaluate the personal significance weights and perceived values for the proposed stimulus/concept.
The underlying mathematical formula used by the simulation platform to determine your actions is:
Utility = (W_savings * V_gains) + (W_urgency * V_urgency) + (W_ego * V_ego) - Cost

You do NOT decide the final action_decision or emotional state yourself. The simulation engine will mathematically compute your final decision and automatically update your state machine based on the weights and values you output below. 

Format your evaluation strictly as the valid JSON structure shown below.

--- RESPONSE FORMAT ---
You must output a single valid JSON object containing exactly the following keys. Do NOT output any conversational text or explanation outside of the JSON block.

{{
  "internal_monologue": "Your raw, private thoughts about the stimulus/concept. Reflect deeply on your archetype, financial standing, risk tolerance, and real motivations. (Hidden from other agents)",
  "public_reaction": "What you say out loud, write down, or do in front of the others regarding this stimulus. Direct and opinionated.",
  "utility_weights": {{
    "w_savings": 0.0, // weight you place on saving money/resources (0.0 to 1.0)
    "w_urgency": 0.0, // weight you place on immediate need/urgency (0.0 to 1.0)
    "w_ego": 0.0      // weight you place on status, pride, or ego (0.0 to 1.0)
  }},
  "stimulus_evaluated_values": {{
    "v_gains": 0.0,   // estimated value/gain of this stimulus to you (0.0 to 1.0)
    "v_urgency": 0.0, // perceived urgency of action (0.0 to 1.0)
    "v_ego": 0.0,     // perceived status/glorification gained (0.0 to 1.0)
    "cost": 0.0       // estimated price or resource cost you have to pay (scaled 0.0 to 1.0)
  }},
  "new_memory_to_store": "A short, single-sentence episodic memory representing what you learned or resolved from this interaction (to be stored in memory)."
}}
"""
        return system_prompt

    def _parse_json_robustly(self, text: str) -> Dict[str, Any]:
        """
        Extract and parse a JSON object from text that may be polluted with
        preambles, markdown formatting, or postscripts.
        """
        # Try direct parsing first
        cleaned = text.strip()
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # Try to clean standard markdown code blocks first
        if "```" in cleaned:
            parts = cleaned.split("```")
            for part in parts:
                part_stripped = part.strip()
                if part_stripped.startswith("json"):
                    part_stripped = part_stripped[4:].strip()
                if part_stripped.startswith("{") and part_stripped.endswith("}"):
                    try:
                        return json.loads(part_stripped)
                    except Exception:
                        pass

        # Failover search for the first '{' and the last '}'
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            substring = cleaned[start_idx:end_idx + 1]
            try:
                return json.loads(substring)
            except Exception:
                pass

        # If everything fails, do a standard json.loads to trigger the original exception
        return json.loads(text)

    def _evaluate_utility_and_transition(self, parsed_data: Dict[str, Any]):
        """
        Evaluate weights & values from LLM, calculate mathematical utility,
        programmatically assign action_decision and new_internal_state Enum,
        and update resources if action is BUY.
        """
        weights = parsed_data.get("utility_weights", {})
        vals = parsed_data.get("stimulus_evaluated_values", {})

        # Safe extraction
        w_savings = float(weights.get("w_savings", 0.0))
        w_urgency = float(weights.get("w_urgency", 0.0))
        w_ego = float(weights.get("w_ego", 0.0))

        v_gains = float(vals.get("v_gains", 0.0))
        v_urgency = float(vals.get("v_urgency", 0.0))
        v_ego = float(vals.get("v_ego", 0.0))
        cost = float(vals.get("cost", 0.0))

        # Calculate exact utility U(A)_t = W_savings * V_gains + W_urgency * V_urgency + W_ego * V_ego - Cost
        utility = (w_savings * v_gains) + (w_urgency * v_urgency) + (w_ego * v_ego) - cost
        
        # Decide action and state transition programmatically based on utility
        # Threshold theta = 0.5 (BUY threshold)
        if utility > self.decision_threshold:
            action = "BUY"
        elif 0.1 < utility <= self.decision_threshold:
            # High aggressiveness leads to DEBATE, low aggressiveness to COLLABORATE
            if self.profile.attributes.aggressiveness > 0.6:
                action = "DEBATE"
            else:
                action = "COLLABORATE"
        elif -0.1 <= utility <= 0.1:
            action = "IGNORE"
        else: # utility < -0.1
            action = "REJECT"

        # Determine emotional transition strictly using our StrEnum
        if action == "BUY":
            if utility > 0.8:
                new_state = AgentState.EXCITED
            else:
                new_state = AgentState.SATISFIED
        elif action == "REJECT":
            if self.profile.attributes.aggressiveness > 0.6:
                new_state = AgentState.ANGRY
            elif self.profile.attributes.risk_tolerance < 0.3:
                new_state = AgentState.PARANOID
            else:
                new_state = AgentState.SKEPTICAL
        elif action in ("DEBATE", "COLLABORATE"):
            if self.profile.attributes.rationality_index > 0.7:
                new_state = AgentState.ANALYTICAL
            else:
                new_state = AgentState.INQUISITIVE
        else: # IGNORE
            new_state = AgentState.BORED

        # Inject clean programmatic results into parsed_data
        parsed_data["action_decision"] = action
        parsed_data["new_internal_state"] = str(new_state)

        # Apply state changes to AgentProfile (emotional state + episodic memory)
        self.profile.current_internal_state = new_state

        new_memory = parsed_data.get("new_memory_to_store")
        if new_memory and isinstance(new_memory, str):
            new_memory = new_memory.strip()
            if new_memory and new_memory not in self.profile.memory_vectors:
                self.profile.memory_vectors.append(new_memory)
                if len(self.profile.memory_vectors) > 10:
                    self.profile.memory_vectors.pop(0)

        # Resource deduct if BUY
        if action == "BUY" and cost > 0:
            damage = cost * (self.profile.resource_pool.max_capacity * 0.1)
            new_balance = max(0.0, self.profile.resource_pool.current_balance - damage)
            self.profile.resource_pool.current_balance = new_balance

    async def perceive_and_react(
        self, stimulus: str, context_summary: str = "", model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an environmental stimulus or message, perform utility evaluation,
        and generate a structured behavioral response using Ollama.
        """
        system_prompt = self.build_system_prompt(context_summary)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"STIMULUS TO EVALUATE:\n{stimulus}"},
        ]

        try:
            raw_response = await self.client.chat(messages, model=model)
            parsed_data = self._parse_json_robustly(raw_response)

            # Programmatically compute exact math decisions and transition states
            self._evaluate_utility_and_transition(parsed_data)

            return parsed_data

        except json.JSONDecodeError as je:
            # Robust fallback in case the LLM fails to output valid JSON
            return {
                "error": "Failed to parse structured reaction",
                "raw_response": raw_response if 'raw_response' in locals() else "",
                "action_decision": "IGNORE",
                "new_internal_state": str(self.profile.current_internal_state),
            }
        except Exception as e:
            return {
                "error": f"Error during perception: {str(e)}",
                "action_decision": "IGNORE",
                "new_internal_state": str(self.profile.current_internal_state),
            }

    async def debate_and_react(
        self, stimulus: str, round1_transcript: str, adversary: Optional[dict] = None, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Conduct a secondary debate/reflection round. The agent perceives peers' public
        opinions, and decides to either stand their ground, debate, collaborate, or change
        their decisions based on social influence and utility reassessment.
        """
        base_prompt = self.build_system_prompt()
        
        debate_instruction = f"""You are now entering ROUND 2 (DEBATE & REFLECTION) of the simulation.
Your peers in the colony have voiced their initial public reactions.

--- PEER REACTIONS TRANSCRIPT ---
{round1_transcript}

--- YOUR INSTRUCTIONS ---
1. Review what your peers said about the stimulus: "{stimulus}".
2. Evaluate their reasoning. Are they being overly naive, too paranoid, or complaining about price?
3. Decide whether you want to stand your ground, shift your internal utility perceptions, persuade them, scale down your budget, or collaborate/compromise.
4. Respond with a new valid JSON. If you are influenced by your peers, you can shift your weights, value perceptions, and public statement.
5. In your "public_reaction", speak DIRECTLY to your peers' concerns (refer to them or their archetypes!).
"""

        if adversary:
            debate_instruction += f"""
--- DIRECT CHALLENGE ---
You have been challenged directly by the {adversary.get('archetype', 'another agent')} (who took the action {adversary.get('action', 'IGNORE')} and stated publicly: "{adversary.get('statement', '...')}"):
You MUST address their stance directly in your "public_reaction" and "internal_monologue", defend your reasoning against their point of view, and explain why you disagree (or compromise, if their argument makes you shift your utility).
"""

        messages = [
            {"role": "system", "content": base_prompt},
            {"role": "user", "content": debate_instruction},
        ]

        try:
            raw_response = await self.client.chat(messages, model=model)
            parsed_data = self._parse_json_robustly(raw_response)

            # Programmatically compute exact math decisions and transition states
            self._evaluate_utility_and_transition(parsed_data)

            return parsed_data
        except Exception as e:
            return {
                "error": f"Error during debate: {str(e)}",
                "raw_response": raw_response if 'raw_response' in locals() else "",
                "action_decision": "IGNORE",
                "new_internal_state": str(self.profile.current_internal_state),
            }

    async def react_to_crisis(
        self, crisis: str, original_stimulus: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an external crisis event injected mid-simulation, evaluate its economic and 
        emotional impact on the original concept, and update decision and internal state.
        """
        context_summary = f"CRITICAL INTERVENTION: {crisis}\n(Original Concept: {original_stimulus})"
        system_prompt = self.build_system_prompt(context_summary)
        
        prompt = f"""An external crisis event has occurred that impacts the original concept:
Original Concept: "{original_stimulus}"
Crisis Event: "{crisis}"

Evaluate how this crisis changes the parameters of your decision utility:
1. Does it increase the cost / risk (e.g., higher taxes, security concerns)? If so, adjust your evaluated "cost" upwards in the JSON.
2. Does it reduce the perceived gains (v_gains) or increase the urgency (v_urgency)?
3. Respond with a new valid JSON updating your internal monologue, public reaction, utility weights, evaluated values, and new memory.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            raw_response = await self.client.chat(messages, model=model)
            parsed_data = self._parse_json_robustly(raw_response)

            # Programmatically compute exact math decisions and transition states
            self._evaluate_utility_and_transition(parsed_data)

            return parsed_data
        except Exception as e:
            return {
                "error": f"Error during crisis reaction: {str(e)}",
                "raw_response": raw_response if 'raw_response' in locals() else "",
                "action_decision": "IGNORE",
                "new_internal_state": str(self.profile.current_internal_state),
            }

