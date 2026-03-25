"""
Configuration for GenAI Observability SDK.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RedactionConfig:
    """Configuration for data redaction."""
    redact_prompts: bool = False
    redact_responses: bool = False
    redact_tool_inputs: bool = False
    redact_tool_outputs: bool = False
    redact_patterns: List[str] = field(default_factory=list)  # Regex patterns to redact

    # PII patterns to redact by default
    redact_pii: bool = True
    pii_patterns: List[str] = field(default_factory=lambda: [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{16}\b',  # Credit card (simple)
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Phone number
    ])


@dataclass
class BatchConfig:
    """Configuration for event batching."""
    max_batch_size: int = 100
    max_batch_interval_seconds: float = 5.0
    max_queue_size: int = 10000


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0
    backoff_multiplier: float = 2.0


@dataclass
class ObservabilityConfig:
    """Main configuration for the observability SDK."""

    # Required settings
    api_endpoint: str = ""
    api_key: str = ""
    agent_id: str = ""

    # Agent metadata
    agent_type: str = "custom"  # langchain, crewai, custom
    agent_version: str = "1.0.0"
    environment: str = "development"  # development, staging, production

    # Feature flags
    enabled: bool = True
    debug: bool = False

    # Sampling (1.0 = 100% of events)
    sampling_rate: float = 1.0

    # Nested configs
    redaction: RedactionConfig = field(default_factory=RedactionConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)

    # Cost tracking
    track_costs: bool = True
    cost_per_1k_input_tokens: Dict[str, float] = field(default_factory=lambda: {
        "claude-3-opus": 0.015,
        "claude-3-sonnet": 0.003,
        "claude-3-haiku": 0.00025,
        "claude-sonnet-4": 0.003,
        "claude-opus-4": 0.015,
        "gpt-4": 0.03,
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.0005,
    })
    cost_per_1k_output_tokens: Dict[str, float] = field(default_factory=lambda: {
        "claude-3-opus": 0.075,
        "claude-3-sonnet": 0.015,
        "claude-3-haiku": 0.00125,
        "claude-sonnet-4": 0.015,
        "claude-opus-4": 0.075,
        "gpt-4": 0.06,
        "gpt-4-turbo": 0.03,
        "gpt-3.5-turbo": 0.0015,
    })

    # Tags/labels for all events
    global_tags: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Create configuration from environment variables."""
        return cls(
            api_endpoint=os.getenv("GENAI_OBS_ENDPOINT", ""),
            api_key=os.getenv("GENAI_OBS_API_KEY", ""),
            agent_id=os.getenv("GENAI_OBS_AGENT_ID", ""),
            agent_type=os.getenv("GENAI_OBS_AGENT_TYPE", "custom"),
            agent_version=os.getenv("GENAI_OBS_AGENT_VERSION", "1.0.0"),
            environment=os.getenv("GENAI_OBS_ENVIRONMENT", "development"),
            enabled=os.getenv("GENAI_OBS_ENABLED", "true").lower() == "true",
            debug=os.getenv("GENAI_OBS_DEBUG", "false").lower() == "true",
            sampling_rate=float(os.getenv("GENAI_OBS_SAMPLING_RATE", "1.0")),
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.api_endpoint:
            errors.append("api_endpoint is required")
        if not self.api_key:
            errors.append("api_key is required")
        if not self.agent_id:
            errors.append("agent_id is required")
        if not 0.0 <= self.sampling_rate <= 1.0:
            errors.append("sampling_rate must be between 0.0 and 1.0")

        return errors

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage."""
        if not self.track_costs:
            return 0.0

        # Find matching model (handle version suffixes)
        model_key = None
        for key in self.cost_per_1k_input_tokens:
            if key in model.lower():
                model_key = key
                break

        if not model_key:
            return 0.0

        input_cost = (input_tokens / 1000) * self.cost_per_1k_input_tokens.get(model_key, 0)
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output_tokens.get(model_key, 0)

        return input_cost + output_cost
