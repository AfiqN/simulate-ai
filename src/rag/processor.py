"""RAG processor: extract structured facts from raw search results.

Two-tier extraction:
1. Rule-based fast extraction (fallback if no LLM available)
2. LLM-powered fact extraction (preferred — produces clean, cited facts)
"""

import logging
import re
import json
from typing import Optional

from src.rag.models import SearchResult, ProcessedFacts, Citation

logger = logging.getLogger(__name__)

# Junk patterns commonly left over from scraped content
_JUNK_PATTERNS = re.compile(
    r"(?i)(skip to \w+|sign in|log in|cookie|accept all|subscribe|"
    r"close menu|open menu|read more|learn more|click here|"
    r"privacy policy|terms of service|all rights reserved|"
    r"\d+ min read|share this|follow us|join now|"
    r"your cart|add to cart|my cart|0 coupon|browse packages|"
    r"view licence|get awesome|stay up-to-date|"
    r"agree & join|by clicking continue|user agreement|"
    r"see full bio|editorial policy|"
    r"summarized by ai|based on linkedin|"
    r"request a demo|free demo|free trial|contact (us|your|our)|"
    r"let'?s take|thank you for|get started|"
    r"practice areas?\s*[»>|/]|home\s*[»>|/]|"
    r"--\s*>|breadcrumb|"
    r"\.gov websites? use https|locked padlock|"
    r"share sensitive information|official.? secure websites?|"
    r"job role|individual contributor|"
    r"i understand how .+ will use my data|"
    r"editorial curation|candidate data points|"
    r"keeps? innovating|book a demo|"
    r"blog post case studies|media events|"
    r"trusted by thousands|leading brands|"
    r"drop in your details|we'?ll get back|"
    r"just drop in|we will get back|"
    r"online chat and therapy|empower your practice|"
    r"tailored care|mental health tools)"
)

