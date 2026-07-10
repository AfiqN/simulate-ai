"""Unit tests for src.dynamics.historical — Historical Context Engine."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.dynamics.historical import (
    HistoricalPrecedent,
    HistoricalContext,
    build_historical_context,
    generate_precedent_queries,
)


# --- Fixtures ---


@pytest.fixture
def mock_client():
    """Create a mock LLM client with async chat method."""
    client = MagicMock()
    client.chat = AsyncMock()
    return client


@pytest.fixture
def mock_rag_client():
    """Create a mock RAG client with async search method."""
    client = MagicMock()
    client.search = AsyncMock()
    return client


@pytest.fixture
def sample_precedent_dict():
    return {
        "title": "2008 Financial Crisis",
        "year": 2008,
        "summary": "Global banking collapse triggered by subprime mortgages.",
        "outcome": "Massive government bailouts and regulatory overhaul.",
        "relevance": "Shows how interconnected risk can cascade.",
        "source": "https://example.com/2008",
        "domain": "finance",
    }


@pytest.fixture
def sample_precedent():
    return HistoricalPrecedent(
        title="2008 Financial Crisis",
        year=2008,
        summary="Global banking collapse triggered by subprime mortgages.",
        outcome="Massive government bailouts and regulatory overhaul.",
        relevance="Shows how interconnected risk can cascade.",
        source="https://example.com/2008",
        domain="finance",
    )


# --- HistoricalPrecedent dataclass ---


class TestHistoricalPrecedent:
    def test_creation_with_all_fields(self, sample_precedent):
        assert sample_precedent.title == "2008 Financial Crisis"
        assert sample_precedent.year == 2008
        assert sample_precedent.summary == "Global banking collapse triggered by subprime mortgages."
        assert sample_precedent.outcome == "Massive government bailouts and regulatory overhaul."
        assert sample_precedent.relevance == "Shows how interconnected risk can cascade."
        assert sample_precedent.source == "https://example.com/2008"
        assert sample_precedent.domain == "finance"

    def test_creation_minimal(self):
        p = HistoricalPrecedent(title="Test Event")
        assert p.title == "Test Event"
        assert p.year is None
        assert p.summary == ""
        assert p.outcome == ""
        assert p.relevance == ""
        assert p.source == ""
        assert p.domain == ""

    def test_to_context_block_full(self, sample_precedent):
        block = sample_precedent.to_context_block()
        assert "**2008 Financial Crisis** (2008)" in block
        assert "Context: Global banking collapse" in block
        assert "Outcome: Massive government bailouts" in block
        assert "Relevance: Shows how interconnected risk" in block

    def test_to_context_block_no_year(self):
        p = HistoricalPrecedent(title="Some Event", summary="Something happened.")
        block = p.to_context_block()
        assert "**Some Event**" in block
        assert "()" not in block
        assert "Context: Something happened." in block

    def test_to_context_block_minimal(self):
        p = HistoricalPrecedent(title="Bare Event")
        block = p.to_context_block()
        assert block == "**Bare Event**"


# --- HistoricalContext.to_dict() ---


class TestHistoricalContextToDict:
    def test_to_dict_empty(self):
        ctx = HistoricalContext(scenario_name="Test Scenario")
        d = ctx.to_dict()
        assert d["scenario_name"] == "Test Scenario"
        assert d["precedents"] == []
        assert d["search_queries_used"] == []

    def test_to_dict_with_precedents(self, sample_precedent):
        ctx = HistoricalContext(
            scenario_name="Finance Sim",
            precedents=[sample_precedent],
            search_queries_used=["financial crisis 2008 precedent"],
        )
        d = ctx.to_dict()
        assert d["scenario_name"] == "Finance Sim"
        assert len(d["precedents"]) == 1
        assert d["precedents"][0]["title"] == "2008 Financial Crisis"
        assert d["precedents"][0]["year"] == 2008
        assert d["precedents"][0]["summary"] == "Global banking collapse triggered by subprime mortgages."
        assert d["precedents"][0]["outcome"] == "Massive government bailouts and regulatory overhaul."
        assert d["precedents"][0]["relevance"] == "Shows how interconnected risk can cascade."
        assert d["precedents"][0]["source"] == "https://example.com/2008"
        assert d["precedents"][0]["domain"] == "finance"
        assert d["search_queries_used"] == ["financial crisis 2008 precedent"]

    def test_to_dict_multiple_precedents(self):
        p1 = HistoricalPrecedent(title="Event A", year=2000, domain="tech")
        p2 = HistoricalPrecedent(title="Event B", year=2010, domain="health")
        ctx = HistoricalContext(
            scenario_name="Multi",
            precedents=[p1, p2],
            search_queries_used=["query1", "query2"],
        )
        d = ctx.to_dict()
        assert len(d["precedents"]) == 2
        assert d["precedents"][0]["title"] == "Event A"
        assert d["precedents"][1]["title"] == "Event B"
        assert len(d["search_queries_used"]) == 2


# --- HistoricalContext.to_agent_prompt_section() ---


class TestHistoricalContextPromptSection:
    def test_empty_precedents_returns_empty_string(self):
        ctx = HistoricalContext(scenario_name="Empty")
        assert ctx.to_agent_prompt_section() == ""

    def test_prompt_section_includes_header(self, sample_precedent):
        ctx = HistoricalContext(scenario_name="Test", precedents=[sample_precedent])
        section = ctx.to_agent_prompt_section()
        assert "## Historical Precedents" in section
        assert "Consider these real-world analogues" in section

    def test_prompt_section_includes_precedent_content(self, sample_precedent):
        ctx = HistoricalContext(scenario_name="Test", precedents=[sample_precedent])
        section = ctx.to_agent_prompt_section()
        assert "2008 Financial Crisis" in section
        assert "Global banking collapse" in section
        assert "adapt your analysis" in section

    def test_prompt_section_respects_max_precedents(self):
        precedents = [
            HistoricalPrecedent(title=f"Event {i}", summary=f"Summary {i}")
            for i in range(5)
        ]
        ctx = HistoricalContext(scenario_name="Test", precedents=precedents)
        section = ctx.to_agent_prompt_section(max_precedents=2)
        assert "Event 0" in section
        assert "Event 1" in section
        assert "Event 2" not in section

    def test_prompt_section_default_max_is_three(self):
        precedents = [
            HistoricalPrecedent(title=f"Event {i}", summary=f"Summary {i}")
            for i in range(5)
        ]
        ctx = HistoricalContext(scenario_name="Test", precedents=precedents)
        section = ctx.to_agent_prompt_section()
        assert "Event 0" in section
        assert "Event 1" in section
        assert "Event 2" in section
        assert "Event 3" not in section


# --- build_historical_context() with user-supplied precedents only ---


class TestBuildHistoricalContextUserPrecedents:
    @pytest.mark.asyncio
    async def test_user_precedents_only(self, mock_client, sample_precedent_dict):
        ctx = await build_historical_context(
            client=mock_client,
            scenario_name="Test Scenario",
            stimulus="Testing a new product launch",
            dimensions=["market", "adoption"],
            user_precedents=[sample_precedent_dict],
        )
        assert isinstance(ctx, HistoricalContext)
        assert ctx.scenario_name == "Test Scenario"
        assert len(ctx.precedents) == 1
        assert ctx.precedents[0].title == "2008 Financial Crisis"
        assert ctx.precedents[0].year == 2008
        assert ctx.precedents[0].source == "https://example.com/2008"
        # No RAG client, so no LLM calls for query generation
        mock_client.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_precedents_multiple(self, mock_client):
        user_precs = [
            {"title": "Event A", "year": 2001, "summary": "First event"},
            {"title": "Event B", "year": 2015, "outcome": "Second event outcome"},
        ]
        ctx = await build_historical_context(
            client=mock_client,
            scenario_name="Multi Test",
            stimulus="stimulus text",
            dimensions=["dim1"],
            user_precedents=user_precs,
        )
        assert len(ctx.precedents) == 2
        assert ctx.precedents[0].title == "Event A"
        assert ctx.precedents[1].title == "Event B"
        assert ctx.precedents[1].outcome == "Second event outcome"

    @pytest.mark.asyncio
    async def test_user_precedents_minimal_dict(self, mock_client):
        ctx = await build_historical_context(
            client=mock_client,
            scenario_name="Minimal",
            stimulus="stimulus",
            dimensions=[],
            user_precedents=[{"title": "Bare"}],
        )
        assert ctx.precedents[0].title == "Bare"
        assert ctx.precedents[0].source == "user-supplied"

    @pytest.mark.asyncio
    async def test_no_precedents_no_rag(self, mock_client):
        ctx = await build_historical_context(
            client=mock_client,
            scenario_name="Empty",
            stimulus="something",
            dimensions=["a"],
        )
        assert ctx.precedents == []
        assert ctx.search_queries_used == []


# --- build_historical_context() with RAG client ---


class TestBuildHistoricalContextWithRAG:
    @pytest.mark.asyncio
    async def test_rag_generates_queries_and_extracts(self, mock_client, mock_rag_client):
        # LLM returns queries on first call, then extracts precedents on second
        mock_client.chat.side_effect = [
            json.dumps({"queries": ["fintech crisis 2024", "mobile banking failure"]}),
            json.dumps({
                "precedents": [
                    {
                        "title": "M-Pesa Expansion Challenges",
                        "year": 2014,
                        "summary": "Mobile money faced trust issues in new markets.",
                        "outcome": "Gradual adoption after regulatory clarity.",
                        "relevance": "Similar trust dynamics at play.",
                        "domain": "finance",
                    }
                ]
            }),
        ]
        # RAG returns search results
        mock_rag_client.search.return_value = [
            MagicMock(title="Result 1", content="M-Pesa struggled in India")
        ]

        with patch("src.rag.processor.extract_facts_with_llm") as mock_extract:
            mock_processed = MagicMock()
            mock_processed.facts = ["M-Pesa struggled in India due to trust issues"]
            mock_extract.return_value = mock_processed

            ctx = await build_historical_context(
                client=mock_client,
                scenario_name="Fintech Launch",
                stimulus="Launching mobile payments in rural area",
                dimensions=["adoption", "trust", "regulation"],
                rag_client=mock_rag_client,
            )

        assert ctx.scenario_name == "Fintech Launch"
        assert len(ctx.search_queries_used) == 2
        assert "fintech crisis 2024" in ctx.search_queries_used
        assert len(ctx.precedents) == 1
        assert ctx.precedents[0].title == "M-Pesa Expansion Challenges"

    @pytest.mark.asyncio
    async def test_rag_combined_with_user_precedents(self, mock_client, mock_rag_client):
        mock_client.chat.side_effect = [
            json.dumps({"queries": ["test query"]}),
            json.dumps({
                "precedents": [
                    {"title": "RAG Precedent", "year": 2020, "summary": "From search."}
                ]
            }),
        ]
        mock_rag_client.search.return_value = [MagicMock(title="R", content="content")]

        with patch("src.rag.processor.extract_facts_with_llm") as mock_extract:
            mock_processed = MagicMock()
            mock_processed.facts = ["Some fact from search"]
            mock_extract.return_value = mock_processed

            ctx = await build_historical_context(
                client=mock_client,
                scenario_name="Combined",
                stimulus="test stimulus",
                dimensions=["d1"],
                rag_client=mock_rag_client,
                user_precedents=[{"title": "User Precedent", "year": 1999}],
            )

        # User precedents come first
        assert ctx.precedents[0].title == "User Precedent"
        assert ctx.precedents[1].title == "RAG Precedent"
        assert len(ctx.precedents) == 2

    @pytest.mark.asyncio
    async def test_rag_search_failure_continues_gracefully(self, mock_client, mock_rag_client):
        mock_client.chat.return_value = json.dumps({"queries": ["query1"]})
        mock_rag_client.search.side_effect = RuntimeError("Search unavailable")

        ctx = await build_historical_context(
            client=mock_client,
            scenario_name="Fail Gracefully",
            stimulus="test",
            dimensions=["x"],
            rag_client=mock_rag_client,
        )

        # Should not raise, just return empty precedents
        assert isinstance(ctx, HistoricalContext)
        assert ctx.precedents == []

    @pytest.mark.asyncio
    async def test_rag_no_results_skips_extraction(self, mock_client, mock_rag_client):
        mock_client.chat.return_value = json.dumps({"queries": ["query1"]})
        mock_rag_client.search.return_value = []

        ctx = await build_historical_context(
            client=mock_client,
            scenario_name="No Results",
            stimulus="test",
            dimensions=["x"],
            rag_client=mock_rag_client,
        )

        # Only one LLM call for query generation, no extraction call
        assert mock_client.chat.call_count == 1
        assert ctx.precedents == []


# --- generate_precedent_queries() ---


class TestGeneratePrecedentQueries:
    @pytest.mark.asyncio
    async def test_returns_list_of_queries(self, mock_client):
        mock_client.chat.return_value = json.dumps({
            "queries": ["crypto crash 2022", "FTX collapse aftermath", "terra luna depegging"]
        })
        result = await generate_precedent_queries(
            mock_client,
            scenario_name="Crypto Exchange Launch",
            stimulus="Launching a new crypto exchange",
            dimensions=["trust", "regulation", "liquidity"],
        )
        assert isinstance(result, list)
        assert len(result) == 3
        assert "crypto crash 2022" in result

    @pytest.mark.asyncio
    async def test_truncates_to_three_queries(self, mock_client):
        mock_client.chat.return_value = json.dumps({
            "queries": ["q1", "q2", "q3", "q4", "q5"]
        })
        result = await generate_precedent_queries(
            mock_client,
            scenario_name="Test",
            stimulus="test",
            dimensions=["a", "b"],
        )
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_falls_back_on_invalid_json(self, mock_client):
        mock_client.chat.return_value = "not valid json at all"
        result = await generate_precedent_queries(
            mock_client,
            scenario_name="My Scenario",
            stimulus="test stimulus",
            dimensions=["dim1"],
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert "My Scenario" in result[0]
        assert "historical precedent" in result[0]

    @pytest.mark.asyncio
    async def test_falls_back_on_missing_queries_key(self, mock_client):
        mock_client.chat.return_value = json.dumps({"wrong_key": []})
        result = await generate_precedent_queries(
            mock_client,
            scenario_name="Fallback Test",
            stimulus="test",
            dimensions=[],
        )
        # Missing key returns empty from .get("queries", []) then [:3] = []
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_falls_back_on_type_error(self, mock_client):
        """TypeError is caught and triggers fallback query."""
        mock_client.chat.side_effect = TypeError("bad type")
        result = await generate_precedent_queries(
            mock_client,
            scenario_name="Error Scenario",
            stimulus="test",
            dimensions=["x"],
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert "Error Scenario" in result[0]

    @pytest.mark.asyncio
    async def test_uncaught_exception_propagates(self, mock_client):
        """RuntimeError is not caught and propagates to caller."""
        mock_client.chat.side_effect = RuntimeError("LLM exploded")
        with pytest.raises(RuntimeError, match="LLM exploded"):
            await generate_precedent_queries(
                mock_client,
                scenario_name="Error Scenario",
                stimulus="test",
                dimensions=["x"],
            )

    @pytest.mark.asyncio
    async def test_prompt_includes_scenario_info(self, mock_client):
        mock_client.chat.return_value = json.dumps({"queries": ["q1"]})
        await generate_precedent_queries(
            mock_client,
            scenario_name="Healthcare AI",
            stimulus="Deploying AI diagnostics in rural clinics",
            dimensions=["accuracy", "trust", "cost"],
        )
        call_args = mock_client.chat.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "Healthcare AI" in user_msg
        assert "Deploying AI diagnostics" in user_msg
        assert "accuracy" in user_msg

    @pytest.mark.asyncio
    async def test_truncates_long_stimulus(self, mock_client):
        mock_client.chat.return_value = json.dumps({"queries": ["q1"]})
        long_stimulus = "x" * 1000
        await generate_precedent_queries(
            mock_client,
            scenario_name="Test",
            stimulus=long_stimulus,
            dimensions=["a"],
        )
        call_args = mock_client.chat.call_args[0][0]
        user_msg = call_args[1]["content"]
        # Stimulus is truncated to 500 chars
        assert "x" * 501 not in user_msg

    @pytest.mark.asyncio
    async def test_limits_dimensions_in_prompt(self, mock_client):
        mock_client.chat.return_value = json.dumps({"queries": ["q1"]})
        dims = [f"dim{i}" for i in range(10)]
        await generate_precedent_queries(
            mock_client,
            scenario_name="Test",
            stimulus="test",
            dimensions=dims,
        )
        call_args = mock_client.chat.call_args[0][0]
        user_msg = call_args[1]["content"]
        # Only first 6 dimensions should appear
        assert "dim5" in user_msg
        assert "dim6" not in user_msg
