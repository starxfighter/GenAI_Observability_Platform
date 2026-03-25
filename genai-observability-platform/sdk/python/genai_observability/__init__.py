"""
GenAI Observability SDK

A comprehensive observability SDK for GenAI agents, providing automatic
tracing, metrics, and error tracking.

Usage:
    from genai_observability import ObservabilityClient, init

    # Quick start with global client
    client = init(
        api_endpoint="https://observability.example.com",
        api_key="your-api-key",
        agent_id="my-agent",
    )

    # Use the tracer
    with client.tracer.start_execution() as execution:
        with client.tracer.trace_llm_call(model="claude-sonnet-4") as llm_span:
            response = call_llm(...)
            llm_span.set_token_usage(input_tokens=100, output_tokens=50)

    # Shutdown when done
    client.shutdown()

For framework integrations:
    from genai_observability.integrations import LangChainCallbackHandler
    from genai_observability.integrations import CrewAICallbackHandler

For OpenTelemetry integration:
    from genai_observability.exporters import OTelExporter, setup_otel_tracing

For multi-region support:
    from genai_observability.multi_region import (
        create_multi_region_client,
        MultiRegionClient,
        RegionRouter,
    )
"""

__version__ = "0.1.0"
__author__ = "Platform Engineering Team"

# Core client
from .client import (
    ObservabilityClient,
    init,
    init_from_env,
    get_client,
    get_tracer,
    shutdown,
)

# Configuration
from .config import (
    ObservabilityConfig,
    RedactionConfig,
    BatchConfig,
    RetryConfig,
)

# Tracer
from .tracer import (
    Tracer,
    ExecutionSpan,
    LLMSpan,
    ToolSpan,
    MCPSpan,
    trace_function,
)

# Models
from .models import (
    EventType,
    Severity,
    TokenUsage,
    SpanContext,
    BaseEvent,
    ExecutionStartEvent,
    ExecutionEndEvent,
    LLMCallStartEvent,
    LLMCallEndEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    MCPCallStartEvent,
    MCPCallEndEvent,
    ErrorEvent,
    MetricEvent,
    LogEvent,
)

# Exporters
from .exporters import (
    HTTPExporter,
    OTelExporter,
    OTelBridgeExporter,
    OTelExporterConfig,
    setup_otel_tracing,
)

# Multi-Region Support
from .multi_region import (
    RegionConfig,
    RegionHealth,
    RegionStatus,
    RoutingStrategy,
    MultiRegionConfig,
    RegionRouter,
    MultiRegionClient,
    create_multi_region_client,
)

__all__ = [
    # Version
    "__version__",
    # Client
    "ObservabilityClient",
    "init",
    "init_from_env",
    "get_client",
    "get_tracer",
    "shutdown",
    # Configuration
    "ObservabilityConfig",
    "RedactionConfig",
    "BatchConfig",
    "RetryConfig",
    # Tracer
    "Tracer",
    "ExecutionSpan",
    "LLMSpan",
    "ToolSpan",
    "MCPSpan",
    "trace_function",
    # Models
    "EventType",
    "Severity",
    "TokenUsage",
    "SpanContext",
    "BaseEvent",
    "ExecutionStartEvent",
    "ExecutionEndEvent",
    "LLMCallStartEvent",
    "LLMCallEndEvent",
    "ToolCallStartEvent",
    "ToolCallEndEvent",
    "MCPCallStartEvent",
    "MCPCallEndEvent",
    "ErrorEvent",
    "MetricEvent",
    "LogEvent",
    # Exporters
    "HTTPExporter",
    "OTelExporter",
    "OTelBridgeExporter",
    "OTelExporterConfig",
    "setup_otel_tracing",
    # Multi-Region
    "RegionConfig",
    "RegionHealth",
    "RegionStatus",
    "RoutingStrategy",
    "MultiRegionConfig",
    "RegionRouter",
    "MultiRegionClient",
    "create_multi_region_client",
]
