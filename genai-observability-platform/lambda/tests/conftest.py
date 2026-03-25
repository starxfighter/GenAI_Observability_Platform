"""Pytest fixtures for Lambda function tests."""

import json
import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# Set up environment variables before importing handlers
@pytest.fixture(autouse=True)
def set_env_vars():
    """Set environment variables for testing."""
    env_vars = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "DEBUG",
        "AWS_REGION": "us-east-1",
        "API_KEYS_TABLE": "test-api-keys",
        "KINESIS_STREAM": "test-kinesis-stream",
        "RAW_EVENTS_BUCKET": "test-raw-events",
        "OPENSEARCH_ENDPOINT": "https://test-opensearch.example.com",
        "TIMESTREAM_DATABASE": "test-database",
        "TIMESTREAM_TABLE": "test-table",
        "ERROR_STORE_TABLE": "test-errors",
        "INVESTIGATION_FUNCTION": "test-investigation-function",
        "ANTHROPIC_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789:secret:anthropic-key",
        "INVESTIGATION_RESULTS_TABLE": "test-investigations",
        "NOTIFICATION_TOPIC": "arn:aws:sns:us-east-1:123456789:test-notifications",
        "SLACK_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789:secret:slack",
        "PAGERDUTY_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789:secret:pagerduty",
        "ALERT_CACHE_TABLE": "test-alert-cache",
        "CRITICAL_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789:test-critical",
        "WARNING_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789:test-warning",
    }
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def lambda_context():
    """Create a mock Lambda context."""
    context = MagicMock()
    context.function_name = "test-function"
    context.function_version = "$LATEST"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:test"
    context.memory_limit_in_mb = 128
    context.aws_request_id = "test-request-id-123"
    context.log_group_name = "/aws/lambda/test-function"
    context.log_stream_name = "2024/01/01/[$LATEST]abc123"
    context.get_remaining_time_in_millis = MagicMock(return_value=30000)
    return context


@pytest.fixture
def api_gateway_event():
    """Create a sample API Gateway event."""
    return {
        "httpMethod": "POST",
        "path": "/ingest",
        "headers": {
            "Content-Type": "application/json",
            "X-API-Key": "test-api-key-123",
        },
        "body": json.dumps({
            "events": [
                {
                    "event_type": "execution_start",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_id": "test-agent",
                    "trace_id": "trace-123",
                    "span_id": "span-456",
                    "name": "test-execution",
                }
            ]
        }),
        "requestContext": {
            "requestId": "test-request-id",
            "stage": "test",
        },
        "isBase64Encoded": False,
    }


@pytest.fixture
def authorizer_event():
    """Create a sample authorizer event."""
    return {
        "type": "REQUEST",
        "methodArn": "arn:aws:execute-api:us-east-1:123456789:api/test/POST/ingest",
        "headers": {
            "X-API-Key": "test-api-key-123",
        },
        "requestContext": {
            "requestId": "test-request-id",
        },
    }


@pytest.fixture
def kinesis_event():
    """Create a sample Kinesis event."""
    record_data = {
        "event_type": "execution_end",
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": "test-agent",
        "trace_id": "trace-123",
        "span_id": "span-456",
        "name": "test-execution",
        "duration_ms": 150,
        "status": "success",
    }

    import base64
    encoded_data = base64.b64encode(json.dumps(record_data).encode()).decode()

    return {
        "Records": [
            {
                "kinesis": {
                    "sequenceNumber": "123456789",
                    "partitionKey": "test-agent",
                    "data": encoded_data,
                    "approximateArrivalTimestamp": 1234567890.123,
                },
                "eventSource": "aws:kinesis",
                "eventSourceARN": "arn:aws:kinesis:us-east-1:123456789:stream/test-stream",
            }
        ]
    }


@pytest.fixture
def sns_event():
    """Create a sample SNS event."""
    message = {
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

    return {
        "Records": [
            {
                "Sns": {
                    "TopicArn": "arn:aws:sns:us-east-1:123456789:test-topic",
                    "Message": json.dumps(message),
                    "MessageId": "msg-123",
                    "Timestamp": datetime.utcnow().isoformat(),
                }
            }
        ]
    }


@pytest.fixture
def scheduled_event():
    """Create a sample scheduled event."""
    return {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "detail": {},
        "time": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_dynamodb():
    """Create a mock DynamoDB client."""
    mock = MagicMock()
    mock.get_item = MagicMock(return_value={
        "Item": {
            "key_id": {"S": "key-123"},
            "key_hash": {"S": "hashed-key"},
            "is_active": {"BOOL": True},
            "scopes": {"L": [{"S": "read"}, {"S": "write"}]},
        }
    })
    mock.put_item = MagicMock(return_value={})
    mock.query = MagicMock(return_value={"Items": []})
    mock.scan = MagicMock(return_value={"Items": []})
    return mock


@pytest.fixture
def mock_kinesis():
    """Create a mock Kinesis client."""
    mock = MagicMock()
    mock.put_record = MagicMock(return_value={
        "ShardId": "shard-123",
        "SequenceNumber": "123456789",
    })
    mock.put_records = MagicMock(return_value={
        "FailedRecordCount": 0,
        "Records": [],
    })
    return mock


@pytest.fixture
def mock_s3():
    """Create a mock S3 client."""
    mock = MagicMock()
    mock.put_object = MagicMock(return_value={})
    mock.get_object = MagicMock(return_value={
        "Body": MagicMock(read=MagicMock(return_value=b"{}"))
    })
    return mock


@pytest.fixture
def mock_sns():
    """Create a mock SNS client."""
    mock = MagicMock()
    mock.publish = MagicMock(return_value={"MessageId": "msg-123"})
    return mock


@pytest.fixture
def mock_secretsmanager():
    """Create a mock Secrets Manager client."""
    mock = MagicMock()
    mock.get_secret_value = MagicMock(return_value={
        "SecretString": json.dumps({
            "api_key": "test-secret-key",
            "webhook_url": "https://hooks.slack.com/test",
            "routing_key": "test-routing-key",
        })
    })
    return mock


@pytest.fixture
def mock_lambda():
    """Create a mock Lambda client."""
    mock = MagicMock()
    mock.invoke = MagicMock(return_value={
        "StatusCode": 200,
        "Payload": MagicMock(read=MagicMock(return_value=b'{"status": "success"}')),
    })
    return mock
