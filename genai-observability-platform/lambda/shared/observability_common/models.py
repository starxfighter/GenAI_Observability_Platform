"""
Data models for GenAI Observability Lambda functions.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import hashlib


class EventType(str, Enum):
    """Types of telemetry events."""

    EXECUTION_START = "execution_start"
    EXECUTION_END = "execution_end"
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_END = "llm_call_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    MCP_CALL_START = "mcp_call_start"
    MCP_CALL_END = "mcp_call_end"
    ERROR = "error"
    METRIC = "metric"
    LOG = "log"


class Severity(str, Enum):
    """Severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ResolutionStatus(str, Enum):
    """Resolution status for errors and investigations."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


@dataclass
class TokenUsage:
    """Token usage information."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class Event:
    """Base event model."""

    event_type: str
    agent_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    execution_id: str = ""
    trace_id: str = ""
    span_id: str = ""
    parent_span_id: Optional[str] = None
    agent_type: str = ""
    agent_version: str = ""
    environment: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    global_tags: Dict[str, str] = field(default_factory=dict)
    ingestion_timestamp: str = ""

    # Optional fields for specific event types
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    cost: Optional[float] = None
    tool_name: Optional[str] = None
    server_name: Optional[str] = None
    method: Optional[str] = None
    severity: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    unit: Optional[str] = None
    dimensions: Optional[Dict[str, str]] = None
    message: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create an Event from a dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result

    def is_error(self) -> bool:
        """Check if this is an error event."""
        return self.event_type == EventType.ERROR.value

    def is_end_event(self) -> bool:
        """Check if this is an end event (has duration)."""
        return self.event_type in [
            EventType.EXECUTION_END.value,
            EventType.LLM_CALL_END.value,
            EventType.TOOL_CALL_END.value,
            EventType.MCP_CALL_END.value,
        ]


@dataclass
class Error:
    """Error record model."""

    error_id: str
    agent_id: str
    timestamp: str
    error_type: str
    error_message: str
    execution_id: str = ""
    stack_trace: Optional[str] = None
    severity: str = Severity.ERROR.value
    context: Optional[Dict[str, Any]] = None

    # LLM Analysis fields
    llm_analysis: Optional[str] = None
    root_cause: Optional[str] = None
    remediation_steps: Optional[List[str]] = None
    impact_assessment: Optional[str] = None
    prevention_notes: Optional[str] = None

    # Resolution tracking
    resolution_status: str = ResolutionStatus.OPEN.value
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None

    # TTL for automatic cleanup
    ttl: int = 0

    @classmethod
    def from_event(cls, event: Event, error_id: Optional[str] = None) -> "Error":
        """Create an Error from an Event."""
        if error_id is None:
            error_id = f"{event.agent_id}-{event.execution_id or uuid.uuid4()}-{datetime.utcnow().timestamp()}"

        return cls(
            error_id=error_id,
            agent_id=event.agent_id,
            timestamp=event.timestamp,
            error_type=event.error_type or "unknown",
            error_message=event.error_message or "",
            execution_id=event.execution_id,
            stack_trace=event.stack_trace,
            severity=event.severity or Severity.ERROR.value,
            context=event.context,
        )

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        item = {
            "error_id": self.error_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "severity": self.severity,
            "resolution_status": self.resolution_status,
        }

        if self.execution_id:
            item["execution_id"] = self.execution_id
        if self.stack_trace:
            item["stack_trace"] = self.stack_trace
        if self.context:
            item["context"] = self.context
        if self.llm_analysis:
            item["llm_analysis"] = self.llm_analysis
        if self.root_cause:
            item["root_cause"] = self.root_cause
        if self.remediation_steps:
            item["remediation_steps"] = self.remediation_steps
        if self.ttl > 0:
            item["ttl"] = self.ttl

        return item


@dataclass
class Investigation:
    """Investigation result model."""

    investigation_id: str
    agent_id: str
    anomaly_type: str
    severity: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    execution_id: Optional[str] = None

    # LLM Analysis
    llm_analysis: str = ""
    root_cause: str = ""
    evidence: str = ""
    impact_assessment: str = ""
    remediation_steps: List[str] = field(default_factory=list)
    prevention_notes: str = ""
    similar_incidents_analysis: str = ""

    # Model metadata
    model_used: str = ""
    token_usage: Optional[Dict[str, int]] = None

    # Resolution tracking
    resolution_status: str = ResolutionStatus.OPEN.value
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None

    # TTL
    ttl: int = 0

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        item = {
            "investigation_id": self.investigation_id,
            "agent_id": self.agent_id,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "llm_analysis": self.llm_analysis,
            "resolution_status": self.resolution_status,
        }

        if self.execution_id:
            item["execution_id"] = self.execution_id
        if self.root_cause:
            item["root_cause"] = self.root_cause
        if self.remediation_steps:
            item["remediation_steps"] = self.remediation_steps
        if self.model_used:
            item["model_used"] = self.model_used
        if self.token_usage:
            item["token_usage"] = self.token_usage
        if self.ttl > 0:
            item["ttl"] = self.ttl

        return item


@dataclass
class Alert:
    """Alert model for notifications."""

    agent_id: str
    anomaly_type: str
    severity: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    execution_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    recent_errors: List[Dict[str, Any]] = field(default_factory=list)

    # Investigation results (if available)
    investigation: Optional[Dict[str, Any]] = None

    # Links
    dashboard_url: Optional[str] = None
    traces_url: Optional[str] = None
    agent_details_url: Optional[str] = None

    def generate_fingerprint(self) -> str:
        """Generate a fingerprint for deduplication."""
        components = [
            self.agent_id,
            self.anomaly_type,
            str(self.metrics)[:100],
        ]
        fingerprint_str = "|".join(components)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()

    def to_sns_message(self) -> Dict[str, Any]:
        """Convert to SNS message format."""
        message = {
            "notification_type": "alert",
            "incident": {
                "agent_id": self.agent_id,
                "anomaly_type": self.anomaly_type,
                "severity": self.severity,
                "timestamp": self.timestamp,
                "execution_id": self.execution_id,
                "metrics": self.metrics,
            },
        }

        if self.investigation:
            message["investigation"] = self.investigation

        if self.dashboard_url or self.traces_url or self.agent_details_url:
            message["links"] = {
                "dashboard": self.dashboard_url,
                "traces": self.traces_url,
                "agent_details": self.agent_details_url,
            }

        return message

    def to_sns_attributes(self) -> Dict[str, Dict[str, str]]:
        """Get SNS message attributes."""
        return {
            "severity": {"DataType": "String", "StringValue": self.severity},
            "agent_id": {"DataType": "String", "StringValue": self.agent_id},
            "anomaly_type": {"DataType": "String", "StringValue": self.anomaly_type},
            "has_investigation": {
                "DataType": "String",
                "StringValue": "true" if self.investigation else "false",
            },
        }
