"""Pytest fixtures for Portal API tests."""

import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import AsyncGenerator

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Set environment variables before importing app
os.environ.update({
    "OBSERVABILITY_ENVIRONMENT": "test",
    "OBSERVABILITY_DEBUG": "true",
    "OBSERVABILITY_AWS_REGION": "us-east-1",
    "OBSERVABILITY_JWT_SECRET_KEY": "test-secret-key",
    "OBSERVABILITY_TRACES_TABLE": "test-traces",
    "OBSERVABILITY_AGENTS_TABLE": "test-agents",
    "OBSERVABILITY_ALERTS_TABLE": "test-alerts",
})


@pytest.fixture
def mock_dynamodb_client():
    """Create a mock DynamoDB client."""
    mock = MagicMock()

    # Traces
    mock.get_trace = AsyncMock(return_value={
        "trace_id": "trace-123",
        "agent_id": "test-agent",
        "name": "Test Trace",
        "start_time": datetime.utcnow().isoformat(),
        "status": "completed",
        "duration_ms": 150,
        "spans": [],
    })
    mock.list_traces = AsyncMock(return_value=([
        {
            "trace_id": "trace-123",
            "agent_id": "test-agent",
            "name": "Test Trace",
            "start_time": datetime.utcnow().isoformat(),
            "status": "completed",
            "duration_ms": 150,
            "spans": [],
        }
    ], None))
    mock.create_trace = AsyncMock()
    mock.update_trace = AsyncMock()

    # Agents
    mock.get_agent = AsyncMock(return_value={
        "agent_id": "test-agent",
        "name": "Test Agent",
        "framework": "LangChain",
        "version": "1.0.0",
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {},
    })
    mock.list_agents = AsyncMock(return_value=([
        {
            "agent_id": "test-agent",
            "name": "Test Agent",
            "framework": "LangChain",
            "version": "1.0.0",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
        }
    ], None))
    mock.create_agent = AsyncMock()
    mock.update_agent = AsyncMock()
    mock.delete_agent = AsyncMock(return_value=True)

    # Alerts
    mock.get_alert = AsyncMock(return_value={
        "alert_id": "alert-123",
        "agent_id": "test-agent",
        "anomaly_type": "high_error_rate",
        "severity": "critical",
        "status": "open",
        "message": "Error rate exceeded",
        "timestamp": datetime.utcnow().isoformat(),
        "details": {},
    })
    mock.list_alerts = AsyncMock(return_value=([
        {
            "alert_id": "alert-123",
            "agent_id": "test-agent",
            "anomaly_type": "high_error_rate",
            "severity": "critical",
            "status": "open",
            "message": "Error rate exceeded",
            "timestamp": datetime.utcnow().isoformat(),
        }
    ], None))
    mock.create_alert = AsyncMock()
    mock.update_alert = AsyncMock()
    mock.get_investigation = AsyncMock(return_value=None)

    # API Keys
    mock.get_api_key_by_hash = AsyncMock(return_value={
        "key_id": "key-123",
        "is_active": True,
        "scopes": ["read", "write"],
    })
    mock.update_api_key_last_used = AsyncMock()

    return mock


@pytest.fixture
def mock_timestream_client():
    """Create a mock Timestream client."""
    mock = MagicMock()
    mock.get_dashboard_metrics = AsyncMock(return_value={
        "period": "24h",
        "total_traces": 1000,
        "total_errors": 10,
        "avg_latency_ms": 250,
        "p95_latency_ms": 500,
        "total_tokens": 100000,
        "total_cost": 10.50,
    })
    mock.get_latency_series = AsyncMock(return_value=[
        {"timestamp": datetime.utcnow().isoformat(), "value": 250, "p95": 500}
    ])
    mock.get_request_series = AsyncMock(return_value=[
        {"timestamp": datetime.utcnow().isoformat(), "value": 100}
    ])
    mock.get_agent_metrics = AsyncMock(return_value={
        "agent_id": "test-agent",
        "period": "24h",
        "request_count": 100,
        "error_count": 5,
        "error_rate": 0.05,
        "avg_latency_ms": 250,
        "p50_latency_ms": 200,
        "p95_latency_ms": 500,
        "p99_latency_ms": 800,
        "total_tokens": 10000,
        "input_tokens": 6000,
        "output_tokens": 4000,
        "total_cost": 1.50,
    })
    return mock


@pytest.fixture
def mock_opensearch_client():
    """Create a mock OpenSearch client."""
    mock = MagicMock()
    mock.search_traces = AsyncMock(return_value=([], 0))
    mock.search_spans = AsyncMock(return_value=([], 0))
    return mock


@pytest.fixture
def app(mock_dynamodb_client, mock_timestream_client, mock_opensearch_client):
    """Create a test app with mocked dependencies."""
    with patch('observability_api.db.dynamodb.DynamoDBClient', return_value=mock_dynamodb_client):
        with patch('observability_api.db.timestream.TimestreamClient', return_value=mock_timestream_client):
            with patch('observability_api.db.opensearch.OpenSearchClient', return_value=mock_opensearch_client):
                from observability_api.main import create_app
                return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {"X-API-Key": "test-api-key-123"}


@pytest.fixture
def sample_trace():
    """Create a sample trace."""
    return {
        "trace_id": "trace-123",
        "agent_id": "test-agent",
        "name": "Test Trace",
        "start_time": datetime.utcnow().isoformat(),
        "status": "completed",
        "duration_ms": 150,
        "spans": [
            {
                "span_id": "span-1",
                "trace_id": "trace-123",
                "name": "root",
                "span_type": "execution",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration_ms": 150,
                "status": "completed",
            }
        ],
    }


@pytest.fixture
def sample_agent():
    """Create a sample agent."""
    return {
        "agent_id": "test-agent",
        "name": "Test Agent",
        "framework": "LangChain",
        "version": "1.0.0",
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {"team": "platform"},
    }


@pytest.fixture
def sample_alert():
    """Create a sample alert."""
    return {
        "alert_id": "alert-123",
        "agent_id": "test-agent",
        "anomaly_type": "high_error_rate",
        "severity": "critical",
        "status": "open",
        "message": "Error rate exceeded threshold",
        "timestamp": datetime.utcnow().isoformat(),
        "details": {"error_rate": 0.15, "threshold": 0.10},
    }
