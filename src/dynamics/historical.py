"""Historical Context Engine — inject real-world precedents into simulations.

This module finds and structures historical analogues for a given scenario,
providing grounding context that agents can reference in their reasoning.
Precedents are sourced via RAG (web search) or can be user-supplied.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class HistoricalPrecedent:
    """A single historical analogue for the simulation scenario."""
    title: str
    year: Optional[int] = None
    summary: str = ""
    outcome: str = ""  # What happened / how it resolved
    relevance: str = ""  # Why this is relevant to the current scenario
    source: str = ""  # Attribution / URL
    domain: str = ""  # e.g. "technology", "finance", "geopolitics"

    def to_context_block(self) -> str:
        """Format as an injection block for agent prompts."""
        parts = [f"**{self.title}**"]
        if self.year:
            parts[0] += f" ({self.year})"
        if self.summary:
            parts.append(f"  Context: {self.summary}")
        if self.outcome:
            parts.append(f"  Outcome: {self.outcome}")
        if self.relevance:
            parts.append(f"  Relevance: {self.relevance}")
        return "\n".join(parts)


@dataclass
class HistoricalContext:
    """Collection of historical precedents for a simulation."""
    scenario_name: str
    precedents: list[HistoricalPrecedent] = field(default_factory=list)
    search_queries_used: list[str] = field(default_factory=list)

    def to_agent_prompt_section(self, max_precedents: int = 3) -> str:
        """Render as a section to inject into agent system prompts."""
        if not self.precedents:
            return ""
        selected = self.precedents[:max_precedents]
        blocks = "\n\n".join(p.to_context_block() for p in selected)
        return (
            f"## Historical Precedents\n"
            f"Consider these real-world analogues when forming your position:\n\n"
            f"{blocks}\n\n"
            f"Use these precedents to inform your reasoning, but adapt your analysis "
            f"to the specific circumstances of the current scenario."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "precedents": [
                {
                    "title": p.title,
                    "year": p.year,
                    "summary": p.summary,
                    "outcome": p.outcome,
                    "relevance": p.relevance,
                    "source": p.source,
                    "domain": p.domain,
                }
                for p in self.precedents
            ],
            "search_queries_used": self.search_queries_used,
        }


_PRECEDENT_QUERY_PROMPT = """You are a research assistant specializing in historical analysis.
Given a simulation scenario, identify the most relevant historical precedents — real events,
decisions, or crises that mirror the dynamics at play.

Produce 2-3 specific web search queries that would find detailed accounts of these precedents.
Focus on: same industry/domain, similar decision pressures, comparable stakes.

Scenario: {scenario_name}
Stimulus: {stimulus}
Key dimensions: {dimensions}

Respond with ONLY valid JSON: {{"queries": ["query1", "query2", "query3"]}}"""


_PRECEDENT_EXTRACT_PROMPT = """You are a historical analyst. Given search results about real-world precedents,
extract structured precedent entries relevant to this simulation scenario.

Scenario: {scenario_name}
Stimulus: {stimulus}

For each relevant precedent found, provide:
- title: Short name of the event/decision
- year: When it happened (integer or null)
- summary: 1-2 sentence description of what happened
- outcome: How it resolved and consequences
- relevance: Why it matters for the current scenario
- domain: Category (technology, finance, healthcare, geopolitics, etc.)

Search results:
{search_results}

Respond with ONLY valid JSON: {{"precedents": [{{...}}]}}
Limit to the 3-5 most relevant precedents."""


async def generate_precedent_queries(
    client,
    scenario_name: str,
    stimulus: str,
    dimensions: list[str],
) -> list[str]:
    """Generate web search queries to find historical precedents."""
    prompt = _PRECEDENT_QUERY_PROMPT.format(
        scenario_name=scenario_name,
        stimulus=stimulus[:500],
        dimensions=", ".join(dimensions[:6]),
    )
    try:
        response = await client.chat([
            {"role": "system", "content": "You produce JSON search queries."},
            {"role": "user", "content": prompt},
        ])
        data = json.loads(response)
        queries = data.get("queries", [])
        return queries[:3]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to generate precedent queries: {e}")
        # Fallback: basic keyword query
        return [f"{scenario_name} historical precedent case study"]


async def extract_precedents_from_results(
    client,
    search_results: list[str],
    scenario_name: str,
    stimulus: str,
) -> list[HistoricalPrecedent]:
    """Extract structured precedents from RAG search results."""
    if not search_results:
        return []

    results_text = "\n---\n".join(search_results[:10])
    prompt = _PRECEDENT_EXTRACT_PROMPT.format(
        scenario_name=scenario_name,
        stimulus=stimulus[:400],
        search_results=results_text[:3000],
    )

    try:
        response = await client.chat([
            {"role": "system", "content": "You extract structured historical data as JSON."},
            {"role": "user", "content": prompt},
        ])
        data = json.loads(response)
        precedents = []
        for p in data.get("precedents", []):
            precedents.append(HistoricalPrecedent(
                title=p.get("title", "Unknown"),
                year=p.get("year"),
                summary=p.get("summary", ""),
                outcome=p.get("outcome", ""),
                relevance=p.get("relevance", ""),
                domain=p.get("domain", ""),
            ))
        return precedents[:5]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to extract precedents: {e}")
        return []


async def build_historical_context(
    client,
    scenario_name: str,
    stimulus: str,
    dimensions: list[str],
    rag_client=None,
    user_precedents: Optional[list[dict]] = None,
) -> HistoricalContext:
    """Build full historical context for a simulation.

    Combines RAG-sourced precedents with optional user-supplied ones.

    Args:
        client: LLM client for query generation and extraction.
        scenario_name: Name of the scenario.
        stimulus: The scenario stimulus text.
        dimensions: Evaluation dimensions from the schema.
        rag_client: Optional web search client for fetching precedents.
        user_precedents: Optional list of user-provided precedent dicts.

    Returns:
        HistoricalContext with all discovered precedents.
    """
    context = HistoricalContext(scenario_name=scenario_name)

    # 1. Add user-supplied precedents first (highest priority)
    if user_precedents:
        for up in user_precedents:
            context.precedents.append(HistoricalPrecedent(
                title=up.get("title", "User-supplied precedent"),
                year=up.get("year"),
                summary=up.get("summary", ""),
                outcome=up.get("outcome", ""),
                relevance=up.get("relevance", ""),
                source=up.get("source", "user-supplied"),
                domain=up.get("domain", ""),
            ))

    # 2. RAG-sourced precedents
    if rag_client:
        queries = await generate_precedent_queries(client, scenario_name, stimulus, dimensions)
        context.search_queries_used = queries

        all_facts: list[str] = []
        for query in queries:
            try:
                results = await rag_client.search(query)
                if results:
                    from src.rag.processor import extract_facts_with_llm
                    processed = await extract_facts_with_llm(
                        client, results, query,
                        context=f"Finding historical precedents for: {scenario_name}",
                        max_facts=4,
                    )
                    if processed.facts:
                        all_facts.extend(processed.facts)
            except Exception as e:
                logger.warning(f"RAG search failed for query '{query}': {e}")

        if all_facts:
            rag_precedents = await extract_precedents_from_results(
                client, all_facts, scenario_name, stimulus
            )
            context.precedents.extend(rag_precedents)

    return context
