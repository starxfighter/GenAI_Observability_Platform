"""
PagerDuty Formatter Lambda

Formats alerts for PagerDuty Events API v2.
"""

import json
import os
import urllib.request
from typing import Any, Dict, Optional

import boto3

# Configuration
PAGERDUTY_SECRET_ARN = os.environ.get("PAGERDUTY_SECRET_ARN", "")
PAGERDUTY_API_URL = "https://events.pagerduty.com/v2/enqueue"

# Initialize clients
secrets = boto3.client("secretsmanager")

# Cached integration key
_integration_key: Optional[str] = None


def get_integration_key() -> Optional[str]:
    """Get PagerDuty integration key from Secrets Manager."""
    global _integration_key

    if _integration_key is None and PAGERDUTY_SECRET_ARN:
        try:
            response = secrets.get_secret_value(SecretId=PAGERDUTY_SECRET_ARN)
            secret = json.loads(response["SecretString"])
            _integration_key = secret.get("integration_key")
        except Exception as e:
            print(f"Error getting PagerDuty key: {e}")
            return None

    return _integration_key


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for PagerDuty formatting.

    Triggered by SNS subscription.

    Args:
        event: SNS event
        context: Lambda context

    Returns:
        Processing result
    """
    incidents_created = 0
    skipped = 0
    errors = 0

    for record in event.get("Records", []):
        try:
            sns_message = record["Sns"]
            message_data = json.loads(sns_message["Message"])

            # Get severity from message attributes
            severity = (
                sns_message.get("MessageAttributes", {})
                .get("severity", {})
                .get("Value", "info")
            )

            # Only create incidents for critical and warning
            if severity not in ["critical", "warning"]:
                skipped += 1
                continue

            # Send to PagerDuty
            if send_to_pagerduty(message_data, severity):
                incidents_created += 1
            else:
                errors += 1

        except Exception as e:
            print(f"Error processing record: {e}")
            errors += 1

    return {
        "statusCode": 200,
        "incidents_created": incidents_created,
        "skipped": skipped,
        "errors": errors,
    }


def send_to_pagerduty(message: Dict[str, Any], severity: str) -> bool:
    """
    Send event to PagerDuty.

    Args:
        message: Message data
        severity: Severity level

    Returns:
        True if successful
    """
    integration_key = get_integration_key()

    if not integration_key or integration_key == "PLACEHOLDER_REPLACE_ME":
        print("PagerDuty integration key not configured, skipping notification")
        return False

    incident = message.get("incident", {})
    investigation = message.get("investigation", {})

    # Map severity to PagerDuty severity
    pd_severity_map = {
        "critical": "critical",
        "warning": "warning",
        "error": "error",
        "info": "info",
    }
    pd_severity = pd_severity_map.get(severity, "info")

    # Generate dedup key to prevent duplicate incidents
    dedup_key = f"{incident.get('agent_id', 'unknown')}-{incident.get('anomaly_type', 'unknown')}"

    # Build PagerDuty event
    pd_event = {
        "routing_key": integration_key,
        "event_action": "trigger",
        "dedup_key": dedup_key,
        "payload": {
            "summary": f"{severity.upper()}: {incident.get('anomaly_type', 'Alert')} - {incident.get('agent_id', 'unknown')}",
            "source": "GenAI Observability Platform",
            "severity": pd_severity,
            "timestamp": incident.get("timestamp"),
            "custom_details": {
                "agent_id": incident.get("agent_id"),
                "anomaly_type": incident.get("anomaly_type"),
                "metrics": incident.get("metrics", {}),
                "root_cause": investigation.get("root_cause", "Under investigation"),
                "immediate_actions": investigation.get("immediate_actions", []),
            },
        },
    }

    # Add links if available
    links = message.get("links", {})
    if links:
        pd_event["links"] = []
        if links.get("dashboard"):
            pd_event["links"].append(
                {"href": links["dashboard"], "text": "View Dashboard"}
            )
        if links.get("traces"):
            pd_event["links"].append({"href": links["traces"], "text": "View Traces"})

    try:
        req = urllib.request.Request(
            PAGERDUTY_API_URL,
            data=json.dumps(pd_event).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        response = urllib.request.urlopen(req, timeout=10)

        if response.status == 202:
            print(f"PagerDuty incident created: {dedup_key}")
            return True
        else:
            print(f"PagerDuty returned status {response.status}")
            return False

    except Exception as e:
        print(f"Error sending to PagerDuty: {e}")
        return False
