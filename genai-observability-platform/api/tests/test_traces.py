"""Tests for traces endpoints."""

import pytest


class TestTracesEndpoints:
    """Tests for trace endpoints."""

    def test_list_traces(self, client, auth_headers):
        """Test listing traces."""
        response = client.get("/api/v1/traces", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_list_traces_with_filters(self, client, auth_headers):
        """Test listing traces with filters."""
        response = client.get(
            "/api/v1/traces",
            params={
                "agent_id": "test-agent",
                "status": "completed",
                "time_range": "24h",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_list_traces_pagination(self, client, auth_headers):
        """Test trace list pagination."""
        response = client.get(
            "/api/v1/traces",
            params={"page": 2, "page_size": 10},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_get_trace(self, client, auth_headers, sample_trace):
        """Test getting a single trace."""
        response = client.get(
            f"/api/v1/traces/{sample_trace['trace_id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["trace_id"] == sample_trace["trace_id"]

    def test_get_trace_not_found(self, client, auth_headers, mock_dynamodb_client):
        """Test getting non-existent trace."""
        mock_dynamodb_client.get_trace.return_value = None

        response = client.get(
            "/api/v1/traces/non-existent-trace",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_create_trace(self, client, auth_headers):
        """Test creating a trace."""
        response = client.post(
            "/api/v1/traces",
            json={
                "agent_id": "test-agent",
                "name": "New Trace",
                "metadata": {"key": "value"},
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        data = response.json()
        assert "trace_id" in data
        assert data["agent_id"] == "test-agent"
        assert data["name"] == "New Trace"

    def test_complete_trace(self, client, auth_headers, sample_trace):
        """Test completing a trace."""
        response = client.post(
            f"/api/v1/traces/{sample_trace['trace_id']}/complete",
            params={"status": "completed"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_get_trace_spans(self, client, auth_headers, sample_trace):
        """Test getting trace spans."""
        response = client.get(
            f"/api/v1/traces/{sample_trace['trace_id']}/spans",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_invalid_time_range(self, client, auth_headers):
        """Test invalid time range parameter."""
        response = client.get(
            "/api/v1/traces",
            params={"time_range": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_search_traces(self, client, auth_headers):
        """Test searching traces."""
        response = client.get(
            "/api/v1/traces",
            params={"search": "test query"},
            headers=auth_headers,
        )
        assert response.status_code == 200
