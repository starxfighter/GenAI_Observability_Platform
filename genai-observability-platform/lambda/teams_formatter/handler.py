"""
Microsoft Teams Formatter Lambda
Formats alerts as Adaptive Cards and sends to MS Teams webhooks.
"""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any

# Environment variables
TEAMS_WEBHOOK_URL = os.environ.get('TEAMS_WEBHOOK_URL')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
DASHBOARD_URL = os.environ.get('DASHBOARD_URL', 'https://observability.example.com')


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Process SNS messages and send formatted alerts to Microsoft Teams.
    """
    print(f"Received event: {json.dumps(event)}")

    results = []

    for record in event.get('Records', []):
        try:
            # Parse SNS message
            sns_message = record.get('Sns', {})
            message_body = sns_message.get('Message', '{}')

            if isinstance(message_body, str):
                alert_data = json.loads(message_body)
            else:
                alert_data = message_body

            # Build Adaptive Card
            card = build_adaptive_card(alert_data)

            # Send to Teams
            response = send_to_teams(card)
            results.append({
                'alert_id': alert_data.get('alert_id', 'unknown'),
                'status': 'sent',
                'response': response
            })

        except Exception as e:
            print(f"Error processing record: {str(e)}")
            results.append({
                'alert_id': alert_data.get('alert_id', 'unknown') if 'alert_data' in locals() else 'unknown',
                'status': 'error',
                'error': str(e)
            })

    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(results),
            'results': results
        })
    }


def build_adaptive_card(alert: dict) -> dict:
    """
    Build a Microsoft Teams Adaptive Card from alert data.
    """
    severity = alert.get('severity', 'medium').upper()
    alert_type = alert.get('alert_type', 'Unknown')
    agent_id = alert.get('agent_id', 'Unknown')
    title = alert.get('title', 'GenAI Observability Alert')
    description = alert.get('description', '')
    trace_id = alert.get('trace_id')
    timestamp = alert.get('timestamp', datetime.utcnow().isoformat())

    # Color based on severity
    severity_colors = {
        'CRITICAL': 'attention',  # Red
        'HIGH': 'attention',
        'MEDIUM': 'warning',      # Yellow
        'LOW': 'good',            # Green
        'INFO': 'accent'          # Blue
    }
    color = severity_colors.get(severity, 'default')

    # Build facts list
    facts = [
        {"title": "Severity", "value": severity},
        {"title": "Alert Type", "value": alert_type},
        {"title": "Agent", "value": agent_id},
        {"title": "Environment", "value": ENVIRONMENT},
        {"title": "Time", "value": timestamp}
    ]

    if trace_id:
        facts.append({"title": "Trace ID", "value": trace_id})

    # Add metrics if present
    metrics = alert.get('metrics', {})
    if metrics:
        if 'error_rate' in metrics:
            facts.append({"title": "Error Rate", "value": f"{metrics['error_rate']:.2%}"})
        if 'latency_p95' in metrics:
            facts.append({"title": "P95 Latency", "value": f"{metrics['latency_p95']:.0f}ms"})
        if 'token_usage' in metrics:
            facts.append({"title": "Token Usage", "value": f"{metrics['token_usage']:,}"})

    # Build actions
    actions = []

    if trace_id:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "View Trace",
            "url": f"{DASHBOARD_URL}/traces/{trace_id}"
        })

    actions.append({
        "type": "Action.OpenUrl",
        "title": "View Agent",
        "url": f"{DASHBOARD_URL}/agents/{agent_id}"
    })

    actions.append({
        "type": "Action.OpenUrl",
        "title": "Open Dashboard",
        "url": DASHBOARD_URL
    })

    # Investigation details if present
    investigation = alert.get('investigation')
    investigation_section = None

    if investigation:
        investigation_section = {
            "type": "Container",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "🔍 AI Investigation",
                    "weight": "bolder",
                    "size": "medium"
                },
                {
                    "type": "TextBlock",
                    "text": f"**Root Cause:** {investigation.get('root_cause', 'Unknown')}",
                    "wrap": True
                },
                {
                    "type": "TextBlock",
                    "text": f"**Recommendation:** {investigation.get('recommendation', 'No recommendation available')}",
                    "wrap": True
                }
            ]
        }

        if investigation.get('similar_incidents'):
            investigation_section['items'].append({
                "type": "TextBlock",
                "text": f"**Similar Past Incidents:** {len(investigation['similar_incidents'])}",
                "wrap": True
            })

    # Build the Adaptive Card
    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "Container",
                            "style": color,
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"🚨 {title}",
                                    "weight": "bolder",
                                    "size": "large",
                                    "wrap": True
                                }
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": description,
                            "wrap": True,
                            "spacing": "medium"
                        },
                        {
                            "type": "FactSet",
                            "facts": facts,
                            "spacing": "medium"
                        }
                    ],
                    "actions": actions
                }
            }
        ]
    }

    # Add investigation section if present
    if investigation_section:
        card['attachments'][0]['content']['body'].append(investigation_section)

    # Add error details if present
    error_details = alert.get('error_details')
    if error_details:
        card['attachments'][0]['content']['body'].append({
            "type": "Container",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "Error Details",
                    "weight": "bolder",
                    "size": "medium"
                },
                {
                    "type": "TextBlock",
                    "text": f"```\n{error_details.get('message', '')[:500]}\n```",
                    "wrap": True,
                    "fontType": "monospace"
                }
            ]
        })

    return card


def send_to_teams(card: dict) -> dict:
    """
    Send the Adaptive Card to Microsoft Teams via webhook.
    """
    if not TEAMS_WEBHOOK_URL:
        print("Warning: TEAMS_WEBHOOK_URL not configured")
        return {'status': 'skipped', 'reason': 'webhook_not_configured'}

    try:
        data = json.dumps(card).encode('utf-8')

        request = urllib.request.Request(
            TEAMS_WEBHOOK_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Content-Length': len(data)
            },
            method='POST'
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode('utf-8')
            return {
                'status': 'success',
                'http_status': response.status,
                'response': response_body
            }

    except urllib.error.HTTPError as e:
        print(f"HTTP Error sending to Teams: {e.code} - {e.reason}")
        return {
            'status': 'error',
            'http_status': e.code,
            'error': e.reason
        }
    except urllib.error.URLError as e:
        print(f"URL Error sending to Teams: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }
    except Exception as e:
        print(f"Error sending to Teams: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


def build_daily_summary_card(summary: dict) -> dict:
    """
    Build an Adaptive Card for daily summary reports.
    """
    date = summary.get('date', datetime.utcnow().strftime('%Y-%m-%d'))

    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"📊 Daily Observability Summary - {date}",
                            "weight": "bolder",
                            "size": "large"
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Total Traces",
                                            "weight": "bolder"
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": f"{summary.get('total_traces', 0):,}",
                                            "size": "extraLarge",
                                            "color": "accent"
                                        }
                                    ]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Success Rate",
                                            "weight": "bolder"
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": f"{summary.get('success_rate', 0):.1%}",
                                            "size": "extraLarge",
                                            "color": "good" if summary.get('success_rate', 0) > 0.95 else "warning"
                                        }
                                    ]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Total Cost",
                                            "weight": "bolder"
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": f"${summary.get('total_cost', 0):.2f}",
                                            "size": "extraLarge",
                                            "color": "accent"
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Active Agents", "value": str(summary.get('active_agents', 0))},
                                {"title": "Total Alerts", "value": str(summary.get('total_alerts', 0))},
                                {"title": "Critical Alerts", "value": str(summary.get('critical_alerts', 0))},
                                {"title": "Avg Latency", "value": f"{summary.get('avg_latency_ms', 0):.0f}ms"},
                                {"title": "Total Tokens", "value": f"{summary.get('total_tokens', 0):,}"}
                            ]
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "View Full Report",
                            "url": f"{DASHBOARD_URL}/reports/{date}"
                        },
                        {
                            "type": "Action.OpenUrl",
                            "title": "Open Dashboard",
                            "url": DASHBOARD_URL
                        }
                    ]
                }
            }
        ]
    }

    return card
