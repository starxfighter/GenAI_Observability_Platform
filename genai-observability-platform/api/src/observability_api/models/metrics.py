"""Metrics models and schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class MetricDataPoint(BaseModel):
    """Single metric data point."""

    timestamp: datetime
    value: float
    p95: float | None = None
    p99: float | None = None


class MetricsSeries(BaseModel):
    """Time series metrics data."""

    metric_name: str
    period: str
    data: list[MetricDataPoint] = Field(default_factory=list)


class DashboardMetrics(BaseModel):
    """Dashboard overview metrics."""

    period: str
    total_agents: int = 0
    active_agents: int = 0
    total_traces: int = 0
    total_errors: int = 0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    traces_trend: float = 0.0
    errors_trend: float = 0.0
    latency_trend: float = 0.0


class AgentMetricsSummary(BaseModel):
    """Per-agent metrics summary."""

    agent_id: str
    agent_name: str
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0


class TokenUsageMetrics(BaseModel):
    """Token usage breakdown."""

    period: str
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    by_model: dict[str, int] = Field(default_factory=dict)
    by_agent: dict[str, int] = Field(default_factory=dict)


class CostMetrics(BaseModel):
    """Cost breakdown."""

    period: str
    total_cost: float = 0.0
    by_model: dict[str, float] = Field(default_factory=dict)
    by_agent: dict[str, float] = Field(default_factory=dict)
    daily_breakdown: list[dict[str, float]] = Field(default_factory=list)
