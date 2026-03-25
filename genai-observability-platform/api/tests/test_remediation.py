"""Tests for remediation endpoints."""

import pytest
from datetime import datetime


class TestRemediationEndpoints:
    """Tests for autonomous remediation endpoints."""

    def test_list_remediations(self, client):
        """Test listing all remediations."""
        response = client.get("/api/v1/remediation")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "has_more" in data
        assert isinstance(data["items"], list)

    def test_list_remediations_with_pagination(self, client):
        """Test listing remediations with pagination."""
        response = client.get("/api/v1/remediation?page=1&page_size=10")
        assert response.status_code == 200

        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_remediations_with_status_filter(self, client):
        """Test filtering remediations by status."""
        response = client.get("/api/v1/remediation?status=pending_approval")
        assert response.status_code == 200

        data = response.json()
        for item in data["items"]:
            assert item["status"] == "pending_approval"

    def test_get_remediation(self, client):
        """Test getting a specific remediation."""
        # First list to get an ID
        list_response = client.get("/api/v1/remediation")
        items = list_response.json()["items"]

        if items:
            remediation_id = items[0]["remediation_id"]
            response = client.get(f"/api/v1/remediation/{remediation_id}")
            assert response.status_code == 200

            data = response.json()
            assert data["remediation_id"] == remediation_id
            assert "action_plan" in data
            assert "status" in data

    def test_get_remediation_not_found(self, client):
        """Test getting a non-existent remediation."""
        response = client.get("/api/v1/remediation/non-existent-id")
        assert response.status_code == 404

    def test_create_remediation_plan(self, client):
        """Test creating a new remediation plan."""
        response = client.post(
            "/api/v1/remediation/plan",
            json={"investigation_id": "inv_test_123"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "remediation_id" in data
        assert data["investigation_id"] == "inv_test_123"
        assert data["status"] == "pending_approval"
        assert "action_plan" in data

    def test_approve_remediation(self, client):
        """Test approving a remediation."""
        # First create a remediation
        create_response = client.post(
            "/api/v1/remediation/plan",
            json={"investigation_id": "inv_test_456"}
        )
        remediation_id = create_response.json()["remediation_id"]

        # Then approve it
        response = client.post(
            f"/api/v1/remediation/{remediation_id}/approve",
            json={"notes": "Approved for testing"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_at"] is not None

    def test_approve_already_approved_remediation(self, client):
        """Test approving an already approved remediation fails."""
        # Create and approve
        create_response = client.post(
            "/api/v1/remediation/plan",
            json={"investigation_id": "inv_test_789"}
        )
        remediation_id = create_response.json()["remediation_id"]

        client.post(f"/api/v1/remediation/{remediation_id}/approve", json={})

        # Try to approve again
        response = client.post(f"/api/v1/remediation/{remediation_id}/approve", json={})
        assert response.status_code == 400

    def test_reject_remediation(self, client):
        """Test rejecting a remediation."""
        # First create a remediation
        create_response = client.post(
            "/api/v1/remediation/plan",
            json={"investigation_id": "inv_test_reject"}
        )
        remediation_id = create_response.json()["remediation_id"]

        # Then reject it
        response = client.post(
            f"/api/v1/remediation/{remediation_id}/reject",
            json={"reason": "Not applicable"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "rejected"

    def test_execute_remediation(self, client):
        """Test executing an approved remediation."""
        # Create and approve
        create_response = client.post(
            "/api/v1/remediation/plan",
            json={"investigation_id": "inv_test_exec"}
        )
        remediation_id = create_response.json()["remediation_id"]

        client.post(f"/api/v1/remediation/{remediation_id}/approve", json={})

        # Execute
        response = client.post(f"/api/v1/remediation/{remediation_id}/execute")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "in_progress"
        assert data["executed_at"] is not None

    def test_execute_unapproved_remediation_fails(self, client):
        """Test executing an unapproved remediation fails."""
        create_response = client.post(
            "/api/v1/remediation/plan",
            json={"investigation_id": "inv_test_unauth"}
        )
        remediation_id = create_response.json()["remediation_id"]

        response = client.post(f"/api/v1/remediation/{remediation_id}/execute")
        assert response.status_code == 400

    def test_rollback_remediation(self, client):
        """Test rolling back a remediation."""
        # Create, approve, and execute
        create_response = client.post(
            "/api/v1/remediation/plan",
            json={"investigation_id": "inv_test_rollback"}
        )
        remediation_id = create_response.json()["remediation_id"]

        client.post(f"/api/v1/remediation/{remediation_id}/approve", json={})
        client.post(f"/api/v1/remediation/{remediation_id}/execute")

        # Rollback
        response = client.post(
            f"/api/v1/remediation/{remediation_id}/rollback",
            json={"reason": "Testing rollback"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "rolled_back"

    def test_get_remediation_status(self, client):
        """Test getting remediation execution status."""
        # First list to get an ID
        list_response = client.get("/api/v1/remediation")
        items = list_response.json()["items"]

        if items:
            remediation_id = items[0]["remediation_id"]
            response = client.get(f"/api/v1/remediation/{remediation_id}/status")
            assert response.status_code == 200

            data = response.json()
            assert "remediation_id" in data
            assert "status" in data
            assert "total_steps" in data
            assert "completed_steps" in data
            assert "progress_percent" in data
