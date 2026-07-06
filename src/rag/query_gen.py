"""RAG query generation: produce web search queries for persona grounding."""

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _extract_keywords(text: str, max_words: int = 6) -> str:
    """Extract key phrases from text as a fallback search query."""
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


def _fallback_perspective_queries(schema) -> dict[str, str]:
    """Generate perspective queries from schema clusters without LLM."""
    name = getattr(schema, "scenario_name", "")
    clusters = getattr(schema, "linguistic_clusters", [])
    result = {}
    for cluster in clusters:
        desc = getattr(cluster, "description", "")
        cid = getattr(cluster, "cluster_id", "")
        if desc:
            kw = _extract_keywords(desc, 3)
            topic_kw = _extract_keywords(name, 3)
            result[cid] = f"{kw} perspective opinion {topic_kw}"
    return result


def _fallback_crisis_queries(r2_transcript: str, schema) -> list[str]:
    """Generate crisis search query from transcript without LLM."""
    kw = _extract_keywords(r2_transcript[:500], max_words=5)
    name = getattr(schema, "scenario_name", "")
    if kw:
        return [f"{kw} crisis precedent"]
    elif name:
        return [f"{_extract_keywords(name, 4)} crisis event"]
    return []


async def generate_perspective_queries(client, schema, model: Optional[str] = None) -> dict[str, list[str]]:
    """Generate 2 perspective-seeking web search queries per linguistic cluster.

    Returns a dict mapping cluster_id → [sentiment_query, data_query].
    - Query 1: targets human sentiments, frustrations, opinions, behavior
    - Query 2: targets market data, regulations, competitive landscape

    This dual-query approach ensures agents get BOTH the emotional grounding
    (for realistic persona) AND the factual context (for informed reasoning).
    """
    clusters = getattr(schema, "linguistic_clusters", [])
    if not clusters:
        return {}

    cluster_list = "\n".join(
        f"- {c.cluster_id}: {c.description}" for c in clusters
    )

    system = (
        "You are a research assistant helping build realistic simulation personas. "
        "Given stakeholder roles in a scenario, produce TWO web search queries per role:\n\n"
        "Query 1 (SENTIMENT): Find how people in this role ACTUALLY FEEL.\n"
        "- Complaints, frustrations, enthusiasm, fears\n"
        "- Cultural attitudes, local stereotypes, social dynamics\n"
        "- Real opinions from forums, news, interviews\n"
        "- Behavioral patterns and habits\n\n"
        "Query 2 (CONTEXT): Find factual grounding for this role's decisions.\n"
        "- Market data, industry stats, competitive landscape\n"
        "- Regulations, compliance requirements\n"
        "- Recent events, policy changes, tech developments\n"
        "- Domain-specific knowledge this stakeholder would have\n\n"
        "Respond with ONLY valid JSON in this exact format:\n"
        '{"queries": {"cluster_id_1": ["sentiment query", "context query"], '
        '"cluster_id_2": ["sentiment query", "context query"]}}'
    )
    user_content = (
        f"Scenario: {schema.scenario_name}\n"
        f"Description: {schema.scenario_description}\n\n"
        f"Stakeholder roles:\n{cluster_list}\n\n"
        "Generate two search queries per role (sentiment + context). Respond with JSON only."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    try:
        raw = await client.chat(messages, model=model)
        raw = raw.strip()
        # Extract JSON — model might wrap in markdown
        json_match = re.search(r'\{[^{}]*"queries"\s*:\s*\{.*\}\s*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
        data = json.loads(raw)
        queries = data.get("queries", {})
        if isinstance(queries, dict) and queries:
            valid_ids = {c.cluster_id for c in clusters}
            result = {}
            for k, v in queries.items():
                if k not in valid_ids:
                    continue
                if isinstance(v, list):
                    result[k] = [str(q) for q in v[:2]]
                elif isinstance(v, str):
                    # Backward compat: single string → wrap in list
                    result[k] = [v]
            if result:
                return result
    except Exception as e:
        logger.warning(f"generate_perspective_queries LLM failed: {e}")

    # Fallback: keyword extraction per cluster (single query)
    fallback = _fallback_perspective_queries(schema)
    if fallback:
        logger.info(f"Using keyword-fallback perspective queries: {list(fallback.keys())}")
    return {k: [v] for k, v in fallback.items()}


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
