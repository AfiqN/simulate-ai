"""Unit tests for src.rag.client (mocked Tavily)."""

import pytest
from unittest.mock import patch, MagicMock

from src.rag.models import SearchResult
from src.rag.client import TavilySearchClient, TAVILY_AVAILABLE


# --- SearchResult.from_tavily ---

def test_search_result_from_tavily():
    raw = {"title": "Test", "url": "http://example.com", "content": "Hello", "score": 0.85}
    result = SearchResult.from_tavily(raw)
    assert result.title == "Test"
    assert result.url == "http://example.com"
    assert result.content == "Hello"
    assert result.score == 0.85


def test_search_result_from_tavily_missing_fields():
    raw = {}
    result = SearchResult.from_tavily(raw)
    assert result.title == ""
    assert result.url == ""
    assert result.content == ""
    assert result.score == 0.0


# --- TavilySearchClient.search (mocked) ---

@pytest.fixture
def mock_tavily_client():
    """Create a TavilySearchClient with a mocked underlying client."""
    # tavily-python may not be installed — construct the client manually
    client = object.__new__(TavilySearchClient)
    client._cache = {}
    client._client = MagicMock()
    yield client, client._client


@pytest.mark.asyncio
async def test_search_returns_results(mock_tavily_client):
    client, mock_sdk = mock_tavily_client
    mock_sdk.search.return_value = {
        "results": [
            {"title": "R1", "url": "http://a.com", "content": "Content A", "score": 0.9},
            {"title": "R2", "url": "http://b.com", "content": "Content B", "score": 0.7},
        ]
    }
    results = await client.search("test query")
    assert len(results) == 2
    assert results[0].title == "R1"
    assert results[1].score == 0.7


@pytest.mark.asyncio
async def test_search_caches_results(mock_tavily_client):
    client, mock_sdk = mock_tavily_client
    mock_sdk.search.return_value = {"results": [{"title": "R1", "url": "http://a.com", "content": "C", "score": 0.9}]}

    # First call
    results1 = await client.search("cached query")
    # Second call — should not hit the SDK again
    results2 = await client.search("cached query")

    assert results1 == results2
    assert mock_sdk.search.call_count == 1


@pytest.mark.asyncio
async def test_search_returns_empty_on_exception(mock_tavily_client):
    client, mock_sdk = mock_tavily_client
    mock_sdk.search.side_effect = RuntimeError("network error")

    results = await client.search("failing query")
    assert results == []


@pytest.mark.asyncio
async def test_search_handles_empty_response(mock_tavily_client):
    client, mock_sdk = mock_tavily_client
    mock_sdk.search.return_value = {"results": []}

    results = await client.search("empty query")
    assert results == []


# --- create_if_available ---

def test_create_if_available_returns_none_when_tavily_unavailable():
    with patch("src.rag.client.TAVILY_AVAILABLE", False):
        result = TavilySearchClient.create_if_available()
        assert result is None


def test_create_if_available_returns_none_when_key_empty():
    with patch("src.rag.client.TAVILY_AVAILABLE", True):
        with patch.dict("sys.modules", {"config": MagicMock(TAVILY_API_KEY="", RAG_ENABLED=True)}):
            result = TavilySearchClient.create_if_available()
            assert result is None


def test_create_if_available_returns_none_when_rag_disabled():
    with patch("src.rag.client.TAVILY_AVAILABLE", True):
        with patch.dict("sys.modules", {"config": MagicMock(TAVILY_API_KEY="key123", RAG_ENABLED=False)}):
            result = TavilySearchClient.create_if_available()
            assert result is None
