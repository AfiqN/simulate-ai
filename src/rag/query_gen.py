"""RAG query generation: produce web search queries from scenario context."""

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _extract_keywords(text: str, max_words: int = 6) -> str:
    """Extract key phrases from text as a fallback search query."""
    # Remove very short/common words
    stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "need", "dare", "ought",
            "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above", "below",
            "between", "out", "off", "over", "under", "again", "further", "then",
            "once", "here", "there", "when", "where", "why", "how", "all", "each",
            "every", "both", "few", "more", "most", "other", "some", "such", "no",
            "nor", "not", "only", "own", "same", "so", "than", "too", "very",
            "just", "because", "but", "and", "or", "if", "while", "this", "that",
            "these", "those", "it", "its", "what", "which", "who", "whom",
            "new", "also", "about", "any", "many", "much", "well", "way"}
    words = re.findall(r"[A-Za-z]{3,}", text)
    keywords = [w for w in words if w.lower() not in stop]
    # Prefer capitalized words (proper nouns, acronyms)
    proper = [w for w in keywords if w[0].isupper() or w.isupper()]
    if len(proper) >= 3:
        keywords = proper
    # Deduplicate preserving order
    seen = set()
    unique = []
    for w in keywords:
        low = w.lower()
        if low not in seen:
            seen.add(low)
            unique.append(w)
    return " ".join(unique[:max_words])


def _fallback_stimulus_queries(stimulus: str) -> list[str]:
    """Generate search queries from stimulus text without LLM."""
    kw = _extract_keywords(stimulus, max_words=5)
    if not kw:
        return []
    return [
        f"{kw} recent developments 2024 2025",
        f"{kw} regulations market data",
    ]


def _fallback_domain_queries(schema) -> list[str]:
    """Generate search queries from schema without LLM."""
    name = getattr(schema, "scenario_name", "")
    dims = getattr(schema, "crisis_dimensions", [])
    queries = []
    if name:
        queries.append(f"{_extract_keywords(name, 4)} real world cases")
    if dims:
        queries.append(f"{dims[0].replace('_', ' ')} incidents 2024 2025")
    return queries


def _fallback_crisis_queries(r2_transcript: str, schema) -> list[str]:
    """Generate crisis search query from transcript without LLM."""
    kw = _extract_keywords(r2_transcript[:500], max_words=5)
    name = getattr(schema, "scenario_name", "")
    if kw:
        return [f"{kw} crisis precedent"]
    elif name:
        return [f"{_extract_keywords(name, 4)} crisis event"]
    return []


async def generate_stimulus_queries(client, stimulus: str, model: Optional[str] = None) -> list[str]:
    """Generate web search queries from a scenario stimulus using the LLM."""
    system = (
        "You are a research assistant. Given a scenario stimulus, produce exactly 2 "
        "targeted web search queries that would retrieve real-world facts, regulations, "
        "market data, or recent events relevant to evaluating this scenario.\n\n"
        'You MUST respond with ONLY valid JSON in this exact format: {"queries": ["query1", "query2"]}'
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Scenario stimulus:\n{stimulus}\n\nRespond with JSON only."},
    ]
    try:
        raw = await client.chat(messages, model=model)
        raw = raw.strip()
        # Try to extract JSON from response (model might wrap in markdown)
        json_match = re.search(r'\{[^{}]*"queries"[^{}]*\}', raw)
        if json_match:
            raw = json_match.group(0)
        data = json.loads(raw)
        queries = data.get("queries", [])
        result = [str(q) for q in queries] if isinstance(queries, list) else []
        if result:
            return result
    except Exception as e:
        logger.warning(f"generate_stimulus_queries LLM failed: {e}")

    # Fallback: keyword extraction
    fallback = _fallback_stimulus_queries(stimulus)
    if fallback:
        logger.info(f"Using keyword-fallback queries: {fallback}")
    return fallback


async def generate_domain_queries(client, schema, model: Optional[str] = None) -> list[str]:
    """Generate domain-specific search queries from the simulation schema."""
    system = (
        "You are a research assistant. Given a simulation scenario and its crisis dimensions, "
        "produce 1-2 targeted web search queries to find domain-specific facts, recent incidents, "
        'or regulatory data.\n\nYou MUST respond with ONLY valid JSON: {"queries": ["query1"]}'
    )
    user_content = (
        f"Scenario: {schema.scenario_name}\n"
        f"Crisis dimensions: {', '.join(schema.crisis_dimensions)}\n\n"
        "Respond with JSON only."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    try:
        raw = await client.chat(messages, model=model)
        raw = raw.strip()
        json_match = re.search(r'\{[^{}]*"queries"[^{}]*\}', raw)
        if json_match:
            raw = json_match.group(0)
        data = json.loads(raw)
        queries = data.get("queries", [])
        result = [str(q) for q in queries] if isinstance(queries, list) else []
        if result:
            return result
    except Exception as e:
        logger.warning(f"generate_domain_queries LLM failed: {e}")

    fallback = _fallback_domain_queries(schema)
    if fallback:
        logger.info(f"Using keyword-fallback domain queries: {fallback}")
    return fallback


async def generate_crisis_query(client, r2_transcript: str, schema, model: Optional[str] = None) -> list[str]:
    """Generate a search query targeting the dominant concern from the debate transcript."""
    system = (
        "You are a research assistant. Given a debate transcript from a simulation, "
        "identify the single most dominant concern or fear expressed by participants. "
        "Produce exactly 1 web search query to find recent real-world events or precedents "
        'matching that concern.\n\nYou MUST respond with ONLY valid JSON: {"queries": ["query1"]}'
    )
    user_content = (
        f"Scenario: {schema.scenario_name}\n\n"
        f"Debate transcript (excerpts):\n{r2_transcript[:2000]}\n\n"
        "Respond with JSON only."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    try:
        raw = await client.chat(messages, model=model)
        raw = raw.strip()
        json_match = re.search(r'\{[^{}]*"queries"[^{}]*\}', raw)
        if json_match:
            raw = json_match.group(0)
        data = json.loads(raw)
        queries = data.get("queries", [])
        result = [str(q) for q in queries] if isinstance(queries, list) else []
        if result:
            return result
    except Exception as e:
        logger.warning(f"generate_crisis_query LLM failed: {e}")

    fallback = _fallback_crisis_queries(r2_transcript, schema)
    if fallback:
        logger.info(f"Using keyword-fallback crisis queries: {fallback}")
    return fallback
