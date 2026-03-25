"""Tests for SDK models."""

import pytest
from datetime import datetime
from dataclasses import asdict

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


class TestTokenUsage:
    """Tests for TokenUsage model."""

    def test_create_token_usage(self):
        """Test creating token usage."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150

    def test_token_usage_to_dict(self):
        """Test converting token usage to dict."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        data = asdict(usage)
        assert data["input_tokens"] == 100
        assert data["output_tokens"] == 50
        assert data["total_tokens"] == 150

    def test_token_usage_with_cost(self):
        """Test token usage with cost."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost=0.0015,
        )
        assert usage.cost == 0.0015


class TestSpanContext:
    """Tests for SpanContext model."""

    def test_create_span_context(self):
        """Test creating span context."""
        ctx = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
        )
        assert ctx.trace_id == "trace-123"
        assert ctx.span_id == "span-456"
        assert ctx.parent_span_id is None

    def test_span_context_with_parent(self):
        """Test span context with parent."""
        ctx = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id="span-parent",
        )
        assert ctx.parent_span_id == "span-parent"


class TestExecutionEvents:
    """Tests for execution events."""

    def test_execution_start_event(self, execution_start_event):
        """Test execution start event."""
        assert execution_start_event.event_type == "execution_start"
        assert execution_start_event.agent_id == "test-agent"
        assert execution_start_event.name == "test-execution"
        assert execution_start_event.input_data == {"query": "test input"}

    def test_execution_end_event(self, execution_end_event):
        """Test execution end event."""
        assert execution_end_event.event_type == "execution_end"
        assert execution_end_event.status == "success"
        assert execution_end_event.duration_ms == 150
        assert execution_end_event.output_data == {"result": "test output"}

    def test_execution_event_to_dict(self, execution_start_event):
        """Test converting execution event to dict."""
        data = asdict(execution_start_event)
        assert data["event_type"] == "execution_start"
        assert data["agent_id"] == "test-agent"
        assert "timestamp" in data


class TestLLMEvents:
    """Tests for LLM events."""

    def test_llm_request_event(self, llm_request_event):
        """Test LLM request event."""
        assert llm_request_event.event_type == "llm_request"
        assert llm_request_event.model == "claude-sonnet-4-20250514"
        assert llm_request_event.provider == "anthropic"
        assert llm_request_event.temperature == 0.7
        assert len(llm_request_event.messages) == 1

    def test_llm_response_event(self, llm_response_event, token_usage):
        """Test LLM response event."""
        assert llm_response_event.event_type == "llm_response"
        assert llm_response_event.status == "success"
        assert llm_response_event.duration_ms == 500
        assert llm_response_event.token_usage.total_tokens == 150

    def test_llm_response_event_to_dict(self, llm_response_event):
        """Test converting LLM response event to dict."""
        data = asdict(llm_response_event)
        assert data["model"] == "claude-sonnet-4-20250514"
        assert data["token_usage"]["total_tokens"] == 150


class TestToolCallEvent:
    """Tests for tool call events."""

    def test_tool_call_event(self, tool_call_event):
        """Test tool call event."""
        assert tool_call_event.event_type == "tool_call"
        assert tool_call_event.tool_name == "search"
        assert tool_call_event.tool_input == {"query": "test search"}
        assert tool_call_event.status == "success"

    def test_tool_call_event_to_dict(self, tool_call_event):
        """Test converting tool call event to dict."""
        data = asdict(tool_call_event)
        assert data["tool_name"] == "search"
        assert data["duration_ms"] == 200


class TestErrorEvent:
    """Tests for error events."""

    def test_error_event(self, error_event):
        """Test error event."""
        assert error_event.event_type == "error"
        assert error_event.error_type == "ValueError"
        assert error_event.error_message == "Test error message"
        assert "Traceback" in error_event.stack_trace

    def test_error_event_to_dict(self, error_event):
        """Test converting error event to dict."""
        data = asdict(error_event)
        assert data["error_type"] == "ValueError"
        assert data["error_message"] == "Test error message"
