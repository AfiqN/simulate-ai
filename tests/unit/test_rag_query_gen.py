"""Unit tests for src.rag.query_gen (mocked LLM client)."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.rag.query_gen import (
    generate_stimulus_queries, generate_domain_queries, generate_crisis_query,
    _extract_keywords, _fallback_stimulus_queries,
)


@pytest.fixture
def mock_client():
    """Create a mock LLM client with async chat method."""
    client = MagicMock()
    client.chat = AsyncMock()
    return client


@pytest.fixture
def mock_schema():
    """Create a mock schema with scenario_name and crisis_dimensions."""
    schema = MagicMock()
    schema.scenario_name = "Fintech Lending Platform Launch"
    schema.crisis_dimensions = ["regulatory_freeze", "data_breach", "liquidity_crisis"]
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


def test_fallback_stimulus_queries_returns_two():
    queries = _fallback_stimulus_queries("A new fintech lending platform launch in Indonesia")
    assert len(queries) == 2
    assert "2024 2025" in queries[0]


# --- generate_stimulus_queries ---

@pytest.mark.asyncio
async def test_stimulus_queries_returns_list(mock_client):
    mock_client.chat.return_value = json.dumps({"queries": ["fintech regulation 2024", "digital lending market"]})
    result = await generate_stimulus_queries(mock_client, "A new digital lending app in Indonesia")
    assert result == ["fintech regulation 2024", "digital lending market"]


@pytest.mark.asyncio
async def test_stimulus_queries_falls_back_on_invalid_json(mock_client):
    mock_client.chat.return_value = "not json at all"
    result = await generate_stimulus_queries(mock_client, "Some stimulus about fintech")
    # Should return keyword-based fallback, not empty
    assert len(result) == 2
    assert any("fintech" in q.lower() for q in result)


@pytest.mark.asyncio
async def test_stimulus_queries_falls_back_on_exception(mock_client):
    mock_client.chat.side_effect = RuntimeError("LLM down")
    result = await generate_stimulus_queries(mock_client, "Digital lending in Indonesia")
    # Should return keyword-based fallback
    assert len(result) == 2


@pytest.mark.asyncio
async def test_stimulus_queries_falls_back_on_missing_key(mock_client):
    mock_client.chat.return_value = json.dumps({"wrong_key": ["a", "b"]})
    result = await generate_stimulus_queries(mock_client, "Some stimulus text")
    # Fallback is keyword-based
    assert len(result) == 2


@pytest.mark.asyncio
async def test_stimulus_queries_coerces_non_string_items(mock_client):
    mock_client.chat.return_value = json.dumps({"queries": [123, True]})
    result = await generate_stimulus_queries(mock_client, "Some stimulus")
    assert result == ["123", "True"]


@pytest.mark.asyncio
async def test_stimulus_queries_handles_markdown_wrapped_json(mock_client):
    mock_client.chat.return_value = '```json\n{"queries": ["query one", "query two"]}\n```'
    result = await generate_stimulus_queries(mock_client, "Test stimulus")
    assert result == ["query one", "query two"]


# --- generate_domain_queries ---

@pytest.mark.asyncio
async def test_domain_queries_returns_list(mock_client, mock_schema):
    mock_client.chat.return_value = json.dumps({"queries": ["recent fintech data breaches SE Asia"]})
    result = await generate_domain_queries(mock_client, mock_schema)
    assert result == ["recent fintech data breaches SE Asia"]


@pytest.mark.asyncio
async def test_domain_queries_falls_back_on_exception(mock_client, mock_schema):
    mock_client.chat.side_effect = RuntimeError("timeout")
    result = await generate_domain_queries(mock_client, mock_schema)
    # Should return keyword-based fallback from schema
    assert len(result) >= 1
    assert any("Fintech" in q or "regulatory" in q for q in result)


@pytest.mark.asyncio
async def test_domain_queries_passes_schema_to_prompt(mock_client, mock_schema):
    mock_client.chat.return_value = json.dumps({"queries": ["q1"]})
    await generate_domain_queries(mock_client, mock_schema)

    # Verify the user message contains schema info
    call_args = mock_client.chat.call_args[0][0]  # messages list
    user_msg = call_args[1]["content"]
    assert "Fintech Lending Platform Launch" in user_msg
    assert "regulatory_freeze" in user_msg


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
