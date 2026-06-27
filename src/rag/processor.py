import re

from src.rag.models import SearchResult, ProcessedFacts, Citation


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

# Patterns that indicate a sentence is navigation/UI rather than content
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
    """Word-level Jaccard similarity on lowercased word sets."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _clean_fact_text(text: str) -> str:
    """Remove residual HTML artifacts and navigation junk from fact text."""
    # Strip numeric/named HTML entities that slipped through
    text = re.sub(r'&#x?[0-9a-fA-F]+;', '', text)
    text = re.sub(r'&[a-zA-Z]+;', '', text)
    # Remove junk phrases
    text = _JUNK_PATTERNS.sub('', text)
    # Remove dangling punctuation and collapse whitespace
    text = re.sub(r'\s{2,}', ' ', text).strip()
    text = re.sub(r'^[\s\-|>»]+', '', text)
    return text


def _extract_best_sentence(content: str, max_chars: int) -> str:
    """Pick the most factual sentence(s) from content.

    Aggressively filters navigation text, author bylines, and generic filler.
    Prefers sentences with data points, legal/policy terms, and study findings.
    """
    sentences = _SENTENCE_SPLIT.split(content)
    # Also split on period + space as fallback
    if len(sentences) <= 1:
        sentences = re.split(r'\.\s', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 30]

    if not sentences:
        cleaned = _clean_fact_text(content[:max_chars])
        return cleaned if len(cleaned) >= 30 else ""

    def _score_sentence(sentence: str) -> float:
        score = 0.0
        # Hard reject: navigation/UI text
        if _NAV_INDICATORS.search(sentence):
            return -10.0
        # Hard reject: junk boilerplate
        if _JUNK_PATTERNS.search(sentence):
            return -10.0
        # Hard reject: starts with a truncated word fragment
        if sentence and sentence[0].islower():
            score -= 2.0
        # Hard reject: short sentence dominated by a URL
        if re.search(r'https?://\S{30,}', sentence):
            if len(sentence) < 120:
                return -10.0
        # Hard reject: table of contents header
        if re.search(r'(?i)^table of contents\b', sentence):
            return -10.0
        # Hard reject: non-English UI noise
        if re.search(r'(?i)(tentang|hak cipta|hubungi kami|kreator|beriklan|persyaratan|kebijakan)', sentence):
            return -10.0
        # Hard reject: academic citation metadata (emails, PMC IDs, received/accepted dates)
        if re.search(r'(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b|PMCID|PMC Copyright|Received \d{4}|Accepted \d{4})', sentence):
            return -10.0
        # Penalize disclaimer/legal boilerplate
        if re.search(r'(?i)(does not imply|endorsement|not responsible for|disclaimer|we make no|no guarantee)', sentence):
            score -= 4.0

        # === POSITIVE SIGNALS — prioritize PERSPECTIVES and SENTIMENTS ===
        has_positive = False

        # HIGH PRIORITY: Opinions, complaints, sentiments (strongest signal)
        if re.search(r'(?i)\b(complain|frustrated|skeptical|enthusiastic|reluctant|resistant|refuse|hesitant|worried|angry|disappointed|excited|hopeful|fearful|distrust|resent|oppose|support|embrace|reject|struggle|suffer)\b', sentence):
            score += 4.0
            has_positive = True
        # HIGH PRIORITY: Attributed perspectives ("merchants say", "locals believe")
        if re.search(r'(?i)\b(say|believe|feel|think|argue|claim|insist|worry|fear|complain|prefer|tend to|usually|rarely|often|seldom)\b.{0,20}\b(that|about|is|are|they|we|it)\b', sentence):
            score += 3.5
            has_positive = True
        # HIGH PRIORITY: Behavioral patterns and habits
        if re.search(r'(?i)\b(tend to|usually|rarely|often avoid|prefer to|accustomed to|habit of|reluctant to|unwilling to|eager to|known for|notorious for|famous for|stereotype)\b', sentence):
            score += 3.5
            has_positive = True
        # HIGH PRIORITY: Social dynamics and cultural attitudes
        if re.search(r'(?i)\b(community|neighbors?|locals?|residents?|villagers?|traders?|merchants?|vendors?|drivers?|workers?|employees?|students?|youth|elderly|generation)\b.{0,30}\b(feel|say|believe|complain|prefer|struggle|tend|resist|embrace|reject)\b', sentence):
            score += 4.0
            has_positive = True
        # MEDIUM: Quotes or direct speech patterns
        if re.search(r'["“”].{10,}["“”]', sentence):
            score += 3.0
            has_positive = True
        # MEDIUM: Causal/impact from human perspective
        if re.search(r'(?i)\b(led to|caused|resulted in|forced|pushed|drove|made them|left them|struggle with)\b', sentence):
            score += 2.0
            has_positive = True
        # MEDIUM: Comparative/causal claims (still useful for grounding)
        if re.search(r'(?i)\b(increased|decreased|reduced|grew|declined|rose|fell|compared to)\b', sentence):
            score += 1.5
            has_positive = True
        # LOWER: Research findings (useful but not primary)
        if re.search(r'(?i)\b(found that|shows? that|reveals? that|reports? that|survey|poll|interview)\b', sentence):
            score += 1.5
            has_positive = True
        # LOWER: Data points (still okay, not primary goal)
        if re.search(r'\b\d+\s*(%|percent|billion|million|trillion)\b', sentence, re.I):
            score += 1.0
            has_positive = True
        # LOWER: Named organizations (context, not primary)
        if re.search(r'\b(CDC|WHO|FDA|OJK|Bank Indonesia|Federal Reserve|KFF|Pew Research|according to)\b', sentence):
            score += 1.0
            has_positive = True
        # LOWER: Years with context
        if re.search(r'\b(in|since|from|by|until)\s+(19|20)\d{2}\b', sentence, re.I):
            score += 0.5
            has_positive = True

        # If no positive signal found, this is likely filler
        if not has_positive:
            score -= 2.0

        # DEMOTE: Pure regulatory/legal language without human perspective
        if re.search(r'(?i)\b(regulation|compliance|mandate|pursuant|statutory|provision|subsection|hereby)\b', sentence):
            if not re.search(r'(?i)\b(complain|frustrat|struggle|resist|worry|fear|oppose)\b', sentence):
                score -= 1.5

        # Penalize author bylines (unless they contain perspective)
        if re.search(r'(?i)(professor|university|department|author|written by|published by)', sentence):
            if not has_positive:
                score -= 2.0
        # Prefer sentences with proper nouns (not sentence-start)
        words = sentence.split()
        for word in words[1:5]:
            if word[0:1].isupper() and word.isalpha() and len(word) > 2:
                score += 0.3
                break
        # Penalize very short
        if len(sentence) < 40:
            score -= 1.5
        # Penalize title-like strings (few words)
        if sentence.count(' ') < 5:
            score -= 1.5
        # Penalize overly generic/truistic statements
        if re.search(r'(?i)(being |it is |this is )?(healthy|important|crucial|essential|critical|necessary|vital)\b.{0,40}(important|well|good|better|necessary|longevity|living)', sentence):
            score -= 3.0
        # Penalize table-of-contents style lists (many capitalized words, no verbs)
        cap_ratio = sum(1 for w in words if w[0:1].isupper()) / max(len(words), 1)
        if cap_ratio > 0.6 and len(words) > 5 and not re.search(r'\b(is|are|was|were|has|have|requires?|found|shows?|indicates?)\b', sentence, re.I):
            score -= 3.0
        # Boost longer substantive sentences
        if len(sentence) > 80:
            score += 0.5
        return score

    scored = sorted(sentences, key=_score_sentence, reverse=True)

    # Take best sentence(s) up to max_chars, skipping junk
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
    max_chars_per_fact: int = 200,
    min_score: float = 0.35,
) -> ProcessedFacts:
    """Filter, deduplicate, and compress search results into concise facts.

    Args:
        results: Raw scored search results from the web client.
        max_facts: Maximum number of facts to return.
        max_chars_per_fact: Maximum characters per extracted fact.
        min_score: Minimum relevance score threshold (default lowered to 0.35
            to avoid discarding relevant results from long natural-language queries).
    """
    # 1. Score filter — adaptive: if nothing passes, take top results anyway
    filtered = [r for r in results if r.score >= min_score]
    if not filtered and results:
        # Adaptive fallback: take top 2 results regardless of score
        filtered = sorted(results, key=lambda r: r.score, reverse=True)[:2]

    # 2. Dedup via Jaccard similarity
    kept: list[SearchResult] = []
    for result in filtered:
        is_duplicate = False
        for existing in kept:
            if _jaccard_similarity(result.content, existing.content) > 0.8:
                # Drop the lower-scored one
                if result.score <= existing.score:
                    is_duplicate = True
                    break
                else:
                    kept.remove(existing)
                    break
        if not is_duplicate:
            kept.append(result)

    # 3. Sort by score descending, take top max_facts
    kept.sort(key=lambda r: r.score, reverse=True)
    kept = kept[:max_facts]

    # 4. Compress each result's content into factual sentences
    facts: list[str] = []
    for result in kept:
        compressed = _extract_best_sentence(result.content, max_chars_per_fact)
        # Enforce minimum fact length to avoid junk like "11.2" or single words
        if len(compressed) >= 30:
            facts.append(compressed)

    # 5. Build citations (only for results that produced valid facts)
    citations = [Citation(url=r.url, title=r.title) for r in kept[:len(facts)]]

    return ProcessedFacts(facts=facts, citations=citations, raw_results=kept)
