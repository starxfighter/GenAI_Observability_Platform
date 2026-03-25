"""Tests for SDK configuration."""

import pytest
import os
from unittest.mock import patch

from genai_observability.config import (
    ObservabilityConfig,
    BatchConfig,
    RetryConfig,
    RedactionConfig,
)


class TestBatchConfig:
    """Tests for BatchConfig."""

    def test_default_values(self):
        """Test default batch configuration."""
        config = BatchConfig()
        assert config.max_size == 100
        assert config.max_wait_seconds == 5.0
        assert config.enabled is True

    def test_custom_values(self):
        """Test custom batch configuration."""
        config = BatchConfig(
            max_size=50,
            max_wait_seconds=2.0,
            enabled=False,
        )
        assert config.max_size == 50
        assert config.max_wait_seconds == 2.0
        assert config.enabled is False


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_values(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0

    def test_custom_values(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=60.0,
            exponential_base=3.0,
        )
        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0


class TestRedactionConfig:
    """Tests for RedactionConfig."""

    def test_default_values(self):
        """Test default redaction configuration."""
        config = RedactionConfig()
        assert config.enabled is True
        assert "password" in config.patterns
        assert "api_key" in config.patterns
        assert config.replacement == "[REDACTED]"

    def test_custom_patterns(self):
        """Test custom redaction patterns."""
        config = RedactionConfig(
            enabled=True,
            patterns=["secret", "token"],
            replacement="***",
        )
        assert "secret" in config.patterns
        assert "token" in config.patterns
        assert config.replacement == "***"

    def test_disabled_redaction(self):
        """Test disabled redaction."""
        config = RedactionConfig(enabled=False)
        assert config.enabled is False


class TestObservabilityConfig:
    """Tests for ObservabilityConfig."""

    def test_required_fields(self):
        """Test configuration with required fields."""
        config = ObservabilityConfig(
            endpoint="https://api.example.com",
            api_key="test-key",
            agent_id="test-agent",
        )
        assert config.endpoint == "https://api.example.com"
        assert config.api_key == "test-key"
        assert config.agent_id == "test-agent"

    def test_optional_fields(self):
        """Test configuration with optional fields."""
        config = ObservabilityConfig(
            endpoint="https://api.example.com",
            api_key="test-key",
            agent_id="test-agent",
            agent_name="Test Agent",
            environment="production",
            service_version="1.0.0",
        )
        assert config.agent_name == "Test Agent"
        assert config.environment == "production"
        assert config.service_version == "1.0.0"

    def test_nested_configs(self):
        """Test configuration with nested configs."""
        config = ObservabilityConfig(
            endpoint="https://api.example.com",
            api_key="test-key",
            agent_id="test-agent",
            batch=BatchConfig(max_size=50),
            retry=RetryConfig(max_retries=5),
            redaction=RedactionConfig(enabled=False),
        )
        assert config.batch.max_size == 50
        assert config.retry.max_retries == 5
        assert config.redaction.enabled is False

    def test_default_nested_configs(self):
        """Test default nested configurations."""
        config = ObservabilityConfig(
            endpoint="https://api.example.com",
            api_key="test-key",
            agent_id="test-agent",
        )
        # Should use default BatchConfig, RetryConfig, RedactionConfig
        assert config.batch is not None
        assert config.retry is not None
        assert config.redaction is not None

    @patch.dict(os.environ, {
        "OBSERVABILITY_ENDPOINT": "https://env-api.example.com",
        "OBSERVABILITY_API_KEY": "env-api-key",
        "OBSERVABILITY_AGENT_ID": "env-agent",
    })
    def test_from_environment(self):
        """Test configuration from environment variables."""
        config = ObservabilityConfig.from_env()
        assert config.endpoint == "https://env-api.example.com"
        assert config.api_key == "env-api-key"
        assert config.agent_id == "env-agent"

    def test_endpoint_validation(self):
        """Test endpoint URL validation."""
        # Valid HTTPS endpoint
        config = ObservabilityConfig(
            endpoint="https://api.example.com",
            api_key="test-key",
            agent_id="test-agent",
        )
        assert config.endpoint == "https://api.example.com"

        # Valid HTTP endpoint (allowed for local dev)
        config = ObservabilityConfig(
            endpoint="http://localhost:8000",
            api_key="test-key",
            agent_id="test-agent",
        )
        assert config.endpoint == "http://localhost:8000"

    def test_metadata(self):
        """Test configuration with metadata."""
        config = ObservabilityConfig(
            endpoint="https://api.example.com",
            api_key="test-key",
            agent_id="test-agent",
            metadata={"team": "platform", "region": "us-east-1"},
        )
        assert config.metadata["team"] == "platform"
        assert config.metadata["region"] == "us-east-1"
