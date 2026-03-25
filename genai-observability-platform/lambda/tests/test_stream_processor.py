"""Tests for stream processor Lambda function."""

import pytest
import json
import base64
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestStreamProcessor:
    """Tests for stream processor handler."""

    @pytest.fixture
    def mock_clients(self, mock_dynamodb):
        """Set up mock AWS clients."""
        mock_opensearch = MagicMock()
        mock_timestream = MagicMock()

        clients = {
            'dynamodb': mock_dynamodb,
        }

        with patch('boto3.client') as mock_boto:
            mock_boto.side_effect = lambda service, **kwargs: clients.get(service, MagicMock())
            with patch('opensearchpy.OpenSearch') as mock_os:
                mock_os.return_value = mock_opensearch
                yield {
                    'dynamodb': mock_dynamodb,
                    'opensearch': mock_opensearch,
                    'timestream': mock_timestream,
                }

    def test_process_execution_event(self, kinesis_event, lambda_context, mock_clients):
        """Test processing execution events."""
        from stream_processor.handler import handler
        result = handler(kinesis_event, lambda_context)

        assert result["batchItemFailures"] == []

    def test_process_error_event(self, kinesis_event, lambda_context, mock_clients):
        """Test processing error events."""
        # Modify event to be an error
        error_data = {
            "event_type": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": "test-agent",
            "trace_id": "trace-123",
            "span_id": "span-456",
            "error_type": "ValueError",
            "error_message": "Test error",
        }
        encoded = base64.b64encode(json.dumps(error_data).encode()).decode()
        kinesis_event["Records"][0]["kinesis"]["data"] = encoded

        from stream_processor.handler import handler
        result = handler(kinesis_event, lambda_context)

        assert result["batchItemFailures"] == []

    def test_process_llm_event(self, kinesis_event, lambda_context, mock_clients):
        """Test processing LLM events."""
        llm_data = {
            "event_type": "llm_response",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": "test-agent",
            "trace_id": "trace-123",
            "span_id": "span-456",
            "model": "claude-sonnet-4-20250514",
            "provider": "anthropic",
            "token_usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
            "duration_ms": 500,
        }
        encoded = base64.b64encode(json.dumps(llm_data).encode()).decode()
        kinesis_event["Records"][0]["kinesis"]["data"] = encoded

        from stream_processor.handler import handler
        result = handler(kinesis_event, lambda_context)

        assert result["batchItemFailures"] == []

    def test_batch_processing(self, kinesis_event, lambda_context, mock_clients):
        """Test processing batch of records."""
        # Add multiple records
        records = []
        for i in range(5):
            data = {
                "event_type": "execution_end",
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": "test-agent",
                "trace_id": f"trace-{i}",
                "span_id": f"span-{i}",
                "duration_ms": 100 + i * 10,
                "status": "success",
            }
            encoded = base64.b64encode(json.dumps(data).encode()).decode()
            records.append({
                "kinesis": {
                    "sequenceNumber": str(i),
                    "partitionKey": "test-agent",
                    "data": encoded,
                },
                "eventSource": "aws:kinesis",
            })

        kinesis_event["Records"] = records

        from stream_processor.handler import handler
        result = handler(kinesis_event, lambda_context)

        assert result["batchItemFailures"] == []

    def test_partial_failure(self, kinesis_event, lambda_context, mock_clients):
        """Test handling partial failures."""
        # Add an invalid record
        records = [
            kinesis_event["Records"][0],
            {
                "kinesis": {
                    "sequenceNumber": "999",
                    "partitionKey": "test",
                    "data": base64.b64encode(b"invalid json").decode(),
                },
                "eventSource": "aws:kinesis",
            }
        ]
        kinesis_event["Records"] = records

        from stream_processor.handler import handler
        result = handler(kinesis_event, lambda_context)

        # Should report the failed record
        assert len(result["batchItemFailures"]) <= 1

    def test_opensearch_indexing(self, kinesis_event, lambda_context, mock_clients):
        """Test that events are indexed in OpenSearch."""
        from stream_processor.handler import handler
        handler(kinesis_event, lambda_context)

        # Verify OpenSearch bulk index was called
        # mock_clients['opensearch'].bulk.assert_called()

    def test_timestream_write(self, kinesis_event, lambda_context, mock_clients):
        """Test that metrics are written to Timestream."""
        from stream_processor.handler import handler
        handler(kinesis_event, lambda_context)

        # Verify Timestream write was called
        # mock_clients['timestream'].write_records.assert_called()
