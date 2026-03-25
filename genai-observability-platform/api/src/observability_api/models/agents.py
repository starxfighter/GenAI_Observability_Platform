"""Agent models and schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentStatus = Literal["active", "inactive", "error"]


class Agent(BaseModel):
    """Agent model."""

    agent_id: str
    name: str
    framework: str
    version: str
    status: AgentStatus = "active"
    last_seen: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentCreate(BaseModel):
    """Schema for registering an agent."""

    agent_id: str | None = None
    name: str
    framework: str
    version: str = "1.0.0"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: str | None = None
    framework: str | None = None
    version: str | None = None
    status: AgentStatus | None = None
    metadata: dict[str, Any] | None = None


class AgentMetrics(BaseModel):
    """Agent metrics for a time period."""

    agent_id: str
    period: str
    request_count: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0


class AgentSummary(BaseModel):
    """Agent summary for list views."""

    agent_id: str
    name: str
    framework: str
    version: str
    status: AgentStatus
    last_seen: datetime | None = None
    request_count_24h: int = 0
    error_rate_24h: float = 0.0
