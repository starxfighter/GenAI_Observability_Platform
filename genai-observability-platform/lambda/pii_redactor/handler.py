"""
PII Redactor Lambda

Provides stream-level PII detection and redaction for the observability pipeline.
Can be used as a Kinesis Data Firehose transformation or standalone processor.
"""

import base64
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

import boto3

# Import shared PII module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from observability_common.pii_redaction import (
    PIIDetector,
    PIIRedactor,
    JSONPIIRedactor,
    PIIType,
    RedactionStrategy,
    PIIPattern,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
REDACTION_STRATEGY = RedactionStrategy(
    os.environ.get("REDACTION_STRATEGY", "type_mask")
)
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.7"))
REDACT_ALL_STRINGS = os.environ.get("REDACT_ALL_STRINGS", "false").lower() == "true"
LOG_PII_STATS = os.environ.get("LOG_PII_STATS", "true").lower() == "true"
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# Custom patterns from environment (JSON encoded)
CUSTOM_PATTERNS_JSON = os.environ.get("CUSTOM_PATTERNS", "[]")

# Fields to always redact
ALWAYS_REDACT_FIELDS = os.environ.get(
    "ALWAYS_REDACT_FIELDS",
    "password,secret,api_key,token,authorization"
).split(",")

# Fields to never scan (for performance)
SKIP_FIELDS = os.environ.get(
    "SKIP_FIELDS",
    "timestamp,trace_id,span_id,event_type"
).split(",")

# PII types to detect (empty = all)
ENABLED_PII_TYPES = os.environ.get("ENABLED_PII_TYPES", "")

# DynamoDB for audit logging
AUDIT_TABLE = os.environ.get("AUDIT_TABLE", "")

# SNS for alerts
ALERT_TOPIC = os.environ.get("ALERT_TOPIC", "")
PII_THRESHOLD = int(os.environ.get("PII_THRESHOLD", "100"))  # Alert if > N PII found

# Initialize clients
dynamodb = boto3.resource("dynamodb") if AUDIT_TABLE else None
sns = boto3.client("sns") if ALERT_TOPIC else None

# Initialize redactor with configuration
def create_detector() -> PIIDetector:
    """Create configured PII detector."""
    # Parse custom patterns
    custom_patterns = []
    try:
        patterns_data = json.loads(CUSTOM_PATTERNS_JSON)
        for p in patterns_data:
            custom_patterns.append(
                PIIPattern(
                    pii_type=PIIType(p.get("type", "custom")),
                    pattern=p["pattern"],
                    description=p.get("description", ""),
                    confidence=p.get("confidence", 0.8),
                )
            )
    except Exception as e:
        logger.warning(f"Failed to parse custom patterns: {e}")

    detector = PIIDetector(
        patterns=custom_patterns,
        use_defaults=True,
        min_confidence=MIN_CONFIDENCE,
    )

    # Filter to enabled types if specified
    if ENABLED_PII_TYPES:
        enabled = set(ENABLED_PII_TYPES.split(","))
        detector.patterns = [
            p for p in detector.patterns
            if p.pii_type.value in enabled
        ]

    return detector


def create_redactor(detector: PIIDetector) -> JSONPIIRedactor:
    """Create configured JSON PII redactor."""
    pii_redactor = PIIRedactor(
        detector=detector,
        default_strategy=REDACTION_STRATEGY,
    )

    return JSONPIIRedactor(
        redactor=pii_redactor,
        sensitive_keys=ALWAYS_REDACT_FIELDS,
        redact_all_strings=REDACT_ALL_STRINGS,
    )


# Global instances
_detector = None
_redactor = None


def get_detector() -> PIIDetector:
    global _detector
    if _detector is None:
        _detector = create_detector()
    return _detector


def get_redactor() -> JSONPIIRedactor:
    global _redactor
    if _redactor is None:
        _redactor = create_redactor(get_detector())
    return _redactor


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for PII redaction.

    Supports multiple invocation modes:
    1. Kinesis Firehose transformation
    2. Direct invocation with JSON payload
    3. API Gateway request

    Args:
        event: Input event
        context: Lambda context

    Returns:
        Processed records or redacted data
    """
    # Determine invocation type
    if "records" in event:
        # Kinesis Firehose transformation
        return handle_firehose_transform(event)
    elif "body" in event:
        # API Gateway request
        return handle_api_request(event)
    elif "data" in event:
        # Direct invocation
        return handle_direct_invocation(event)
    else:
        # Assume direct JSON payload
        return handle_direct_invocation({"data": event})


def handle_firehose_transform(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Kinesis Firehose transformation request.

    Args:
        event: Firehose event with records

    Returns:
        Transformed records
    """
    output_records = []
    total_pii_count = 0
    stats = {
        "total_records": 0,
        "records_with_pii": 0,
        "pii_by_type": {},
    }

    for record in event.get("records", []):
        record_id = record["recordId"]
        stats["total_records"] += 1

        try:
            # Decode record data
            payload = base64.b64decode(record["data"]).decode("utf-8")
            data = json.loads(payload)

            # Process the record
            result = process_record(data, stats)

            # Encode result
            output_data = base64.b64encode(
                json.dumps(result["data"]).encode("utf-8")
            ).decode("utf-8")

            total_pii_count += result["pii_count"]
            if result["pii_count"] > 0:
                stats["records_with_pii"] += 1

            output_records.append({
                "recordId": record_id,
                "result": "Ok",
                "data": output_data,
            })

        except Exception as e:
            logger.error(f"Error processing record {record_id}: {e}")
            # Return original record on error
            output_records.append({
                "recordId": record_id,
                "result": "ProcessingFailed",
                "data": record["data"],
            })

    # Log stats
    if LOG_PII_STATS:
        logger.info(f"PII redaction stats: {json.dumps(stats)}")

    # Alert if threshold exceeded
    if total_pii_count > PII_THRESHOLD and ALERT_TOPIC:
        send_alert(stats, total_pii_count)

    # Audit log
    if AUDIT_TABLE:
        log_audit(stats)

    return {"records": output_records}


