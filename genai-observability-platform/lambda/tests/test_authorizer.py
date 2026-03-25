"""Tests for authorizer Lambda function."""

import pytest
from unittest.mock import patch, MagicMock
import hashlib


class TestAuthorizer:
    """Tests for authorizer handler."""

    @pytest.fixture
    def mock_clients(self, mock_dynamodb):
        """Set up mock AWS clients."""
        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = mock_dynamodb
            yield mock_dynamodb

    def test_valid_api_key(self, authorizer_event, lambda_context, mock_clients):
        """Test authorization with valid API key."""
        # Set up mock to return valid API key
        key_hash = hashlib.sha256("test-api-key-123".encode()).hexdigest()
        mock_clients.get_item.return_value = {
            "Item": {
                "key_id": {"S": "key-123"},
                "key_hash": {"S": key_hash},
                "is_active": {"BOOL": True},
                "scopes": {"L": [{"S": "read"}, {"S": "write"}]},
            }
        }

        from authorizer.handler import handler
        result = handler(authorizer_event, lambda_context)

        assert result["principalId"] == "key-123"
        assert "Allow" in result["policyDocument"]["Statement"][0]["Effect"]

    def test_missing_api_key(self, authorizer_event, lambda_context, mock_clients):
        """Test authorization with missing API key."""
        # Remove API key from headers
        authorizer_event["headers"] = {}

        from authorizer.handler import handler
        result = handler(authorizer_event, lambda_context)

        assert "Deny" in result["policyDocument"]["Statement"][0]["Effect"]

    def test_invalid_api_key(self, authorizer_event, lambda_context, mock_clients):
        """Test authorization with invalid API key."""
        # Return empty result (key not found)
        mock_clients.get_item.return_value = {}

        from authorizer.handler import handler
        result = handler(authorizer_event, lambda_context)

        assert "Deny" in result["policyDocument"]["Statement"][0]["Effect"]

    def test_inactive_api_key(self, authorizer_event, lambda_context, mock_clients):
        """Test authorization with inactive API key."""
        key_hash = hashlib.sha256("test-api-key-123".encode()).hexdigest()
        mock_clients.get_item.return_value = {
            "Item": {
                "key_id": {"S": "key-123"},
                "key_hash": {"S": key_hash},
                "is_active": {"BOOL": False},  # Inactive
                "scopes": {"L": []},
            }
        }

        from authorizer.handler import handler
        result = handler(authorizer_event, lambda_context)

        assert "Deny" in result["policyDocument"]["Statement"][0]["Effect"]
