"""Unit tests for src.rag.client (DuckDuckGo + scraping)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import httpx as httpx_lib

from src.rag.models import SearchResult
from src.rag.client import WebSearchClient, _clean_html, _compute_relevance, DDGS_AVAILABLE


# --- _clean_html ---

def test_clean_html_strips_tags():
    html = "<p>Hello <b>world</b></p>"
    assert "Hello" in _clean_html(html)
    assert "world" in _clean_html(html)
    assert "<" not in _clean_html(html)


def test_clean_html_removes_script_and_style():
    html = "<script>var x=1;</script><p>Content</p><style>.a{}</style>"
    result = _clean_html(html)
    assert "var x" not in result
    assert ".a{}" not in result
    assert "Content" in result


def test_clean_html_removes_nav_footer():
    html = "<nav>Menu items</nav><main>Main content</main><footer>Footer stuff</footer>"
    result = _clean_html(html)
    assert "Menu items" not in result
    assert "Main content" in result
    assert "Footer stuff" not in result


def test_clean_html_decodes_entities():
    html = "&amp; &lt; &gt; &quot; &#39; &nbsp;"
    result = _clean_html(html)
    assert "&" in result
    assert "<" in result
    assert ">" in result


def test_clean_html_collapses_whitespace():
    html = "<p>Hello     \n\n   world</p>"
    result = _clean_html(html)
    assert "  " not in result


# --- _compute_relevance ---

def test_relevance_high_for_matching_title():
    score = _compute_relevance("python web scraping", "Python Web Scraping Tutorial", "python web scraping content here")
    assert score >= 0.5


def test_relevance_low_for_unrelated():
    score = _compute_relevance("python web scraping", "Cat food recipes", "nothing about python here")
    assert score < 0.3


def test_relevance_empty_query():
    score = _compute_relevance("", "Title", "Content")
    assert score == 0.5


def test_relevance_boosted_by_long_content():
    short = _compute_relevance("test query", "test title", "test")
    long_content = "test " * 100
    long_ = _compute_relevance("test query", "test title", long_content)
    assert long_ >= short


def test_relevance_clamped_between_0_and_1():
    score = _compute_relevance("a b c d e", "a b c d e", "a b c d e " * 50)
    assert 0.0 <= score <= 1.0


# --- WebSearchClient.search (mocked) ---

@pytest.fixture
def mock_web_client():
    """Create a WebSearchClient with mocked DDGS and httpx."""
    client = object.__new__(WebSearchClient)
    client._cache = {}
    client._http = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_search_returns_results(mock_web_client):
    ddgs_results = [
        {"title": "Result 1", "href": "http://a.com", "body": "Python is great for web scraping"},
        {"title": "Result 2", "href": "http://b.com", "body": "Another relevant result about python"},
    ]

    # Mock httpx response for scraping
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.text = "<p>Python is great for web scraping and automation</p>"
    mock_web_client._http.get = AsyncMock(return_value=mock_resp)

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=ddgs_results)
        results = await mock_web_client.search("python web scraping")
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)


@pytest.mark.asyncio
async def test_search_caches_results(mock_web_client):
    ddgs_results = [{"title": "R1", "href": "http://a.com", "body": "Content"}]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.text = "<p>Content</p>"
    mock_web_client._http.get = AsyncMock(return_value=mock_resp)

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=ddgs_results)

        results1 = await mock_web_client.search("cached query")
        results2 = await mock_web_client.search("cached query")

        assert results1 == results2
        # run_in_executor should only be called once (second is from cache)
        assert mock_loop.return_value.run_in_executor.await_count == 1


@pytest.mark.asyncio
async def test_search_returns_empty_on_ddgs_exception(mock_web_client):
    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=RuntimeError("network error"))
        results = await mock_web_client.search("failing query")
        assert results == []


@pytest.mark.asyncio
async def test_search_falls_back_to_snippet_on_scrape_failure(mock_web_client):
    ddgs_results = [{"title": "Title", "href": "http://fail.com", "body": "Snippet content here"}]

    # Scraping fails
    mock_web_client._http.get = AsyncMock(side_effect=httpx_lib.ConnectError("timeout"))

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=ddgs_results)
        results = await mock_web_client.search("test query")
        assert len(results) == 1
        assert results[0].content == "Snippet content here"


# --- create_if_available ---

def test_create_if_available_returns_none_when_ddgs_unavailable():
    with patch("src.rag.client.DDGS_AVAILABLE", False):
        result = WebSearchClient.create_if_available()
        assert result is None


def test_create_if_available_returns_none_when_rag_disabled():
    with patch("src.rag.client.DDGS_AVAILABLE", True):
        with patch.dict("sys.modules", {"config": MagicMock(RAG_ENABLED=False)}):
            result = WebSearchClient.create_if_available()
            assert result is None


def test_create_if_available_returns_client_when_enabled():
    with patch("src.rag.client.DDGS_AVAILABLE", True):
        with patch.dict("sys.modules", {"config": MagicMock(RAG_ENABLED=True)}):
            result = WebSearchClient.create_if_available()
            assert result is not None
            assert isinstance(result, WebSearchClient)
