"""Alert models and schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AlertSeverity = Literal["critical", "warning", "info"]
AlertStatus = Literal["open", "acknowledged", "resolved"]
AnomalyType = Literal["high_error_rate", "high_latency", "error_spike", "custom"]


class Investigation(BaseModel):
    """LLM investigation result."""

    investigation_id: str
    alert_id: str
    timestamp: datetime
    root_cause: str
    evidence: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    model_used: str = ""


class Alert(BaseModel):
    """Alert model."""

    alert_id: str
    agent_id: str
    anomaly_type: AnomalyType
    severity: AlertSeverity
    status: AlertStatus = "open"
    message: str
    timestamp: datetime
    resolved_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_by: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    investigation: Investigation | None = None


class AlertCreate(BaseModel):
    """Schema for creating an alert."""

    agent_id: str
    anomaly_type: AnomalyType
    severity: AlertSeverity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class AlertUpdate(BaseModel):
    """Schema for updating an alert."""

    status: AlertStatus | None = None
    severity: AlertSeverity | None = None
    message: str | None = None


class AlertAction(BaseModel):
    """Schema for alert actions (acknowledge/resolve)."""

    action: Literal["acknowledge", "resolve"]
    user: str
    comment: str | None = None


class AlertFilter(BaseModel):
    """Alert filter options."""

    agent_id: str | None = None
    status: AlertStatus | None = None
    severity: AlertSeverity | None = None
    anomaly_type: AnomalyType | None = None
    time_range: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class AlertSummary(BaseModel):
    """Alert summary for list views."""

    alert_id: str
    agent_id: str
    anomaly_type: AnomalyType
    severity: AlertSeverity
    status: AlertStatus
    message: str
    timestamp: datetime
    has_investigation: bool = False
