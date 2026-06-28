"""Pydantic models for API request/response schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    """Request body for POST /api/simulate."""
    stimulus: str = Field(..., min_length=1, description="The scenario stimulus text.")
    agent_count: int = Field(default=5, ge=1, le=100, description="Number of agents (1-100).")
    concurrency: int = Field(default=2, ge=1, le=5, description="Max concurrent LLM calls.")
    model: Optional[str] = Field(default=None, description="Override LLM model name.")
    provider: Optional[str] = Field(default=None, description="Override LLM provider (gemini/ollama/openai).")
    crisis_override: Optional[str] = Field(default=None, description="Custom crisis event for Round 3.")
    rag_enabled: Optional[bool] = Field(default=None, description="Override RAG. None=use config default, True=force on, False=force off.")


class SimulationStatus(BaseModel):
    """Response for GET /api/simulate/{run_id}."""
    id: str
    status: str  # queued | running | completed | failed
    scenario_name: Optional[str] = None
    verdict: Optional[str] = None
    elapsed_s: Optional[float] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    progress: Optional[str] = None  # current phase description


class RunSummary(BaseModel):
    """Brief summary of a historical run."""
    id: str
    scenario_name: str
    status: str
    verdict: Optional[str] = None
    agent_count: Optional[int] = None
    elapsed_s: Optional[float] = None
    created_at: str


class RunListResponse(BaseModel):
    """Response for GET /api/runs."""
    runs: list[RunSummary]
    total: int
