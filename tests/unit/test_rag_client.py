"""Unit tests for src.rag.client (SearXNG + scraping)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import httpx as httpx_lib

from src.rag.models import SearchResult
from src.rag.client import (
    WebSearchClient,
    _clean_html,
    _compute_relevance,
    _is_blocked_url,
    _get_domain_boost,
)


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
    score = _compute_relevance(
        "python web scraping", "Python Web Scraping Tutorial",
        "python web scraping content here", "http://example.com"
    )
    assert score >= 0.5


def test_relevance_low_for_unrelated():
    score = _compute_relevance(
        "python web scraping", "Cat food recipes",
        "nothing about python here", "http://example.com"
    )
    assert score < 0.3


def test_relevance_empty_query():
    score = _compute_relevance("", "Title", "Content", "http://example.com")
    assert score == 0.5


def test_relevance_boosted_by_long_content():
    short = _compute_relevance("test query", "test title", "test", "http://example.com")
    long_content = "test " * 100
    long_ = _compute_relevance("test query", "test title", long_content, "http://example.com")
    assert long_ >= short


def test_relevance_clamped_between_0_and_1():
    score = _compute_relevance("a b c d e", "a b c d e", "a b c d e " * 50, "http://example.com")
    assert 0.0 <= score <= 1.0


# --- _is_blocked_url ---

def test_blocks_social_media():
    assert _is_blocked_url("https://www.instagram.com/reel/123") is True
    assert _is_blocked_url("https://www.tiktok.com/@user/video/123") is True
    assert _is_blocked_url("https://www.facebook.com/post/123") is True


def test_allows_news_sites():
    assert _is_blocked_url("https://www.reuters.com/article/123") is False
    assert _is_blocked_url("https://kompas.com/news/123") is False


def test_blocks_binary_files():
    assert _is_blocked_url("https://example.com/file.pdf") is True
    assert _is_blocked_url("https://example.com/image.jpg") is True


# --- _get_domain_boost ---

def test_boost_authoritative_domains():
    assert _get_domain_boost("https://www.reuters.com/article") == 0.15
    assert _get_domain_boost("https://bloomberg.com/news") == 0.15


def test_boost_gov_domains():
    assert _get_domain_boost("https://bps.go.id/stats") == 0.15  # in boosted set
    assert _get_domain_boost("https://kemenkeu.go.id/data") == 0.10  # .go.id generic


def test_no_boost_random_domains():
    assert _get_domain_boost("https://randomsite.com/page") == 0.0


# --- WebSearchClient.search (mocked) ---

@pytest.fixture
def mock_web_client():
    """Create a WebSearchClient with mocked internals."""
    client = WebSearchClient(searxng_url="http://mock:8888")
    client._cache = {}
    client._http = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_search_returns_results(mock_web_client):
    # Mock SearXNG response
    searxng_resp = MagicMock()
    searxng_resp.status_code = 200
    searxng_resp.json.return_value = {
        "results": [
            {"title": "Result 1", "url": "http://a.com/page", "content": "Python is great for web scraping"},
            {"title": "Result 2", "url": "http://b.com/page", "content": "Another relevant result about python"},
        ]
    }

    # Mock scrape response
    scrape_resp = MagicMock()
    scrape_resp.status_code = 200
    scrape_resp.headers = {"content-type": "text/html"}
    scrape_resp.text = "<p>Python is great for web scraping and automation with many libraries</p>" * 5

    mock_web_client._http.get = AsyncMock(side_effect=[searxng_resp, scrape_resp, scrape_resp])

    results = await mock_web_client.search("python web scraping")
    assert len(results) >= 1
    assert all(isinstance(r, SearchResult) for r in results)


@pytest.mark.asyncio
async def test_search_caches_results(mock_web_client):
    searxng_resp = MagicMock()
    searxng_resp.status_code = 200
    searxng_resp.json.return_value = {
        "results": [{"title": "R1", "url": "http://a.com/page", "content": "Content about the topic here"}]
    }

    scrape_resp = MagicMock()
    scrape_resp.status_code = 200
    scrape_resp.headers = {"content-type": "text/html"}
    scrape_resp.text = "<p>Content about the topic here with enough text to pass threshold</p>" * 3

    mock_web_client._http.get = AsyncMock(side_effect=[searxng_resp, scrape_resp])

    results1 = await mock_web_client.search("cached query")
    results2 = await mock_web_client.search("cached query")

    assert results1 == results2
    # Only 2 HTTP calls total (searxng + scrape), not 4
    assert mock_web_client._http.get.await_count == 2


@pytest.mark.asyncio
async def test_search_returns_empty_on_searxng_failure(mock_web_client):
    mock_web_client._http.get = AsyncMock(side_effect=httpx_lib.ConnectError("timeout"))
    results = await mock_web_client.search("failing query")
    assert results == []


@pytest.mark.asyncio
async def test_search_falls_back_to_snippet_on_scrape_failure(mock_web_client):
    searxng_resp = MagicMock()
    searxng_resp.status_code = 200
    searxng_resp.json.return_value = {
        "results": [{"title": "Title", "url": "http://fail.com/page", "content": "Snippet content here that is long enough to pass the fifty char threshold for valid results"}]
    }

    # First call = SearXNG success, subsequent calls = scrape failure
    mock_web_client._http.get = AsyncMock(
        side_effect=[searxng_resp, httpx_lib.ConnectError("timeout")]
    )
    results = await mock_web_client.search("test query")
    assert len(results) == 1
    assert "Snippet content" in results[0].content


@pytest.mark.asyncio
async def test_search_filters_blocked_urls(mock_web_client):
    searxng_resp = MagicMock()
    searxng_resp.status_code = 200
    searxng_resp.json.return_value = {
        "results": [
            {"title": "IG post", "url": "https://www.instagram.com/reel/123", "content": "travel content"},
            {"title": "Real article", "url": "http://news.com/article", "content": "Actual news content about travel industry trends and market analysis"},
        ]
    }

    scrape_resp = MagicMock()
    scrape_resp.status_code = 200
    scrape_resp.headers = {"content-type": "text/html"}
    scrape_resp.text = "<p>Actual news content about travel industry trends and market analysis in Indonesia region</p>" * 3

    mock_web_client._http.get = AsyncMock(side_effect=[searxng_resp, scrape_resp])
    results = await mock_web_client.search("travel Indonesia")
    # Instagram should be filtered out
    assert all("instagram.com" not in r.url for r in results)


# --- create_if_available ---

def test_create_if_available_returns_none_when_rag_disabled():
    with patch.dict("sys.modules", {"config": MagicMock(RAG_ENABLED=False)}):
        result = WebSearchClient.create_if_available()
        assert result is None


def test_create_if_available_returns_client_when_enabled():
    with patch.dict("sys.modules", {"config": MagicMock(RAG_ENABLED=True)}):
        result = WebSearchClient.create_if_available()
        assert result is not None
        assert isinstance(result, WebSearchClient)
