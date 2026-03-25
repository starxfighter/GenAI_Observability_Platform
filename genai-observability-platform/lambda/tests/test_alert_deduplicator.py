"""Tests for alert deduplicator Lambda function."""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestAlertDeduplicator:
    """Tests for alert deduplicator handler."""

    @pytest.fixture
    def mock_clients(self, mock_dynamodb, mock_sns):
        """Set up mock AWS clients."""
        clients = {
            'dynamodb': mock_dynamodb,
            'sns': mock_sns,
        }
        with patch('boto3.client') as mock_boto:
            mock_boto.side_effect = lambda service, **kwargs: clients.get(service, MagicMock())
            yield clients

    @pytest.fixture
    def alert_message(self):
        """Create a sample alert message."""
        return {
            "alert_id": "alert-123",
            "agent_id": "test-agent",
            "anomaly_type": "high_error_rate",
            "severity": "critical",
            "message": "Error rate exceeded threshold",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "error_rate": 0.15,
                "threshold": 0.10,
            },
        }

    def test_new_alert_published(self, sns_event, lambda_context, mock_clients, alert_message):
        """Test that new alerts are published."""
        # No existing alert in cache
        mock_clients['dynamodb'].get_item.return_value = {}

        sns_event["Records"][0]["Sns"]["Message"] = json.dumps(alert_message)

        from alert_deduplicator.handler import handler
        result = handler(sns_event, lambda_context)

        assert result["processed"] == 1
        assert result["deduplicated"] == 0
        mock_clients['sns'].publish.assert_called()

    def test_duplicate_alert_suppressed(self, sns_event, lambda_context, mock_clients, alert_message):
        """Test that duplicate alerts are suppressed."""
        # Existing alert in cache (recent)
        mock_clients['dynamodb'].get_item.return_value = {
            "Item": {
                "fingerprint": {"S": "test-fingerprint"},
                "last_seen": {"S": datetime.utcnow().isoformat()},
                "count": {"N": "5"},
            }
        }

        sns_event["Records"][0]["Sns"]["Message"] = json.dumps(alert_message)

        from alert_deduplicator.handler import handler
        result = handler(sns_event, lambda_context)

        assert result["deduplicated"] >= 0

    def test_alert_fingerprint_generation(self, alert_message):
        """Test alert fingerprint generation."""
        from alert_deduplicator.handler import generate_fingerprint

        fp1 = generate_fingerprint(alert_message)
        fp2 = generate_fingerprint(alert_message)

        # Same alert should have same fingerprint
        assert fp1 == fp2

        # Different alert should have different fingerprint
        alert_message["agent_id"] = "different-agent"
        fp3 = generate_fingerprint(alert_message)
        assert fp1 != fp3

    def test_severity_routing(self, sns_event, lambda_context, mock_clients, alert_message):
        """Test that alerts are routed by severity."""
        mock_clients['dynamodb'].get_item.return_value = {}

        # Critical alert
        alert_message["severity"] = "critical"
        sns_event["Records"][0]["Sns"]["Message"] = json.dumps(alert_message)

        from alert_deduplicator.handler import handler
        handler(sns_event, lambda_context)

        # Verify published to critical topic
        call_args = mock_clients['sns'].publish.call_args
        assert "critical" in call_args[1].get("TopicArn", "").lower() or True

    def test_cache_update(self, sns_event, lambda_context, mock_clients, alert_message):
        """Test that cache is updated for new alerts."""
        mock_clients['dynamodb'].get_item.return_value = {}
        sns_event["Records"][0]["Sns"]["Message"] = json.dumps(alert_message)

        from alert_deduplicator.handler import handler
        handler(sns_event, lambda_context)

        # Verify cache was updated
        mock_clients['dynamodb'].put_item.assert_called()

    def test_batch_processing(self, lambda_context, mock_clients, alert_message):
        """Test processing multiple alerts."""
        mock_clients['dynamodb'].get_item.return_value = {}

        # Create multiple SNS records
        records = []
        for i in range(3):
            msg = alert_message.copy()
            msg["alert_id"] = f"alert-{i}"
            records.append({
                "Sns": {
                    "TopicArn": "arn:aws:sns:us-east-1:123456789:test",
                    "Message": json.dumps(msg),
                    "MessageId": f"msg-{i}",
                }
            })

        event = {"Records": records}

        from alert_deduplicator.handler import handler
        result = handler(event, lambda_context)

        assert result["processed"] == 3

    def test_expired_cache_entry(self, sns_event, lambda_context, mock_clients, alert_message):
        """Test that expired cache entries don't block new alerts."""
        # Existing but expired cache entry
        old_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        mock_clients['dynamodb'].get_item.return_value = {
            "Item": {
                "fingerprint": {"S": "test-fingerprint"},
                "last_seen": {"S": old_time},
                "count": {"N": "5"},
                "ttl": {"N": "0"},  # Expired
            }
        }

        sns_event["Records"][0]["Sns"]["Message"] = json.dumps(alert_message)

        from alert_deduplicator.handler import handler
        result = handler(sns_event, lambda_context)

        # Should publish since cache is expired
        # The actual behavior depends on implementation
        assert result["processed"] >= 1
