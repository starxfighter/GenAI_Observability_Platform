"""
Anomaly Detector Lambda

Detects anomalies in agent behavior by analyzing error rates and latency.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import boto3

# Configuration
TIMESTREAM_DATABASE = os.environ.get("TIMESTREAM_DATABASE", "")
TIMESTREAM_TABLE = os.environ.get("TIMESTREAM_LATENCY_TABLE", "latency-metrics")
ERROR_STORE_TABLE = os.environ.get("ERROR_STORE_TABLE", "")
INVESTIGATION_FUNCTION = os.environ.get("INVESTIGATION_FUNCTION", "")
CRITICAL_SNS_TOPIC = os.environ.get("CRITICAL_SNS_TOPIC", "")
WARNING_SNS_TOPIC = os.environ.get("WARNING_SNS_TOPIC", "")

# Thresholds
ERROR_RATE_THRESHOLD = float(os.environ.get("ERROR_RATE_THRESHOLD", "0.1"))
LATENCY_THRESHOLD_MS = float(os.environ.get("LATENCY_THRESHOLD_MS", "5000"))
ERROR_COUNT_THRESHOLD = int(os.environ.get("ERROR_COUNT_THRESHOLD", "5"))
ANOMALY_WINDOW_MINUTES = int(os.environ.get("ANOMALY_WINDOW_MINUTES", "5"))

# Initialize clients
timestream_query = boto3.client("timestream-query")
dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")
sns = boto3.client("sns")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for anomaly detection.

    Can be triggered by:
    - EventBridge scheduled rule (periodic)
    - Stream processor (on errors)

    Args:
        event: Trigger event
        context: Lambda context

    Returns:
        Detection result
    """
    print(f"Anomaly detection triggered: {json.dumps(event)}")

    anomalies = []

    # Check error rates
    error_anomalies = check_error_rates()
    anomalies.extend(error_anomalies)

    # Check latency anomalies
    latency_anomalies = check_latency_anomalies()
    anomalies.extend(latency_anomalies)

    # Process detected anomalies
    for anomaly in anomalies:
        # Trigger LLM investigation for critical anomalies
        if anomaly["severity"] == "critical":
            trigger_investigation(anomaly)

        # Send notification
        send_notification(anomaly)

    result = {
        "statusCode": 200,
        "anomalies_detected": len(anomalies),
        "error_anomalies": len(error_anomalies),
        "latency_anomalies": len(latency_anomalies),
    }

    print(f"Anomaly detection complete: {json.dumps(result)}")
    return result


def check_error_rates() -> List[Dict[str, Any]]:
    """
    Check for high error rates in recent data.

    Returns:
        List of error rate anomalies
    """
    anomalies = []

    if not ERROR_STORE_TABLE:
        print("ERROR_STORE_TABLE not configured")
        return anomalies

    try:
        table = dynamodb.Table(ERROR_STORE_TABLE)

        # Calculate time window
        cutoff_time = (
            datetime.utcnow() - timedelta(minutes=ANOMALY_WINDOW_MINUTES)
        ).isoformat()

        # Scan for recent errors
        # Note: In production, use a GSI with a more efficient query pattern
        response = table.scan(
            FilterExpression="#ts >= :time_threshold",
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues={":time_threshold": cutoff_time},
        )

        errors = response.get("Items", [])

        # Group by agent
        agent_errors: Dict[str, List[Dict]] = {}
        for error in errors:
            agent_id = error.get("agent_id", "unknown")
            if agent_id not in agent_errors:
                agent_errors[agent_id] = []
            agent_errors[agent_id].append(error)

        # Check thresholds
        for agent_id, agent_error_list in agent_errors.items():
            error_count = len(agent_error_list)

            if error_count >= ERROR_COUNT_THRESHOLD:
                # Determine severity based on error count
                if error_count >= ERROR_COUNT_THRESHOLD * 2:
                    severity = "critical"
                else:
                    severity = "warning"

                anomaly = {
                    "anomaly_type": "high_error_rate",
                    "agent_id": agent_id,
                    "severity": severity,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metrics": {
                        "error_count": error_count,
                        "threshold": ERROR_COUNT_THRESHOLD,
                        "window_minutes": ANOMALY_WINDOW_MINUTES,
                    },
                    "recent_errors": [
                        {
                            "error_type": e.get("error_type"),
                            "error_message": e.get("error_message", "")[:200],
                            "timestamp": e.get("timestamp"),
                        }
                        for e in agent_error_list[:5]
                    ],
                }
                anomalies.append(anomaly)
                print(f"Error rate anomaly detected for {agent_id}: {error_count} errors")

    except Exception as e:
        print(f"Error checking error rates: {e}")

    return anomalies


