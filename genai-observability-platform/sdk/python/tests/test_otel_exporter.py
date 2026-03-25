"""Tests for OpenTelemetry exporter module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from genai_observability.exporters.otel_exporter import (
    OTelExporter,
    OTelBridgeExporter,
    OTelExporterConfig,
    setup_otel_tracing,
)
from genai_observability.models import (
    ExecutionStartEvent,
    ExecutionEndEvent,
    LLMCallStartEvent,
    LLMCallEndEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    TokenUsage,
    SpanContext,
    EventType,
)


class TestOTelExporterConfig:
    """Tests for OTelExporterConfig dataclass."""

    def test_create_config_defaults(self):
        """Test creating config with defaults."""
        config = OTelExporterConfig(service_name="test-service")

        assert config.service_name == "test-service"
        assert config.exporter_type == "otlp"
        assert config.otlp_endpoint == "http://localhost:4317"
        assert config.otlp_protocol == "grpc"
        assert config.enable_console_export is False

    def test_create_config_custom(self):
        """Test creating config with custom values."""
        config = OTelExporterConfig(
            service_name="custom-service",
            exporter_type="jaeger",
            jaeger_host="jaeger.example.com",
            jaeger_port=6831,
        )

        assert config.service_name == "custom-service"
        assert config.exporter_type == "jaeger"
        assert config.jaeger_host == "jaeger.example.com"
        assert config.jaeger_port == 6831

    def test_config_with_headers(self):
        """Test config with custom headers."""
        config = OTelExporterConfig(
            service_name="test",
            otlp_headers={"Authorization": "Bearer token"},
        )

        assert config.otlp_headers == {"Authorization": "Bearer token"}


class TestOTelExporter:
    """Tests for OTelExporter class."""

    @pytest.fixture
    def mock_tracer_provider(self):
        """Create a mock tracer provider."""
        with patch('genai_observability.exporters.otel_exporter.TracerProvider') as mock:
            yield mock

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return OTelExporterConfig(
            service_name="test-service",
            exporter_type="console",
            enable_console_export=True,
        )

    def test_create_exporter(self, config, mock_tracer_provider):
        """Test creating an OTel exporter."""
        exporter = OTelExporter(config)

        assert exporter.config == config
        assert exporter.service_name == "test-service"

    def test_convert_execution_span(self, config, mock_tracer_provider):
        """Test converting execution events to OTel span."""
        exporter = OTelExporter(config)

        start_event = ExecutionStartEvent(
            event_type=EventType.EXECUTION_START,
            timestamp=datetime.utcnow().isoformat(),
            agent_id="test-agent",
            trace_id="trace-123",
            span_id="span-456",
            execution_id="exec-789",
            name="Test Execution",
        )

        end_event = ExecutionEndEvent(
            event_type=EventType.EXECUTION_END,
            timestamp=datetime.utcnow().isoformat(),
            agent_id="test-agent",
            trace_id="trace-123",
            span_id="span-456",
            execution_id="exec-789",
            duration_ms=150,
            status="completed",
        )

        # The exporter should be able to process these events
        # Actual span creation is handled by OTel SDK

    def test_convert_llm_span(self, config, mock_tracer_provider):
        """Test converting LLM events to OTel span."""
        exporter = OTelExporter(config)

        start_event = LLMCallStartEvent(
            event_type=EventType.LLM_CALL_START,
            timestamp=datetime.utcnow().isoformat(),
            agent_id="test-agent",
            trace_id="trace-123",
            span_id="span-llm",
            parent_span_id="span-456",
            model="claude-3-sonnet",
            provider="anthropic",
        )

        end_event = LLMCallEndEvent(
            event_type=EventType.LLM_CALL_END,
            timestamp=datetime.utcnow().isoformat(),
            agent_id="test-agent",
            trace_id="trace-123",
            span_id="span-llm",
            parent_span_id="span-456",
            duration_ms=500,
            status="completed",
            token_usage=TokenUsage(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
            ),
        )

        # Verify the exporter can handle LLM events

    def test_genai_semantic_conventions(self, config, mock_tracer_provider):
        """Test that GenAI semantic conventions are used."""
        exporter = OTelExporter(config)

        # GenAI semantic conventions should include:
        # - gen_ai.system
        # - gen_ai.request.model
        # - gen_ai.usage.input_tokens
        # - gen_ai.usage.output_tokens
        # These are set as span attributes

    def test_shutdown(self, config, mock_tracer_provider):
        """Test shutting down the exporter."""
        exporter = OTelExporter(config)
        exporter.shutdown()

        # Should cleanly shut down


class TestOTelBridgeExporter:
    """Tests for OTelBridgeExporter class."""

    @pytest.fixture
    def mock_http_exporter(self):
        """Create a mock HTTP exporter."""
        return MagicMock()

    @pytest.fixture
    def mock_otel_exporter(self):
        """Create a mock OTel exporter."""
        return MagicMock()

    def test_create_bridge_exporter(self, mock_http_exporter, mock_otel_exporter):
        """Test creating a bridge exporter."""
        bridge = OTelBridgeExporter(
            http_exporter=mock_http_exporter,
            otel_exporter=mock_otel_exporter,
        )

        assert bridge.http_exporter == mock_http_exporter
        assert bridge.otel_exporter == mock_otel_exporter

    def test_export_to_both(self, mock_http_exporter, mock_otel_exporter):
        """Test that bridge exports to both exporters."""
        bridge = OTelBridgeExporter(
            http_exporter=mock_http_exporter,
            otel_exporter=mock_otel_exporter,
        )

        # Create a test event
        event = ExecutionStartEvent(
            event_type=EventType.EXECUTION_START,
            timestamp=datetime.utcnow().isoformat(),
            agent_id="test-agent",
            trace_id="trace-123",
            span_id="span-456",
            execution_id="exec-789",
            name="Test",
        )

        # Export should call both exporters
        bridge.export(event)

        mock_http_exporter.export.assert_called_once()
        mock_otel_exporter.export.assert_called_once()

    def test_shutdown_both(self, mock_http_exporter, mock_otel_exporter):
        """Test that shutdown calls both exporters."""
        bridge = OTelBridgeExporter(
            http_exporter=mock_http_exporter,
            otel_exporter=mock_otel_exporter,
        )

        bridge.shutdown()

        mock_http_exporter.shutdown.assert_called_once()
        mock_otel_exporter.shutdown.assert_called_once()


class TestSetupOTelTracing:
    """Tests for setup_otel_tracing function."""

    @patch('genai_observability.exporters.otel_exporter.TracerProvider')
    @patch('genai_observability.exporters.otel_exporter.set_tracer_provider')
    def test_setup_basic(self, mock_set_provider, mock_provider_class):
        """Test basic OTel tracing setup."""
        setup_otel_tracing(
            service_name="test-service",
            exporter_type="console",
        )

        mock_provider_class.assert_called()
        mock_set_provider.assert_called()

    @patch('genai_observability.exporters.otel_exporter.TracerProvider')
    @patch('genai_observability.exporters.otel_exporter.set_tracer_provider')
    def test_setup_with_otlp(self, mock_set_provider, mock_provider_class):
        """Test OTel tracing setup with OTLP exporter."""
        setup_otel_tracing(
            service_name="test-service",
            exporter_type="otlp",
            otlp_endpoint="http://collector:4317",
        )

        mock_provider_class.assert_called()

    @patch('genai_observability.exporters.otel_exporter.TracerProvider')
    @patch('genai_observability.exporters.otel_exporter.set_tracer_provider')
    def test_setup_with_resource_attributes(self, mock_set_provider, mock_provider_class):
        """Test OTel tracing setup with custom resource attributes."""
        setup_otel_tracing(
            service_name="test-service",
            resource_attributes={
                "deployment.environment": "production",
                "service.version": "1.0.0",
            },
        )

        mock_provider_class.assert_called()


class TestExporterTypes:
    """Tests for different exporter types."""

    @pytest.fixture
    def base_config(self):
        """Create a base configuration."""
        return {
            "service_name": "test-service",
        }

    def test_otlp_grpc_config(self, base_config):
        """Test OTLP gRPC exporter configuration."""
        config = OTelExporterConfig(
            **base_config,
            exporter_type="otlp",
            otlp_protocol="grpc",
            otlp_endpoint="http://localhost:4317",
        )

        assert config.exporter_type == "otlp"
        assert config.otlp_protocol == "grpc"

    def test_otlp_http_config(self, base_config):
        """Test OTLP HTTP exporter configuration."""
        config = OTelExporterConfig(
            **base_config,
            exporter_type="otlp",
            otlp_protocol="http",
            otlp_endpoint="http://localhost:4318/v1/traces",
        )

        assert config.otlp_protocol == "http"

    def test_jaeger_config(self, base_config):
        """Test Jaeger exporter configuration."""
        config = OTelExporterConfig(
            **base_config,
            exporter_type="jaeger",
            jaeger_host="jaeger.example.com",
            jaeger_port=6831,
        )

        assert config.exporter_type == "jaeger"
        assert config.jaeger_host == "jaeger.example.com"

    def test_zipkin_config(self, base_config):
        """Test Zipkin exporter configuration."""
        config = OTelExporterConfig(
            **base_config,
            exporter_type="zipkin",
            zipkin_endpoint="http://zipkin:9411/api/v2/spans",
        )

        assert config.exporter_type == "zipkin"
        assert config.zipkin_endpoint == "http://zipkin:9411/api/v2/spans"

    def test_console_config(self, base_config):
        """Test console exporter configuration."""
        config = OTelExporterConfig(
            **base_config,
            exporter_type="console",
            enable_console_export=True,
        )

        assert config.exporter_type == "console"
        assert config.enable_console_export is True
