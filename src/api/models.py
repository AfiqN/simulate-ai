"""Pydantic models for API request/response schemas."""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class CustomStakeholder(BaseModel):
    """A user-defined stakeholder persona to inject into the simulation."""
    role: str = Field(..., min_length=1, max_length=100, description="Role title, e.g. 'CFO', 'Head of Engineering'.")
    description: str = Field(..., min_length=1, max_length=500, description="Character description, e.g. 'conservative, focused on cash flow'.")
    focus_areas: Optional[list[str]] = Field(default=None, max_length=5, description="Key areas this stakeholder focuses on.")
    constraints: Optional[list[str]] = Field(default=None, max_length=5, description="Hard red lines this stakeholder will not cross.")


class SimulationRequest(BaseModel):
    """Request body for POST /api/simulate."""
    stimulus: str = Field(..., min_length=1, description="The scenario stimulus text.")
    agent_count: int = Field(default=5, ge=1, le=100, description="Number of agents (1-100).")
    concurrency: int = Field(default=2, ge=1, le=5, description="Max concurrent LLM calls.")
    model: Optional[str] = Field(default=None, description="Override LLM model name.")
    provider: Optional[str] = Field(default=None, description="Override LLM provider (gemini/ollama/openai).")
    crisis_override: Optional[str] = Field(default=None, description="Custom crisis event for Round 3.")
    rag_enabled: Optional[bool] = Field(default=None, description="Override RAG. None=use config default, True=force on, False=force off.")
    depth: Literal["quick", "standard", "deep"] = Field(default="quick", description="Analysis depth: quick (2 rounds, concise), standard (full), deep (verbose + minority report).")
    mode: Literal["collaborative", "adversarial"] = Field(default="collaborative", description="Debate mode: collaborative (consensus-seeking) or adversarial (argument survival through challenge).")
    custom_stakeholders: Optional[list[CustomStakeholder]] = Field(default=None, max_length=10, description="User-defined stakeholder personas to inject (max 10).")
    historical_precedents: Optional[list[dict[str, Any]]] = Field(default=None, max_length=5, description="User-supplied historical precedents (title, year, summary, outcome, relevance, domain).")


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


class SchemaApprovalRequest(BaseModel):
    """Request body for POST /api/simulate/{run_id}/schema — approve or edit the generated schema."""
    approved: bool = Field(default=True, description="Whether to approve the schema as-is or with overrides.")
    overrides: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional partial schema overrides: actions, evaluation_dimensions, state_vocabulary."
    )


class WebhookRegisterRequest(BaseModel):
    """Request body for POST /api/webhooks."""
    url: str = Field(..., description="HTTPS endpoint to receive webhook payloads.")
    events: list[str] = Field(
        default=["*"],
        description="Event types to subscribe to. Use '*' for all. Options: simulation.started, simulation.schema_ready, simulation.round_complete, simulation.completed, simulation.failed, simulation.cancelled."
    )
    secret: Optional[str] = Field(default=None, description="Shared secret for HMAC-SHA256 payload signing.")


class WebhookResponse(BaseModel):
    """Response for webhook endpoints."""
    id: str
    url: str
    events: list[str]
    active: bool
    created_at: float
    failure_count: int

