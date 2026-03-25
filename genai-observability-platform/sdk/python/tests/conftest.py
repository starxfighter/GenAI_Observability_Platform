"""Pytest fixtures for SDK tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from genai_observability.config import ObservabilityConfig, BatchConfig
from genai_observability.client import ObservabilityClient
from genai_observability.models import (
    TelemetryEvent,
    ExecutionStartEvent,
    ExecutionEndEvent,
    LLMRequestEvent,
    LLMResponseEvent,
    ToolCallEvent,
    ErrorEvent,
    TokenUsage,
    SpanContext,
)


@pytest.fixture
def config():
    """Create a test configuration."""
    return ObservabilityConfig(
        endpoint="https://test-api.example.com",
        api_key="test-api-key-123",
        agent_id="test-agent",
        agent_name="Test Agent",
        environment="test",
        batch=BatchConfig(
            max_size=10,
            max_wait_seconds=1.0,
        ),
    )


@pytest.fixture
def mock_exporter():
    """Create a mock exporter."""
    exporter = MagicMock()
    exporter.export = MagicMock(return_value=True)
    exporter.export_async = AsyncMock(return_value=True)
    exporter.flush = MagicMock()
    exporter.shutdown = MagicMock()
    return exporter


@pytest.fixture
def client(config, mock_exporter):
    """Create a test client with mock exporter."""
    client = ObservabilityClient(config)
    client._exporter = mock_exporter
    return client


@pytest.fixture
def span_context():
    """Create a test span context."""
    return SpanContext(
        trace_id="trace-123",
        span_id="span-456",
        parent_span_id=None,
    )


@pytest.fixture
def token_usage():
    """Create test token usage."""
    return TokenUsage(
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
    )


@pytest.fixture
def execution_start_event(span_context):
    """Create a test execution start event."""
    return ExecutionStartEvent(
        event_type="execution_start",
        timestamp=datetime.utcnow(),
        agent_id="test-agent",
        trace_id=span_context.trace_id,
        span_id=span_context.span_id,
        name="test-execution",
        input_data={"query": "test input"},
    )


@pytest.fixture
def execution_end_event(span_context):
    """Create a test execution end event."""
    return ExecutionEndEvent(
        event_type="execution_end",
        timestamp=datetime.utcnow(),
        agent_id="test-agent",
        trace_id=span_context.trace_id,
        span_id=span_context.span_id,
        name="test-execution",
        output_data={"result": "test output"},
        duration_ms=150,
        status="success",
    )


@pytest.fixture
def llm_request_event(span_context):
    """Create a test LLM request event."""
    return LLMRequestEvent(
        event_type="llm_request",
        timestamp=datetime.utcnow(),
        agent_id="test-agent",
        trace_id=span_context.trace_id,
        span_id=span_context.span_id,
        model="claude-sonnet-4-20250514",
        provider="anthropic",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
        max_tokens=1000,
    )


@pytest.fixture
def llm_response_event(span_context, token_usage):
    """Create a test LLM response event."""
    return LLMResponseEvent(
        event_type="llm_response",
        timestamp=datetime.utcnow(),
        agent_id="test-agent",
        trace_id=span_context.trace_id,
        span_id=span_context.span_id,
        model="claude-sonnet-4-20250514",
        provider="anthropic",
        response_content="Hello! How can I help?",
        token_usage=token_usage,
        duration_ms=500,
        status="success",
    )


@pytest.fixture
def tool_call_event(span_context):
    """Create a test tool call event."""
    return ToolCallEvent(
        event_type="tool_call",
        timestamp=datetime.utcnow(),
        agent_id="test-agent",
        trace_id=span_context.trace_id,
        span_id=span_context.span_id,
        tool_name="search",
        tool_input={"query": "test search"},
        tool_output={"results": []},
        duration_ms=200,
        status="success",
    )


@pytest.fixture
def error_event(span_context):
    """Create a test error event."""
    return ErrorEvent(
        event_type="error",
        timestamp=datetime.utcnow(),
        agent_id="test-agent",
        trace_id=span_context.trace_id,
        span_id=span_context.span_id,
        error_type="ValueError",
        error_message="Test error message",
        stack_trace="Traceback...",
    )
