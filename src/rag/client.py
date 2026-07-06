"""RAG search client using Brave Search API (primary) + SearXNG fallback."""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse

import httpx

from src.rag.models import SearchResult

logger = logging.getLogger(__name__)

# Brave Search API (primary — reliable, 1000 free queries/month)
BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"

# Local SearXNG instance (fallback — started via scripts/start-searxng.sh)
SEARXNG_URL = "http://127.0.0.1:8888"

# --- Source quality filtering ---

# Domains that almost never provide useful factual content for simulations
_BLOCKED_DOMAINS = frozenset({
    "instagram.com", "www.instagram.com",
    "tiktok.com", "www.tiktok.com",
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "twitter.com", "x.com",
    "pinterest.com", "www.pinterest.com",
    "youtube.com", "www.youtube.com",  # transcripts too noisy
    "reddit.com", "www.reddit.com",  # opinions but too unstructured
    "quora.com", "www.quora.com",
})

# Social platforms allowed in sentiment mode (opinions, rants, reviews)
_SOCIAL_DOMAINS = frozenset({
    "twitter.com", "x.com",
    "reddit.com", "www.reddit.com", "old.reddit.com",
    "kaskus.co.id", "www.kaskus.co.id",
    "medium.com",
    "quora.com", "www.quora.com",
})

# Domains that get a quality boost (authoritative sources)
_BOOSTED_DOMAINS = frozenset({
    "reuters.com", "bloomberg.com", "ft.com",
    "mckinsey.com", "bain.com", "bcg.com",
    "hbr.org", "economist.com",
    "worldbank.org", "imf.org", "adb.org",
    "bps.go.id", "ojk.go.id", "bi.go.id",  # Indonesian gov data
    "kompas.com", "tempo.co", "katadata.co.id",  # Indonesian news
    "techcrunch.com", "techasia.com", "e27.co",
    "thejakartapost.com", "jakartaglobe.id",
    "cnbcindonesia.com", "bisnis.com",
})

# File extensions that are not scrapeable
_SKIP_EXTENSIONS = frozenset({
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".tar", ".gz",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi",
})


