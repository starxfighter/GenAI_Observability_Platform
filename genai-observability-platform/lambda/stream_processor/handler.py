"""
Stream Processor Lambda

Processes events from Kinesis and routes them to appropriate storage backends.
"""

import base64
import json
import os
from datetime import datetime
from typing import Any, Dict, List

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Configuration
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
TIMESTREAM_DATABASE = os.environ.get("TIMESTREAM_DATABASE", "")
TIMESTREAM_TABLE = os.environ.get("TIMESTREAM_LATENCY_TABLE", "latency-metrics")
ERROR_STORE_TABLE = os.environ.get("ERROR_STORE_TABLE", "")
ANOMALY_DETECTOR_FUNCTION = os.environ.get("ANOMALY_DETECTOR_FUNCTION", "")

# Initialize clients
dynamodb = boto3.resource("dynamodb")
timestream = boto3.client("timestream-write")
lambda_client = boto3.client("lambda")

# OpenSearch client (lazy initialization)
_opensearch_client = None


def get_opensearch_client():
    """Get or create OpenSearch client."""
    global _opensearch_client

    if _opensearch_client is None and OPENSEARCH_ENDPOINT:
        region = os.environ.get("AWS_REGION", "us-east-1")
        credentials = boto3.Session().get_credentials()

        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            "aoss",
            session_token=credentials.token,
        )

        host = OPENSEARCH_ENDPOINT.replace("https://", "").replace("http://", "")
        _opensearch_client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )

    return _opensearch_client


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Kinesis stream processing.

    Args:
        event: Kinesis event with records
        context: Lambda context

    Returns:
        Processing result
    """
    records_processed = 0
    errors_detected = 0
    metrics_written = 0
    trace_indexed = 0

    error_events = []

    # Process Kinesis records
    for record in event.get("Records", []):
        try:
            # Decode Kinesis record
            payload = base64.b64decode(record["kinesis"]["data"])
            event_data = json.loads(payload)

            event_type = event_data.get("event_type", "unknown")

            # Route based on event type
            if event_type == "error":
                process_error(event_data)
                errors_detected += 1
                error_events.append(event_data)

            elif is_end_event(event_type):
                write_metrics(event_data)
                metrics_written += 1

            # Index all events to OpenSearch for tracing
            if write_to_opensearch(event_data):
                trace_indexed += 1

            records_processed += 1

        except Exception as e:
            print(f"Error processing record: {e}")
            continue

    # Trigger anomaly detection if we have errors
    if errors_detected > 0:
        trigger_anomaly_detection(len(error_events))

    result = {
        "statusCode": 200,
        "records_processed": records_processed,
        "errors_detected": errors_detected,
        "metrics_written": metrics_written,
        "trace_indexed": trace_indexed,
    }

    print(f"Processing complete: {json.dumps(result)}")
    return result


def is_end_event(event_type: str) -> bool:
    """Check if event type is an end event (has duration/metrics)."""
    return event_type in [
        "execution_end",
        "llm_call_end",
        "tool_call_end",
        "mcp_call_end",
    ]


def process_error(event_data: Dict[str, Any]) -> None:
    """
    Store error in DynamoDB for investigation.

    Args:
        event_data: Error event data
    """
    if not ERROR_STORE_TABLE:
        print("ERROR_STORE_TABLE not configured")
        return

    try:
        table = dynamodb.Table(ERROR_STORE_TABLE)

        # Generate error ID
        agent_id = event_data.get("agent_id", "unknown")
        execution_id = event_data.get("execution_id", "")
        timestamp = datetime.utcnow().timestamp()
        error_id = f"{agent_id}-{execution_id or 'no-exec'}-{timestamp}"

        # Calculate TTL (90 days)
        ttl = int(timestamp + (90 * 24 * 60 * 60))

        item = {
            "error_id": error_id,
            "agent_id": agent_id,
            "execution_id": execution_id,
            "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            "error_type": event_data.get("error_type", "unknown"),
            "error_message": event_data.get("error_message", ""),
            "severity": event_data.get("severity", "error"),
            "resolution_status": "open",
            "ttl": ttl,
        }

        # Optional fields
        if event_data.get("stack_trace"):
            item["stack_trace"] = event_data["stack_trace"]
        if event_data.get("context"):
            item["context"] = event_data["context"]

        table.put_item(Item=item)

    except Exception as e:
        print(f"Error storing error: {e}")


def write_metrics(event_data: Dict[str, Any]) -> None:
    """
    Write metrics to Timestream.

    Args:
        event_data: Event data with metrics
    """
    if not TIMESTREAM_DATABASE:
        print("TIMESTREAM_DATABASE not configured")
        return

    try:
        agent_id = event_data.get("agent_id", "unknown")
        event_type = event_data.get("event_type", "unknown")

        common_dimensions = [
            {"Name": "agent_id", "Value": agent_id},
            {"Name": "agent_type", "Value": event_data.get("agent_type", "unknown")},
            {"Name": "environment", "Value": event_data.get("environment", "unknown")},
        ]

        records = []
        current_time = str(int(datetime.utcnow().timestamp() * 1000))

        # Duration metric
        duration_ms = event_data.get("duration_ms")
        if duration_ms is not None:
            records.append(
                {
                    "Dimensions": common_dimensions
                    + [{"Name": "event_type", "Value": event_type}],
                    "MeasureName": "duration_ms",
                    "MeasureValue": str(duration_ms),
                    "MeasureValueType": "DOUBLE",
                    "Time": current_time,
                }
            )

        # Token metrics for LLM calls
        token_usage = event_data.get("token_usage")
        if event_type == "llm_call_end" and token_usage:
            model = event_data.get("model", "unknown")
            provider = event_data.get("provider", "unknown")

            model_dimensions = common_dimensions + [
                {"Name": "model", "Value": model},
                {"Name": "provider", "Value": provider},
            ]

            if token_usage.get("input_tokens"):
                records.append(
                    {
                        "Dimensions": model_dimensions,
                        "MeasureName": "input_tokens",
                        "MeasureValue": str(token_usage["input_tokens"]),
                        "MeasureValueType": "BIGINT",
                        "Time": current_time,
                    }
                )

            if token_usage.get("output_tokens"):
                records.append(
                    {
                        "Dimensions": model_dimensions,
                        "MeasureName": "output_tokens",
                        "MeasureValue": str(token_usage["output_tokens"]),
                        "MeasureValueType": "BIGINT",
                        "Time": current_time,
                    }
                )

        # Cost metric
        cost = event_data.get("cost")
        if cost and cost > 0:
            records.append(
                {
                    "Dimensions": common_dimensions,
                    "MeasureName": "cost_usd",
                    "MeasureValue": str(cost),
                    "MeasureValueType": "DOUBLE",
                    "Time": current_time,
                }
            )

        # Write to Timestream
        if records:
            timestream.write_records(
                DatabaseName=TIMESTREAM_DATABASE,
                TableName=TIMESTREAM_TABLE,
                Records=records,
            )

    except Exception as e:
        print(f"Error writing to Timestream: {e}")


def write_to_opensearch(event_data: Dict[str, Any]) -> bool:
    """
    Index event in OpenSearch for tracing.

    Args:
        event_data: Event data

    Returns:
        True if successful
    """
    opensearch = get_opensearch_client()
    if opensearch is None:
        return False

    try:
        # Use monthly indices for traces
        index_name = f"traces-{datetime.utcnow().strftime('%Y-%m')}"

        opensearch.index(index=index_name, body=event_data)
        return True

    except Exception as e:
        print(f"Error writing to OpenSearch: {e}")
        return False


def trigger_anomaly_detection(error_count: int) -> None:
    """
    Trigger anomaly detection Lambda asynchronously.

    Args:
        error_count: Number of errors in this batch
    """
    if not ANOMALY_DETECTOR_FUNCTION:
        return

    try:
        lambda_client.invoke(
            FunctionName=ANOMALY_DETECTOR_FUNCTION,
            InvocationType="Event",  # Async
            Payload=json.dumps(
                {
                    "trigger": "stream_processor",
                    "error_count": error_count,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            ),
        )
    except Exception as e:
        print(f"Error triggering anomaly detection: {e}")
