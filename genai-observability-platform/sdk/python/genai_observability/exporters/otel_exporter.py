"""
OpenTelemetry Exporter for GenAI Observability SDK.

This module provides integration with OpenTelemetry, allowing telemetry data
to be exported to any OTEL-compatible backend (Jaeger, Zipkin, OTLP, etc.).
"""

import logging
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# OpenTelemetry imports with graceful fallback
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
    from opentelemetry.sdk.trace.export import (
        SpanExporter,
        SpanExportResult,
        BatchSpanProcessor,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import (
        Span,
        SpanKind,
        Status,
        StatusCode,
        get_current_span,
        set_span_in_context,
    )
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.context import Context
    from opentelemetry.sdk.trace.export import ReadableSpan
    from opentelemetry.semconv.trace import SpanAttributes
    from opentelemetry.semconv.resource import ResourceAttributes

    # OTLP exporters
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPGrpcExporter
        OTLP_GRPC_AVAILABLE = True
    except ImportError:
        OTLP_GRPC_AVAILABLE = False

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHttpExporter
        OTLP_HTTP_AVAILABLE = True
    except ImportError:
        OTLP_HTTP_AVAILABLE = False

    # Jaeger exporter
    try:
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter
        JAEGER_AVAILABLE = True
    except ImportError:
        JAEGER_AVAILABLE = False

    # Zipkin exporter
    try:
        from opentelemetry.exporter.zipkin.json import ZipkinExporter
        ZIPKIN_AVAILABLE = True
    except ImportError:
        ZIPKIN_AVAILABLE = False

    OTEL_AVAILABLE = True

except ImportError:
    OTEL_AVAILABLE = False
    logger.warning(
        "OpenTelemetry not installed. Install with: pip install opentelemetry-api opentelemetry-sdk"
    )


class GenAISpanAttributes:
    """Semantic conventions for GenAI observability spans."""

    # LLM attributes
    LLM_SYSTEM = "gen_ai.system"
    LLM_REQUEST_MODEL = "gen_ai.request.model"
    LLM_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    LLM_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    LLM_REQUEST_TOP_P = "gen_ai.request.top_p"
    LLM_RESPONSE_ID = "gen_ai.response.id"
    LLM_RESPONSE_MODEL = "gen_ai.response.model"
    LLM_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
    LLM_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    LLM_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    LLM_USAGE_TOTAL_TOKENS = "gen_ai.usage.total_tokens"

    # Agent attributes
    AGENT_ID = "gen_ai.agent.id"
    AGENT_TYPE = "gen_ai.agent.type"
    AGENT_VERSION = "gen_ai.agent.version"
    EXECUTION_ID = "gen_ai.execution.id"

    # Tool attributes
    TOOL_NAME = "gen_ai.tool.name"
    TOOL_DESCRIPTION = "gen_ai.tool.description"

    # MCP attributes
    MCP_SERVER_NAME = "gen_ai.mcp.server_name"
    MCP_METHOD = "gen_ai.mcp.method"

    # Cost attributes
    COST_USD = "gen_ai.cost.usd"


class OTelExporter:
    """
    OpenTelemetry exporter for GenAI Observability SDK.

    Bridges the GenAI observability data model to OpenTelemetry spans,
    enabling export to any OTEL-compatible backend.

    Usage:
        from genai_observability.exporters.otel_exporter import OTelExporter

        # Create exporter with OTLP endpoint
        otel_exporter = OTelExporter(
            service_name="my-agent",
            otlp_endpoint="http://localhost:4317",
        )

        # Or with Jaeger
        otel_exporter = OTelExporter(
            service_name="my-agent",
            jaeger_host="localhost",
            jaeger_port=6831,
        )

        # Use with tracer
        config = ObservabilityConfig(...)
        tracer = Tracer(config, exporter=otel_exporter)
    """

    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: str = "development",
        # OTLP configuration
        otlp_endpoint: Optional[str] = None,
        otlp_protocol: str = "grpc",  # "grpc" or "http"
        otlp_headers: Optional[Dict[str, str]] = None,
        # Jaeger configuration
        jaeger_host: Optional[str] = None,
        jaeger_port: int = 6831,
        # Zipkin configuration
        zipkin_endpoint: Optional[str] = None,
        # Processing configuration
        batch_export: bool = True,
        max_queue_size: int = 2048,
        max_export_batch_size: int = 512,
        export_timeout_millis: int = 30000,
        # Additional resource attributes
        resource_attributes: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the OpenTelemetry exporter.

        Args:
            service_name: Name of the service for OTEL resource
            service_version: Version of the service
            environment: Deployment environment
            otlp_endpoint: OTLP collector endpoint
            otlp_protocol: OTLP protocol ("grpc" or "http")
            otlp_headers: Headers to send with OTLP requests
            jaeger_host: Jaeger agent host
            jaeger_port: Jaeger agent port
            zipkin_endpoint: Zipkin collector endpoint
            batch_export: Whether to batch exports
            max_queue_size: Maximum queue size for batch processor
            max_export_batch_size: Maximum batch size for export
            export_timeout_millis: Export timeout in milliseconds
            resource_attributes: Additional resource attributes
        """
        if not OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry is not installed. Install with: "
                "pip install opentelemetry-api opentelemetry-sdk"
            )

        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.batch_export = batch_export

        # Create resource
        resource_attrs = {
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: service_version,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: environment,
        }
        if resource_attributes:
            resource_attrs.update(resource_attributes)

        self.resource = Resource.create(resource_attrs)

        # Create exporter based on configuration
        self.span_exporter = self._create_span_exporter(
            otlp_endpoint=otlp_endpoint,
            otlp_protocol=otlp_protocol,
            otlp_headers=otlp_headers,
            jaeger_host=jaeger_host,
            jaeger_port=jaeger_port,
            zipkin_endpoint=zipkin_endpoint,
        )

        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=self.resource)

        # Add span processor
        if batch_export and self.span_exporter:
            processor = BatchSpanProcessor(
                self.span_exporter,
                max_queue_size=max_queue_size,
                max_export_batch_size=max_export_batch_size,
                export_timeout_millis=export_timeout_millis,
            )
        elif self.span_exporter:
            processor = SimpleSpanProcessor(self.span_exporter)
        else:
            processor = None

        if processor:
            self.tracer_provider.add_span_processor(processor)

        # Set as global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer
        self.tracer = trace.get_tracer(
            instrumenting_module_name="genai-observability",
            instrumenting_library_version=service_version,
        )

        # Track active spans for correlation
        self._active_spans: Dict[str, Span] = {}

        # Propagator for distributed tracing
        self.propagator = TraceContextTextMapPropagator()

        logger.info(f"OTelExporter initialized for service: {service_name}")

    def _create_span_exporter(
        self,
        otlp_endpoint: Optional[str],
        otlp_protocol: str,
        otlp_headers: Optional[Dict[str, str]],
        jaeger_host: Optional[str],
        jaeger_port: int,
        zipkin_endpoint: Optional[str],
    ) -> Optional[SpanExporter]:
        """Create the appropriate span exporter based on configuration."""

        # OTLP exporter (preferred)
        if otlp_endpoint:
            if otlp_protocol == "grpc" and OTLP_GRPC_AVAILABLE:
                logger.info(f"Using OTLP gRPC exporter: {otlp_endpoint}")
                return OTLPGrpcExporter(
                    endpoint=otlp_endpoint,
                    headers=otlp_headers,
                )
            elif otlp_protocol == "http" and OTLP_HTTP_AVAILABLE:
                logger.info(f"Using OTLP HTTP exporter: {otlp_endpoint}")
                return OTLPHttpExporter(
                    endpoint=otlp_endpoint,
                    headers=otlp_headers,
                )
            else:
                logger.warning(
                    f"OTLP {otlp_protocol} exporter not available. "
                    f"Install with: pip install opentelemetry-exporter-otlp-proto-{otlp_protocol}"
                )

        # Jaeger exporter
        if jaeger_host and JAEGER_AVAILABLE:
            logger.info(f"Using Jaeger exporter: {jaeger_host}:{jaeger_port}")
            return JaegerExporter(
                agent_host_name=jaeger_host,
                agent_port=jaeger_port,
            )
        elif jaeger_host:
            logger.warning(
                "Jaeger exporter not available. "
                "Install with: pip install opentelemetry-exporter-jaeger"
            )

        # Zipkin exporter
        if zipkin_endpoint and ZIPKIN_AVAILABLE:
            logger.info(f"Using Zipkin exporter: {zipkin_endpoint}")
            return ZipkinExporter(endpoint=zipkin_endpoint)
        elif zipkin_endpoint:
            logger.warning(
                "Zipkin exporter not available. "
                "Install with: pip install opentelemetry-exporter-zipkin"
            )

        logger.warning("No span exporter configured, spans will not be exported")
        return None

    def export(self, event: Any) -> None:
        """
        Export a GenAI observability event as an OpenTelemetry span.

        Args:
            event: GenAI observability event
        """
        event_dict = event.to_dict() if hasattr(event, "to_dict") else event
        event_type = event_dict.get("event_type", "")

        # Handle different event types
        if event_type.endswith("_start"):
            self._start_span(event_dict)
        elif event_type.endswith("_end"):
            self._end_span(event_dict)
        elif event_type == "error":
            self._record_error(event_dict)
        elif event_type == "metric":
            self._record_metric(event_dict)
        elif event_type == "log":
            self._record_log(event_dict)

    def _start_span(self, event: Dict[str, Any]) -> None:
        """Start a new span for a start event."""
        event_type = event.get("event_type", "")
        span_id = event.get("span_id", "")

        # Determine span name and kind
        if "execution" in event_type:
            span_name = f"agent.execution"
            span_kind = SpanKind.SERVER
        elif "llm_call" in event_type:
            span_name = f"llm.{event.get('provider', 'unknown')}.{event.get('model', 'unknown')}"
            span_kind = SpanKind.CLIENT
        elif "tool_call" in event_type:
            span_name = f"tool.{event.get('tool_name', 'unknown')}"
            span_kind = SpanKind.INTERNAL
        elif "mcp_call" in event_type:
            span_name = f"mcp.{event.get('server_name', 'unknown')}.{event.get('method', 'unknown')}"
            span_kind = SpanKind.CLIENT
        else:
            span_name = event_type
            span_kind = SpanKind.INTERNAL

        # Create span
        span = self.tracer.start_span(
            name=span_name,
            kind=span_kind,
            attributes=self._extract_attributes(event),
        )

        # Store span for later completion
        if span_id:
            self._active_spans[span_id] = span

    def _end_span(self, event: Dict[str, Any]) -> None:
        """End an existing span for an end event."""
        span_id = event.get("span_id", "")
        span = self._active_spans.pop(span_id, None)

        if not span:
            # No matching start event, create and immediately end span
            logger.debug(f"No matching start span for {span_id}")
            return

        # Add end event attributes
        self._add_end_attributes(span, event)

        # Set status based on success
        if event.get("success", True):
            span.set_status(Status(StatusCode.OK))
        else:
            error_message = event.get("error_message", "Unknown error")
            span.set_status(Status(StatusCode.ERROR, error_message))

        # End the span
        span.end()

    def _record_error(self, event: Dict[str, Any]) -> None:
        """Record an error event."""
        current_span = get_current_span()
        if current_span:
            current_span.record_exception(
                Exception(event.get("error_message", "Unknown error")),
                attributes={
                    "error.type": event.get("error_type", "Error"),
                    "error.stack_trace": event.get("stack_trace", ""),
                },
            )
            current_span.set_status(
                Status(StatusCode.ERROR, event.get("error_message", ""))
            )

    def _record_metric(self, event: Dict[str, Any]) -> None:
        """Record a metric event as span event."""
        current_span = get_current_span()
        if current_span:
            current_span.add_event(
                name=f"metric.{event.get('metric_name', 'unknown')}",
                attributes={
                    "metric.value": event.get("metric_value", 0),
                    "metric.unit": event.get("unit", ""),
                    **(event.get("dimensions", {})),
                },
            )

    def _record_log(self, event: Dict[str, Any]) -> None:
        """Record a log event as span event."""
        current_span = get_current_span()
        if current_span:
            current_span.add_event(
                name="log",
                attributes={
                    "log.severity": event.get("severity", "info"),
                    "log.message": event.get("message", ""),
                },
            )

    def _extract_attributes(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Extract OpenTelemetry attributes from a GenAI event."""
        attributes = {}

        # Agent attributes
        if event.get("agent_id"):
            attributes[GenAISpanAttributes.AGENT_ID] = event["agent_id"]
        if event.get("agent_type"):
            attributes[GenAISpanAttributes.AGENT_TYPE] = event["agent_type"]
        if event.get("agent_version"):
            attributes[GenAISpanAttributes.AGENT_VERSION] = event["agent_version"]
        if event.get("execution_id"):
            attributes[GenAISpanAttributes.EXECUTION_ID] = event["execution_id"]

        # LLM attributes
        if event.get("model"):
            attributes[GenAISpanAttributes.LLM_REQUEST_MODEL] = event["model"]
        if event.get("provider"):
            attributes[GenAISpanAttributes.LLM_SYSTEM] = event["provider"]
        if event.get("max_tokens"):
            attributes[GenAISpanAttributes.LLM_REQUEST_MAX_TOKENS] = event["max_tokens"]
        if event.get("temperature") is not None:
            attributes[GenAISpanAttributes.LLM_REQUEST_TEMPERATURE] = event["temperature"]

        # Tool attributes
        if event.get("tool_name"):
            attributes[GenAISpanAttributes.TOOL_NAME] = event["tool_name"]

        # MCP attributes
        if event.get("server_name"):
            attributes[GenAISpanAttributes.MCP_SERVER_NAME] = event["server_name"]
        if event.get("method"):
            attributes[GenAISpanAttributes.MCP_METHOD] = event["method"]

        # Environment
        if event.get("environment"):
            attributes[ResourceAttributes.DEPLOYMENT_ENVIRONMENT] = event["environment"]

        return attributes

    def _add_end_attributes(self, span: Span, event: Dict[str, Any]) -> None:
        """Add attributes from an end event to a span."""
        # Duration
        if event.get("duration_ms"):
            span.set_attribute("duration_ms", event["duration_ms"])

        # Token usage
        token_usage = event.get("token_usage", {})
        if token_usage:
            if token_usage.get("input_tokens"):
                span.set_attribute(
                    GenAISpanAttributes.LLM_USAGE_INPUT_TOKENS,
                    token_usage["input_tokens"],
                )
            if token_usage.get("output_tokens"):
                span.set_attribute(
                    GenAISpanAttributes.LLM_USAGE_OUTPUT_TOKENS,
                    token_usage["output_tokens"],
                )
            if token_usage.get("total_tokens"):
                span.set_attribute(
                    GenAISpanAttributes.LLM_USAGE_TOTAL_TOKENS,
                    token_usage["total_tokens"],
                )

        # Cost
        if event.get("cost"):
            span.set_attribute(GenAISpanAttributes.COST_USD, event["cost"])

    def inject_context(self, carrier: Dict[str, str]) -> None:
        """
        Inject trace context into a carrier for distributed tracing.

        Args:
            carrier: Dictionary to inject context into (e.g., HTTP headers)
        """
        self.propagator.inject(carrier)

    def extract_context(self, carrier: Dict[str, str]) -> Context:
        """
        Extract trace context from a carrier.

        Args:
            carrier: Dictionary containing trace context

        Returns:
            OpenTelemetry context
        """
        return self.propagator.extract(carrier)

    def flush(self) -> None:
        """Flush any pending spans."""
        if self.tracer_provider:
            self.tracer_provider.force_flush()

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        # End any remaining active spans
        for span_id, span in list(self._active_spans.items()):
            span.set_status(Status(StatusCode.ERROR, "Span not properly closed"))
            span.end()

        self._active_spans.clear()

        if self.tracer_provider:
            self.tracer_provider.shutdown()

        logger.info("OTelExporter shutdown complete")


class OTelBridgeExporter:
    """
    Bridge exporter that sends to both GenAI observability backend
    and OpenTelemetry simultaneously.

    Usage:
        from genai_observability.exporters.http_exporter import HTTPExporter
        from genai_observability.exporters.otel_exporter import OTelBridgeExporter

        http_exporter = HTTPExporter(config)
        otel_exporter = OTelExporter(service_name="my-agent", otlp_endpoint="...")

        bridge = OTelBridgeExporter(http_exporter, otel_exporter)
        tracer = Tracer(config, exporter=bridge)
    """

    def __init__(
        self,
        primary_exporter: Any,
        otel_exporter: OTelExporter,
    ):
        """
        Initialize the bridge exporter.

        Args:
            primary_exporter: Primary exporter (usually HTTPExporter)
            otel_exporter: OpenTelemetry exporter
        """
        self.primary_exporter = primary_exporter
        self.otel_exporter = otel_exporter

    def export(self, event: Any) -> None:
        """Export to both backends."""
        # Export to primary backend
        if self.primary_exporter:
            try:
                self.primary_exporter.export(event)
            except Exception as e:
                logger.error(f"Error exporting to primary backend: {e}")

        # Export to OpenTelemetry
        if self.otel_exporter:
            try:
                self.otel_exporter.export(event)
            except Exception as e:
                logger.error(f"Error exporting to OpenTelemetry: {e}")

    def flush(self) -> None:
        """Flush both exporters."""
        if self.primary_exporter and hasattr(self.primary_exporter, "flush"):
            self.primary_exporter.flush()
        if self.otel_exporter:
            self.otel_exporter.flush()

    def shutdown(self) -> None:
        """Shutdown both exporters."""
        if self.primary_exporter and hasattr(self.primary_exporter, "shutdown"):
            self.primary_exporter.shutdown()
        if self.otel_exporter:
            self.otel_exporter.shutdown()


# Convenience function for quick setup
def setup_otel_tracing(
    service_name: str,
    otlp_endpoint: Optional[str] = None,
    jaeger_host: Optional[str] = None,
    zipkin_endpoint: Optional[str] = None,
    **kwargs,
) -> OTelExporter:
    """
    Convenience function to set up OpenTelemetry tracing.

    Args:
        service_name: Name of the service
        otlp_endpoint: OTLP collector endpoint
        jaeger_host: Jaeger agent host
        zipkin_endpoint: Zipkin collector endpoint
        **kwargs: Additional arguments for OTelExporter

    Returns:
        Configured OTelExporter instance
    """
    return OTelExporter(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        jaeger_host=jaeger_host,
        zipkin_endpoint=zipkin_endpoint,
        **kwargs,
    )
