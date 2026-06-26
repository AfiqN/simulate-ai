"""RAG search client using DuckDuckGo + lightweight scraping."""

import asyncio
import logging
import re
from typing import Optional

import httpx

from src.rag.models import SearchResult

logger = logging.getLogger(__name__)

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


def _clean_html(html: str) -> str:
    """Strip HTML to plain text, removing boilerplate sections."""
    # Remove script, style, nav, footer, etc.
    text = _BOILERPLATE_TAGS.sub("", html)
    # Remove remaining tags
    text = _TAG_RE.sub(" ", text)
    # Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # Collapse whitespace
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    return text


def _compute_relevance(query: str, title: str, content: str) -> float:
    """Compute a 0-1 relevance score based on keyword overlap with the query."""
    query_words = set(query.lower().split())
    if not query_words:
        return 0.5

    # Combine title (weighted higher) and content
    title_words = set(title.lower().split())
    content_words = set(content.lower().split()[:200])  # first 200 words

    # Title overlap (0-1, weighted 0.4)
    title_overlap = len(query_words & title_words) / len(query_words) if query_words else 0
    # Content overlap (0-1, weighted 0.6)
    content_overlap = len(query_words & content_words) / len(query_words) if query_words else 0

    score = (title_overlap * 0.4) + (content_overlap * 0.6)
    # Boost if content has substantial length (indicates real content, not stub)
    if len(content) > 200:
        score = min(1.0, score + 0.1)

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
                # Take a meaningful chunk (first 1500 chars after cleanup)
                if len(full_text) > len(snippet) + 50:
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
