"""Trace models and schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SpanType = Literal["execution", "llm", "tool", "mcp"]
TraceStatus = Literal["running", "completed", "error"]


class Span(BaseModel):
    """Individual span within a trace."""

    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    name: str
    span_type: SpanType
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: int | None = None
    status: TraceStatus = "running"
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)


class Trace(BaseModel):
    """Complete trace with all spans."""

    trace_id: str
    agent_id: str
    name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: int | None = None
    status: TraceStatus = "running"
    spans: list[Span] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceSummary(BaseModel):
    """Trace summary for list views."""

    trace_id: str
    agent_id: str
    name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: int | None = None
    status: TraceStatus
    span_count: int = 0


class TraceCreate(BaseModel):
    """Schema for creating a trace."""

    trace_id: str | None = None
    agent_id: str
    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceFilter(BaseModel):
    """Trace filter options."""

    agent_id: str | None = None
    status: TraceStatus | None = None
    search: str | None = None
    time_range: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    min_duration_ms: int | None = None
    max_duration_ms: int | None = None


class SpanCreate(BaseModel):
    """Schema for creating a span."""

    span_id: str | None = None
    trace_id: str
    parent_span_id: str | None = None
    name: str
    span_type: SpanType
    attributes: dict[str, Any] = Field(default_factory=dict)
