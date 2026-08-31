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
    stimulus: str = Field(..., min_length=1, max_length=20_000, description="The scenario stimulus text.")
    agent_count: int = Field(default=5, ge=1, le=20, description="Number of agents (1-20).")
    concurrency: int = Field(default=2, ge=1, le=5, description="Max concurrent LLM calls.")
    model: Optional[str] = Field(default=None, max_length=200, description="Override LLM model name.")
    provider: Optional[Literal["gemini", "ollama", "openai"]] = Field(default=None, description="Override LLM provider.")
    crisis_override: Optional[str] = Field(default=None, max_length=5_000, description="Custom crisis event for Round 3.")
    rag_enabled: Optional[bool] = Field(default=None, description="Override RAG. None=use config default.")
    depth: Literal["quick", "standard", "deep"] = Field(default="quick", description="Analysis depth.")
    mode: Literal["collaborative", "adversarial"] = Field(default="collaborative", description="Debate mode.")
    schema_approval: Literal["auto", "manual"] = Field(default="auto", description="Whether generated schemas require manual approval.")
    custom_stakeholders: Optional[list[CustomStakeholder]] = Field(default=None, max_length=10)
    historical_precedents: Optional[list[dict[str, Any]]] = Field(default=None, max_length=5)


class SimulationStartResponse(BaseModel):
    id: str
    status: str
    access_token: str


class SimulationStatus(BaseModel):
    """Response for GET /api/simulate/{run_id}."""
    id: str
    status: str  # queued | running | schema_pending | completed | failed | cancelled
    scenario_name: Optional[str] = None
    verdict: Optional[str] = None
    elapsed_s: Optional[float] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    progress: Optional[str] = None  # human-readable current phase
    progress_percent: int = 0
    stage: Optional[str] = None
    schema_pending: bool = False
    latest_seq: int = 0


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

