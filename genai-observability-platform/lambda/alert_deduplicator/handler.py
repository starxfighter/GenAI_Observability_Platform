"""
Alert Deduplicator Lambda

Deduplicates alerts to prevent alert fatigue.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import boto3

# Configuration
ALERT_CACHE_TABLE = os.environ.get("ALERT_CACHE_TABLE", "")
CRITICAL_TOPIC_ARN = os.environ.get("CRITICAL_TOPIC_ARN", "")
WARNING_TOPIC_ARN = os.environ.get("WARNING_TOPIC_ARN", "")
INFO_TOPIC_ARN = os.environ.get("INFO_TOPIC_ARN", "")
DEDUP_WINDOW_HOURS = int(os.environ.get("DEDUP_WINDOW_HOURS", "24"))

# Initialize clients
dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for alert deduplication.

    Can be invoked directly with alert data.

    Args:
        event: Alert event with 'alert' key
        context: Lambda context

    Returns:
        Processing result
    """
    alert_data = event.get("alert", event)
    severity = alert_data.get("severity", "info")

    # Generate fingerprint
    fingerprint = generate_fingerprint(alert_data)

    # Check if we should send this alert
    if should_send_alert(fingerprint):
        # Forward to appropriate SNS topic
        topic_arn = get_topic_for_severity(severity)

        if topic_arn:
            send_alert(topic_arn, alert_data)

            return {
                "statusCode": 200,
                "sent": True,
                "fingerprint": fingerprint,
                "severity": severity,
            }
        else:
            return {
                "statusCode": 200,
                "sent": False,
                "reason": "no_topic_configured",
                "severity": severity,
            }
    else:
        return {
            "statusCode": 200,
            "sent": False,
            "reason": "duplicate_alert",
            "fingerprint": fingerprint,
            "dedup_window_hours": DEDUP_WINDOW_HOURS,
        }


def generate_fingerprint(alert_data: Dict[str, Any]) -> str:
    """
    Generate a unique fingerprint for the alert.

    Args:
        alert_data: Alert data

    Returns:
        SHA-256 hash fingerprint
    """
    # Use agent_id, anomaly_type, and key metrics for fingerprinting
    components = [
        alert_data.get("agent_id", ""),
        alert_data.get("anomaly_type", ""),
    ]

    # Include some metric info but not exact values
    metrics = alert_data.get("metrics", {})
    if metrics:
        # Only include metric names, not values (to group similar alerts)
        components.append(",".join(sorted(metrics.keys())))

    fingerprint_str = "|".join(components)
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()


def should_send_alert(fingerprint: str) -> bool:
    """
    Check if alert should be sent or if it's a duplicate.

    Args:
        fingerprint: Alert fingerprint

    Returns:
        True if alert should be sent
    """
    if not ALERT_CACHE_TABLE:
        print("ALERT_CACHE_TABLE not configured, sending alert")
        return True

    try:
        table = dynamodb.Table(ALERT_CACHE_TABLE)

        # Check cache
        response = table.get_item(Key={"alert_fingerprint": fingerprint})

        if "Item" in response:
            # Check if within dedup window
            last_sent_str = response["Item"].get("last_sent", "")
            if last_sent_str:
                last_sent = datetime.fromisoformat(last_sent_str)
                if datetime.utcnow() - last_sent < timedelta(hours=DEDUP_WINDOW_HOURS):
                    # Update count but don't send
                    increment_alert_count(fingerprint)
                    print(f"Duplicate alert suppressed: {fingerprint[:16]}...")
                    return False

        # Cache the alert and send it
        cache_alert(fingerprint)
        return True

    except Exception as e:
        print(f"Error checking alert cache: {e}")
        # If cache check fails, send the alert
        return True


def cache_alert(fingerprint: str) -> None:
    """
    Cache an alert fingerprint.

    Args:
        fingerprint: Alert fingerprint
    """
    if not ALERT_CACHE_TABLE:
        return

    try:
        table = dynamodb.Table(ALERT_CACHE_TABLE)

        # TTL: 7 days
        ttl = int((datetime.utcnow() + timedelta(days=7)).timestamp())

        table.put_item(
            Item={
                "alert_fingerprint": fingerprint,
                "last_sent": datetime.utcnow().isoformat(),
                "count": 1,
                "ttl": ttl,
            }
        )
    except Exception as e:
        print(f"Error caching alert: {e}")


def increment_alert_count(fingerprint: str) -> None:
    """
    Increment the count for a cached alert.

    Args:
        fingerprint: Alert fingerprint
    """
    if not ALERT_CACHE_TABLE:
        return

    try:
        table = dynamodb.Table(ALERT_CACHE_TABLE)

        table.update_item(
            Key={"alert_fingerprint": fingerprint},
            UpdateExpression="SET #count = #count + :inc, last_occurrence = :now",
            ExpressionAttributeNames={"#count": "count"},
            ExpressionAttributeValues={
                ":inc": 1,
                ":now": datetime.utcnow().isoformat(),
            },
        )
    except Exception as e:
        print(f"Error incrementing alert count: {e}")


def get_topic_for_severity(severity: str) -> Optional[str]:
    """
    Get the SNS topic ARN for a severity level.

    Args:
        severity: Severity level

    Returns:
        SNS topic ARN or None
    """
    topic_map = {
        "critical": CRITICAL_TOPIC_ARN,
        "warning": WARNING_TOPIC_ARN,
        "info": INFO_TOPIC_ARN,
    }
    return topic_map.get(severity.lower()) or INFO_TOPIC_ARN


def send_alert(topic_arn: str, alert_data: Dict[str, Any]) -> None:
    """
    Send alert to SNS topic.

    Args:
        topic_arn: SNS topic ARN
        alert_data: Alert data
    """
    try:
        severity = alert_data.get("severity", "info")
        agent_id = alert_data.get("agent_id", "unknown")
        anomaly_type = alert_data.get("anomaly_type", "Alert")

        # Build message
        message = {
            "notification_type": "alert",
            "incident": {
                "agent_id": agent_id,
                "anomaly_type": anomaly_type,
                "severity": severity,
                "timestamp": alert_data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                "metrics": alert_data.get("metrics", {}),
            },
        }

        if alert_data.get("recent_errors"):
            message["recent_errors"] = alert_data["recent_errors"]

        sns.publish(
            TopicArn=topic_arn,
            Subject=f"[{severity.upper()}] {anomaly_type} - {agent_id}",
            Message=json.dumps(message, indent=2),
            MessageAttributes={
                "severity": {"DataType": "String", "StringValue": severity},
                "agent_id": {"DataType": "String", "StringValue": agent_id},
                "anomaly_type": {"DataType": "String", "StringValue": anomaly_type},
            },
        )
        print(f"Alert sent to {topic_arn}")

    except Exception as e:
        print(f"Error sending alert: {e}")
