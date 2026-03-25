"""Tests for integrations endpoints."""

import pytest


class TestIntegrationsEndpoints:
    """Tests for integration hub endpoints."""

    def test_list_integrations(self, client):
        """Test listing all integrations."""
        response = client.get("/api/v1/integrations")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_list_integrations_with_type_filter(self, client):
        """Test filtering integrations by type."""
        response = client.get("/api/v1/integrations?type=jira")
        assert response.status_code == 200

        data = response.json()
        for item in data:
            assert item["type"] == "jira"

    def test_list_integrations_with_status_filter(self, client):
        """Test filtering integrations by status."""
        response = client.get("/api/v1/integrations?status=connected")
        assert response.status_code == 200

        data = response.json()
        for item in data:
            assert item["status"] == "connected"

    def test_list_integrations_with_enabled_filter(self, client):
        """Test filtering integrations by enabled state."""
        response = client.get("/api/v1/integrations?enabled=true")
        assert response.status_code == 200

        data = response.json()
        for item in data:
            assert item["enabled"] is True

    def test_get_integration(self, client):
        """Test getting a specific integration."""
        # First list to get an ID
        list_response = client.get("/api/v1/integrations")
        items = list_response.json()

        if items:
            integration_id = items[0]["integration_id"]
            response = client.get(f"/api/v1/integrations/{integration_id}")
            assert response.status_code == 200

            data = response.json()
            assert data["integration_id"] == integration_id
            assert "type" in data
            assert "name" in data
            assert "enabled" in data

    def test_get_integration_not_found(self, client):
        """Test getting a non-existent integration."""
        response = client.get("/api/v1/integrations/non-existent-id")
        assert response.status_code == 404

    def test_create_integration(self, client):
        """Test creating a new integration."""
        response = client.post(
            "/api/v1/integrations",
            json={
                "type": "slack",
                "name": "Test Slack Integration",
                "config": {"webhook_url": "https://hooks.slack.com/test"}
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "integration_id" in data
        assert data["type"] == "slack"
        assert data["name"] == "Test Slack Integration"
        assert data["enabled"] is True

    def test_create_jira_integration(self, client):
        """Test creating a Jira integration."""
        response = client.post(
            "/api/v1/integrations",
            json={
                "type": "jira",
                "name": "Test Jira",
                "config": {
                    "base_url": "https://test.atlassian.net",
                    "username": "test@example.com",
                    "api_token": "test-token",
                    "project_key": "TEST"
                }
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["type"] == "jira"

    def test_update_integration(self, client):
        """Test updating an integration."""
        # First create an integration
        create_response = client.post(
            "/api/v1/integrations",
            json={
                "type": "slack",
                "name": "To Update",
                "config": {"webhook_url": "https://hooks.slack.com/test"}
            }
        )
        integration_id = create_response.json()["integration_id"]

        # Then update it
        response = client.patch(
            f"/api/v1/integrations/{integration_id}",
            json={"name": "Updated Name", "enabled": False}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["enabled"] is False

    def test_delete_integration(self, client):
        """Test deleting an integration."""
        # First create an integration
        create_response = client.post(
            "/api/v1/integrations",
            json={
                "type": "teams",
                "name": "To Delete",
                "config": {"webhook_url": "https://teams.webhook.test"}
            }
        )
        integration_id = create_response.json()["integration_id"]

        # Then delete it
        response = client.delete(f"/api/v1/integrations/{integration_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = client.get(f"/api/v1/integrations/{integration_id}")
        assert get_response.status_code == 404

    def test_test_integration(self, client):
        """Test testing an integration connection."""
        # First list to get an ID
        list_response = client.get("/api/v1/integrations")
        items = list_response.json()

        if items:
            integration_id = items[0]["integration_id"]
            response = client.post(f"/api/v1/integrations/{integration_id}/test")
            assert response.status_code == 200

            data = response.json()
            assert "success" in data
            assert "message" in data

    def test_sync_integration(self, client):
        """Test syncing an integration."""
        # Get a connected integration
        list_response = client.get("/api/v1/integrations?status=connected&enabled=true")
        items = list_response.json()

        if items:
            integration_id = items[0]["integration_id"]
            response = client.post(f"/api/v1/integrations/{integration_id}/sync")
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert "synced_at" in data

    def test_sync_disabled_integration_fails(self, client):
        """Test syncing a disabled integration fails."""
        # Create a disabled integration
        create_response = client.post(
            "/api/v1/integrations",
            json={
                "type": "slack",
                "name": "Disabled",
                "config": {"webhook_url": "https://hooks.slack.com/test"}
            }
        )
        integration_id = create_response.json()["integration_id"]

        # Disable it
        client.patch(f"/api/v1/integrations/{integration_id}", json={"enabled": False})

        # Try to sync
        response = client.post(f"/api/v1/integrations/{integration_id}/sync")
        assert response.status_code == 400

    def test_create_external_issue(self, client):
        """Test creating an external issue."""
        # Get a Jira integration
        list_response = client.get("/api/v1/integrations?type=jira&status=connected")
        items = list_response.json()

        if items:
            integration_id = items[0]["integration_id"]
            response = client.post(
                f"/api/v1/integrations/{integration_id}/issues",
                json={
                    "alert_id": "alert-123",
                    "issue_type": "Bug",
                    "priority": "High"
                }
            )
            assert response.status_code == 200

            data = response.json()
            assert "external_id" in data
            assert "url" in data

    def test_create_issue_unsupported_type(self, client):
        """Test creating issue with unsupported integration type fails."""
        # Get a Slack integration (doesn't support issues)
        list_response = client.get("/api/v1/integrations?type=slack")
        items = list_response.json()

        if items:
            integration_id = items[0]["integration_id"]
            response = client.post(
                f"/api/v1/integrations/{integration_id}/issues",
                json={"alert_id": "alert-123"}
            )
            assert response.status_code == 400

    def test_send_notification(self, client):
        """Test sending a notification."""
        # Get a Slack integration
        list_response = client.get("/api/v1/integrations?type=slack&status=connected")
        items = list_response.json()

        if items:
            integration_id = items[0]["integration_id"]
            response = client.post(
                f"/api/v1/integrations/{integration_id}/notify",
                params={
                    "message": "Test notification",
                    "severity": "info"
                }
            )
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True

    def test_list_available_types(self, client):
        """Test listing available integration types."""
        response = client.get("/api/v1/integrations/types/available")
        assert response.status_code == 200

        data = response.json()
        assert "jira" in data
        assert "servicenow" in data
        assert "github" in data
        assert "slack" in data
        assert "pagerduty" in data
        assert "teams" in data

        # Check structure
        jira = data["jira"]
        assert "name" in jira
        assert "description" in jira
        assert "category" in jira
        assert "required_fields" in jira
