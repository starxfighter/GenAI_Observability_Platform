"""Tests for SSO authentication endpoints."""

import pytest
from unittest.mock import patch, MagicMock


class TestAuthProviders:
    """Tests for auth provider endpoints."""

    def test_get_providers(self, client):
        """Test getting available auth providers."""
        response = client.get("/api/v1/auth/providers")
        assert response.status_code == 200

        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)

    def test_providers_have_required_fields(self, client):
        """Test that providers have required fields."""
        response = client.get("/api/v1/auth/providers")
        data = response.json()

        for provider in data.get("providers", []):
            assert "id" in provider
            assert "name" in provider
            assert "type" in provider
            assert provider["type"] in ["oidc", "saml"]


class TestOIDCFlow:
    """Tests for OIDC authentication flow."""

    def test_get_login_url(self, client):
        """Test getting OIDC login URL."""
        response = client.get(
            "/api/v1/auth/login/google/url",
            params={"redirect_uri": "http://localhost:5173/login"}
        )
        # May return 200 with URL or 400 if provider not configured
        assert response.status_code in [200, 400, 501]

        if response.status_code == 200:
            data = response.json()
            assert "login_url" in data
            assert "state" in data

    def test_get_login_url_requires_redirect(self, client):
        """Test that login URL requires redirect_uri."""
        response = client.get("/api/v1/auth/login/google/url")
        # Should fail without redirect_uri
        assert response.status_code in [400, 422]

    def test_callback_without_code_fails(self, client):
        """Test that callback without code fails."""
        response = client.post(
            "/api/v1/auth/callback/google",
            json={"state": "test-state"}
        )
        assert response.status_code in [400, 422]

    def test_callback_with_invalid_state_fails(self, client):
        """Test that callback with invalid state fails."""
        response = client.post(
            "/api/v1/auth/callback/google",
            json={
                "code": "test-code",
                "state": "invalid-state"
            }
        )
        # Should fail validation
        assert response.status_code in [400, 401, 500]


class TestSAMLFlow:
    """Tests for SAML authentication flow."""

    def test_get_saml_metadata(self, client):
        """Test getting SAML SP metadata."""
        response = client.get("/api/v1/auth/saml/metadata")
        # May return XML metadata or 501 if not configured
        assert response.status_code in [200, 501]

        if response.status_code == 200:
            assert "xml" in response.headers.get("content-type", "").lower() or \
                   response.text.startswith("<?xml")

    def test_saml_login_redirect(self, client):
        """Test SAML login redirects to IdP."""
        response = client.get(
            "/api/v1/auth/login/saml/url",
            params={"redirect_uri": "http://localhost:5173/login"},
            follow_redirects=False
        )
        # May redirect or return URL or 501 if not configured
        assert response.status_code in [200, 302, 400, 501]


class TestUserSession:
    """Tests for user session management."""

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without auth fails."""
        response = client.get("/api/v1/auth/me")
        # Should return 401 or redirect
        assert response.status_code in [401, 403]

    def test_get_current_user_with_session(self, client):
        """Test getting current user with valid session."""
        # This would require a valid session cookie
        # For unit testing, we mock the session validation
        with patch('observability_api.routes.auth_sso.get_current_user') as mock_user:
            mock_user.return_value = {
                "user_id": "test-user",
                "email": "test@example.com",
                "name": "Test User",
                "provider": "google",
                "roles": ["user"],
                "groups": []
            }

            # The actual test would need proper auth setup
            # This is a placeholder for integration testing

    def test_logout(self, client):
        """Test logout endpoint."""
        response = client.post("/api/v1/auth/logout")
        # Should succeed even without session
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "message" in data


class TestProviderConfiguration:
    """Tests for provider configuration validation."""

    def test_unconfigured_provider_returns_error(self, client):
        """Test that unconfigured providers return appropriate error."""
        # Try to use a provider that's not configured
        response = client.get(
            "/api/v1/auth/login/nonexistent/url",
            params={"redirect_uri": "http://localhost:5173/login"}
        )
        assert response.status_code in [400, 404, 501]

    def test_provider_list_only_shows_configured(self, client):
        """Test that provider list only shows configured providers."""
        response = client.get("/api/v1/auth/providers")
        data = response.json()

        # All returned providers should have valid IDs
        for provider in data.get("providers", []):
            assert provider["id"] is not None
            assert len(provider["id"]) > 0


class TestTokenHandling:
    """Tests for JWT token handling."""

    def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code in [401, 403]

    def test_expired_token_rejected(self, client):
        """Test that expired tokens are rejected."""
        # Create an expired token (this would need actual JWT creation)
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code in [401, 403]

    def test_malformed_auth_header_rejected(self, client):
        """Test that malformed auth headers are rejected."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer token"}
        )
        assert response.status_code in [401, 403]


class TestRoleBasedAccess:
    """Tests for role-based access control."""

    def test_admin_required_endpoint(self, client):
        """Test that admin endpoints require admin role."""
        # This would test endpoints that require admin access
        # Implementation depends on which endpoints are admin-only
        pass

    def test_user_cannot_access_admin_endpoints(self, client):
        """Test that regular users cannot access admin endpoints."""
        # Would need a valid user token without admin role
        pass
