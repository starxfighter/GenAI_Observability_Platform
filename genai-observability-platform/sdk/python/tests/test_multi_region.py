"""Tests for multi-region support module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from genai_observability.multi_region import (
    RegionConfig,
    RegionHealth,
    RegionStatus,
    RoutingStrategy,
    MultiRegionConfig,
    RegionRouter,
    MultiRegionClient,
    create_multi_region_client,
)


class TestRegionConfig:
    """Tests for RegionConfig dataclass."""

    def test_create_region_config(self):
        """Test creating a region configuration."""
        config = RegionConfig(
            region_id="us-east-1",
            endpoint="https://api.us-east-1.example.com",
            priority=1,
            is_primary=True,
        )

        assert config.region_id == "us-east-1"
        assert config.endpoint == "https://api.us-east-1.example.com"
        assert config.priority == 1
        assert config.is_primary is True
        assert config.weight == 100  # default
        assert config.health_check_path == "/health"  # default

    def test_region_config_defaults(self):
        """Test default values for region config."""
        config = RegionConfig(
            region_id="test",
            endpoint="https://test.example.com"
        )

        assert config.priority == 1
        assert config.weight == 100
        assert config.is_primary is False
        assert config.health_check_interval == 30
        assert config.failure_threshold == 3
        assert config.recovery_threshold == 2


class TestRegionHealth:
    """Tests for RegionHealth dataclass."""

    def test_create_region_health(self):
        """Test creating region health status."""
        health = RegionHealth(region_id="us-east-1")

        assert health.region_id == "us-east-1"
        assert health.status == RegionStatus.UNKNOWN
        assert health.consecutive_failures == 0
        assert health.consecutive_successes == 0
        assert health.latency_ms == 0.0

    def test_region_health_status_values(self):
        """Test region health status enum values."""
        assert RegionStatus.HEALTHY.value == "healthy"
        assert RegionStatus.DEGRADED.value == "degraded"
        assert RegionStatus.UNHEALTHY.value == "unhealthy"
        assert RegionStatus.UNKNOWN.value == "unknown"


class TestRoutingStrategy:
    """Tests for RoutingStrategy enum."""

    def test_routing_strategies(self):
        """Test all routing strategy values."""
        assert RoutingStrategy.PRIMARY_ONLY.value == "primary_only"
        assert RoutingStrategy.FAILOVER.value == "failover"
        assert RoutingStrategy.ROUND_ROBIN.value == "round_robin"
        assert RoutingStrategy.LATENCY_BASED.value == "latency_based"
        assert RoutingStrategy.GEOGRAPHIC.value == "geographic"


class TestMultiRegionConfig:
    """Tests for MultiRegionConfig dataclass."""

    def test_create_multi_region_config(self):
        """Test creating multi-region configuration."""
        regions = [
            RegionConfig(region_id="primary", endpoint="https://primary.example.com", is_primary=True),
            RegionConfig(region_id="secondary", endpoint="https://secondary.example.com"),
        ]

        config = MultiRegionConfig(
            regions=regions,
            routing_strategy=RoutingStrategy.FAILOVER,
        )

        assert len(config.regions) == 2
        assert config.routing_strategy == RoutingStrategy.FAILOVER
        assert config.enable_health_checks is True  # default

    def test_multi_region_config_defaults(self):
        """Test default values for multi-region config."""
        config = MultiRegionConfig()

        assert config.regions == []
        assert config.routing_strategy == RoutingStrategy.FAILOVER
        assert config.enable_health_checks is True
        assert config.health_check_timeout == 5
        assert config.request_timeout == 30
        assert config.retry_count == 3


class TestRegionRouter:
    """Tests for RegionRouter class."""

    @pytest.fixture
    def router_config(self):
        """Create a test router configuration."""
        return MultiRegionConfig(
            regions=[
                RegionConfig(
                    region_id="primary",
                    endpoint="https://primary.example.com",
                    priority=1,
                    is_primary=True,
                ),
                RegionConfig(
                    region_id="secondary",
                    endpoint="https://secondary.example.com",
                    priority=2,
                ),
            ],
            enable_health_checks=False,  # Disable for testing
        )

    def test_create_router(self, router_config):
        """Test creating a region router."""
        router = RegionRouter(router_config)

        assert router.config == router_config
        assert len(router._health) == 2
        assert "primary" in router._health
        assert "secondary" in router._health

    def test_get_region_failover_strategy(self, router_config):
        """Test getting region with failover strategy."""
        router_config.routing_strategy = RoutingStrategy.FAILOVER
        router = RegionRouter(router_config)

        region = router.get_region()

        assert region is not None
        assert region.region_id == "primary"  # Primary should be first

    def test_get_region_primary_only_strategy(self, router_config):
        """Test getting region with primary-only strategy."""
        router_config.routing_strategy = RoutingStrategy.PRIMARY_ONLY
        router = RegionRouter(router_config)

        region = router.get_region()

        assert region is not None
        assert region.is_primary is True

    def test_get_region_latency_based(self, router_config):
        """Test getting region with latency-based strategy."""
        router_config.routing_strategy = RoutingStrategy.LATENCY_BASED
        router = RegionRouter(router_config)

        # Set latency values
        router._latencies["primary"] = [100, 110, 105]
        router._latencies["secondary"] = [50, 55, 52]

        region = router.get_region()

        assert region is not None
        # Secondary should be chosen (lower latency)
        assert region.region_id == "secondary"

    def test_record_request_failure(self, router_config):
        """Test recording a request failure."""
        router = RegionRouter(router_config)

        router.record_request_failure("primary")

        health = router._health["primary"]
        assert health.consecutive_failures == 1
        assert health.consecutive_successes == 0

    def test_record_request_success(self, router_config):
        """Test recording a request success."""
        router = RegionRouter(router_config)

        router.record_request_success("primary", 50.0)

        health = router._health["primary"]
        assert health.consecutive_successes == 1
        assert health.consecutive_failures == 0
        assert health.latency_ms == 50.0

    def test_circuit_breaker_opens(self, router_config):
        """Test that circuit breaker opens after threshold."""
        router = RegionRouter(router_config)

        # Record failures up to threshold
        for _ in range(router_config.circuit_breaker_threshold):
            router.record_request_failure("primary")

        assert "primary" in router._circuit_breakers
        assert router._health["primary"].status == RegionStatus.UNHEALTHY

    def test_get_health_status(self, router_config):
        """Test getting health status of all regions."""
        router = RegionRouter(router_config)

        health = router.get_health_status()

        assert "primary" in health
        assert "secondary" in health
        assert isinstance(health["primary"], RegionHealth)

    def test_shutdown(self, router_config):
        """Test shutting down the router."""
        router = RegionRouter(router_config)
        router.shutdown()

        assert router._stop_health_checks.is_set()


class TestMultiRegionClient:
    """Tests for MultiRegionClient class."""

    @pytest.fixture
    def client_config(self):
        """Create a test client configuration."""
        return MultiRegionConfig(
            regions=[
                RegionConfig(
                    region_id="primary",
                    endpoint="https://primary.example.com",
                    is_primary=True,
                ),
            ],
            enable_health_checks=False,
        )

    def test_create_client(self, client_config):
        """Test creating a multi-region client."""
        client = MultiRegionClient(client_config)

        assert client.config == client_config
        assert client.router is not None

    @patch('urllib.request.urlopen')
    def test_request_success(self, mock_urlopen, client_config):
        """Test making a successful request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"result": "success"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = MultiRegionClient(client_config)
        status, body = client.request("GET", "/test")

        assert status == 200
        assert body["result"] == "success"

    def test_get_health(self, client_config):
        """Test getting client health."""
        client = MultiRegionClient(client_config)
        health = client.get_health()

        assert "primary" in health
        assert "status" in health["primary"]
        assert "latency_ms" in health["primary"]

    def test_shutdown(self, client_config):
        """Test shutting down the client."""
        client = MultiRegionClient(client_config)
        client.shutdown()

        assert client.router._stop_health_checks.is_set()


class TestCreateMultiRegionClient:
    """Tests for create_multi_region_client factory function."""

    def test_create_with_primary_only(self):
        """Test creating client with primary endpoint only."""
        client = create_multi_region_client(
            primary_endpoint="https://primary.example.com",
            enable_health_checks=False,
        )

        assert len(client.config.regions) == 1
        assert client.config.regions[0].is_primary is True

    def test_create_with_secondary(self):
        """Test creating client with primary and secondary endpoints."""
        client = create_multi_region_client(
            primary_endpoint="https://primary.example.com",
            secondary_endpoint="https://secondary.example.com",
            enable_health_checks=False,
        )

        assert len(client.config.regions) == 2
        assert client.config.regions[0].is_primary is True
        assert client.config.regions[1].is_primary is False

    def test_create_with_custom_strategy(self):
        """Test creating client with custom routing strategy."""
        client = create_multi_region_client(
            primary_endpoint="https://primary.example.com",
            strategy=RoutingStrategy.ROUND_ROBIN,
            enable_health_checks=False,
        )

        assert client.config.routing_strategy == RoutingStrategy.ROUND_ROBIN
