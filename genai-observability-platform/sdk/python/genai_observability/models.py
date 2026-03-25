"""
Data models for GenAI Observability telemetry events.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


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
    """Severity levels for errors and alerts."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TokenUsage:
    """Token usage information for LLM calls."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class SpanContext:
    """Context for distributed tracing."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None

    def child(self) -> "SpanContext":
        """Create a child span context."""
        return SpanContext(
            trace_id=self.trace_id,
            span_id=str(uuid.uuid4()),
            parent_span_id=self.span_id
        )


@dataclass
class BaseEvent:
    """Base class for all telemetry events."""
    event_type: EventType
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    agent_id: str = ""
    execution_id: str = ""
    trace_id: str = ""
    span_id: str = ""
    parent_span_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data


@dataclass
class ExecutionStartEvent(BaseEvent):
    """Event for when an agent execution starts."""
    event_type: EventType = field(default=EventType.EXECUTION_START)
    agent_type: str = ""  # langchain, crewai, custom
    agent_version: str = ""
    input_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        return data


@dataclass
class ExecutionEndEvent(BaseEvent):
    """Event for when an agent execution ends."""
    event_type: EventType = field(default=EventType.EXECUTION_END)
    duration_ms: float = 0.0
    success: bool = True
    output_data: Optional[Dict[str, Any]] = None
    total_tokens: int = 0
    total_cost: float = 0.0
    error_message: Optional[str] = None


@dataclass
class LLMCallStartEvent(BaseEvent):
    """Event for when an LLM call starts."""
    event_type: EventType = field(default=EventType.LLM_CALL_START)
    model: str = ""
    provider: str = ""  # anthropic, openai, etc.
    prompt: Optional[str] = None  # Can be redacted
    messages: Optional[List[Dict[str, str]]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@dataclass
class LLMCallEndEvent(BaseEvent):
    """Event for when an LLM call ends."""
    event_type: EventType = field(default=EventType.LLM_CALL_END)
    model: str = ""
    provider: str = ""
    duration_ms: float = 0.0
    success: bool = True
    token_usage: Optional[TokenUsage] = None
    response: Optional[str] = None  # Can be redacted
    error_message: Optional[str] = None
    cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        if self.token_usage:
            data["token_usage"] = asdict(self.token_usage)
        return data


@dataclass
class ToolCallStartEvent(BaseEvent):
    """Event for when a tool call starts."""
    event_type: EventType = field(default=EventType.TOOL_CALL_START)
    tool_name: str = ""
    tool_input: Optional[Dict[str, Any]] = None


@dataclass
class ToolCallEndEvent(BaseEvent):
    """Event for when a tool call ends."""
    event_type: EventType = field(default=EventType.TOOL_CALL_END)
    tool_name: str = ""
    duration_ms: float = 0.0
    success: bool = True
    tool_output: Optional[Any] = None
    error_message: Optional[str] = None


@dataclass
class MCPCallStartEvent(BaseEvent):
    """Event for when an MCP server call starts."""
    event_type: EventType = field(default=EventType.MCP_CALL_START)
    server_name: str = ""
    method: str = ""
    params: Optional[Dict[str, Any]] = None


@dataclass
class MCPCallEndEvent(BaseEvent):
    """Event for when an MCP server call ends."""
    event_type: EventType = field(default=EventType.MCP_CALL_END)
    server_name: str = ""
    method: str = ""
    duration_ms: float = 0.0
    success: bool = True
    result: Optional[Any] = None
    error_message: Optional[str] = None


@dataclass
class ErrorEvent(BaseEvent):
    """Event for errors."""
    event_type: EventType = field(default=EventType.ERROR)
    severity: Severity = Severity.ERROR
    error_type: str = ""
    error_message: str = ""
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["severity"] = self.severity.value
        return data


@dataclass
class MetricEvent(BaseEvent):
    """Event for custom metrics."""
    event_type: EventType = field(default=EventType.METRIC)
    metric_name: str = ""
    metric_value: float = 0.0
    unit: str = ""  # ms, count, bytes, etc.
    dimensions: Dict[str, str] = field(default_factory=dict)


@dataclass
class LogEvent(BaseEvent):
    """Event for log messages."""
    event_type: EventType = field(default=EventType.LOG)
    severity: Severity = Severity.INFO
    message: str = ""
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["severity"] = self.severity.value
        return data
