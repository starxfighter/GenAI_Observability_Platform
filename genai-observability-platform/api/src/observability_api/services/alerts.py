"""Alert service for business logic."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from ..db import DynamoDBClient
from ..models.alerts import Alert, AlertAction, AlertCreate, AlertFilter, AlertSummary, Investigation
from ..models.common import PaginatedResponse


class AlertService:
    """Service for alert operations."""

    def __init__(self) -> None:
        """Initialize alert service."""
        self._dynamodb = DynamoDBClient()

    async def get_alert(self, alert_id: str) -> Alert | None:
        """Get an alert by ID with investigation."""
        alert_data = await self._dynamodb.get_alert(alert_id)
        if not alert_data:
            return None

        # Get investigation if exists
        investigation = await self._dynamodb.get_investigation(alert_id)
        if investigation:
            alert_data["investigation"] = Investigation(**investigation)

        return Alert(**alert_data)

    async def list_alerts(
        self,
        filters: AlertFilter,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[AlertSummary]:
        """List alerts with filters and pagination."""
        items, _ = await self._dynamodb.list_alerts(
            agent_id=filters.agent_id,
            status=filters.status,
            severity=filters.severity,
            start_time=filters.start_time,
            end_time=filters.end_time,
            limit=page_size,
        )

        # Convert to AlertSummary
        summaries = []
        for item in items:
            # Check if investigation exists
            investigation = await self._dynamodb.get_investigation(item["alert_id"])

            summaries.append(AlertSummary(
                alert_id=item["alert_id"],
                agent_id=item["agent_id"],
                anomaly_type=item["anomaly_type"],
                severity=item["severity"],
                status=item["status"],
                message=item["message"],
                timestamp=item["timestamp"],
                has_investigation=investigation is not None,
            ))

        total = len(items)  # Simplified

        return PaginatedResponse.create(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def create_alert(self, data: AlertCreate) -> Alert:
        """Create a new alert."""
        alert_id = str(uuid4())
        now = datetime.utcnow()

        alert_data = {
            "alert_id": alert_id,
            "agent_id": data.agent_id,
            "anomaly_type": data.anomaly_type,
            "severity": data.severity,
            "status": "open",
            "message": data.message,
            "timestamp": now.isoformat(),
            "details": data.details,
        }

        await self._dynamodb.create_alert(alert_data)
        return Alert(**alert_data)

    async def acknowledge_alert(self, alert_id: str, action: AlertAction) -> Alert | None:
        """Acknowledge an alert."""
        now = datetime.utcnow()

        updates = {
            "status": "acknowledged",
            "acknowledged_at": now.isoformat(),
            "acknowledged_by": action.user,
        }

        if action.comment:
            updates["acknowledge_comment"] = action.comment

        updated = await self._dynamodb.update_alert(alert_id, updates)
        if not updated:
            return None

        return Alert(**updated)

    async def resolve_alert(self, alert_id: str, action: AlertAction) -> Alert | None:
        """Resolve an alert."""
        now = datetime.utcnow()

        updates = {
            "status": "resolved",
            "resolved_at": now.isoformat(),
            "resolved_by": action.user,
        }

        if action.comment:
            updates["resolution_comment"] = action.comment

        updated = await self._dynamodb.update_alert(alert_id, updates)
        if not updated:
            return None

        return Alert(**updated)

    async def get_open_alerts_count(self, agent_id: str | None = None) -> dict[str, int]:
        """Get count of open alerts by severity."""
        items, _ = await self._dynamodb.list_alerts(
            agent_id=agent_id,
            status="open",
            limit=1000,
        )

        counts = {"critical": 0, "warning": 0, "info": 0, "total": 0}
        for item in items:
            severity = item.get("severity", "info")
            counts[severity] = counts.get(severity, 0) + 1
            counts["total"] += 1

        return counts

    async def get_alert_investigation(self, alert_id: str) -> Investigation | None:
        """Get investigation for an alert."""
        investigation = await self._dynamodb.get_investigation(alert_id)
        if not investigation:
            return None
        return Investigation(**investigation)

    async def get_recent_alerts(
        self, agent_id: str | None = None, limit: int = 10
    ) -> list[AlertSummary]:
        """Get recent alerts."""
        items, _ = await self._dynamodb.list_alerts(
            agent_id=agent_id,
            limit=limit,
        )

        return [
            AlertSummary(
                alert_id=item["alert_id"],
                agent_id=item["agent_id"],
                anomaly_type=item["anomaly_type"],
                severity=item["severity"],
                status=item["status"],
                message=item["message"],
                timestamp=item["timestamp"],
                has_investigation=False,
            )
            for item in items
        ]
