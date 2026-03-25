"""
Event Ingestion Lambda

Receives telemetry events from agents via API Gateway and writes to Kinesis.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

import boto3

# Initialize clients
kinesis = boto3.client("kinesis")
s3 = boto3.client("s3")

# Configuration
EVENTS_STREAM_NAME = os.environ.get("EVENTS_STREAM_NAME", "")
RAW_DATA_BUCKET = os.environ.get("RAW_DATA_BUCKET", "")
MAX_KINESIS_BATCH_SIZE = 500  # Kinesis limit


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for event ingestion.

    Args:
        event: API Gateway HTTP API event
        context: Lambda context

    Returns:
        API response
    """
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))

        # Get agent context from authorizer
        authorizer_context = (
            event.get("requestContext", {}).get("authorizer", {}).get("lambda", {})
        )

        agent_id = authorizer_context.get("agent_id") or body.get("agent_id", "unknown")

        # Extract events
        events = body.get("events", [])

        if not events:
            return create_response(400, {"error": "No events provided"})

        # Validate event count
        if len(events) > 1000:
            return create_response(400, {"error": "Too many events (max 1000)"})

        # Enrich events with metadata
        enriched_events = enrich_events(events, body, authorizer_context, agent_id)

        # Write to Kinesis
        kinesis_result = write_to_kinesis(agent_id, enriched_events)

        # Write raw backup to S3
        s3_key = write_to_s3(agent_id, enriched_events)

        return create_response(
            202,
            {
                "status": "accepted",
                "events_count": len(enriched_events),
                "agent_id": agent_id,
                "kinesis_records": kinesis_result["success_count"],
                "failed_records": kinesis_result["failed_count"],
            },
        )

    except json.JSONDecodeError as e:
        return create_response(400, {"error": f"Invalid JSON: {str(e)}"})
    except Exception as e:
        print(f"Ingestion error: {e}")
        return create_response(500, {"error": "Internal server error"})


def enrich_events(
    events: List[Dict[str, Any]],
    body: Dict[str, Any],
    authorizer_context: Dict[str, str],
    agent_id: str,
) -> List[Dict[str, Any]]:
    """
    Enrich events with metadata.

    Args:
        events: Raw events from the request
        body: Full request body
        authorizer_context: Context from the authorizer
        agent_id: Agent identifier

    Returns:
        List of enriched events
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    enriched = []
    for evt in events:
        enriched_event = {
            **evt,
            "agent_id": agent_id,
            "ingestion_timestamp": timestamp,
            "environment": body.get("environment", authorizer_context.get("environment", "unknown")),
            "agent_type": body.get("agent_type", authorizer_context.get("agent_type", "unknown")),
            "agent_version": body.get("agent_version", "unknown"),
            "global_tags": body.get("global_tags", {}),
        }
        enriched.append(enriched_event)

    return enriched


def write_to_kinesis(agent_id: str, events: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Write events to Kinesis in batches.

    Args:
        agent_id: Agent identifier (used as partition key)
        events: Events to write

    Returns:
        Dict with success and failed counts
    """
    if not EVENTS_STREAM_NAME:
        print("EVENTS_STREAM_NAME not configured")
        return {"success_count": 0, "failed_count": len(events)}

    success_count = 0
    failed_count = 0

    # Batch events
    records = []
    for evt in events:
        records.append(
            {
                "Data": json.dumps(evt).encode("utf-8"),
                "PartitionKey": agent_id,
            }
        )

        # Send batch when full
        if len(records) >= MAX_KINESIS_BATCH_SIZE:
            result = send_kinesis_batch(records)
            success_count += result["success"]
            failed_count += result["failed"]
            records = []

    # Send remaining records
    if records:
        result = send_kinesis_batch(records)
        success_count += result["success"]
        failed_count += result["failed"]

    return {"success_count": success_count, "failed_count": failed_count}


def send_kinesis_batch(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Send a batch of records to Kinesis.

    Args:
        records: Records to send

    Returns:
        Dict with success and failed counts
    """
    try:
        response = kinesis.put_records(StreamName=EVENTS_STREAM_NAME, Records=records)

        failed_count = response.get("FailedRecordCount", 0)
        success_count = len(records) - failed_count

        if failed_count > 0:
            print(f"Failed to write {failed_count} records to Kinesis")

        return {"success": success_count, "failed": failed_count}

    except Exception as e:
        print(f"Error writing to Kinesis: {e}")
        return {"success": 0, "failed": len(records)}


def write_to_s3(agent_id: str, events: List[Dict[str, Any]]) -> str:
    """
    Write events to S3 for backup/archival.

    Args:
        agent_id: Agent identifier
        events: Events to write

    Returns:
        S3 key where events were written
    """
    if not RAW_DATA_BUCKET:
        print("RAW_DATA_BUCKET not configured")
        return ""

    try:
        date_prefix = datetime.utcnow().strftime("%Y/%m/%d/%H")
        s3_key = f"events/{agent_id}/{date_prefix}/{uuid.uuid4()}.json"

        s3.put_object(
            Bucket=RAW_DATA_BUCKET,
            Key=s3_key,
            Body=json.dumps(
                {
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "event_count": len(events),
                    "events": events,
                }
            ),
            ContentType="application/json",
        )

        return s3_key

    except Exception as e:
        print(f"Error writing to S3: {e}")
        return ""


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create an API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