def handle_api_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle API Gateway request for PII redaction.

    Args:
        event: API Gateway event

    Returns:
        API response
    """
    try:
        body = json.loads(event.get("body", "{}"))
        action = body.get("action", "redact")

        if action == "redact":
            data = body.get("data", {})
            stats = {"pii_by_type": {}}
            result = process_record(data, stats)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "redacted_data": result["data"],
                    "pii_found": result["pii_count"],
                    "pii_types": stats["pii_by_type"],
                }),
                "headers": {"Content-Type": "application/json"},
            }

        elif action == "detect":
            text = body.get("text", "")
            matches = get_detector().detect(text)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "pii_found": len(matches),
                    "matches": [
                        {
                            "type": m.pii_type.value,
                            "start": m.start,
                            "end": m.end,
                            "confidence": m.confidence,
                        }
                        for m in matches
                    ],
                }),
                "headers": {"Content-Type": "application/json"},
            }

        elif action == "validate":
            # Validate that data contains no PII
            data = body.get("data", {})
            text = json.dumps(data)
            matches = get_detector().detect(text)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "valid": len(matches) == 0,
                    "pii_found": len(matches),
                    "types_found": list(set(m.pii_type.value for m in matches)),
                }),
                "headers": {"Content-Type": "application/json"},
            }

        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Unknown action: {action}"}),
                "headers": {"Content-Type": "application/json"},
            }

    except Exception as e:
        logger.error(f"Error handling API request: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }


def handle_direct_invocation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle direct Lambda invocation.

    Args:
        event: Direct invocation event

    Returns:
        Redacted data
    """
    data = event.get("data", {})
    stats = {"pii_by_type": {}}

    result = process_record(data, stats)

    return {
        "statusCode": 200,
        "redacted_data": result["data"],
        "pii_found": result["pii_count"],
        "pii_types": stats["pii_by_type"],
        "dry_run": DRY_RUN,
    }


def process_record(
    data: Dict[str, Any],
    stats: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Process a single record for PII redaction.

    Args:
        data: Record data
        stats: Statistics dictionary to update

    Returns:
        Processing result with redacted data and PII count
    """
    redactor = get_redactor()
    detector = get_detector()

    # Count PII before redaction
    original_text = json.dumps(data)
    matches = detector.detect(original_text)
    pii_count = len(matches)

    # Update stats
    for match in matches:
        pii_type = match.pii_type.value
        stats["pii_by_type"][pii_type] = stats["pii_by_type"].get(pii_type, 0) + 1

    # Skip redaction in dry run mode
    if DRY_RUN:
        return {
            "data": data,
            "pii_count": pii_count,
            "dry_run": True,
        }

    # Perform redaction
    redacted_data = redactor.redact(data)

    # Add redaction metadata
    if pii_count > 0:
        redacted_data["_pii_redaction"] = {
            "redacted": True,
            "pii_count": pii_count,
            "redacted_at": datetime.utcnow().isoformat() + "Z",
            "strategy": REDACTION_STRATEGY.value,
        }

    return {
        "data": redacted_data,
        "pii_count": pii_count,
    }


def send_alert(stats: Dict[str, Any], total_pii: int) -> None:
    """Send alert for high PII detection."""
    if not sns or not ALERT_TOPIC:
        return

    try:
        message = {
            "alert_type": "high_pii_detection",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_pii_detected": total_pii,
            "threshold": PII_THRESHOLD,
            "stats": stats,
        }

        sns.publish(
            TopicArn=ALERT_TOPIC,
            Subject="[ALERT] High PII Detection in Observability Data",
            Message=json.dumps(message, indent=2),
            MessageAttributes={
                "alert_type": {
                    "DataType": "String",
                    "StringValue": "high_pii_detection",
                },
            },
        )
        logger.info(f"Sent PII alert: {total_pii} instances detected")

    except Exception as e:
        logger.error(f"Failed to send PII alert: {e}")


def log_audit(stats: Dict[str, Any]) -> None:
    """Log audit record to DynamoDB."""
    if not dynamodb or not AUDIT_TABLE:
        return

    try:
        table = dynamodb.Table(AUDIT_TABLE)

        audit_record = {
            "audit_id": f"pii-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "operation": "pii_redaction",
            "stats": stats,
            "ttl": int(datetime.utcnow().timestamp() + (90 * 24 * 60 * 60)),
        }

        table.put_item(Item=audit_record)

    except Exception as e:
        logger.error(f"Failed to log audit: {e}")


# Configuration endpoint for runtime updates
def update_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update redaction configuration at runtime.

    Args:
        config: New configuration values

    Returns:
        Status
    """
    global _detector, _redactor, REDACTION_STRATEGY, MIN_CONFIDENCE

    if "strategy" in config:
        REDACTION_STRATEGY = RedactionStrategy(config["strategy"])

    if "min_confidence" in config:
        MIN_CONFIDENCE = float(config["min_confidence"])

    # Force recreation of instances
    _detector = None
    _redactor = None

    return {
        "status": "updated",
        "strategy": REDACTION_STRATEGY.value,
        "min_confidence": MIN_CONFIDENCE,
    }
