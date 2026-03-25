"""
Health Check Lambda

Provides health status for the observability platform.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict

import boto3

# Configuration
KINESIS_STREAM = os.environ.get("KINESIS_STREAM", "")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
TIMESTREAM_DATABASE = os.environ.get("TIMESTREAM_DATABASE", "")
ERROR_STORE_TABLE = os.environ.get("ERROR_STORE_TABLE", "")

# Initialize clients
kinesis = boto3.client("kinesis")
dynamodb = boto3.resource("dynamodb")
timestream_query = boto3.client("timestream-query")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for health checks.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Health status response
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": os.environ.get("VERSION", "1.0.0"),
        "components": {},
    }

    issues = []

    # Check Kinesis
    kinesis_status = check_kinesis()
    health_status["components"]["kinesis"] = kinesis_status
    if kinesis_status["status"] != "healthy":
        issues.append("kinesis")

    # Check DynamoDB
    dynamodb_status = check_dynamodb()
    health_status["components"]["dynamodb"] = dynamodb_status
    if dynamodb_status["status"] != "healthy":
        issues.append("dynamodb")

    # Check Timestream
    timestream_status = check_timestream()
    health_status["components"]["timestream"] = timestream_status
    if timestream_status["status"] != "healthy":
        issues.append("timestream")

    # Overall status
    if issues:
        health_status["status"] = "degraded"
        health_status["issues"] = issues

    # Determine HTTP status code
    status_code = 200 if health_status["status"] == "healthy" else 503

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        },
        "body": json.dumps(health_status),
    }


def check_kinesis() -> Dict[str, Any]:
    """Check Kinesis stream health."""
    if not KINESIS_STREAM:
        return {"status": "unconfigured", "message": "Stream not configured"}

    try:
        response = kinesis.describe_stream_summary(StreamName=KINESIS_STREAM)
        stream_status = response["StreamDescriptionSummary"]["StreamStatus"]

        if stream_status == "ACTIVE":
            return {
                "status": "healthy",
                "stream_name": KINESIS_STREAM,
                "shard_count": response["StreamDescriptionSummary"]["OpenShardCount"],
            }
        else:
            return {
                "status": "unhealthy",
                "stream_name": KINESIS_STREAM,
                "stream_status": stream_status,
            }

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_dynamodb() -> Dict[str, Any]:
    """Check DynamoDB table health."""
    if not ERROR_STORE_TABLE:
        return {"status": "unconfigured", "message": "Table not configured"}

    try:
        table = dynamodb.Table(ERROR_STORE_TABLE)
        table_status = table.table_status

        if table_status == "ACTIVE":
            return {
                "status": "healthy",
                "table_name": ERROR_STORE_TABLE,
                "item_count": table.item_count,
            }
        else:
            return {
                "status": "unhealthy",
                "table_name": ERROR_STORE_TABLE,
                "table_status": table_status,
            }

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_timestream() -> Dict[str, Any]:
    """Check Timestream database health."""
    if not TIMESTREAM_DATABASE:
        return {"status": "unconfigured", "message": "Database not configured"}

    try:
        # Simple query to check connectivity
        query = f'SELECT 1 FROM "{TIMESTREAM_DATABASE}"."latency-metrics" LIMIT 1'
        timestream_query.query(QueryString=query)

        return {
            "status": "healthy",
            "database": TIMESTREAM_DATABASE,
        }

    except timestream_query.exceptions.ValidationException:
        # Table might be empty, but connection works
        return {
            "status": "healthy",
            "database": TIMESTREAM_DATABASE,
            "note": "Database accessible, table may be empty",
        }

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
