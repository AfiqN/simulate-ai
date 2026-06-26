import asyncio
import logging
from typing import Optional

from src.rag.models import SearchResult

logger = logging.getLogger(__name__)

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


class TavilySearchClient:
    """Async wrapper around the synchronous Tavily SDK with in-memory caching."""

    def __init__(self, api_key: str):
        self._client = TavilyClient(api_key=api_key)
        self._cache: dict[str, list[SearchResult]] = {}

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if query in self._cache:
            return self._cache[query]

        try:
            loop = asyncio.get_running_loop()
            raw_response = await loop.run_in_executor(
                None,
                lambda: self._client.search(query, max_results=max_results, search_depth="advanced"),
            )
            results = [
                SearchResult.from_tavily(r)
                for r in raw_response.get("results", [])
            ]
            self._cache[query] = results
            return results
        except Exception as e:
            logger.warning(f"Tavily search failed for query '{query}': {e}")
            return []

    @classmethod
    def create_if_available(cls) -> Optional["TavilySearchClient"]:
        if not TAVILY_AVAILABLE:
            return None
        try:
            from config import TAVILY_API_KEY, RAG_ENABLED
            if not RAG_ENABLED or not TAVILY_API_KEY:
                return None
            return cls(api_key=TAVILY_API_KEY)
        except Exception:
            return None
