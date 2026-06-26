import re

from src.rag.models import SearchResult, ProcessedFacts, Citation


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Word-level Jaccard similarity on lowercased word sets."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _extract_best_sentence(content: str, max_chars: int) -> str:
    """Pick the most factual sentence from content, preferring those with numbers or proper nouns."""
    sentences = re.split(r'\.\s|\.\n', content)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return content[:max_chars]

    def _score_sentence(sentence: str) -> float:
        score = 0.0
        # Prefer sentences with digits or 4-digit years
        if re.search(r'\d', sentence):
            score += 2.0
        if re.search(r'\b\d{4}\b', sentence):
            score += 1.0
        # Prefer sentences with capitalized proper nouns (not sentence-start)
        words = sentence.split()
        for word in words[1:]:
            if word[0:1].isupper() and word.isalpha():
                score += 0.5
                break
        # Penalize very short sentences
        if len(sentence) < 20:
            score -= 1.0
        return score

    scored = sorted(sentences, key=_score_sentence, reverse=True)

    # Take best sentence(s) up to max_chars
    result = ""
    for sentence in scored:
        candidate = sentence if not result else result + ". " + sentence
        if len(candidate) <= max_chars:
            result = candidate
        else:
            if not result:
                result = sentence[:max_chars]
            break

    return result if result else content[:max_chars]


def process_search_results(results: list[SearchResult], max_facts: int = 4, max_chars_per_fact: int = 150) -> ProcessedFacts:
    """Filter, deduplicate, and compress search results into concise facts."""
    # 1. Score filter
    filtered = [r for r in results if r.score >= 0.5]

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

    # 4. Compress each result's content
    facts: list[str] = []
    for result in kept:
        compressed = _extract_best_sentence(result.content, max_chars_per_fact)
        facts.append(compressed)

    # 5. Build citations
    citations = [Citation(url=r.url, title=r.title) for r in kept]

    return ProcessedFacts(facts=facts, citations=citations, raw_results=kept)
