"""Metrics endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..models.metrics import DashboardMetrics, MetricsSeries
from ..services import MetricsService

router = APIRouter()


def get_metrics_service() -> MetricsService:
    """Dependency for metrics service."""
    return MetricsService()


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    service: Annotated[MetricsService, Depends(get_metrics_service)],
    period: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
) -> DashboardMetrics:
    """Get dashboard overview metrics."""
    return await service.get_dashboard_metrics(period)


@router.get("/latency", response_model=MetricsSeries)
async def get_latency_series(
    service: Annotated[MetricsService, Depends(get_metrics_service)],
    period: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    agent_id: str | None = None,
) -> MetricsSeries:
    """Get latency time series."""
    return await service.get_latency_series(period, agent_id)


@router.get("/requests", response_model=MetricsSeries)
async def get_request_series(
    service: Annotated[MetricsService, Depends(get_metrics_service)],
    period: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    agent_id: str | None = None,
) -> MetricsSeries:
    """Get request count time series."""
    return await service.get_request_series(period, agent_id)


@router.get("/errors", response_model=MetricsSeries)
async def get_error_series(
    service: Annotated[MetricsService, Depends(get_metrics_service)],
    period: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    agent_id: str | None = None,
) -> MetricsSeries:
    """Get error count time series."""
    return await service.get_error_series(period, agent_id)


@router.get("/tokens")
async def get_token_usage(
    service: Annotated[MetricsService, Depends(get_metrics_service)],
    period: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    agent_id: str | None = None,
) -> dict:
    """Get token usage breakdown."""
    return await service.get_token_usage(period, agent_id)


@router.get("/cost")
async def get_cost_breakdown(
    service: Annotated[MetricsService, Depends(get_metrics_service)],
    period: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    agent_id: str | None = None,
) -> dict:
    """Get cost breakdown."""
    return await service.get_cost_breakdown(period, agent_id)
