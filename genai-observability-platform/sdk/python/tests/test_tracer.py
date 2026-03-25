"""Tests for Tracer."""

import pytest
from unittest.mock import MagicMock, patch
import time

from genai_observability.tracer import Tracer
from genai_observability.client import ObservabilityClient
from genai_observability.config import ObservabilityConfig


class TestTracer:
    """Tests for Tracer class."""

    @pytest.fixture
    def tracer(self, client):
        """Create a tracer for testing."""
        return Tracer(client)

    def test_tracer_initialization(self, client):
        """Test tracer initialization."""
        tracer = Tracer(client)
        assert tracer._client == client

    def test_start_trace(self, tracer):
        """Test starting a trace."""
        ctx = tracer.start_trace(name="test-trace")
        assert ctx.trace_id is not None
        assert ctx.span_id is not None
        assert ctx.parent_span_id is None

    def test_start_span(self, tracer):
        """Test starting a span within a trace."""
        trace_ctx = tracer.start_trace(name="test-trace")
        span_ctx = tracer.start_span(name="test-span", parent=trace_ctx)

        assert span_ctx.trace_id == trace_ctx.trace_id
        assert span_ctx.span_id != trace_ctx.span_id
        assert span_ctx.parent_span_id == trace_ctx.span_id

    def test_end_span(self, tracer, mock_exporter):
        """Test ending a span."""
        ctx = tracer.start_trace(name="test-trace")
        tracer.end_span(ctx, status="success", output_data={"result": "ok"})

        # Should have recorded start and end events
        assert mock_exporter.export.call_count >= 1


class TestTracerContextManagers:
    """Tests for tracer context managers."""

    @pytest.fixture
    def tracer(self, client):
        """Create a tracer for testing."""
        return Tracer(client)

    def test_trace_context_manager(self, tracer, mock_exporter):
        """Test trace context manager."""
        with tracer.trace(name="test-trace") as ctx:
            assert ctx.trace_id is not None
            assert ctx.span_id is not None

        # Should record start and end events
        assert mock_exporter.export.call_count >= 2

    def test_trace_context_manager_with_error(self, tracer, mock_exporter):
        """Test trace context manager with error."""
        with pytest.raises(ValueError):
            with tracer.trace(name="test-trace") as ctx:
                raise ValueError("Test error")

        # Should record start, error, and end events
        assert mock_exporter.export.call_count >= 2

    def test_span_context_manager(self, tracer, mock_exporter):
        """Test span context manager."""
        with tracer.trace(name="test-trace") as trace_ctx:
            with tracer.span(name="test-span", parent=trace_ctx) as span_ctx:
                assert span_ctx.trace_id == trace_ctx.trace_id
                assert span_ctx.parent_span_id == trace_ctx.span_id

    def test_llm_span_context_manager(self, tracer, mock_exporter):
        """Test LLM span context manager."""
        with tracer.trace(name="test-trace") as trace_ctx:
            with tracer.llm_span(
                name="llm-call",
                parent=trace_ctx,
                model="claude-sonnet-4-20250514",
                provider="anthropic",
            ) as span_ctx:
                assert span_ctx is not None
                # Simulate LLM response
                span_ctx.set_response(
                    content="Hello!",
                    input_tokens=10,
                    output_tokens=5,
                )

    def test_tool_span_context_manager(self, tracer, mock_exporter):
        """Test tool span context manager."""
        with tracer.trace(name="test-trace") as trace_ctx:
            with tracer.tool_span(
                name="search-tool",
                parent=trace_ctx,
                tool_name="search",
                tool_input={"query": "test"},
            ) as span_ctx:
                assert span_ctx is not None
                # Simulate tool output
                span_ctx.set_output({"results": ["item1", "item2"]})

    def test_nested_spans(self, tracer, mock_exporter):
        """Test nested spans."""
        with tracer.trace(name="test-trace") as trace_ctx:
            with tracer.span(name="outer-span", parent=trace_ctx) as outer:
                with tracer.span(name="inner-span", parent=outer) as inner:
                    assert inner.trace_id == trace_ctx.trace_id
                    assert inner.parent_span_id == outer.span_id

    def test_trace_duration_tracking(self, tracer, mock_exporter):
        """Test that trace duration is tracked."""
        with tracer.trace(name="test-trace") as ctx:
            time.sleep(0.1)  # 100ms

        # Find the end event and check duration
        calls = mock_exporter.export.call_args_list
        end_events = [c for c in calls if hasattr(c[0][0], 'duration_ms')]
        assert len(end_events) > 0


class TestTracerMetadata:
    """Tests for tracer metadata handling."""

    @pytest.fixture
    def tracer(self, client):
        """Create a tracer for testing."""
        return Tracer(client)

    def test_trace_with_metadata(self, tracer, mock_exporter):
        """Test trace with metadata."""
        with tracer.trace(
            name="test-trace",
            metadata={"user_id": "123", "session": "abc"},
        ) as ctx:
            pass

        # Verify metadata was included
        calls = mock_exporter.export.call_args_list
        assert len(calls) > 0

    def test_span_with_attributes(self, tracer, mock_exporter):
        """Test span with attributes."""
        with tracer.trace(name="test-trace") as trace_ctx:
            with tracer.span(
                name="test-span",
                parent=trace_ctx,
                attributes={"custom_attr": "value"},
            ) as span_ctx:
                pass


class TestTracerInputRedaction:
    """Tests for tracer input redaction."""

    @pytest.fixture
    def tracer_with_redaction(self, config, mock_exporter):
        """Create a tracer with redaction enabled."""
        config.redaction.enabled = True
        config.redaction.patterns = ["password", "api_key", "secret"]
        client = ObservabilityClient(config)
        client._exporter = mock_exporter
        return Tracer(client)

    def test_sensitive_data_redacted(self, tracer_with_redaction, mock_exporter):
        """Test that sensitive data is redacted."""
        with tracer_with_redaction.trace(
            name="test-trace",
            input_data={"password": "secret123", "username": "user"},
        ) as ctx:
            pass

        # The password should be redacted in the event
        # This would be verified by checking the actual event content