def check_latency_anomalies() -> List[Dict[str, Any]]:
    """
    Check for latency anomalies using Timestream.

    Returns:
        List of latency anomalies
    """
    anomalies = []

    if not TIMESTREAM_DATABASE:
        print("TIMESTREAM_DATABASE not configured")
        return anomalies

    try:
        query = f"""
        SELECT
            agent_id,
            AVG(measure_value::double) as avg_latency,
            MAX(measure_value::double) as max_latency,
            COUNT(*) as sample_count
        FROM "{TIMESTREAM_DATABASE}"."{TIMESTREAM_TABLE}"
        WHERE measure_name = 'duration_ms'
            AND time >= ago({ANOMALY_WINDOW_MINUTES}m)
        GROUP BY agent_id
        HAVING AVG(measure_value::double) > {LATENCY_THRESHOLD_MS}
        """

        response = timestream_query.query(QueryString=query)

        for row in response.get("Rows", []):
            data = row["Data"]
            agent_id = data[0].get("ScalarValue", "unknown")
            avg_latency = float(data[1].get("ScalarValue", 0))
            max_latency = float(data[2].get("ScalarValue", 0))
            sample_count = int(data[3].get("ScalarValue", 0))

            # Determine severity
            if avg_latency >= LATENCY_THRESHOLD_MS * 2:
                severity = "critical"
            else:
                severity = "warning"

            anomaly = {
                "anomaly_type": "high_latency",
                "agent_id": agent_id,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metrics": {
                    "avg_latency_ms": round(avg_latency, 2),
                    "max_latency_ms": round(max_latency, 2),
                    "sample_count": sample_count,
                    "threshold_ms": LATENCY_THRESHOLD_MS,
                    "window_minutes": ANOMALY_WINDOW_MINUTES,
                },
            }
            anomalies.append(anomaly)
            print(f"Latency anomaly detected for {agent_id}: {avg_latency}ms avg")

    except Exception as e:
        print(f"Error checking latency anomalies: {e}")

    return anomalies


def trigger_investigation(anomaly: Dict[str, Any]) -> None:
    """
    Trigger LLM investigation for an anomaly.

    Args:
        anomaly: Anomaly data
    """
    if not INVESTIGATION_FUNCTION:
        print("INVESTIGATION_FUNCTION not configured")
        return

    try:
        lambda_client.invoke(
            FunctionName=INVESTIGATION_FUNCTION,
            InvocationType="Event",  # Async
            Payload=json.dumps(anomaly),
        )
        print(f"Investigation triggered for {anomaly['agent_id']}")
    except Exception as e:
        print(f"Error triggering investigation: {e}")


def send_notification(anomaly: Dict[str, Any]) -> None:
    """
    Send notification about the anomaly.

    Args:
        anomaly: Anomaly data
    """
    severity = anomaly.get("severity", "info")

    # Select appropriate topic
    if severity == "critical" and CRITICAL_SNS_TOPIC:
        topic_arn = CRITICAL_SNS_TOPIC
    elif severity == "warning" and WARNING_SNS_TOPIC:
        topic_arn = WARNING_SNS_TOPIC
    else:
        print(f"No SNS topic configured for severity: {severity}")
        return

    try:
        message = {
            "notification_type": "anomaly_alert",
            "incident": {
                "agent_id": anomaly["agent_id"],
                "anomaly_type": anomaly["anomaly_type"],
                "severity": anomaly["severity"],
                "timestamp": anomaly["timestamp"],
                "metrics": anomaly.get("metrics", {}),
            },
        }

        if anomaly.get("recent_errors"):
            message["recent_errors"] = anomaly["recent_errors"]

        sns.publish(
            TopicArn=topic_arn,
            Subject=f"[{severity.upper()}] {anomaly['anomaly_type']} - {anomaly['agent_id']}",
            Message=json.dumps(message, indent=2),
            MessageAttributes={
                "severity": {"DataType": "String", "StringValue": severity},
                "agent_id": {"DataType": "String", "StringValue": anomaly["agent_id"]},
                "anomaly_type": {"DataType": "String", "StringValue": anomaly["anomaly_type"]},
            },
        )
        print(f"Notification sent for {anomaly['agent_id']}")

    except Exception as e:
        print(f"Error sending notification: {e}")
