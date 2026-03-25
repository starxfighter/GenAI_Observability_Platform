"""
Slack Formatter Lambda

Formats alerts and investigation results for Slack using Block Kit.
"""

import json
import os
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

# Configuration
SLACK_SECRET_ARN = os.environ.get("SLACK_SECRET_ARN", "")

# Initialize clients
secrets = boto3.client("secretsmanager")

# Cached webhook URL
_webhook_url: Optional[str] = None


def get_webhook_url() -> Optional[str]:
    """Get Slack webhook URL from Secrets Manager."""
    global _webhook_url

    if _webhook_url is None and SLACK_SECRET_ARN:
        try:
            response = secrets.get_secret_value(SecretId=SLACK_SECRET_ARN)
            secret = json.loads(response["SecretString"])
            _webhook_url = secret.get("webhook_url")
        except Exception as e:
            print(f"Error getting Slack webhook: {e}")
            return None

    return _webhook_url


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Slack formatting.

    Triggered by SNS subscription.

    Args:
        event: SNS event
        context: Lambda context

    Returns:
        Processing result
    """
    messages_sent = 0
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

            # Build Slack blocks
            blocks = build_slack_blocks(message_data, severity)

            # Send to Slack
            if send_to_slack(blocks, severity):
                messages_sent += 1
            else:
                errors += 1

        except Exception as e:
            print(f"Error processing record: {e}")
            errors += 1

    return {
        "statusCode": 200,
        "messages_sent": messages_sent,
        "errors": errors,
    }


def build_slack_blocks(message: Dict[str, Any], severity: str) -> List[Dict[str, Any]]:
    """
    Build Slack Block Kit message.

    Args:
        message: Message data
        severity: Severity level

    Returns:
        List of Slack blocks
    """
    emoji_map = {
        "critical": ":rotating_light:",
        "warning": ":warning:",
        "info": ":information_source:",
    }

    incident = message.get("incident", {})
    investigation = message.get("investigation", {})
    notification_type = message.get("notification_type", "alert")

    # Header
    header_text = f"{emoji_map.get(severity, ':bell:')} {severity.upper()}: {incident.get('anomaly_type', 'Alert')}"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text[:150],  # Slack limit
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Agent:*\n{incident.get('agent_id', 'unknown')}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Time:*\n{format_timestamp(incident.get('timestamp'))}",
                },
            ],
        },
    ]

    # Add metrics if available
    metrics = incident.get("metrics", {})
    if metrics:
        metrics_text = format_metrics(metrics)
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Metrics:*\n{metrics_text}"},
            }
        )

    # Add investigation results if available
    if investigation:
        blocks.append({"type": "divider"})

        # Investigation summary
        summary = investigation.get("summary", "")
        if summary:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*:robot_face: AI Investigation Summary*\n{truncate(summary, 500)}",
                    },
                }
            )

        # Root cause
        root_cause = investigation.get("root_cause", "")
        if root_cause:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Root Cause:*\n{truncate(root_cause, 500)}",
                    },
                }
            )

        # Immediate actions
        actions = investigation.get("immediate_actions", [])
        if actions:
            actions_text = "\n".join([f"• {action}" for action in actions[:3]])
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Immediate Actions:*\n{actions_text}",
                    },
                }
            )

    # Add links if available
    links = message.get("links", {})
    if any(links.values()):
        blocks.append({"type": "divider"})

        link_buttons = []
        if links.get("dashboard"):
            link_buttons.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Dashboard"},
                    "url": links["dashboard"],
                    "style": "primary",
                }
            )
        if links.get("traces"):
            link_buttons.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Traces"},
                    "url": links["traces"],
                }
            )
        if links.get("agent_details"):
            link_buttons.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Agent Details"},
                    "url": links["agent_details"],
                }
            )

        if link_buttons:
            blocks.append({"type": "actions", "elements": link_buttons})

    # Add context footer
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"GenAI Observability Platform | {notification_type}",
                }
            ],
        }
    )

    return blocks


def send_to_slack(blocks: List[Dict[str, Any]], severity: str) -> bool:
    """
    Send message to Slack.

    Args:
        blocks: Slack Block Kit blocks
        severity: Severity for color

    Returns:
        True if successful
    """
    webhook_url = get_webhook_url()

    if not webhook_url or webhook_url == "PLACEHOLDER_REPLACE_ME":
        print("Slack webhook not configured, skipping notification")
        return False

    color_map = {
        "critical": "#FF0000",
        "warning": "#FFA500",
        "info": "#0000FF",
    }

    payload = {
        "username": "GenAI Observability",
        "icon_emoji": ":robot_face:",
        "attachments": [
            {
                "color": color_map.get(severity, "#808080"),
                "blocks": blocks,
            }
        ],
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        response = urllib.request.urlopen(req, timeout=10)
        return response.status == 200
    except Exception as e:
        print(f"Error sending to Slack: {e}")
        return False


def format_timestamp(iso_timestamp: Optional[str]) -> str:
    """Format timestamp for display."""
    if not iso_timestamp:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return iso_timestamp


def format_metrics(metrics: Dict[str, Any]) -> str:
    """Format metrics for display."""
    lines = []
    for key, value in metrics.items():
        if isinstance(value, float):
            lines.append(f"• {key}: {value:.2f}")
        else:
            lines.append(f"• {key}: {value}")
    return "\n".join(lines) if lines else "No metrics available"


def truncate(text: str, max_length: int) -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