def _is_blocked_url(url: str, allow_social: bool = False) -> bool:
    """Check if URL should be skipped.

    Args:
        allow_social: If True, social platforms (X, Reddit, Kaskus, Medium)
                      are allowed through for sentiment-seeking queries.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # If social mode, allow social domains through
        if allow_social and domain in _SOCIAL_DOMAINS:
            return False
        # Check blocked domains
        if domain in _BLOCKED_DOMAINS:
            return True
        # Check file extensions
        path = parsed.path.lower()
        for ext in _SKIP_EXTENSIONS:
            if path.endswith(ext):
                return True
    except Exception:
        pass
    return False


def _get_domain_boost(url: str) -> float:
    """Return a score boost for authoritative domains."""
    try:
        domain = urlparse(url).netloc.lower()
        # Direct match
        if domain in _BOOSTED_DOMAINS:
            return 0.15
        # Subdomain match (e.g. www.reuters.com)
        parts = domain.split(".")
        if len(parts) >= 2:
            base = ".".join(parts[-2:])
            if base in _BOOSTED_DOMAINS:
                return 0.15
        # .gov and .edu domains get a small boost
        if domain.endswith(".go.id") or domain.endswith(".gov") or domain.endswith(".edu"):
            return 0.10
        # .ac.id (Indonesian academic)
        if domain.endswith(".ac.id"):
            return 0.08
    except Exception:
        pass
    return 0.0


# --- HTML cleaning helpers ---

_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"\s{2,}")
_BOILERPLATE_TAGS = re.compile(
    r"<(script|style|nav|footer|header|aside|iframe|noscript)[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
_HTML_ENTITY_NAMED = re.compile(r"&([a-zA-Z]+);")
_HTML_ENTITY_NUM = re.compile(r"&#x?([0-9a-fA-F]+);")

_BOILERPLATE_PHRASES = [
    "Skip to content", "Skip to main content", "Skip to navigation",
    "Sign in", "Log in", "Sign up", "Register", "Subscribe",
    "Close menu", "Open menu", "Open navigation menu",
    "Close suggestions", "Search Search", "REGISTER FREE",
    "Cookie", "Accept all", "Reject all", "I agree",
    "Terms of Service", "Privacy Policy", "All Rights Reserved",
]

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
    name = match.group(1)
    entities = {
        "amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'",
        "nbsp": " ", "ndash": "-", "mdash": "-", "laquo": '"',
        "raquo": '"', "ldquo": "“", "rdquo": "”",
        "lsquo": "‘", "rsquo": "’", "hellip": "...",
    }
    return entities.get(name.lower(), "")


def _decode_numeric_entity(match: re.Match) -> str:
    val = match.group(1)
    try:
        if match.group(0).startswith("&#x"):
            return chr(int(val, 16))
        return chr(int(val))
    except (ValueError, OverflowError):
        return ""


def _clean_html(html: str) -> str:
    """Strip HTML to plain text, removing boilerplate sections."""
    text = _BOILERPLATE_TAGS.sub("", html)
    text = _TAG_RE.sub(" ", text)
    text = _HTML_ENTITY_NAMED.sub(_decode_entity, text)
    text = _HTML_ENTITY_NUM.sub(_decode_numeric_entity, text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    for phrase in _BOILERPLATE_PHRASES:
        text = text.replace(phrase, " ")
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    return text


def _compute_relevance(query: str, title: str, content: str, url: str) -> float:
    """Compute a 0-1 relevance score with domain-awareness."""
    query_words = {w for w in query.lower().split() if w not in _SCORE_STOPWORDS and len(w) > 2}
    if not query_words:
        query_words = set(query.lower().split())
    if not query_words:
        return 0.5

    title_words = set(title.lower().split())
    content_words = set(content.lower().split()[:300])

    title_overlap = len(query_words & title_words) / len(query_words)
    content_overlap = len(query_words & content_words) / len(query_words)

    score = (title_overlap * 0.4) + (content_overlap * 0.6)

    # Content length bonus (real articles have substance)
    if len(content) > 500:
        score = min(1.0, score + 0.12)
    elif len(content) > 200:
        score = min(1.0, score + 0.06)

    # Title match bonus
    if title_overlap >= 0.5:
        score = min(1.0, score + 0.05)

    # Domain authority bonus
    score = min(1.0, score + _get_domain_boost(url))

    return round(min(1.0, max(0.0, score)), 3)


class WebSearchClient:
    """Search client using Brave Search API (primary) + SearXNG fallback."""

    def __init__(self, searxng_url: str | None = None, brave_api_key: str | None = None):
        self._cache: dict[str, list[SearchResult]] = {}
        self._searxng_url = searxng_url or SEARXNG_URL

        # Load Brave API key from config
        if brave_api_key is None:
            try:
                from config import BRAVE_API_KEY
                brave_api_key = BRAVE_API_KEY
            except (ImportError, AttributeError):
                brave_api_key = None
        self._brave_api_key = brave_api_key

        self._http = httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            },
        )

    # ------------------------------------------------------------------
    # Brave Search API (primary)
    # ------------------------------------------------------------------

    async def _brave_search(self, query: str, max_results: int = 8, allow_social: bool = False) -> list[dict]:
        """Query Brave Search API. Returns list of {title, url, content} dicts."""
        if not self._brave_api_key:
            return []

        try:
            resp = await self._http.get(
                BRAVE_API_URL,
                params={
                    "q": query,
                    "count": min(max_results + 3, 20),  # Brave max is 20
                    "text_decorations": "false",
                    "search_lang": "en",
                },
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self._brave_api_key,
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                web_results = data.get("web", {}).get("results", [])
                # Convert to common format
                results = []
                for r in web_results:
                    url = r.get("url", "")
                    if _is_blocked_url(url, allow_social=allow_social):
                        continue
                    results.append({
                        "title": r.get("title", ""),
                        "url": url,
                        "content": r.get("description", ""),
                    })
                logger.info(
                    f"Brave API: {len(web_results)} raw → {len(results)} after filtering "
                    f"for: {query[:50]}"
                )
                return results[:max_results]
            elif resp.status_code == 429:
                logger.warning("Brave API rate limited (429)")
            elif resp.status_code == 401:
                logger.warning("Brave API key invalid (401)")
            else:
                logger.warning(f"Brave API returned status {resp.status_code}")
        except Exception as e:
            logger.warning(f"Brave API search failed: {e}")

        return []

    # ------------------------------------------------------------------
    # SearXNG (fallback)
    # ------------------------------------------------------------------

    async def _searxng_search(self, query: str, max_results: int = 8, allow_social: bool = False) -> list[dict]:
        """Query local SearXNG instance with retry on empty results."""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                resp = await self._http.get(
                    f"{self._searxng_url}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "categories": "general",
                        "language": "auto",
                        "safesearch": "0",
                    },
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    # Filter blocked URLs before returning
                    filtered = [r for r in results if not _is_blocked_url(r.get("url", ""), allow_social=allow_social)]
                    logger.info(
                        f"SearXNG: {len(results)} raw → {len(filtered)} after filtering "
                        f"for: {query[:50]}"
                    )
                    if filtered:
                        return filtered[:max_results]
                    # Empty results — retry with backoff if attempts remain
                    if attempt < max_retries:
                        logger.info(f"SearXNG returned 0 results, retrying ({attempt + 1}/{max_retries})...")
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    return []
                elif resp.status_code == 429:
                    # Rate limited — wait and retry
                    if attempt < max_retries:
                        logger.info(f"SearXNG rate limited (429), retrying...")
                        await asyncio.sleep(2.0 * (attempt + 1))
                        continue
                    logger.warning(f"SearXNG rate limited after {max_retries} retries")
                else:
                    logger.warning(f"SearXNG returned status {resp.status_code}")
            except Exception as e:
                logger.warning(f"SearXNG search failed: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(1.0)
                    continue

        return []

    # Site filter appended to sentiment queries for social targeting
    SOCIAL_SITE_FILTER = "site:x.com OR site:reddit.com OR site:kaskus.co.id OR site:medium.com"

    async def search(self, query: str, max_results: int = 5, allow_social: bool = False) -> list[SearchResult]:
        """Search via Brave API (primary) or SearXNG (fallback), scrape top results.

        Args:
            allow_social: If True, allow social platform results (X, Reddit,
                          Kaskus, Medium) AND run a secondary social-targeted
                          search with site: filters to maximize social hits.
        """
        cache_key = f"{query}|social={allow_social}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try Brave API first (reliable, proper rate limits)
        raw_results = await self._brave_search(query, max_results=max_results + 3, allow_social=allow_social)
        source = "brave"

        # Fallback to SearXNG if Brave returns nothing
        if not raw_results:
            raw_results = await self._searxng_search(query, max_results=max_results + 3, allow_social=allow_social)
            source = "searxng"

        # When social mode is on, also run a social-targeted query
        if allow_social:
            social_query = f"{query} {self.SOCIAL_SITE_FILTER}"
            if source == "brave" and self._brave_api_key:
                social_results = await self._brave_search(social_query, max_results=max_results, allow_social=True)
            else:
                social_results = await self._searxng_search(social_query, max_results=max_results, allow_social=True)
            # Merge, avoiding duplicate URLs
            seen_urls = {r.get("url", "") for r in raw_results}
            for r in social_results:
                if r.get("url", "") not in seen_urls:
                    raw_results.append(r)
                    seen_urls.add(r.get("url", ""))

        if not raw_results:
            return []

        # Scrape and score each result concurrently
        scrape_tasks = [
            self._scrape_and_score(item, query)
            for item in raw_results
        ]
        scraped = await asyncio.gather(*scrape_tasks, return_exceptions=True)

        results: list[SearchResult] = []
        for item in scraped:
            if isinstance(item, SearchResult) and item.content and len(item.content) > 50:
                results.append(item)

        # Sort by score descending, take top max_results
        results.sort(key=lambda r: r.score, reverse=True)
        results = results[:max_results]
        self._cache[cache_key] = results
        return results

    async def _scrape_and_score(self, item: dict, query: str) -> SearchResult:
        """Fetch a URL, clean HTML, and compute relevance score."""
        title = item.get("title", "")
        url = item.get("url", item.get("href", ""))
        snippet = item.get("content", item.get("body", ""))

        # Try to scrape the full page for richer content
        content = snippet
        try:
            resp = await self._http.get(url, timeout=8.0)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                full_text = _clean_html(resp.text)
                if len(full_text) > 300:
                    # Skip early boilerplate, take meaningful chunk
                    start = min(200, len(full_text) // 5)
                    content = full_text[start:start + 2000]
                elif len(full_text) > len(snippet) + 50:
                    content = full_text[:2000]
        except Exception:
            pass

        score = _compute_relevance(query, title, content, url)
        return SearchResult(title=title, url=url, content=content, score=score)

    async def close(self):
        await self._http.aclose()

    @classmethod
    def create_if_available(cls) -> Optional["WebSearchClient"]:
        """Factory: returns client if RAG is enabled in config."""
        try:
            from config import RAG_ENABLED
            if not RAG_ENABLED:
                return None
            return cls()
        except Exception:
            return None


# Keep backward-compatible alias
TavilySearchClient = WebSearchClient
