"""Tests for metrics endpoints."""

import pytest


class TestMetricsEndpoints:
    """Tests for metrics endpoints."""

    def test_get_dashboard_metrics(self, client, auth_headers):
        """Test getting dashboard metrics."""
        response = client.get(
            "/api/v1/metrics/dashboard",
            params={"period": "24h"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["period"] == "24h"
        assert "total_agents" in data
        assert "total_traces" in data
        assert "total_errors" in data
        assert "avg_latency_ms" in data
        assert "total_tokens" in data
        assert "total_cost" in data

    def test_get_dashboard_metrics_different_periods(self, client, auth_headers):
        """Test dashboard metrics with different time periods."""
        for period in ["1h", "6h", "24h", "7d", "30d"]:
            response = client.get(
                "/api/v1/metrics/dashboard",
                params={"period": period},
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert response.json()["period"] == period

    def test_get_latency_series(self, client, auth_headers):
        """Test getting latency time series."""
        response = client.get(
            "/api/v1/metrics/latency",
            params={"period": "24h"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["metric_name"] == "latency"
        assert data["period"] == "24h"
        assert "data" in data

    def test_get_latency_series_by_agent(self, client, auth_headers):
        """Test getting latency series for specific agent."""
        response = client.get(
            "/api/v1/metrics/latency",
            params={"period": "24h", "agent_id": "test-agent"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_get_request_series(self, client, auth_headers):
        """Test getting request count time series."""
        response = client.get(
            "/api/v1/metrics/requests",
            params={"period": "24h"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["metric_name"] == "requests"
        assert "data" in data

    def test_get_error_series(self, client, auth_headers):
        """Test getting error count time series."""
        response = client.get(
            "/api/v1/metrics/errors",
            params={"period": "24h"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["metric_name"] == "errors"

    def test_get_token_usage(self, client, auth_headers):
        """Test getting token usage."""
        response = client.get(
            "/api/v1/metrics/tokens",
            params={"period": "24h"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "period" in data
        assert "total_tokens" in data

    def test_get_token_usage_by_agent(self, client, auth_headers):
        """Test getting token usage for specific agent."""
        response = client.get(
            "/api/v1/metrics/tokens",
            params={"period": "24h", "agent_id": "test-agent"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_get_cost_breakdown(self, client, auth_headers):
        """Test getting cost breakdown."""
        response = client.get(
            "/api/v1/metrics/cost",
            params={"period": "24h"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "period" in data
        assert "total_cost" in data

    def test_get_cost_breakdown_by_agent(self, client, auth_headers):
        """Test getting cost breakdown for specific agent."""
        response = client.get(
            "/api/v1/metrics/cost",
            params={"period": "24h", "agent_id": "test-agent"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_invalid_period(self, client, auth_headers):
        """Test invalid period parameter."""
        response = client.get(
            "/api/v1/metrics/dashboard",
            params={"period": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_metrics_data_structure(self, client, auth_headers):
        """Test metrics data point structure."""
        response = client.get(
            "/api/v1/metrics/latency",
            params={"period": "24h"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        if data["data"]:
            point = data["data"][0]
            assert "timestamp" in point
            assert "value" in point
