"""
LangChain integration for GenAI Observability SDK.

This module provides automatic instrumentation for LangChain applications.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from ..client import ObservabilityClient, get_client
from ..models import Severity, TokenUsage
from ..tracer import Tracer

logger = logging.getLogger(__name__)

# Track active spans for async operations
_active_llm_spans: Dict[str, Any] = {}
_active_chain_spans: Dict[str, Any] = {}
_active_tool_spans: Dict[str, Any] = {}


class LangChainCallbackHandler:
    """
    LangChain callback handler for automatic observability instrumentation.

    This handler automatically captures:
    - LLM calls (start, end, tokens, errors)
    - Chain executions
    - Tool calls
    - Agent actions

    Usage:
        from langchain.llms import OpenAI
        from genai_observability.integrations.langchain import LangChainCallbackHandler

        client = ObservabilityClient(...)
        handler = LangChainCallbackHandler(client)

        llm = OpenAI(callbacks=[handler])
        result = llm.invoke("Hello")
    """

    def __init__(
        self,
        client: Optional[ObservabilityClient] = None,
        capture_prompts: bool = True,
        capture_responses: bool = True,
    ):
        """
        Initialize the LangChain callback handler.

        Args:
            client: ObservabilityClient instance (uses global client if not provided)
            capture_prompts: Whether to capture prompts (can be disabled for privacy)
            capture_responses: Whether to capture responses (can be disabled for privacy)
        """
        self.client = client or get_client()
        if not self.client:
            raise ValueError(
                "No ObservabilityClient provided and no global client initialized. "
                "Either pass a client or call init() first."
            )

        self.tracer = self.client.tracer
        self.capture_prompts = capture_prompts
        self.capture_responses = capture_responses

        self._llm_start_times: Dict[str, float] = {}
        self._chain_start_times: Dict[str, float] = {}
        self._tool_start_times: Dict[str, float] = {}

    # ========== LLM Callbacks ==========

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts running."""
        run_id_str = str(run_id)
        self._llm_start_times[run_id_str] = time.time()

        # Extract model info
        model_name = serialized.get("name", "unknown")
        if "kwargs" in serialized:
            model_name = serialized["kwargs"].get("model_name", model_name)
            model_name = serialized["kwargs"].get("model", model_name)

        # Determine provider from model name or serialized info
        provider = self._detect_provider(model_name, serialized)

        # Capture prompt if enabled
        prompt_text = None
        if self.capture_prompts and prompts:
            prompt_text = prompts[0] if len(prompts) == 1 else "\n---\n".join(prompts)

        # Create span context
        _active_llm_spans[run_id_str] = {
            "model": model_name,
            "provider": provider,
            "prompt": prompt_text,
            "metadata": metadata or {},
            "tags": tags or [],
        }

        self.tracer.log(
            f"LLM call started: {model_name}",
            severity=Severity.DEBUG,
            context={"run_id": run_id_str, "model": model_name},
        )

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM ends running."""
        run_id_str = str(run_id)
        start_time = self._llm_start_times.pop(run_id_str, time.time())
        duration_ms = (time.time() - start_time) * 1000

        span_data = _active_llm_spans.pop(run_id_str, {})
        model = span_data.get("model", "unknown")
        provider = span_data.get("provider", "unknown")

        # Extract token usage
        token_usage = None
        llm_output = getattr(response, "llm_output", {}) or {}
        if "token_usage" in llm_output:
            usage = llm_output["token_usage"]
            token_usage = TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

        # Extract response text
        response_text = None
        if self.capture_responses:
            generations = getattr(response, "generations", [])
            if generations and generations[0]:
                response_text = generations[0][0].text if hasattr(generations[0][0], "text") else str(generations[0][0])

        # Calculate cost
        cost = 0.0
        if token_usage:
            cost = self.client.config.calculate_cost(
                model,
                token_usage.input_tokens,
                token_usage.output_tokens,
            )

        # Record via tracer (emit events directly since we're in callback)
        from ..models import LLMCallEndEvent

        event = LLMCallEndEvent(
            model=model,
            provider=provider,
            duration_ms=duration_ms,
            success=True,
            token_usage=token_usage,
            response=response_text,
            cost=cost,
            metadata=span_data.get("metadata", {}),
        )
        self.tracer._emit(event)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM errors."""
        run_id_str = str(run_id)
        start_time = self._llm_start_times.pop(run_id_str, time.time())
        duration_ms = (time.time() - start_time) * 1000

        span_data = _active_llm_spans.pop(run_id_str, {})
        model = span_data.get("model", "unknown")
        provider = span_data.get("provider", "unknown")

        from ..models import LLMCallEndEvent

        event = LLMCallEndEvent(
            model=model,
            provider=provider,
            duration_ms=duration_ms,
            success=False,
            error_message=str(error),
            metadata=span_data.get("metadata", {}),
        )
        self.tracer._emit(event)
        self.tracer.error(error, context={"run_id": run_id_str, "model": model})

    # ========== Chain Callbacks ==========

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chain starts running."""
        run_id_str = str(run_id)
        self._chain_start_times[run_id_str] = time.time()

        chain_name = serialized.get("name", serialized.get("id", ["unknown"])[-1])

        _active_chain_spans[run_id_str] = {
            "name": chain_name,
            "inputs": inputs,
            "metadata": metadata or {},
            "tags": tags or [],
        }

        self.tracer.log(
            f"Chain started: {chain_name}",
            severity=Severity.DEBUG,
            context={"run_id": run_id_str, "chain": chain_name},
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chain ends."""
        run_id_str = str(run_id)
        start_time = self._chain_start_times.pop(run_id_str, time.time())
        duration_ms = (time.time() - start_time) * 1000

        span_data = _active_chain_spans.pop(run_id_str, {})
        chain_name = span_data.get("name", "unknown")

        self.tracer.metric(
            name="chain_duration_ms",
            value=duration_ms,
            unit="ms",
            dimensions={"chain": chain_name},
        )

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chain errors."""
        run_id_str = str(run_id)
        self._chain_start_times.pop(run_id_str, None)
        span_data = _active_chain_spans.pop(run_id_str, {})

        self.tracer.error(
            error,
            context={"run_id": run_id_str, "chain": span_data.get("name", "unknown")},
        )

    # ========== Tool Callbacks ==========

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when tool starts running."""
        run_id_str = str(run_id)
        self._tool_start_times[run_id_str] = time.time()

        tool_name = serialized.get("name", "unknown")

        _active_tool_spans[run_id_str] = {
            "name": tool_name,
            "input": input_str,
            "metadata": metadata or {},
        }

        from ..models import ToolCallStartEvent

        event = ToolCallStartEvent(
            tool_name=tool_name,
            tool_input={"input": input_str},
            metadata=metadata or {},
        )
        self.tracer._emit(event)

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when tool ends."""
        run_id_str = str(run_id)
        start_time = self._tool_start_times.pop(run_id_str, time.time())
        duration_ms = (time.time() - start_time) * 1000

        span_data = _active_tool_spans.pop(run_id_str, {})
        tool_name = span_data.get("name", "unknown")

        from ..models import ToolCallEndEvent

        event = ToolCallEndEvent(
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=True,
            tool_output=output,
            metadata=span_data.get("metadata", {}),
        )
        self.tracer._emit(event)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when tool errors."""
        run_id_str = str(run_id)
        start_time = self._tool_start_times.pop(run_id_str, time.time())
        duration_ms = (time.time() - start_time) * 1000

        span_data = _active_tool_spans.pop(run_id_str, {})
        tool_name = span_data.get("name", "unknown")

        from ..models import ToolCallEndEvent

        event = ToolCallEndEvent(
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=False,
            error_message=str(error),
            metadata=span_data.get("metadata", {}),
        )
        self.tracer._emit(event)
        self.tracer.error(error, context={"tool": tool_name})

    # ========== Agent Callbacks ==========

    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when agent takes an action."""
        action_name = getattr(action, "tool", "unknown")
        action_input = getattr(action, "tool_input", {})

        self.tracer.log(
            f"Agent action: {action_name}",
            severity=Severity.DEBUG,
            context={"action": action_name, "input": str(action_input)[:500]},
        )

    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when agent finishes."""
        output = getattr(finish, "return_values", {})

        self.tracer.log(
            "Agent finished",
            severity=Severity.DEBUG,
            context={"output": str(output)[:500]},
        )

    # ========== Helper Methods ==========

    def _detect_provider(self, model_name: str, serialized: Dict[str, Any]) -> str:
        """Detect the LLM provider from model name or serialized info."""
        model_lower = model_name.lower()

        if "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "llama" in model_lower or "meta" in model_lower:
            return "meta"
        elif "gemini" in model_lower or "google" in model_lower:
            return "google"
        elif "mistral" in model_lower:
            return "mistral"
        elif "cohere" in model_lower:
            return "cohere"

        # Check serialized for class info
        class_name = serialized.get("id", [""])[-1].lower()
        if "anthropic" in class_name:
            return "anthropic"
        elif "openai" in class_name:
            return "openai"

        return "unknown"


def instrument_langchain(
    client: Optional[ObservabilityClient] = None,
    capture_prompts: bool = True,
    capture_responses: bool = True,
) -> LangChainCallbackHandler:
    """
    Create a LangChain callback handler for observability.

    This is a convenience function to create and return a handler.

    Args:
        client: ObservabilityClient instance (uses global client if not provided)
        capture_prompts: Whether to capture prompts
        capture_responses: Whether to capture responses

    Returns:
        LangChainCallbackHandler: The callback handler to use with LangChain
    """
    return LangChainCallbackHandler(
        client=client,
        capture_prompts=capture_prompts,
        capture_responses=capture_responses,
    )
