import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def generate_stimulus_queries(client, stimulus: str, model: Optional[str] = None) -> list[str]:
    """Generate web search queries from a scenario stimulus using the LLM."""
    system = (
        "You are a research assistant. Given a scenario stimulus, produce exactly 2 "
        "targeted web search queries that would retrieve real-world facts, regulations, "
        "market data, or recent events relevant to evaluating this scenario. "
        'Return JSON: {"queries": ["...", "..."]}'
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": stimulus},
    ]
    try:
        raw = await client.chat(messages, model=model, response_format={"type": "json_object"})
        data = json.loads(raw)
        queries = data.get("queries", [])
        return [str(q) for q in queries] if isinstance(queries, list) else []
    except Exception as e:
        logger.warning(f"generate_stimulus_queries failed: {e}")
        return []


async def generate_domain_queries(client, schema, model: Optional[str] = None) -> list[str]:
    """Generate domain-specific search queries from the simulation schema."""
    system = (
        "You are a research assistant. Given a simulation scenario and its crisis dimensions, "
        "produce 1-2 targeted web search queries to find domain-specific facts, recent incidents, "
        'or regulatory data. Return JSON: {"queries": ["..."]}'
    )
    user_content = (
        f"Scenario: {schema.scenario_name}\n"
        f"Crisis dimensions: {', '.join(schema.crisis_dimensions)}"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    try:
        raw = await client.chat(messages, model=model, response_format={"type": "json_object"})
        data = json.loads(raw)
        queries = data.get("queries", [])
        return [str(q) for q in queries] if isinstance(queries, list) else []
    except Exception as e:
        logger.warning(f"generate_domain_queries failed: {e}")
        return []


async def generate_crisis_query(client, r2_transcript: str, schema, model: Optional[str] = None) -> list[str]:
    """Generate a search query targeting the dominant concern from the debate transcript."""
    system = (
        "You are a research assistant. Given a debate transcript from a simulation, "
        "identify the single most dominant concern or fear expressed by participants. "
        "Produce exactly 1 web search query to find recent real-world events or precedents "
        'matching that concern. Return JSON: {"queries": ["..."]}'
    )
    user_content = (
        f"Scenario: {schema.scenario_name}\n\n"
        f"Debate transcript (excerpts):\n{r2_transcript[:2000]}"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    try:
        raw = await client.chat(messages, model=model, response_format={"type": "json_object"})
        data = json.loads(raw)
        queries = data.get("queries", [])
        return [str(q) for q in queries] if isinstance(queries, list) else []
    except Exception as e:
        logger.warning(f"generate_crisis_query failed: {e}")
        return []
