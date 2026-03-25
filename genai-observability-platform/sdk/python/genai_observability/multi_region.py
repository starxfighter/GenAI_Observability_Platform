"""
Multi-Region Support Module

Provides intelligent region routing, failover handling, and cross-region
replication support for the GenAI Observability SDK.
"""

import logging
import random
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import urllib.request
import urllib.error
import json
import socket

logger = logging.getLogger(__name__)


class RegionStatus(str, Enum):
    """Region health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class RoutingStrategy(str, Enum):
    """Request routing strategy."""
    PRIMARY_ONLY = "primary_only"
    FAILOVER = "failover"
    ROUND_ROBIN = "round_robin"
    LATENCY_BASED = "latency_based"
    GEOGRAPHIC = "geographic"


@dataclass
class RegionConfig:
    """Configuration for a single region."""
    region_id: str
    endpoint: str
    priority: int = 1  # Lower = higher priority
    weight: int = 100  # For weighted routing
    is_primary: bool = False
    health_check_path: str = "/health"
    health_check_interval: int = 30  # seconds
    failure_threshold: int = 3
    recovery_threshold: int = 2


@dataclass
class RegionHealth:
    """Health status of a region."""
    region_id: str
    status: RegionStatus = RegionStatus.UNKNOWN
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    latency_ms: float = 0.0
    last_error: Optional[str] = None


@dataclass
class MultiRegionConfig:
    """Multi-region configuration."""
    regions: List[RegionConfig] = field(default_factory=list)
    routing_strategy: RoutingStrategy = RoutingStrategy.FAILOVER
    enable_health_checks: bool = True
    health_check_timeout: int = 5  # seconds
    request_timeout: int = 30  # seconds
    retry_count: int = 3
    retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60  # seconds


class RegionRouter:
    """
    Intelligent region router with health checking and failover support.

    Features:
    - Multiple routing strategies
    - Automatic health monitoring
    - Circuit breaker pattern
    - Latency-based routing
    - Geographic routing
    """

    def __init__(self, config: MultiRegionConfig):
        self.config = config
        self._health: Dict[str, RegionHealth] = {}
        self._circuit_breakers: Dict[str, datetime] = {}
        self._latencies: Dict[str, List[float]] = {}
        self._health_check_thread: Optional[threading.Thread] = None
        self._stop_health_checks = threading.Event()

        # Initialize health for all regions
        for region in config.regions:
            self._health[region.region_id] = RegionHealth(region_id=region.region_id)
            self._latencies[region.region_id] = []

        # Start health check thread if enabled
        if config.enable_health_checks and config.regions:
            self._start_health_checks()

    def _start_health_checks(self):
        """Start background health check thread."""
        self._stop_health_checks.clear()
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
        )
        self._health_check_thread.start()
        logger.info("Started multi-region health check thread")

    def _health_check_loop(self):
        """Background health check loop."""
        while not self._stop_health_checks.is_set():
            for region in self.config.regions:
                try:
                    self._check_region_health(region)
                except Exception as e:
                    logger.error(f"Health check error for {region.region_id}: {e}")

            # Wait for next check interval
            self._stop_health_checks.wait(
                timeout=min(r.health_check_interval for r in self.config.regions)
            )

    def _check_region_health(self, region: RegionConfig):
        """Perform health check for a region."""
        health = self._health[region.region_id]
        url = f"{region.endpoint.rstrip('/')}{region.health_check_path}"

        start_time = time.time()
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.config.health_check_timeout) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status == 200:
                    health.consecutive_successes += 1
                    health.consecutive_failures = 0
                    health.latency_ms = latency_ms
                    health.last_error = None

                    # Update latency history
                    self._latencies[region.region_id].append(latency_ms)
                    if len(self._latencies[region.region_id]) > 10:
                        self._latencies[region.region_id].pop(0)

                    # Determine status
                    if health.consecutive_successes >= region.recovery_threshold:
                        health.status = RegionStatus.HEALTHY
                        # Reset circuit breaker
                        self._circuit_breakers.pop(region.region_id, None)
                else:
                    self._record_failure(region, health, f"HTTP {response.status}")

        except urllib.error.URLError as e:
            self._record_failure(region, health, str(e))
        except socket.timeout:
            self._record_failure(region, health, "Timeout")
        except Exception as e:
            self._record_failure(region, health, str(e))

        health.last_check = datetime.utcnow()

    def _record_failure(self, region: RegionConfig, health: RegionHealth, error: str):
        """Record a health check failure."""
        health.consecutive_failures += 1
        health.consecutive_successes = 0
        health.last_error = error

        if health.consecutive_failures >= region.failure_threshold:
            health.status = RegionStatus.UNHEALTHY
            logger.warning(f"Region {region.region_id} marked unhealthy: {error}")
        elif health.consecutive_failures >= region.failure_threshold // 2:
            health.status = RegionStatus.DEGRADED

    def get_region(self) -> Optional[RegionConfig]:
        """
        Get the best region based on routing strategy.

        Returns:
            Best available region or None if all are unhealthy
        """
        strategy = self.config.routing_strategy
        available_regions = self._get_available_regions()

        if not available_regions:
            logger.error("No healthy regions available")
            return None

        if strategy == RoutingStrategy.PRIMARY_ONLY:
            return self._route_primary_only(available_regions)
        elif strategy == RoutingStrategy.FAILOVER:
            return self._route_failover(available_regions)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin(available_regions)
        elif strategy == RoutingStrategy.LATENCY_BASED:
            return self._route_latency_based(available_regions)
        elif strategy == RoutingStrategy.GEOGRAPHIC:
            return self._route_geographic(available_regions)
        else:
            return available_regions[0]

    def _get_available_regions(self) -> List[RegionConfig]:
        """Get list of available (not circuit-broken) regions."""
        available = []
        now = datetime.utcnow()

        for region in self.config.regions:
            region_id = region.region_id

            # Check circuit breaker
            if region_id in self._circuit_breakers:
                breaker_time = self._circuit_breakers[region_id]
                if now < breaker_time + timedelta(seconds=self.config.circuit_breaker_timeout):
                    continue  # Still in circuit breaker timeout
                else:
                    # Circuit breaker timeout expired, allow retry
                    del self._circuit_breakers[region_id]

            # Check health status
            health = self._health.get(region_id)
            if health and health.status != RegionStatus.UNHEALTHY:
                available.append(region)
            elif not self.config.enable_health_checks:
                # If health checks disabled, assume all regions available
                available.append(region)

        return available

    def _route_primary_only(self, regions: List[RegionConfig]) -> Optional[RegionConfig]:
        """Route to primary region only."""
        for region in regions:
            if region.is_primary:
                return region
        return regions[0] if regions else None

    def _route_failover(self, regions: List[RegionConfig]) -> Optional[RegionConfig]:
        """Route with failover - use highest priority healthy region."""
        sorted_regions = sorted(regions, key=lambda r: (r.priority, not r.is_primary))
        return sorted_regions[0] if sorted_regions else None

    def _route_round_robin(self, regions: List[RegionConfig]) -> Optional[RegionConfig]:
        """Route using weighted round-robin."""
        total_weight = sum(r.weight for r in regions)
        r = random.randint(1, total_weight)

        cumulative = 0
        for region in regions:
            cumulative += region.weight
            if r <= cumulative:
                return region

        return regions[0] if regions else None

    def _route_latency_based(self, regions: List[RegionConfig]) -> Optional[RegionConfig]:
        """Route to region with lowest latency."""
        def avg_latency(region: RegionConfig) -> float:
            latencies = self._latencies.get(region.region_id, [])
            if latencies:
                return sum(latencies) / len(latencies)
            return float('inf')

        sorted_regions = sorted(regions, key=avg_latency)
        return sorted_regions[0] if sorted_regions else None

    def _route_geographic(self, regions: List[RegionConfig]) -> Optional[RegionConfig]:
        """Route based on geographic proximity (simplified)."""
        # In production, this would use client IP geolocation
        # For now, fall back to latency-based routing
        return self._route_latency_based(regions)

    def record_request_failure(self, region_id: str):
        """Record a request failure for circuit breaker."""
        health = self._health.get(region_id)
        if health:
            health.consecutive_failures += 1

            if health.consecutive_failures >= self.config.circuit_breaker_threshold:
                self._circuit_breakers[region_id] = datetime.utcnow()
                health.status = RegionStatus.UNHEALTHY
                logger.warning(f"Circuit breaker opened for region {region_id}")

    def record_request_success(self, region_id: str, latency_ms: float):
        """Record a successful request."""
        health = self._health.get(region_id)
        if health:
            health.consecutive_successes += 1
            health.consecutive_failures = 0
            health.latency_ms = latency_ms

            # Update latency history
            self._latencies[region_id].append(latency_ms)
            if len(self._latencies[region_id]) > 10:
                self._latencies[region_id].pop(0)

    def get_health_status(self) -> Dict[str, RegionHealth]:
        """Get health status of all regions."""
        return dict(self._health)

    def shutdown(self):
        """Shutdown the router."""
        self._stop_health_checks.set()
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)


class MultiRegionClient:
    """
    HTTP client with multi-region support.

    Automatically routes requests to healthy regions with retry and failover.
    """

    def __init__(self, config: MultiRegionConfig):
        self.config = config
        self.router = RegionRouter(config)

    def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Make a request with automatic region routing and failover.

        Args:
            method: HTTP method
            path: Request path
            data: Request body
            headers: Request headers

        Returns:
            Tuple of (status_code, response_body)
        """
        last_error = None

        for attempt in range(self.config.retry_count):
            region = self.router.get_region()

            if not region:
                raise Exception("No healthy regions available")

            try:
                status, response = self._make_request(
                    region, method, path, data, headers
                )

                if status < 500:
                    return status, response

                # Server error - try next region
                self.router.record_request_failure(region.region_id)
                last_error = f"HTTP {status}"

            except Exception as e:
                self.router.record_request_failure(region.region_id)
                last_error = str(e)
                logger.warning(f"Request failed to {region.region_id}: {e}")

            # Wait before retry
            if attempt < self.config.retry_count - 1:
                time.sleep(self.config.retry_delay * (attempt + 1))

        raise Exception(f"All regions failed. Last error: {last_error}")

    def _make_request(
        self,
        region: RegionConfig,
        method: str,
        path: str,
        data: Optional[Dict],
        headers: Optional[Dict[str, str]],
    ) -> Tuple[int, Dict[str, Any]]:
        """Make a single request to a region."""
        url = f"{region.endpoint.rstrip('/')}{path}"

        request_headers = headers or {}
        request_headers["Content-Type"] = "application/json"

        body = json.dumps(data).encode() if data else None

        req = urllib.request.Request(
            url,
            data=body,
            headers=request_headers,
            method=method,
        )

        start_time = time.time()

        try:
            with urllib.request.urlopen(req, timeout=self.config.request_timeout) as response:
                latency_ms = (time.time() - start_time) * 1000
                self.router.record_request_success(region.region_id, latency_ms)

                response_body = json.loads(response.read().decode())
                return response.status, response_body

        except urllib.error.HTTPError as e:
            latency_ms = (time.time() - start_time) * 1000

            if e.code < 500:
                # Client error - don't count as region failure
                self.router.record_request_success(region.region_id, latency_ms)

            try:
                response_body = json.loads(e.read().decode())
            except Exception:
                response_body = {"error": str(e)}

            return e.code, response_body

    def get_health(self) -> Dict[str, Any]:
        """Get health status of all regions."""
        health = self.router.get_health_status()
        return {
            region_id: {
                "status": h.status.value,
                "latency_ms": h.latency_ms,
                "last_check": h.last_check.isoformat() if h.last_check else None,
                "last_error": h.last_error,
            }
            for region_id, h in health.items()
        }

    def shutdown(self):
        """Shutdown the client."""
        self.router.shutdown()


# Factory function for easy setup
def create_multi_region_client(
    primary_endpoint: str,
    secondary_endpoint: Optional[str] = None,
    strategy: RoutingStrategy = RoutingStrategy.FAILOVER,
    enable_health_checks: bool = True,
) -> MultiRegionClient:
    """
    Create a multi-region client with simple configuration.

    Args:
        primary_endpoint: Primary region endpoint URL
        secondary_endpoint: Optional secondary region endpoint
        strategy: Routing strategy
        enable_health_checks: Whether to enable background health checks

    Returns:
        Configured MultiRegionClient
    """
    regions = [
        RegionConfig(
            region_id="primary",
            endpoint=primary_endpoint,
            priority=1,
            is_primary=True,
        )
    ]

    if secondary_endpoint:
        regions.append(
            RegionConfig(
                region_id="secondary",
                endpoint=secondary_endpoint,
                priority=2,
                is_primary=False,
            )
        )

    config = MultiRegionConfig(
        regions=regions,
        routing_strategy=strategy,
        enable_health_checks=enable_health_checks,
    )

    return MultiRegionClient(config)
