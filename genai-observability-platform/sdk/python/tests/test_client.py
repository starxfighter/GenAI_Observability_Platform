"""Tests for ObservabilityClient."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from genai_observability.client import ObservabilityClient, init, get_client, shutdown
from genai_observability.config import ObservabilityConfig
from genai_observability.models import ExecutionStartEvent, LLMResponseEvent


class TestObservabilityClient:
    """Tests for ObservabilityClient."""

    def test_client_initialization(self, config):
        """Test client initialization."""
        client = ObservabilityClient(config)
        assert client._config == config
        assert client._exporter is not None

    def test_record_event(self, client, execution_start_event, mock_exporter):
        """Test recording an event."""
        client.record(execution_start_event)
        mock_exporter.export.assert_called_once()

    def test_record_multiple_events(self, client, execution_start_event, execution_end_event, mock_exporter):
        """Test recording multiple events."""
        client.record(execution_start_event)
        client.record(execution_end_event)
        assert mock_exporter.export.call_count == 2

    def test_flush(self, client, mock_exporter):
        """Test flushing events."""
        client.flush()
        mock_exporter.flush.assert_called_once()

    def test_shutdown(self, client, mock_exporter):
        """Test client shutdown."""
        client.shutdown()
        mock_exporter.shutdown.assert_called_once()

    def test_context_manager(self, config, mock_exporter):
        """Test client as context manager."""
        with patch('genai_observability.client.HTTPExporter', return_value=mock_exporter):
            with ObservabilityClient(config) as client:
                assert client is not None
            mock_exporter.shutdown.assert_called_once()

    def test_get_tracer(self, client):
        """Test getting a tracer."""
        tracer = client.get_tracer()
        assert tracer is not None
        assert tracer._client == client


class TestGlobalClient:
    """Tests for global client functions."""

    def test_init_creates_client(self, config):
        """Test init creates a global client."""
        with patch('genai_observability.client.HTTPExporter'):
            client = init(config)
            assert client is not None
            assert get_client() == client
            shutdown()

    def test_get_client_raises_when_not_initialized(self):
        """Test get_client raises when not initialized."""
        # Reset global client
        import genai_observability.client as client_module
        client_module._global_client = None

        with pytest.raises(RuntimeError, match="Client not initialized"):
            get_client()

    def test_shutdown_cleans_up(self, config):
        """Test shutdown cleans up global client."""
        with patch('genai_observability.client.HTTPExporter'):
            init(config)
            shutdown()

            import genai_observability.client as client_module
            assert client_module._global_client is None

    def test_init_with_kwargs(self):
        """Test init with keyword arguments."""
        with patch('genai_observability.client.HTTPExporter'):
            client = init(
                endpoint="https://api.example.com",
                api_key="test-key",
                agent_id="test-agent",
            )
            assert client is not None
            assert client._config.endpoint == "https://api.example.com"
            shutdown()


class TestClientEventRecording:
    """Tests for client event recording helpers."""

    def test_record_execution_start(self, client, mock_exporter):
        """Test recording execution start."""
        client.record_execution_start(
            trace_id="trace-123",
            span_id="span-456",
            name="test-execution",
            input_data={"query": "test"},
        )
        mock_exporter.export.assert_called_once()
        event = mock_exporter.export.call_args[0][0]
        assert event.event_type == "execution_start"

    def test_record_execution_end(self, client, mock_exporter):
        """Test recording execution end."""
        client.record_execution_end(
            trace_id="trace-123",
            span_id="span-456",
            name="test-execution",
            output_data={"result": "success"},
            duration_ms=100,
            status="success",
        )
        mock_exporter.export.assert_called_once()
        event = mock_exporter.export.call_args[0][0]
        assert event.event_type == "execution_end"

    def test_record_llm_request(self, client, mock_exporter):
        """Test recording LLM request."""
        client.record_llm_request(
            trace_id="trace-123",
            span_id="span-456",
            model="claude-sonnet-4-20250514",
            provider="anthropic",
            messages=[{"role": "user", "content": "Hello"}],
        )
        mock_exporter.export.assert_called_once()
        event = mock_exporter.export.call_args[0][0]
        assert event.event_type == "llm_request"

    def test_record_llm_response(self, client, mock_exporter, token_usage):
        """Test recording LLM response."""
        client.record_llm_response(
            trace_id="trace-123",
            span_id="span-456",
            model="claude-sonnet-4-20250514",
            provider="anthropic",
            response_content="Hello!",
            token_usage=token_usage,
            duration_ms=500,
        )
        mock_exporter.export.assert_called_once()
        event = mock_exporter.export.call_args[0][0]
        assert event.event_type == "llm_response"

    def test_record_tool_call(self, client, mock_exporter):
        """Test recording tool call."""
        client.record_tool_call(
            trace_id="trace-123",
            span_id="span-456",
            tool_name="search",
            tool_input={"query": "test"},
            tool_output={"results": []},
            duration_ms=200,
        )
        mock_exporter.export.assert_called_once()
        event = mock_exporter.export.call_args[0][0]
        assert event.event_type == "tool_call"

    def test_record_error(self, client, mock_exporter):
        """Test recording error."""
        client.record_error(
            trace_id="trace-123",
            span_id="span-456",
            error_type="ValueError",
            error_message="Test error",
            stack_trace="Traceback...",
        )
        mock_exporter.export.assert_called_once()
        event = mock_exporter.export.call_args[0][0]
        assert event.event_type == "error"
