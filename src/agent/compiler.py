import json
from typing import List, Dict, Any, Optional
from src.llm.client import OllamaClient


class ExecutiveCompiler:
    """
    Dedicated AI analyzer that compiles raw, complex swarm debate logs
    into a structured, clinically sharp Executive Diagnostic Report.
    """

    def __init__(self, client: OllamaClient):
        self.client = client

    async def generate_crisis_event(
        self, stimulus: str, debate_transcript: str, model: Optional[str] = None
    ) -> str:
        """
        Analyze Round 2 debate transcripts to identify the dominant concern/complaint,
        then synthesize one realistic, highly contextual external crisis event.
        """
        crisis_prompt = f"""You are the SimulateAI External Event Catalyst.
Analyze the following debate transcripts from a swarm simulation and identify the single most dominant concern, fear, or structural complaint voiced by the agents.

Original Concept/Stimulus:
"{stimulus}"

Round 2 Debate Transcript:
{debate_transcript}

Your Task:
1. Identify the single most recurring or emotionally charged concern from the agents' debate.
2. Generate ONE external crisis event that directly hits this concern and would destabilize the ecosystem. It must be short, specific, and realistic (e.g., a regulatory announcement, market shock, competitor move, or social backlash).
3. Output ONLY the crisis event sentence. Do NOT provide explanation, context, or preamble. Just the raw crisis statement.

Example good outputs:
- "The government has just announced a new 3% digital transaction tax effective next month."
- "A major competitor has released an identical product at 40% lower price with a free tier."
- "A viral social media post exposes a critical data privacy vulnerability in similar apps."
"""
        messages = [
            {"role": "system", "content": "You are a crisis event synthesis engine. Output only a single raw sentence describing the crisis event."},
            {"role": "user", "content": crisis_prompt}
        ]

        try:
            crisis = await self.client.chat(messages, model=model)
            # Strip markdown, quotes, or extra whitespace from the output
            return crisis.strip().strip('"').strip("'").strip()
        except Exception as e:
            return f"An unexpected market disruption has occurred that directly impacts the viability of the proposed concept."

    async def compile_report(
        self,
        stimulus: str,
        round1_results: List[Dict[str, Any]],
        round2_results: List[Dict[str, Any]],
        round3_results: Optional[List[Dict[str, Any]]] = None,
        crisis_event: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Synthesize simulation decisions, monologues, and actions across all rounds,
        calculating metrics and drafting actionable strategic pivot advice.
        Now includes crisis resilience analysis if Round 3 data is provided.
        """
        # Formulate compilation transcript
        transcript_parts = []
        for i in range(len(round1_results)):
            r1 = round1_results[i]
            r2 = round2_results[i] if i < len(round2_results) else {}
            r3 = round3_results[i] if round3_results and i < len(round3_results) else {}

            p = f"""Agent: {r1['archetype']} (ID: {r1['id']})
- Initial Decision: {r1.get('action')} (Utility: {r1.get('utility', 0.0):.4f})
- Initial Inner Monologue: "{r1.get('monologue')}"
- Initial Public Statement: "{r1.get('statement')}"
"""
            if r2 and not r2.get("error"):
                p += f"""- Debate (Round 2) Decision: {r2.get('action')} (Utility: {r2.get('utility', 0.0):.4f})
- Debate (Round 2) Inner Monologue: "{r2.get('monologue')}"
- Debate (Round 2) Public Statement: "{r2.get('statement')}"
- Ending State after Debate: {r2.get('new_state')}
"""
            if r3 and not r3.get("error"):
                p += f"""- Crisis Reaction (Round 3) Decision: {r3.get('action')} (Utility: {r3.get('utility', 0.0):.4f})
- Crisis Inner Monologue: "{r3.get('monologue')}"
- Crisis Public Statement: "{r3.get('statement')}"
- Ending State after Crisis: {r3.get('new_state')}
"""
            transcript_parts.append(p)

        full_transcript = "\n---\n".join(transcript_parts)

        crisis_section = ""
        if crisis_event:
            crisis_section = f"""
## CRISIS EVENT INJECTED (Round 3 Stress-Test)
The following external crisis was autonomously synthesized and injected into the simulation:
> "{crisis_event}"
"""

        compiler_prompt = f"""You are the SimulateAI Chief Behavioral Architect & Diagnostic Director.
Your task is to analyze the raw execution transcripts of a multi-agent social colony simulation and compile a high-level, extremely objective, and actionable executive report.

The user proposed the following concept/product/stimulus:
"{stimulus}"
{crisis_section}
Below are the raw behavioral traces, debate transcripts, and crisis reaction data from the full simulation:
{full_transcript}

Please write the "EXECUTIVE BEHAVIORAL DIAGNOSTIC REPORT." It must be written in professional, sharp business English and formatted exactly using the Markdown rules below. Do NOT use backticks for paths or files. Use headers and well-structured lists.

YOUR ANALYSIS MUST INCLUDE:

1. EXECUTIVE SUMMARY & VERDICT
- Calculate a qualitative "Market Acceptance Score" (High / Mixed / Rejected) based on the final decisions.
- Give a raw, radically honest summary of the market fit.

2. FACTION MAPPING & ALIGNMENT
- Group the agents into distinct emergent factions (e.g., "The Conservative Value Seekers", "The Premium Status Buyers").
- Explain the dynamic conflict or consensus between these factions during the debate. Did any agent change their mind or get influenced?

3. PRODUCT/CONCEPT BLIND SPOTS (RED-TEAMING ANALYSIS)
- Explicitly pull out and list the structural flaws, price friction, safety concerns, or skepticism voiced in the agents' secret monologues and debate points.

4. SYSTEM STABILITY & CONSENSUS INDEX
- Evaluate how volatile or stable this ecosystem's reaction is. (e.g., high polarization or unanimous rejection/approval).

5. CRISIS RESILIENCE VERDICT (STRESS-TEST ANALYSIS)
- Analyze how the swarm reacted to the injected crisis event. Did it cause a cascading rejection, or did some agents pivot and adapt?
- Rate the concept's resilience: (Fragile / Moderate / Resilient).
- Identify which agent archetype is the most risk-sensitive pivot point under crisis conditions.

6. STRATEGIC PIVOT RECOMMENDATIONS (ACTIONABLE ADVICE)
- Give 3 distinct, highly concrete modifications to the original stimulus (e.g., changes in pricing, messaging, security guarantees) that would successfully convert high-utility skeptics or reduce safety friction.
"""

        messages = [
            {"role": "system", "content": "You are a professional behavioral economist and business diagnostic intelligence. Output a comprehensive report in clean English Markdown."},
            {"role": "user", "content": compiler_prompt}
        ]

        try:
            report = await self.client.chat(messages, model=model)
            return report
        except Exception as e:
            return f"Error compiling diagnostic report: {str(e)}"
