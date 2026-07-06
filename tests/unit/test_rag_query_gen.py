"""Unit tests for src.rag.query_gen (mocked LLM client)."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.rag.query_gen import (
    generate_perspective_queries, generate_crisis_query,
    _extract_keywords, _fallback_perspective_queries,
)


@pytest.fixture
def mock_client():
    """Create a mock LLM client with async chat method."""
    client = MagicMock()
    client.chat = AsyncMock()
    return client


@pytest.fixture
def mock_schema():
    """Create a mock schema with linguistic_clusters."""
    schema = MagicMock()
    schema.scenario_name = "Fintech Lending Platform Launch"
    schema.scenario_description = "A digital lending startup launches in rural Indonesia"
    schema.crisis_dimensions = ["regulatory_freeze", "data_breach", "liquidity_crisis"]

    cluster1 = MagicMock()
    cluster1.cluster_id = "traditional_merchant"
    cluster1.description = "Small market traders who prefer cash transactions"

    cluster2 = MagicMock()
    cluster2.cluster_id = "tech_savvy_youth"
    cluster2.description = "Young urban adopters who embrace digital payments"

    cluster3 = MagicMock()
    cluster3.cluster_id = "rural_farmer"
    cluster3.description = "Agricultural workers with limited internet access"

    schema.linguistic_clusters = [cluster1, cluster2, cluster3]
    return schema


# --- _extract_keywords helper ---

def test_extract_keywords_removes_stop_words():
    text = "A new digital lending app in the Indonesian market"
    kw = _extract_keywords(text)
    assert "the" not in kw.lower()
    assert "new" not in kw.lower()
    assert "digital" in kw.lower() or "lending" in kw.lower()


def test_extract_keywords_prefers_proper_nouns():
    text = "The QRIS system helps Indonesian workers save money"
    kw = _extract_keywords(text)
    assert "QRIS" in kw
    assert "Indonesian" in kw


# --- _fallback_perspective_queries ---

def test_fallback_perspective_queries_returns_per_cluster(mock_schema):
    result = _fallback_perspective_queries(mock_schema)
    assert isinstance(result, dict)
    assert "traditional_merchant" in result
    assert "tech_savvy_youth" in result
    assert "rural_farmer" in result
    # Each query should contain keywords from the cluster description
    assert "perspective" in result["traditional_merchant"].lower() or "opinion" in result["traditional_merchant"].lower()


def test_fallback_perspective_queries_empty_clusters():
    schema = MagicMock()
    schema.scenario_name = "Test"
    schema.linguistic_clusters = []
    result = _fallback_perspective_queries(schema)
    assert result == {}


# --- generate_perspective_queries ---

@pytest.mark.asyncio
async def test_perspective_queries_returns_dict(mock_client, mock_schema):
    mock_client.chat.return_value = json.dumps({
        "queries": {
            "traditional_merchant": ["small merchants complaints about digital payments Indonesia", "QRIS adoption rate SME Indonesia 2024"],
            "tech_savvy_youth": ["young Indonesians enthusiasm e-wallet cashback", "e-wallet market share Indonesia Gen Z"],
            "rural_farmer": ["rural farmers struggle with mobile banking access", "financial inclusion rural Indonesia stats"],
        }
    })
    result = await generate_perspective_queries(mock_client, mock_schema)
    assert isinstance(result, dict)
    assert len(result) == 3
    assert "traditional_merchant" in result
    assert isinstance(result["traditional_merchant"], list)
    assert len(result["traditional_merchant"]) == 2
    assert "complaints" in result["traditional_merchant"][0]


@pytest.mark.asyncio
async def test_perspective_queries_filters_invalid_cluster_ids(mock_client, mock_schema):
    mock_client.chat.return_value = json.dumps({
        "queries": {
            "traditional_merchant": ["merchants complaints cash", "merchant market data"],
            "nonexistent_cluster": ["should be filtered out", "also filtered"],
            "tech_savvy_youth": ["youth digital payment enthusiasm", "youth fintech stats"],
        }
    })
    result = await generate_perspective_queries(mock_client, mock_schema)
    assert "nonexistent_cluster" not in result
    assert "traditional_merchant" in result
    assert "tech_savvy_youth" in result


@pytest.mark.asyncio
async def test_perspective_queries_falls_back_on_invalid_json(mock_client, mock_schema):
    mock_client.chat.return_value = "not json at all"
    result = await generate_perspective_queries(mock_client, mock_schema)
    # Should return keyword-based fallback per cluster (wrapped in lists)
    assert isinstance(result, dict)
    assert len(result) == 3
    assert all(isinstance(v, list) for v in result.values())


@pytest.mark.asyncio
async def test_perspective_queries_falls_back_on_exception(mock_client, mock_schema):
    mock_client.chat.side_effect = RuntimeError("LLM down")
    result = await generate_perspective_queries(mock_client, mock_schema)
    assert isinstance(result, dict)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_perspective_queries_falls_back_on_missing_key(mock_client, mock_schema):
    mock_client.chat.return_value = json.dumps({"wrong_key": {}})
    result = await generate_perspective_queries(mock_client, mock_schema)
    # Fallback is keyword-based
    assert isinstance(result, dict)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_perspective_queries_passes_clusters_to_prompt(mock_client, mock_schema):
    mock_client.chat.return_value = json.dumps({
        "queries": {"traditional_merchant": ["q1", "q1b"], "tech_savvy_youth": ["q2", "q2b"], "rural_farmer": ["q3", "q3b"]}
    })
    await generate_perspective_queries(mock_client, mock_schema)

    # Verify the user message contains cluster info
    call_args = mock_client.chat.call_args[0][0]  # messages list
    user_msg = call_args[1]["content"]
    assert "traditional_merchant" in user_msg
    assert "tech_savvy_youth" in user_msg
    assert "Small market traders" in user_msg


@pytest.mark.asyncio
async def test_perspective_queries_empty_clusters(mock_client):
    schema = MagicMock()
    schema.linguistic_clusters = []
    result = await generate_perspective_queries(mock_client, schema)
    assert result == {}
    mock_client.chat.assert_not_called()


@pytest.mark.asyncio
async def test_perspective_queries_handles_markdown_wrapped_json(mock_client, mock_schema):
    mock_client.chat.return_value = '```json\n{"queries": {"traditional_merchant": ["q1", "q1b"], "tech_savvy_youth": ["q2", "q2b"], "rural_farmer": ["q3", "q3b"]}}\n```'
    result = await generate_perspective_queries(mock_client, mock_schema)
    assert "traditional_merchant" in result


# --- generate_crisis_query ---

@pytest.mark.asyncio
async def test_crisis_query_returns_list(mock_client, mock_schema):
    mock_client.chat.return_value = json.dumps({"queries": ["recent data breach fintech 2024"]})
    result = await generate_crisis_query(mock_client, "Agents debated data security risks", mock_schema)
    assert result == ["recent data breach fintech 2024"]


@pytest.mark.asyncio
async def test_crisis_query_truncates_long_transcript(mock_client, mock_schema):
    long_transcript = "A" * 5000
    mock_client.chat.return_value = json.dumps({"queries": ["q"]})
    await generate_crisis_query(mock_client, long_transcript, mock_schema)

    user_msg = mock_client.chat.call_args[0][0][1]["content"]
    # Transcript portion should be truncated to ~2000 chars
    assert len(user_msg) < 3000


@pytest.mark.asyncio
async def test_crisis_query_falls_back_on_failure(mock_client, mock_schema):
    mock_client.chat.side_effect = Exception("crash")
    result = await generate_crisis_query(mock_client, "data breach concerns among workers", mock_schema)
    # Should return keyword-based fallback
    assert len(result) >= 1
    assert "crisis" in result[0].lower() or "precedent" in result[0].lower()
