"""Alert endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.alerts import (
    Alert,
    AlertAction,
    AlertCreate,
    AlertFilter,
    AlertSummary,
    Investigation,
)
from ..models.common import PaginatedResponse
from ..services import AlertService

router = APIRouter()


def get_alert_service() -> AlertService:
    """Dependency for alert service."""
    return AlertService()


@router.get("", response_model=PaginatedResponse[AlertSummary])
async def list_alerts(
    service: Annotated[AlertService, Depends(get_alert_service)],
    agent_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    time_range: str | None = Query(None, regex="^(1h|6h|24h|7d|30d)$"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[AlertSummary]:
    """List alerts with optional filters."""
    filters = AlertFilter(
        agent_id=agent_id,
        status=status,
        severity=severity,
        time_range=time_range,
        start_time=start_time,
        end_time=end_time,
    )
    return await service.list_alerts(filters, page, page_size)


@router.get("/counts")
async def get_alert_counts(
    service: Annotated[AlertService, Depends(get_alert_service)],
    agent_id: str | None = None,
) -> dict:
    """Get count of open alerts by severity."""
    return await service.get_open_alerts_count(agent_id)


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: str,
    service: Annotated[AlertService, Depends(get_alert_service)],
) -> Alert:
    """Get an alert by ID."""
    alert = await service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("", response_model=Alert, status_code=201)
async def create_alert(
    data: AlertCreate,
    service: Annotated[AlertService, Depends(get_alert_service)],
) -> Alert:
    """Create a new alert."""
    return await service.create_alert(data)


@router.post("/{alert_id}/acknowledge", response_model=Alert)
async def acknowledge_alert(
    alert_id: str,
    action: AlertAction,
    service: Annotated[AlertService, Depends(get_alert_service)],
) -> Alert:
    """Acknowledge an alert."""
    if action.action != "acknowledge":
        raise HTTPException(status_code=400, detail="Invalid action")

    alert = await service.acknowledge_alert(alert_id, action)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/resolve", response_model=Alert)
async def resolve_alert(
    alert_id: str,
    action: AlertAction,
    service: Annotated[AlertService, Depends(get_alert_service)],
) -> Alert:
    """Resolve an alert."""
    if action.action != "resolve":
        raise HTTPException(status_code=400, detail="Invalid action")

    alert = await service.resolve_alert(alert_id, action)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/{alert_id}/investigation", response_model=Investigation)
async def get_alert_investigation(
    alert_id: str,
    service: Annotated[AlertService, Depends(get_alert_service)],
) -> Investigation:
    """Get investigation for an alert."""
    investigation = await service.get_alert_investigation(alert_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation
