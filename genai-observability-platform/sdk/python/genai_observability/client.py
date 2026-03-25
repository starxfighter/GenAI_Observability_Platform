"""
Main client for GenAI Observability SDK.
"""

import logging
from typing import Optional

from .config import ObservabilityConfig
from .exporters.http_exporter import HTTPExporter
from .tracer import Tracer

logger = logging.getLogger(__name__)

# Global client instance
_client: Optional["ObservabilityClient"] = None


class ObservabilityClient:
    """
    Main client for the GenAI Observability SDK.

    This is the primary entry point for using the SDK. It manages the configuration,
    tracer, and exporter.

    Usage:
        from genai_observability import ObservabilityClient

        # Initialize with explicit config
        client = ObservabilityClient(
            api_endpoint="https://observability.example.com",
            api_key="your-api-key",
            agent_id="my-agent",
        )

        # Or initialize from environment variables
        client = ObservabilityClient.from_env()

        # Use the tracer
        with client.tracer.start_execution() as execution:
            with client.tracer.trace_llm_call(model="claude-sonnet-4") as llm_span:
                response = call_llm(...)
                llm_span.set_token_usage(input_tokens=100, output_tokens=50)
    """

    def __init__(
        self,
        api_endpoint: str = "",
        api_key: str = "",
        agent_id: str = "",
        agent_type: str = "custom",
        agent_version: str = "1.0.0",
        environment: str = "development",
        enabled: bool = True,
        debug: bool = False,
        sampling_rate: float = 1.0,
        config: Optional[ObservabilityConfig] = None,
    ):
        """
        Initialize the observability client.

        Args:
            api_endpoint: The API endpoint URL
            api_key: Your API key
            agent_id: Unique identifier for your agent
            agent_type: Type of agent (langchain, crewai, custom)
            agent_version: Version of your agent
            environment: Environment name (development, staging, production)
            enabled: Whether observability is enabled
            debug: Enable debug logging
            sampling_rate: Sampling rate (0.0 to 1.0)
            config: Full configuration object (overrides other parameters)
        """
        if config:
            self.config = config
        else:
            self.config = ObservabilityConfig(
                api_endpoint=api_endpoint,
                api_key=api_key,
                agent_id=agent_id,
                agent_type=agent_type,
                agent_version=agent_version,
                environment=environment,
                enabled=enabled,
                debug=debug,
                sampling_rate=sampling_rate,
            )

        # Validate configuration
        errors = self.config.validate()
        if errors and self.config.enabled:
            logger.warning(f"Configuration errors: {errors}")

        # Initialize components
        self.exporter = HTTPExporter(self.config)
        self.tracer = Tracer(self.config, self.exporter)

        # Set up logging
        if self.config.debug:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)

        if self.config.debug:
            logger.debug(f"Observability client initialized for agent: {self.config.agent_id}")

    @classmethod
    def from_env(cls) -> "ObservabilityClient":
        """
        Create a client from environment variables.

        Environment variables:
            GENAI_OBS_ENDPOINT: API endpoint URL
            GENAI_OBS_API_KEY: API key
            GENAI_OBS_AGENT_ID: Agent ID
            GENAI_OBS_AGENT_TYPE: Agent type (default: custom)
            GENAI_OBS_AGENT_VERSION: Agent version (default: 1.0.0)
            GENAI_OBS_ENVIRONMENT: Environment (default: development)
            GENAI_OBS_ENABLED: Enable/disable (default: true)
            GENAI_OBS_DEBUG: Debug mode (default: false)
            GENAI_OBS_SAMPLING_RATE: Sampling rate (default: 1.0)

        Returns:
            ObservabilityClient: Configured client instance
        """
        config = ObservabilityConfig.from_env()
        return cls(config=config)

    def start(self):
        """Start the observability client (starts the exporter)."""
        self.exporter.start()

    def shutdown(self):
        """Shutdown the observability client."""
        self.tracer.shutdown()

    def flush(self):
        """Flush all pending events."""
        self.tracer.flush()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
        return False


def init(
    api_endpoint: str = "",
    api_key: str = "",
    agent_id: str = "",
    **kwargs,
) -> ObservabilityClient:
    """
    Initialize the global observability client.

    This is a convenience function that creates a global client instance
    that can be accessed via get_client().

    Args:
        api_endpoint: The API endpoint URL
        api_key: Your API key
        agent_id: Unique identifier for your agent
        **kwargs: Additional configuration options

    Returns:
        ObservabilityClient: The initialized client
    """
    global _client
    _client = ObservabilityClient(
        api_endpoint=api_endpoint,
        api_key=api_key,
        agent_id=agent_id,
        **kwargs,
    )
    _client.start()
    return _client


def init_from_env() -> ObservabilityClient:
    """
    Initialize the global observability client from environment variables.

    Returns:
        ObservabilityClient: The initialized client
    """
    global _client
    _client = ObservabilityClient.from_env()
    _client.start()
    return _client


def get_client() -> Optional[ObservabilityClient]:
    """
    Get the global observability client.

    Returns:
        ObservabilityClient: The global client, or None if not initialized
    """
    return _client


def get_tracer() -> Optional[Tracer]:
    """
    Get the tracer from the global client.

    Returns:
        Tracer: The tracer, or None if client not initialized
    """
    if _client:
        return _client.tracer
    return None


def shutdown():
    """Shutdown the global observability client."""
    global _client
    if _client:
        _client.shutdown()
        _client = None
