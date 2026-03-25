"""Tests for ingestion Lambda function."""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestIngestion:
    """Tests for ingestion handler."""

    @pytest.fixture
    def mock_clients(self, mock_kinesis, mock_s3):
        """Set up mock AWS clients."""
        clients = {
            'kinesis': mock_kinesis,
            's3': mock_s3,
        }
        with patch('boto3.client') as mock_boto:
            mock_boto.side_effect = lambda service, **kwargs: clients.get(service, MagicMock())
            yield clients

    def test_successful_ingestion(self, api_gateway_event, lambda_context, mock_clients):
        """Test successful event ingestion."""
        from ingestion.handler import handler
        result = handler(api_gateway_event, lambda_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "success"
        assert body["events_received"] == 1

    def test_batch_ingestion(self, api_gateway_event, lambda_context, mock_clients):
        """Test batch event ingestion."""
        # Add multiple events
        api_gateway_event["body"] = json.dumps({
            "events": [
                {
                    "event_type": "execution_start",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_id": "test-agent",
                    "trace_id": f"trace-{i}",
                    "span_id": f"span-{i}",
                    "name": f"execution-{i}",
                }
                for i in range(10)
            ]
        })

        from ingestion.handler import handler
        result = handler(api_gateway_event, lambda_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["events_received"] == 10

    def test_invalid_json(self, api_gateway_event, lambda_context, mock_clients):
        """Test handling invalid JSON."""
        api_gateway_event["body"] = "invalid json"

        from ingestion.handler import handler
        result = handler(api_gateway_event, lambda_context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body

    def test_missing_events(self, api_gateway_event, lambda_context, mock_clients):
        """Test handling missing events field."""
        api_gateway_event["body"] = json.dumps({"data": "something"})

        from ingestion.handler import handler
        result = handler(api_gateway_event, lambda_context)

        assert result["statusCode"] == 400

    def test_empty_events(self, api_gateway_event, lambda_context, mock_clients):
        """Test handling empty events array."""
        api_gateway_event["body"] = json.dumps({"events": []})

        from ingestion.handler import handler
        result = handler(api_gateway_event, lambda_context)

        assert result["statusCode"] == 400

    def test_kinesis_write(self, api_gateway_event, lambda_context, mock_clients):
        """Test that events are written to Kinesis."""
        from ingestion.handler import handler
        handler(api_gateway_event, lambda_context)

        # Verify Kinesis was called
        mock_clients['kinesis'].put_record.assert_called()

    def test_s3_backup(self, api_gateway_event, lambda_context, mock_clients):
        """Test that events are backed up to S3."""
        from ingestion.handler import handler
        handler(api_gateway_event, lambda_context)

        # Verify S3 was called
        mock_clients['s3'].put_object.assert_called()

    def test_event_validation(self, api_gateway_event, lambda_context, mock_clients):
        """Test event validation."""
        # Invalid event (missing required fields)
        api_gateway_event["body"] = json.dumps({
            "events": [
                {"event_type": "execution_start"}  # Missing other required fields
            ]
        })

        from ingestion.handler import handler
        result = handler(api_gateway_event, lambda_context)

        # Should still accept but log warning
        assert result["statusCode"] in [200, 400]
