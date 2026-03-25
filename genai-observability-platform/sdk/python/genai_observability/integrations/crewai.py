"""
CrewAI integration for GenAI Observability SDK.

This module provides automatic instrumentation for CrewAI applications.
"""

import functools
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

from ..client import ObservabilityClient, get_client
from ..models import Severity
from ..tracer import Tracer

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CrewAICallbackHandler:
    """
    CrewAI callback handler for automatic observability instrumentation.

    This handler captures:
    - Crew execution (start, end)
    - Agent task execution
    - Tool usage
    - LLM calls made by agents

    Usage:
        from crewai import Crew, Agent, Task
        from genai_observability.integrations.crewai import CrewAICallbackHandler

        client = ObservabilityClient(...)
        handler = CrewAICallbackHandler(client)

        crew = Crew(
            agents=[...],
            tasks=[...],
        )

        # Wrap the crew execution
        with handler.trace_crew(crew):
            result = crew.kickoff()
    """

    def __init__(
        self,
        client: Optional[ObservabilityClient] = None,
        capture_inputs: bool = True,
        capture_outputs: bool = True,
    ):
        """
        Initialize the CrewAI callback handler.

        Args:
            client: ObservabilityClient instance (uses global client if not provided)
            capture_inputs: Whether to capture task inputs
            capture_outputs: Whether to capture task outputs
        """
        self.client = client or get_client()
        if not self.client:
            raise ValueError(
                "No ObservabilityClient provided and no global client initialized. "
                "Either pass a client or call init() first."
            )

        self.tracer = self.client.tracer
        self.capture_inputs = capture_inputs
        self.capture_outputs = capture_outputs

    def trace_crew(self, crew: Any):
        """
        Context manager to trace a crew execution.

        Args:
            crew: The CrewAI Crew instance

        Usage:
            with handler.trace_crew(crew):
                result = crew.kickoff()
        """
        return CrewExecutionContext(self, crew)

    def on_crew_start(
        self,
        crew: Any,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Called when crew execution starts."""
        crew_name = getattr(crew, "name", None) or "unnamed_crew"
        agents = getattr(crew, "agents", [])
        tasks = getattr(crew, "tasks", [])

        agent_names = [getattr(a, "role", str(a)) for a in agents]
        task_descriptions = [getattr(t, "description", str(t))[:100] for t in tasks]

        self.tracer.log(
            f"Crew started: {crew_name}",
            severity=Severity.INFO,
            context={
                "crew": crew_name,
                "agents": agent_names,
                "tasks": task_descriptions,
                "inputs": inputs if self.capture_inputs else None,
            },
        )

        return crew_name

    def on_crew_end(
        self,
        crew_name: str,
        duration_ms: float,
        success: bool,
        output: Optional[Any] = None,
        error: Optional[Exception] = None,
    ):
        """Called when crew execution ends."""
        self.tracer.metric(
            name="crew_duration_ms",
            value=duration_ms,
            unit="ms",
            dimensions={"crew": crew_name, "success": str(success)},
        )

        if success:
            self.tracer.log(
                f"Crew completed: {crew_name}",
                severity=Severity.INFO,
                context={
                    "crew": crew_name,
                    "duration_ms": duration_ms,
                    "output": str(output)[:500] if self.capture_outputs and output else None,
                },
            )
        else:
            self.tracer.error(
                error or "Unknown error",
                severity=Severity.ERROR,
                context={"crew": crew_name, "duration_ms": duration_ms},
            )

    def on_agent_start(
        self,
        agent: Any,
        task: Any,
    ) -> Dict[str, Any]:
        """Called when an agent starts working on a task."""
        agent_role = getattr(agent, "role", "unknown")
        task_desc = getattr(task, "description", str(task))[:200]

        self.tracer.log(
            f"Agent started: {agent_role}",
            severity=Severity.DEBUG,
            context={
                "agent": agent_role,
                "task": task_desc,
            },
        )

        return {
            "agent_role": agent_role,
            "task": task_desc,
            "start_time": time.time(),
        }

    def on_agent_end(
        self,
        context: Dict[str, Any],
        output: Optional[Any] = None,
        error: Optional[Exception] = None,
    ):
        """Called when an agent finishes a task."""
        duration_ms = (time.time() - context.get("start_time", time.time())) * 1000
        agent_role = context.get("agent_role", "unknown")

        self.tracer.metric(
            name="agent_task_duration_ms",
            value=duration_ms,
            unit="ms",
            dimensions={"agent": agent_role},
        )

        if error:
            self.tracer.error(
                error,
                context={"agent": agent_role, "task": context.get("task")},
            )
        else:
            self.tracer.log(
                f"Agent completed: {agent_role}",
                severity=Severity.DEBUG,
                context={
                    "agent": agent_role,
                    "duration_ms": duration_ms,
                    "output": str(output)[:500] if self.capture_outputs and output else None,
                },
            )

    def on_tool_use(
        self,
        agent: Any,
        tool_name: str,
        tool_input: Any,
    ) -> Dict[str, Any]:
        """Called when an agent uses a tool."""
        agent_role = getattr(agent, "role", "unknown")

        from ..models import ToolCallStartEvent

        event = ToolCallStartEvent(
            tool_name=tool_name,
            tool_input={"input": str(tool_input)[:500]} if self.capture_inputs else None,
            metadata={"agent": agent_role},
        )
        self.tracer._emit(event)

        return {
            "tool_name": tool_name,
            "agent": agent_role,
            "start_time": time.time(),
        }

    def on_tool_end(
        self,
        context: Dict[str, Any],
        output: Optional[Any] = None,
        error: Optional[Exception] = None,
    ):
        """Called when a tool finishes."""
        duration_ms = (time.time() - context.get("start_time", time.time())) * 1000
        tool_name = context.get("tool_name", "unknown")

        from ..models import ToolCallEndEvent

        event = ToolCallEndEvent(
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=error is None,
            tool_output=str(output)[:500] if self.capture_outputs and output else None,
            error_message=str(error) if error else None,
            metadata={"agent": context.get("agent")},
        )
        self.tracer._emit(event)


class CrewExecutionContext:
    """Context manager for tracing crew execution."""

    def __init__(self, handler: CrewAICallbackHandler, crew: Any):
        self.handler = handler
        self.crew = crew
        self.crew_name: Optional[str] = None
        self.start_time: float = 0
        self._execution_span = None

    def __enter__(self):
        self.start_time = time.time()
        self.crew_name = self.handler.on_crew_start(self.crew)

        # Start execution span
        self._execution_span = self.handler.tracer.start_execution(
            input_data={"crew": self.crew_name},
            metadata={"type": "crewai_crew"},
        )
        self._execution_span.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        success = exc_type is None

        self.handler.on_crew_end(
            crew_name=self.crew_name,
            duration_ms=duration_ms,
            success=success,
            error=exc_val if exc_val else None,
        )

        # End execution span
        if self._execution_span:
            self._execution_span.__exit__(exc_type, exc_val, exc_tb)

        return False


def instrument_crewai(
    client: Optional[ObservabilityClient] = None,
    capture_inputs: bool = True,
    capture_outputs: bool = True,
) -> CrewAICallbackHandler:
    """
    Create a CrewAI callback handler for observability.

    Args:
        client: ObservabilityClient instance (uses global client if not provided)
        capture_inputs: Whether to capture task inputs
        capture_outputs: Whether to capture task outputs

    Returns:
        CrewAICallbackHandler: The callback handler to use with CrewAI
    """
    return CrewAICallbackHandler(
        client=client,
        capture_inputs=capture_inputs,
        capture_outputs=capture_outputs,
    )


def patch_crewai(
    client: Optional[ObservabilityClient] = None,
    capture_inputs: bool = True,
    capture_outputs: bool = True,
):
    """
    Monkey-patch CrewAI for automatic instrumentation.

    This patches the Crew.kickoff() method to automatically trace executions.

    Args:
        client: ObservabilityClient instance
        capture_inputs: Whether to capture task inputs
        capture_outputs: Whether to capture task outputs

    Usage:
        from genai_observability.integrations.crewai import patch_crewai

        patch_crewai(client)

        # Now all crew executions are automatically traced
        crew = Crew(...)
        result = crew.kickoff()  # Automatically traced
    """
    try:
        from crewai import Crew
    except ImportError:
        logger.warning("CrewAI not installed, skipping patch")
        return

    handler = CrewAICallbackHandler(
        client=client,
        capture_inputs=capture_inputs,
        capture_outputs=capture_outputs,
    )

    original_kickoff = Crew.kickoff

    @functools.wraps(original_kickoff)
    def patched_kickoff(self, *args, **kwargs):
        with handler.trace_crew(self):
            return original_kickoff(self, *args, **kwargs)

    Crew.kickoff = patched_kickoff

    logger.info("CrewAI patched for automatic observability")
