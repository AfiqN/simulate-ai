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

    async def compile_report(
        self, stimulus: str, round1_results: List[Dict[str, Any]], round2_results: List[Dict[str, Any]], model: Optional[str] = None
    ) -> str:
        """
        Synthesize simulation decisions, monologues, and actions across participants,
        calculating metrics and drafting actionable strategic pivot advice.
        """
        # Formulate compilation transcript
        transcript_parts = []
        for i in range(len(round1_results)):
            r1 = round1_results[i]
            r2 = round2_results[i] if i < len(round2_results) else {}
            
            p = f"""Agent: {r1['archetype']} (ID: {r1['id']})
- Initial Decision: {r1.get('action')} (Utility: {r1.get('utility', 0.0):.4f})
- Initial Inner Monologue: "{r1.get('monologue')}"
- Initial Public Statement: "{r1.get('statement')}"
"""
            if r2 and not r2.get("error"):
                p += f"""- Debate (Round 2) Decision: {r2.get('action')} (Utility: {r2.get('utility', 0.0):.4f})
- Debate (Round 2) Inner Monologue: "{r2.get('monologue')}"
- Debate (Round 2) Public Statement: "{r2.get('statement')}"
- Ending State: {r2.get('new_state')}
"""
            transcript_parts.append(p)

        full_transcript = "\n---\n".join(transcript_parts)

        compiler_prompt = f"""You are the SimulateAI Chief Behavioral Architect & Diagnostic Director.
Your task is to analyze the raw execution transcripts of a multi-agent social colony simulation and compile a high-level, extremely objective, and actionable executive report.

The user proposed the following concept/product/stimulus:
"{stimulus}"

Below are the raw behavioral traces and debate transcripts from the simulation:
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

5. STRATEGIC PIVOT RECOMMENDATIONS (ACTIONABLE ADVICE)
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
