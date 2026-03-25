"""Tests for agents endpoints."""

import pytest


class TestAgentsEndpoints:
    """Tests for agent endpoints."""

    def test_list_agents(self, client, auth_headers):
        """Test listing agents."""
        response = client.get("/api/v1/agents", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_agents_with_status_filter(self, client, auth_headers):
        """Test listing agents with status filter."""
        response = client.get(
            "/api/v1/agents",
            params={"status": "active"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_get_agent(self, client, auth_headers, sample_agent):
        """Test getting a single agent."""
        response = client.get(
            f"/api/v1/agents/{sample_agent['agent_id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["agent_id"] == sample_agent["agent_id"]
        assert data["name"] == sample_agent["name"]

    def test_get_agent_not_found(self, client, auth_headers, mock_dynamodb_client):
        """Test getting non-existent agent."""
        mock_dynamodb_client.get_agent.return_value = None

        response = client.get(
            "/api/v1/agents/non-existent-agent",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_create_agent(self, client, auth_headers):
        """Test creating an agent."""
        response = client.post(
            "/api/v1/agents",
            json={
                "name": "New Agent",
                "framework": "CrewAI",
                "version": "2.0.0",
                "metadata": {"team": "ml"},
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        data = response.json()
        assert "agent_id" in data
        assert data["name"] == "New Agent"
        assert data["framework"] == "CrewAI"

    def test_update_agent(self, client, auth_headers, sample_agent, mock_dynamodb_client):
        """Test updating an agent."""
        mock_dynamodb_client.update_agent.return_value = {
            **sample_agent,
            "name": "Updated Agent",
        }

        response = client.patch(
            f"/api/v1/agents/{sample_agent['agent_id']}",
            json={"name": "Updated Agent"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Agent"

    def test_delete_agent(self, client, auth_headers, sample_agent):
        """Test deleting an agent."""
        response = client.delete(
            f"/api/v1/agents/{sample_agent['agent_id']}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_get_agent_metrics(self, client, auth_headers, sample_agent):
        """Test getting agent metrics."""
        response = client.get(
            f"/api/v1/agents/{sample_agent['agent_id']}/metrics",
            params={"period": "24h"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["agent_id"] == sample_agent["agent_id"]
        assert "request_count" in data
        assert "error_rate" in data
        assert "avg_latency_ms" in data

    def test_agent_heartbeat(self, client, auth_headers, sample_agent):
        """Test agent heartbeat."""
        response = client.post(
            f"/api/v1/agents/{sample_agent['agent_id']}/heartbeat",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_create_agent_validation(self, client, auth_headers):
        """Test agent creation validation."""
        # Missing required fields
        response = client.post(
            "/api/v1/agents",
            json={"name": "Test"},  # Missing framework
            headers=auth_headers,
        )
        assert response.status_code == 422
