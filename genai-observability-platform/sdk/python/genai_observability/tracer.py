"""
Tracer for GenAI agent execution tracing.
"""

import contextvars
import functools
import logging
import re
import sys
import time
import traceback
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from .config import ObservabilityConfig
from .exporters.http_exporter import HTTPExporter
from .models import (
    BaseEvent,
    ErrorEvent,
    ExecutionEndEvent,
    ExecutionStartEvent,
    LLMCallEndEvent,
    LLMCallStartEvent,
    LogEvent,
    MCPCallEndEvent,
    MCPCallStartEvent,
    MetricEvent,
    Severity,
    SpanContext,
    TokenUsage,
    ToolCallEndEvent,
    ToolCallStartEvent,
)

logger = logging.getLogger(__name__)

# Context variable for current span
_current_span: contextvars.ContextVar[Optional[SpanContext]] = contextvars.ContextVar(
    "current_span", default=None
)

# Context variable for current execution
_current_execution: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_execution", default=None
)

T = TypeVar("T")


class Tracer:
    """
    Main tracer class for capturing observability data.

    Usage:
        tracer = Tracer(config)

        with tracer.start_execution() as execution_id:
            with tracer.trace_llm_call(model="claude-sonnet-4") as span:
                # Make LLM call
                response = llm.invoke(prompt)
                span.set_token_usage(input=100, output=50)
                span.set_response(response)
    """

    def __init__(self, config: ObservabilityConfig, exporter: Optional[HTTPExporter] = None):
        self.config = config
        self.exporter = exporter or HTTPExporter(config)
        self._redaction_patterns: List[re.Pattern] = []

        # Compile redaction patterns
        self._compile_redaction_patterns()

    def _compile_redaction_patterns(self):
        """Compile regex patterns for redaction."""
        patterns = []

        if self.config.redaction.redact_pii:
            patterns.extend(self.config.redaction.pii_patterns)

        patterns.extend(self.config.redaction.redact_patterns)

        self._redaction_patterns = [re.compile(p) for p in patterns]

    def _redact(self, text: Optional[str]) -> Optional[str]:
        """Redact sensitive information from text."""
        if text is None:
            return None

        result = text
        for pattern in self._redaction_patterns:
            result = pattern.sub("[REDACTED]", result)

        return result

    def _should_sample(self) -> bool:
        """Check if this event should be sampled."""
        import random
        return random.random() < self.config.sampling_rate

    def _get_current_span(self) -> Optional[SpanContext]:
        """Get the current span context."""
        return _current_span.get()

    def _get_current_execution(self) -> Optional[str]:
        """Get the current execution ID."""
        return _current_execution.get()

    def _set_event_context(self, event: BaseEvent):
        """Set common context on an event."""
        event.agent_id = self.config.agent_id

        execution_id = self._get_current_execution()
        if execution_id:
            event.execution_id = execution_id

        span = self._get_current_span()
        if span:
            event.trace_id = span.trace_id
            event.span_id = span.span_id
            event.parent_span_id = span.parent_span_id

    def _emit(self, event: BaseEvent):
        """Emit an event to the exporter."""
        if not self.config.enabled:
            return

        if not self._should_sample():
            return

        self._set_event_context(event)
        self.exporter.export(event)

        if self.config.debug:
            logger.debug(f"Emitted event: {event.event_type.value}")

    @contextmanager
    def start_execution(
        self,
        input_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Start a new agent execution trace.

        Args:
            input_data: Input data for the execution
            metadata: Additional metadata

        Yields:
            ExecutionSpan: A span object to set execution results
        """
        execution_id = str(uuid.uuid4())
        span_context = SpanContext()

        # Set context vars
        execution_token = _current_execution.set(execution_id)
        span_token = _current_span.set(span_context)

        start_time = time.time()

        # Emit start event
        start_event = ExecutionStartEvent(
            execution_id=execution_id,
            agent_type=self.config.agent_type,
            agent_version=self.config.agent_version,
            input_data=input_data,
            metadata=metadata or {},
        )
        self._emit(start_event)

        # Create span object for user to set results
        span = ExecutionSpan(tracer=self, execution_id=execution_id)

        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Emit end event
            end_event = ExecutionEndEvent(
                execution_id=execution_id,
                duration_ms=duration_ms,
                success=not span._error_occurred,
                output_data=span._output_data,
                total_tokens=span._total_tokens,
                total_cost=span._total_cost,
                error_message=span._error_message,
                metadata=metadata or {},
            )
            self._emit(end_event)

            # Reset context vars
            _current_execution.reset(execution_token)
            _current_span.reset(span_token)

    @contextmanager
    def trace_llm_call(
        self,
        model: str,
        provider: str = "anthropic",
        prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Trace an LLM call.

        Args:
            model: Model name (e.g., "claude-sonnet-4")
            provider: Provider name (e.g., "anthropic", "openai")
            prompt: The prompt text (will be redacted if configured)
            messages: Message list for chat models
            temperature: Temperature setting
            max_tokens: Max tokens setting
            metadata: Additional metadata

        Yields:
            LLMSpan: A span object to set LLM call results
        """
        parent_span = self._get_current_span()
        span_context = parent_span.child() if parent_span else SpanContext()
        span_token = _current_span.set(span_context)

        start_time = time.time()

        # Redact prompt if configured
        redacted_prompt = None
        if prompt and not self.config.redaction.redact_prompts:
            redacted_prompt = self._redact(prompt)

        # Emit start event
        start_event = LLMCallStartEvent(
            model=model,
            provider=provider,
            prompt=redacted_prompt,
            messages=messages if not self.config.redaction.redact_prompts else None,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata or {},
        )
        self._emit(start_event)

        span = LLMSpan(tracer=self, model=model, provider=provider)

        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # Calculate cost
            cost = 0.0
            if span._token_usage:
                cost = self.config.calculate_cost(
                    model,
                    span._token_usage.input_tokens,
                    span._token_usage.output_tokens,
                )

            # Redact response if configured
            redacted_response = None
            if span._response and not self.config.redaction.redact_responses:
                redacted_response = self._redact(span._response)

            end_event = LLMCallEndEvent(
                model=model,
                provider=provider,
                duration_ms=duration_ms,
                success=not span._error_occurred,
                token_usage=span._token_usage,
                response=redacted_response,
                error_message=span._error_message,
                cost=cost,
                metadata=metadata or {},
            )
            self._emit(end_event)

            _current_span.reset(span_token)

    @contextmanager
    def trace_tool_call(
        self,
        tool_name: str,
        tool_input: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Trace a tool call.

        Args:
            tool_name: Name of the tool
            tool_input: Input to the tool
            metadata: Additional metadata

        Yields:
            ToolSpan: A span object to set tool call results
        """
        parent_span = self._get_current_span()
        span_context = parent_span.child() if parent_span else SpanContext()
        span_token = _current_span.set(span_context)

        start_time = time.time()

        # Redact input if configured
        redacted_input = tool_input
        if self.config.redaction.redact_tool_inputs:
            redacted_input = None

        start_event = ToolCallStartEvent(
            tool_name=tool_name,
            tool_input=redacted_input,
            metadata=metadata or {},
        )
        self._emit(start_event)

        span = ToolSpan(tracer=self, tool_name=tool_name)

        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # Redact output if configured
            redacted_output = span._output
            if self.config.redaction.redact_tool_outputs:
                redacted_output = None

            end_event = ToolCallEndEvent(
                tool_name=tool_name,
                duration_ms=duration_ms,
                success=not span._error_occurred,
                tool_output=redacted_output,
                error_message=span._error_message,
                metadata=metadata or {},
            )
            self._emit(end_event)

            _current_span.reset(span_token)

    @contextmanager
    def trace_mcp_call(
        self,
        server_name: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Trace an MCP server call.

        Args:
            server_name: Name of the MCP server
            method: Method being called
            params: Parameters for the call
            metadata: Additional metadata

        Yields:
            MCPSpan: A span object to set MCP call results
        """
        parent_span = self._get_current_span()
        span_context = parent_span.child() if parent_span else SpanContext()
        span_token = _current_span.set(span_context)

        start_time = time.time()

        start_event = MCPCallStartEvent(
            server_name=server_name,
            method=method,
            params=params,
            metadata=metadata or {},
        )
        self._emit(start_event)

        span = MCPSpan(tracer=self, server_name=server_name, method=method)

        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            end_event = MCPCallEndEvent(
                server_name=server_name,
                method=method,
                duration_ms=duration_ms,
                success=not span._error_occurred,
                result=span._result,
                error_message=span._error_message,
                metadata=metadata or {},
            )
            self._emit(end_event)

            _current_span.reset(span_token)

    def log(
        self,
        message: str,
        severity: Severity = Severity.INFO,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log a message."""
        event = LogEvent(
            severity=severity,
            message=message,
            context=context,
        )
        self._emit(event)

    def error(
        self,
        error: Union[Exception, str],
        severity: Severity = Severity.ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log an error."""
        if isinstance(error, Exception):
            error_type = type(error).__name__
            error_message = str(error)
            stack_trace = traceback.format_exc()
        else:
            error_type = "Error"
            error_message = error
            stack_trace = None

        event = ErrorEvent(
            severity=severity,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context,
        )
        self._emit(event)

    def metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        dimensions: Optional[Dict[str, str]] = None,
    ):
        """Record a custom metric."""
        event = MetricEvent(
            metric_name=name,
            metric_value=value,
            unit=unit,
            dimensions=dimensions or {},
        )
        self._emit(event)

    def flush(self):
        """Flush all pending events."""
        self.exporter.flush()

    def shutdown(self):
        """Shutdown the tracer."""
        self.exporter.shutdown()


class ExecutionSpan:
    """Span object for execution tracing."""

    def __init__(self, tracer: Tracer, execution_id: str):
        self._tracer = tracer
        self.execution_id = execution_id
        self._output_data: Optional[Dict[str, Any]] = None
        self._total_tokens: int = 0
        self._total_cost: float = 0.0
        self._error_occurred: bool = False
        self._error_message: Optional[str] = None

    def set_output(self, output: Dict[str, Any]):
        """Set the execution output."""
        self._output_data = output

    def add_tokens(self, input_tokens: int = 0, output_tokens: int = 0):
        """Add to the total token count."""
        self._total_tokens += input_tokens + output_tokens

    def add_cost(self, cost: float):
        """Add to the total cost."""
        self._total_cost += cost

    def set_error(self, error: Exception):
        """Mark the execution as failed."""
        self._error_occurred = True
        self._error_message = str(error)
        self._tracer.error(error)


class LLMSpan:
    """Span object for LLM call tracing."""

    def __init__(self, tracer: Tracer, model: str, provider: str):
        self._tracer = tracer
        self.model = model
        self.provider = provider
        self._token_usage: Optional[TokenUsage] = None
        self._response: Optional[str] = None
        self._error_occurred: bool = False
        self._error_message: Optional[str] = None

    def set_token_usage(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
    ):
        """Set token usage for the LLM call."""
        self._token_usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    def set_response(self, response: str):
        """Set the LLM response."""
        self._response = response

    def set_error(self, error: Exception):
        """Mark the LLM call as failed."""
        self._error_occurred = True
        self._error_message = str(error)
        self._tracer.error(error)


class ToolSpan:
    """Span object for tool call tracing."""

    def __init__(self, tracer: Tracer, tool_name: str):
        self._tracer = tracer
        self.tool_name = tool_name
        self._output: Optional[Any] = None
        self._error_occurred: bool = False
        self._error_message: Optional[str] = None

    def set_output(self, output: Any):
        """Set the tool output."""
        self._output = output

    def set_error(self, error: Exception):
        """Mark the tool call as failed."""
        self._error_occurred = True
        self._error_message = str(error)
        self._tracer.error(error)


class MCPSpan:
    """Span object for MCP call tracing."""

    def __init__(self, tracer: Tracer, server_name: str, method: str):
        self._tracer = tracer
        self.server_name = server_name
        self.method = method
        self._result: Optional[Any] = None
        self._error_occurred: bool = False
        self._error_message: Optional[str] = None

    def set_result(self, result: Any):
        """Set the MCP call result."""
        self._result = result

    def set_error(self, error: Exception):
        """Mark the MCP call as failed."""
        self._error_occurred = True
        self._error_message = str(error)
        self._tracer.error(error)


def trace_function(
    tracer: Tracer,
    name: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to trace a function as a tool call.

    Usage:
        @trace_function(tracer, name="my_tool")
        def my_tool(arg1, arg2):
            return result
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        tool_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            with tracer.trace_tool_call(tool_name=tool_name, tool_input=kwargs) as span:
                result = func(*args, **kwargs)
                span.set_output(result)
                return result

        return wrapper

    return decorator
