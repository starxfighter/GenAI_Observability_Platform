"""Trace service for business logic."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from ..db import DynamoDBClient, OpenSearchClient
from ..models.common import PaginatedResponse
from ..models.traces import Trace, TraceFilter, TraceSummary


class TraceService:
    """Service for trace operations."""

    def __init__(self) -> None:
        """Initialize trace service."""
        self._dynamodb = DynamoDBClient()
        self._opensearch = OpenSearchClient()

    async def get_trace(self, trace_id: str) -> Trace | None:
        """Get a trace by ID with all spans."""
        trace_data = await self._dynamodb.get_trace(trace_id)
        if not trace_data:
            return None
        return Trace(**trace_data)

    async def list_traces(
        self,
        filters: TraceFilter,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[TraceSummary]:
        """List traces with filters and pagination."""
        # Use OpenSearch for full-text search
        if filters.search:
            items, total = await self._opensearch.search_traces(
                query=filters.search,
                agent_id=filters.agent_id,
                status=filters.status,
                start_time=filters.start_time,
                end_time=filters.end_time,
                page=page,
                page_size=page_size,
            )
        else:
            # Use DynamoDB for simple filters
            items, _ = await self._dynamodb.list_traces(
                agent_id=filters.agent_id,
                status=filters.status,
                start_time=filters.start_time,
                end_time=filters.end_time,
                limit=page_size,
            )
            total = len(items)  # Simplified - would need count query for accurate total

        # Convert to TraceSummary
        summaries = []
        for item in items:
            summaries.append(TraceSummary(
                trace_id=item["trace_id"],
                agent_id=item["agent_id"],
                name=item.get("name", ""),
                start_time=item["start_time"],
                end_time=item.get("end_time"),
                duration_ms=item.get("duration_ms"),
                status=item.get("status", "running"),
                span_count=len(item.get("spans", [])),
            ))

        return PaginatedResponse.create(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def create_trace(self, agent_id: str, name: str, metadata: dict[str, Any] | None = None) -> Trace:
        """Create a new trace."""
        trace_id = str(uuid4())
        now = datetime.utcnow()

        trace_data = {
            "trace_id": trace_id,
            "agent_id": agent_id,
            "name": name,
            "start_time": now.isoformat(),
            "status": "running",
            "spans": [],
            "metadata": metadata or {},
        }

        await self._dynamodb.create_trace(trace_data)
        return Trace(**trace_data)

    async def complete_trace(
        self, trace_id: str, status: str = "completed", error: str | None = None
    ) -> Trace | None:
        """Mark a trace as complete."""
        now = datetime.utcnow()

        # Get current trace to calculate duration
        trace = await self._dynamodb.get_trace(trace_id)
        if not trace:
            return None

        start_time = datetime.fromisoformat(trace["start_time"])
        duration_ms = int((now - start_time).total_seconds() * 1000)

        updates: dict[str, Any] = {
            "end_time": now.isoformat(),
            "duration_ms": duration_ms,
            "status": status,
        }

        if error:
            updates["error"] = error

        updated = await self._dynamodb.update_trace(trace_id, updates)
        return Trace(**updated) if updated else None

    async def get_trace_spans(self, trace_id: str) -> list[dict[str, Any]]:
        """Get all spans for a trace."""
        trace = await self._dynamodb.get_trace(trace_id)
        if not trace:
            return []
        return trace.get("spans", [])

    async def get_recent_traces(self, agent_id: str, limit: int = 10) -> list[TraceSummary]:
        """Get recent traces for an agent."""
        items, _ = await self._dynamodb.list_traces(
            agent_id=agent_id,
            limit=limit,
        )

        return [
            TraceSummary(
                trace_id=item["trace_id"],
                agent_id=item["agent_id"],
                name=item.get("name", ""),
                start_time=item["start_time"],
                end_time=item.get("end_time"),
                duration_ms=item.get("duration_ms"),
                status=item.get("status", "running"),
                span_count=len(item.get("spans", [])),
            )
            for item in items
        ]
