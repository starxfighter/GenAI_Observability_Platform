"""Tests for health endpoints."""

import pytest


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert "components" in data

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/api/v1/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data

    def test_health_components(self, client):
        """Test health check includes component status."""
        response = client.get("/api/v1/health")
        data = response.json()

        components = data.get("components", {})
        assert "api" in components
        assert components["api"] == "healthy"