_NAV_INDICATORS = re.compile(
    r"(?i)(home\s*[>»|/]|menu|sidebar|footer|"
    r"^\s*(home|about|contact|blog|news|login|register)\s*$|"
    r"your (offers|cart|account)|sign (in|up)|"
    r"get (started|help|access)|free (trial|account)|"
    r"feel free to contact|reach out to|"
    r"published:?\s*\d|chapter content|free online access|"
    r"cxos?/vp/director|hr professional|"
    r"secure \.gov|you'?ve safely connected)"
)

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _clean_fact_text(text: str) -> str:
    text = re.sub(r'&#x?[0-9a-fA-F]+;', '', text)
    text = re.sub(r'&[a-zA-Z]+;', '', text)
    text = _JUNK_PATTERNS.sub('', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    text = re.sub(r'^[\s\-|>»]+', '', text)
    return text


def _score_sentence(sentence: str) -> float:
    """Score a sentence for factual/perspective value."""
    score = 0.0

    # Hard reject
    if _NAV_INDICATORS.search(sentence):
        return -10.0
    if _JUNK_PATTERNS.search(sentence):
        return -10.0
    if sentence and sentence[0].islower():
        score -= 2.0
    if re.search(r'https?://\S{30,}', sentence) and len(sentence) < 120:
        return -10.0
    if re.search(r'(?i)^table of contents\b', sentence):
        return -10.0
    if re.search(r'(?i)(tentang|hak cipta|hubungi kami|kreator|beriklan|persyaratan|kebijakan)', sentence):
        return -10.0
    if re.search(r'(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b|PMCID|PMC Copyright)', sentence):
        return -10.0

    has_positive = False

    # Opinions, sentiments (strongest signal for simulation)
    if re.search(r'(?i)\b(complain|frustrated|skeptical|enthusiastic|reluctant|resistant|refuse|hesitant|worried|disappointed|excited|hopeful|distrust|oppose|support|embrace|reject|struggle)\b', sentence):
        score += 4.0
        has_positive = True
    # Attributed perspectives
    if re.search(r'(?i)\b(say|believe|feel|think|argue|claim|insist|worry|fear|complain|prefer)\b.{0,20}\b(that|about|is|are|they|we|it)\b', sentence):
        score += 3.5
        has_positive = True
    # Behavioral patterns
    if re.search(r'(?i)\b(tend to|usually|rarely|often avoid|prefer to|accustomed to|reluctant to|unwilling to|eager to|known for)\b', sentence):
        score += 3.5
        has_positive = True
    # Data points
    if re.search(r'\b\d+\s*(%|percent|billion|million|trillion)\b', sentence, re.I):
        score += 2.5
        has_positive = True
    # Comparative/causal claims
    if re.search(r'(?i)\b(increased|decreased|reduced|grew|declined|rose|fell|compared to|led to|caused|resulted in)\b', sentence):
        score += 2.0
        has_positive = True
    # Research findings
    if re.search(r'(?i)\b(found that|shows? that|reveals? that|according to|survey|study)\b', sentence):
        score += 1.5
        has_positive = True
    # Named organizations
    if re.search(r'\b(CDC|WHO|OJK|Bank Indonesia|McKinsey|according to)\b', sentence):
        score += 1.0
        has_positive = True
    # Years
    if re.search(r'\b(in|since|from|by|until)\s+(19|20)\d{2}\b', sentence, re.I):
        score += 0.5
        has_positive = True

    if not has_positive:
        score -= 2.0

    # Length preferences
    if len(sentence) < 40:
        score -= 1.5
    if len(sentence) > 80:
        score += 0.5

    return score


def _extract_best_sentences(content: str, max_chars: int = 300) -> str:
    """Extract most factual sentences from content using rule-based scoring."""
    sentences = _SENTENCE_SPLIT.split(content)
    if len(sentences) <= 1:
        sentences = re.split(r'\.\s', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 30]

    if not sentences:
        cleaned = _clean_fact_text(content[:max_chars])
        return cleaned if len(cleaned) >= 30 else ""

    scored = sorted(sentences, key=_score_sentence, reverse=True)

    result = ""
    for sentence in scored:
        if _score_sentence(sentence) <= -5.0:
            continue
        cleaned = _clean_fact_text(sentence)
        if len(cleaned) < 30:
            continue
        candidate = cleaned if not result else result + ". " + cleaned
        if len(candidate) <= max_chars:
            result = candidate
        else:
            if not result:
                result = cleaned[:max_chars]
            break

    return result


def process_search_results(
    results: list[SearchResult],
    max_facts: int = 4,
    max_chars_per_fact: int = 250,
    min_score: float = 0.30,
) -> ProcessedFacts:
    """Rule-based extraction: filter, deduplicate, extract key sentences.

    Use this as fallback when LLM extraction is not available.
    """
    # 1. Score filter (adaptive)
    filtered = [r for r in results if r.score >= min_score]
    if not filtered and results:
        filtered = sorted(results, key=lambda r: r.score, reverse=True)[:2]

    # 2. Dedup via Jaccard
    kept: list[SearchResult] = []
    for result in filtered:
        is_dup = False
        for existing in kept:
            if _jaccard_similarity(result.content, existing.content) > 0.7:
                if result.score <= existing.score:
                    is_dup = True
                    break
                else:
                    kept.remove(existing)
                    break
        if not is_dup:
            kept.append(result)

    # 3. Top N
    kept.sort(key=lambda r: r.score, reverse=True)
    kept = kept[:max_facts]

    # 4. Extract sentences
    facts: list[str] = []
    for result in kept:
        compressed = _extract_best_sentences(result.content, max_chars_per_fact)
        if len(compressed) >= 30:
            facts.append(compressed)

    # 5. Citations
    citations = [Citation(url=r.url, title=r.title) for r in kept[:len(facts)]]
    return ProcessedFacts(facts=facts, citations=citations, raw_results=kept)


async def extract_facts_with_llm(
    llm_client,
    results: list[SearchResult],
    query: str,
    context: str = "",
    max_facts: int = 5,
    model: Optional[str] = None,
) -> ProcessedFacts:
    """LLM-powered fact extraction — the preferred path.

    Takes raw search results and uses an LLM to:
    1. Filter out irrelevant/noisy content
    2. Extract structured, cited facts
    3. Identify perspectives, data points, and stakeholder sentiments
    4. Return clean, simulation-ready insights

    Falls back to rule-based extraction on LLM failure.
    """
    if not results:
        return ProcessedFacts(facts=[], citations=[], raw_results=[])

    # Pre-filter: only pass results with meaningful content
    valid_results = [r for r in results if r.content and len(r.content) > 50]
    if not valid_results:
        return process_search_results(results, max_facts=max_facts)

    # Resolve model — use client's default or config fallback
    if not model:
        model = getattr(llm_client, "model", None)
    if not model:
        try:
            from config import DEFAULT_MODEL
            model = DEFAULT_MODEL
        except ImportError:
            pass

    # Build source blocks for LLM
    source_blocks = []
    for i, r in enumerate(valid_results[:6], 1):
        # Truncate content to avoid token explosion
        content_preview = r.content[:800]
        source_blocks.append(
            f"[Source {i}] Title: {r.title}\n"
            f"URL: {r.url}\n"
            f"Content: {content_preview}"
        )
    sources_text = "\n\n".join(source_blocks)

    system_prompt = (
        "You are a research analyst extracting actionable intelligence for a stakeholder simulation.\n\n"
        "Your job: extract SPECIFIC, CITED facts from the sources below. Prioritize:\n"
        "1. STAKEHOLDER SENTIMENTS — how specific groups feel (frustrated, enthusiastic, skeptical, worried). "
        "Look for quotes, attributed opinions, complaints, fears, enthusiasm from named groups.\n"
        "2. BEHAVIORAL PATTERNS — what people actually do, habits, preferences, workarounds, resistance, adoption patterns.\n"
        "3. QUANTITATIVE DATA — market sizes, growth rates, adoption percentages, user counts\n"
        "4. MARKET DYNAMICS — competitive landscape, pricing, regulatory constraints\n"
        "5. REAL EVENTS — launches, failures, partnerships, policy changes with dates\n\n"
        "Rules:\n"
        "- Each fact must cite its source number [1], [2], etc.\n"
        "- Each fact must be ONE specific claim, not a vague summary\n"
        "- SENTIMENT and BEHAVIOR facts are EQUALLY valuable as data — do NOT skip them in favor of numbers\n"
        "- When a source contains someone's opinion, complaint, or attitude, extract it as sentiment/behavior\n"
        "- Attributed perspectives ('X says...', 'Y believe...', 'Z complain...') are HIGH VALUE\n"
        "- Prefer recent data (2023-2026) over old data\n"
        "- Skip generic/obvious statements everyone already knows\n"
        "- Skip promotional content, ads, CTAs\n"
        f"- Return exactly {max_facts} facts maximum\n"
        f"- AIM for a MIX of types — ideally at least 1 sentiment/behavior AND 1 data/market/event\n\n"
        "Respond with ONLY valid JSON:\n"
        '{"facts": [{"text": "...", "source_idx": 1, "type": "data|sentiment|behavior|market|event"}]}'
    )

    user_content = f"Search query: {query}\n"
    if context:
        user_content += f"Simulation context: {context}\n"
    user_content += f"\nSources:\n\n{sources_text}\n\nExtract the most valuable facts. JSON only."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        raw = await llm_client.chat(messages, model=model)
        raw = raw.strip()

        # Extract JSON
        json_match = re.search(r'\{[^{}]*"facts"\s*:\s*\[.*?\]\s*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)

        data = json.loads(raw)
        extracted = data.get("facts", [])

        if not extracted:
            logger.warning("LLM extraction returned empty facts, falling back to rule-based")
            return process_search_results(results, max_facts=max_facts)

        # Build ProcessedFacts from LLM output
        facts: list[str] = []
        citations: list[Citation] = []
        seen_sources: set[int] = set()

        for item in extracted[:max_facts]:
            text = item.get("text", "").strip()
            src_idx = item.get("source_idx", 0)
            fact_type = item.get("type", "")

            if not text or len(text) < 20:
                continue

            # Add type prefix for context
            prefix = ""
            if fact_type == "data":
                prefix = "[DATA] "
            elif fact_type == "sentiment":
                prefix = "[SENTIMENT] "
            elif fact_type == "behavior":
                prefix = "[BEHAVIOR] "
            elif fact_type == "market":
                prefix = "[MARKET] "
            elif fact_type == "event":
                prefix = "[EVENT] "

            facts.append(f"{prefix}{text}")

            # Track citation
            if 1 <= src_idx <= len(valid_results):
                r = valid_results[src_idx - 1]
                if src_idx not in seen_sources:
                    citations.append(Citation(url=r.url, title=r.title))
                    seen_sources.add(src_idx)

        if not facts:
            return process_search_results(results, max_facts=max_facts)

        logger.info(f"LLM extracted {len(facts)} facts from {len(valid_results)} sources")
        return ProcessedFacts(facts=facts, citations=citations, raw_results=valid_results)

    except Exception as e:
        logger.warning(f"LLM fact extraction failed: {e}, falling back to rule-based")
        return process_search_results(results, max_facts=max_facts)
