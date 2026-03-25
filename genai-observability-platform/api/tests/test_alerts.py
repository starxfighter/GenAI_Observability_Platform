"""Tests for alerts endpoints."""

import pytest


class TestAlertsEndpoints:
    """Tests for alert endpoints."""

    def test_list_alerts(self, client, auth_headers):
        """Test listing alerts."""
        response = client.get("/api/v1/alerts", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_alerts_with_filters(self, client, auth_headers):
        """Test listing alerts with filters."""
        response = client.get(
            "/api/v1/alerts",
            params={
                "agent_id": "test-agent",
                "status": "open",
                "severity": "critical",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_get_alert_counts(self, client, auth_headers):
        """Test getting alert counts."""
        response = client.get("/api/v1/alerts/counts", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "critical" in data
        assert "warning" in data

    def test_get_alert(self, client, auth_headers, sample_alert):
        """Test getting a single alert."""
        response = client.get(
            f"/api/v1/alerts/{sample_alert['alert_id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["alert_id"] == sample_alert["alert_id"]

    def test_get_alert_not_found(self, client, auth_headers, mock_dynamodb_client):
        """Test getting non-existent alert."""
        mock_dynamodb_client.get_alert.return_value = None

        response = client.get(
            "/api/v1/alerts/non-existent-alert",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_create_alert(self, client, auth_headers):
        """Test creating an alert."""
        response = client.post(
            "/api/v1/alerts",
            json={
                "agent_id": "test-agent",
                "anomaly_type": "high_latency",
                "severity": "warning",
                "message": "Latency spike detected",
                "details": {"latency_ms": 5000},
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        data = response.json()
        assert "alert_id" in data
        assert data["anomaly_type"] == "high_latency"
        assert data["severity"] == "warning"

    def test_acknowledge_alert(self, client, auth_headers, sample_alert, mock_dynamodb_client):
        """Test acknowledging an alert."""
        mock_dynamodb_client.update_alert.return_value = {
            **sample_alert,
            "status": "acknowledged",
        }

        response = client.post(
            f"/api/v1/alerts/{sample_alert['alert_id']}/acknowledge",
            json={
                "action": "acknowledge",
                "user": "test-user",
                "comment": "Looking into it",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "acknowledged"

    def test_resolve_alert(self, client, auth_headers, sample_alert, mock_dynamodb_client):
        """Test resolving an alert."""
        mock_dynamodb_client.update_alert.return_value = {
            **sample_alert,
            "status": "resolved",
        }

        response = client.post(
            f"/api/v1/alerts/{sample_alert['alert_id']}/resolve",
            json={
                "action": "resolve",
                "user": "test-user",
                "comment": "Fixed the issue",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "resolved"

    def test_invalid_action(self, client, auth_headers, sample_alert):
        """Test invalid action on acknowledge endpoint."""
        response = client.post(
            f"/api/v1/alerts/{sample_alert['alert_id']}/acknowledge",
            json={
                "action": "resolve",  # Wrong action for this endpoint
                "user": "test-user",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_get_alert_investigation(self, client, auth_headers, sample_alert, mock_dynamodb_client):
        """Test getting alert investigation."""
        mock_dynamodb_client.get_investigation.return_value = {
            "investigation_id": "inv-123",
            "alert_id": sample_alert["alert_id"],
            "root_cause": "Database connection pool exhausted",
            "evidence": ["High connection count", "Slow queries"],
            "recommendations": ["Increase pool size", "Optimize queries"],
            "confidence": 0.85,
        }

        response = client.get(
            f"/api/v1/alerts/{sample_alert['alert_id']}/investigation",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["alert_id"] == sample_alert["alert_id"]
        assert "root_cause" in data
        assert "recommendations" in data

    def test_get_investigation_not_found(self, client, auth_headers, sample_alert, mock_dynamodb_client):
        """Test getting non-existent investigation."""
        mock_dynamodb_client.get_investigation.return_value = None

        response = client.get(
            f"/api/v1/alerts/{sample_alert['alert_id']}/investigation",
            headers=auth_headers,
        )
        assert response.status_code == 404
