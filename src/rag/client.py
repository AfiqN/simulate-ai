"""RAG search client using DuckDuckGo + lightweight scraping."""

import asyncio
import logging
import re
from typing import Optional

import httpx

from src.rag.models import SearchResult

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False


# --- HTML cleaning helpers ---

_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"\s{2,}")
_BOILERPLATE_TAGS = re.compile(
    r"<(script|style|nav|footer|header|aside|iframe|noscript)[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
_HTML_ENTITY_NAMED = re.compile(r"&([a-zA-Z]+);")
_HTML_ENTITY_NUM = re.compile(r"&#x?([0-9a-fA-F]+);")

# Common navigation/boilerplate phrases to strip from scraped content
_BOILERPLATE_PHRASES = [
    "Skip to content", "Skip to main content", "Skip to navigation",
    "Sign in", "Log in", "Sign up", "Register", "Subscribe",
    "Close menu", "Open menu", "Open navigation menu",
    "Close suggestions", "Search Search", "REGISTER FREE",
    "Cookie", "Accept all", "Reject all",
]

# Stopwords for relevance scoring — removed from query before computing overlap
_SCORE_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "between", "out", "off", "over", "under",
    "and", "or", "but", "if", "while", "this", "that", "these", "those",
    "it", "its", "what", "which", "who", "whom", "how", "when", "where",
    "why", "not", "no", "nor", "so", "than", "too", "very", "just",
    "about", "also", "new", "current", "recent",
})


def _decode_entity(match: re.Match) -> str:
    """Decode a named HTML entity to its character."""
    name = match.group(1)
    entities = {
        "amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'",
        "nbsp": " ", "ndash": "-", "mdash": "-", "laquo": '"',
        "raquo": '"', "ldquo": "“", "rdquo": "”",
        "lsquo": "‘", "rsquo": "’", "hellip": "...",
        "uarr": "", "darr": "", "larr": "", "rarr": "",
    }
    return entities.get(name.lower(), "")


def _decode_numeric_entity(match: re.Match) -> str:
    """Decode a numeric HTML entity."""
    val = match.group(1)
    try:
        if match.group(0).startswith("&#x"):
            return chr(int(val, 16))
        return chr(int(val))
    except (ValueError, OverflowError):
        return ""


def _clean_html(html: str) -> str:
    """Strip HTML to plain text, removing boilerplate sections."""
    # Remove script, style, nav, footer, etc.
    text = _BOILERPLATE_TAGS.sub("", html)
    # Remove remaining tags
    text = _TAG_RE.sub(" ", text)
    # Decode HTML entities
    text = _HTML_ENTITY_NAMED.sub(_decode_entity, text)
    text = _HTML_ENTITY_NUM.sub(_decode_numeric_entity, text)
    # Legacy entity decoding (catch any stragglers)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # Strip boilerplate phrases
    for phrase in _BOILERPLATE_PHRASES:
        text = text.replace(phrase, " ")
    # Collapse whitespace
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    return text


def _compute_relevance(query: str, title: str, content: str) -> float:
    """Compute a 0-1 relevance score based on keyword overlap with the query.

    Strips stopwords from the query so that long natural-language queries
    (common from LLM-generated search strings) aren't penalized for having
    many non-content words that won't appear verbatim in results.
    """
    # Strip stopwords from query to keep only content words
    query_words = {w for w in query.lower().split() if w not in _SCORE_STOPWORDS and len(w) > 2}
    if not query_words:
        # Fallback: use all words if stopword removal was too aggressive
        query_words = set(query.lower().split())
    if not query_words:
        return 0.5

    # Combine title (weighted higher) and content
    title_words = set(title.lower().split())
    content_words = set(content.lower().split()[:300])  # first 300 words

    # Title overlap (0-1, weighted 0.4)
    title_overlap = len(query_words & title_words) / len(query_words)
    # Content overlap (0-1, weighted 0.6)
    content_overlap = len(query_words & content_words) / len(query_words)

    score = (title_overlap * 0.4) + (content_overlap * 0.6)

    # Boost if content has substantial length (real content, not stub)
    if len(content) > 200:
        score = min(1.0, score + 0.1)
    # Boost if title has high overlap (strong signal even with low content match)
    if title_overlap >= 0.5:
        score = min(1.0, score + 0.05)

    return round(min(1.0, max(0.0, score)), 3)


class WebSearchClient:
    """Search client using DuckDuckGo + httpx scraping. No API key needed."""

    def __init__(self):
        self._cache: dict[str, list[SearchResult]] = {}
        self._http = httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SimulateAI/1.0)"},
        )

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search DuckDuckGo, scrape top results, return scored SearchResults."""
        if query in self._cache:
            return self._cache[query]

        try:
            # DuckDuckGo search (synchronous library — run in executor)
            loop = asyncio.get_running_loop()
            raw_results = await loop.run_in_executor(
                None,
                lambda: list(DDGS().text(query, max_results=max_results, region="wt-wt")),
            )
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed for '{query}': {e}")
            return []

        # Scrape and score each result
        results: list[SearchResult] = []
        scrape_tasks = [
            self._scrape_and_score(item, query)
            for item in raw_results[:max_results]
        ]
        scraped = await asyncio.gather(*scrape_tasks, return_exceptions=True)

        for item in scraped:
            if isinstance(item, SearchResult):
                results.append(item)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        self._cache[query] = results
        return results

    async def _scrape_and_score(self, item: dict, query: str) -> SearchResult:
        """Fetch a URL, clean HTML, and compute relevance score."""
        title = item.get("title", "")
        url = item.get("href", item.get("link", ""))
        snippet = item.get("body", item.get("snippet", ""))

        # Try to scrape the full page for richer content
        content = snippet
        try:
            resp = await self._http.get(url)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                full_text = _clean_html(resp.text)
                # Skip the first ~200 chars (usually nav/breadcrumb) and take a meaningful chunk
                if len(full_text) > 300:
                    # Find a good starting point after initial boilerplate
                    start = min(200, len(full_text) // 5)
                    content = full_text[start:start + 1500]
                elif len(full_text) > len(snippet) + 50:
                    content = full_text[:1500]
        except Exception:
            # Scraping failed — fall back to snippet from search results
            pass

        score = _compute_relevance(query, title, content)
        return SearchResult(title=title, url=url, content=content, score=score)

    async def close(self):
        await self._http.aclose()

    @classmethod
    def create_if_available(cls) -> Optional["WebSearchClient"]:
        """Factory: returns client if duckduckgo-search is installed and RAG is enabled."""
        if not DDGS_AVAILABLE:
            return None
        try:
            from config import RAG_ENABLED
            if not RAG_ENABLED:
                return None
            return cls()
        except Exception:
            return None


# Keep backward-compatible alias
TavilySearchClient = WebSearchClient
