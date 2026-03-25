"""Trace endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.common import PaginatedResponse
from ..models.traces import Trace, TraceCreate, TraceFilter, TraceSummary
from ..services import TraceService

router = APIRouter()


def get_trace_service() -> TraceService:
    """Dependency for trace service."""
    return TraceService()


@router.get("", response_model=PaginatedResponse[TraceSummary])
async def list_traces(
    service: Annotated[TraceService, Depends(get_trace_service)],
    agent_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
    time_range: str | None = Query(None, regex="^(1h|6h|24h|7d|30d)$"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[TraceSummary]:
    """List traces with optional filters."""
    filters = TraceFilter(
        agent_id=agent_id,
        status=status,
        search=search,
        time_range=time_range,
        start_time=start_time,
        end_time=end_time,
    )
    return await service.list_traces(filters, page, page_size)


@router.get("/{trace_id}", response_model=Trace)
async def get_trace(
    trace_id: str,
    service: Annotated[TraceService, Depends(get_trace_service)],
) -> Trace:
    """Get a trace by ID."""
    trace = await service.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.post("", response_model=Trace, status_code=201)
async def create_trace(
    data: TraceCreate,
    service: Annotated[TraceService, Depends(get_trace_service)],
) -> Trace:
    """Create a new trace."""
    return await service.create_trace(
        agent_id=data.agent_id,
        name=data.name,
        metadata=data.metadata,
    )


@router.post("/{trace_id}/complete", response_model=Trace)
async def complete_trace(
    trace_id: str,
    service: Annotated[TraceService, Depends(get_trace_service)],
    status: str = "completed",
    error: str | None = None,
) -> Trace:
    """Mark a trace as complete."""
    trace = await service.complete_trace(trace_id, status, error)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.get("/{trace_id}/spans")
async def get_trace_spans(
    trace_id: str,
    service: Annotated[TraceService, Depends(get_trace_service)],
) -> list:
    """Get all spans for a trace."""
    spans = await service.get_trace_spans(trace_id)
    if spans is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return spans
