"""
Email/SES Formatter Lambda
Formats alerts as HTML emails and sends via Amazon SES.
"""
import json
import os
import boto3
from datetime import datetime
from typing import Any, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Environment variables
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'observability@example.com')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
DASHBOARD_URL = os.environ.get('DASHBOARD_URL', 'https://observability.example.com')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize SES client
ses_client = boto3.client('ses', region_name=AWS_REGION)


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Process SNS messages and send formatted emails via SES.
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

            # Get recipients
            recipients = alert_data.get('email_recipients', [])
            if not recipients:
                print("No email recipients specified, skipping")
                continue

            # Build email
            subject, html_body, text_body = build_alert_email(alert_data)

            # Send email
            response = send_email(recipients, subject, html_body, text_body)
            results.append({
                'alert_id': alert_data.get('alert_id', 'unknown'),
                'status': 'sent',
                'message_id': response.get('MessageId')
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


def build_alert_email(alert: dict) -> tuple[str, str, str]:
    """
    Build HTML and plain text email from alert data.
    Returns (subject, html_body, text_body).
    """
    severity = alert.get('severity', 'medium').upper()
    alert_type = alert.get('alert_type', 'Unknown')
    agent_id = alert.get('agent_id', 'Unknown')
    title = alert.get('title', 'GenAI Observability Alert')
    description = alert.get('description', '')
    trace_id = alert.get('trace_id')
    timestamp = alert.get('timestamp', datetime.utcnow().isoformat())

    # Subject line
    severity_emoji = {
        'CRITICAL': '🔴',
        'HIGH': '🟠',
        'MEDIUM': '🟡',
        'LOW': '🟢',
        'INFO': '🔵'
    }
    subject = f"{severity_emoji.get(severity, '⚪')} [{severity}] {title} - {agent_id}"

    # Severity colors
    severity_colors = {
        'CRITICAL': '#dc3545',
        'HIGH': '#fd7e14',
        'MEDIUM': '#ffc107',
        'LOW': '#28a745',
        'INFO': '#17a2b8'
    }
    color = severity_colors.get(severity, '#6c757d')

    # Build metrics section
    metrics_html = ""
    metrics_text = ""
    metrics = alert.get('metrics', {})
    if metrics:
        metrics_rows = []
        metrics_lines = []
        for key, value in metrics.items():
            formatted_key = key.replace('_', ' ').title()
            if isinstance(value, float):
                if 'rate' in key:
                    formatted_value = f"{value:.2%}"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            metrics_rows.append(f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee;'><strong>{formatted_key}</strong></td><td style='padding: 8px; border-bottom: 1px solid #eee;'>{formatted_value}</td></tr>")
            metrics_lines.append(f"  {formatted_key}: {formatted_value}")

        metrics_html = f"""
        <h3 style="color: #333; margin-top: 20px;">Metrics</h3>
        <table style="width: 100%; border-collapse: collapse;">
            {''.join(metrics_rows)}
        </table>
        """
        metrics_text = "Metrics:\n" + "\n".join(metrics_lines)

    # Build investigation section
    investigation_html = ""
    investigation_text = ""
    investigation = alert.get('investigation')
    if investigation:
        investigation_html = f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px;">
            <h3 style="color: #333; margin-top: 0;">🔍 AI Investigation</h3>
            <p><strong>Root Cause:</strong> {investigation.get('root_cause', 'Unknown')}</p>
            <p><strong>Recommendation:</strong> {investigation.get('recommendation', 'No recommendation available')}</p>
            {f"<p><strong>Similar Past Incidents:</strong> {len(investigation.get('similar_incidents', []))}</p>" if investigation.get('similar_incidents') else ""}
        </div>
        """
        investigation_text = f"""
AI Investigation:
  Root Cause: {investigation.get('root_cause', 'Unknown')}
  Recommendation: {investigation.get('recommendation', 'No recommendation available')}
"""

    # Build error details section
    error_html = ""
    error_text = ""
    error_details = alert.get('error_details')
    if error_details:
        error_message = error_details.get('message', '')[:1000]
        error_html = f"""
        <div style="margin-top: 20px;">
            <h3 style="color: #333;">Error Details</h3>
            <pre style="background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; font-size: 12px;">{error_message}</pre>
        </div>
        """
        error_text = f"\nError Details:\n{error_message}\n"

    # Build action links
    links_html = f"""
    <div style="margin-top: 25px;">
        <a href="{DASHBOARD_URL}/agents/{agent_id}" style="display: inline-block; background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-right: 10px;">View Agent</a>
        {f'<a href="{DASHBOARD_URL}/traces/{trace_id}" style="display: inline-block; background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-right: 10px;">View Trace</a>' if trace_id else ''}
        <a href="{DASHBOARD_URL}" style="display: inline-block; background-color: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Open Dashboard</a>
    </div>
    """

    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">🚨 {title}</h1>
        </div>

        <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
            <p style="font-size: 16px;">{description}</p>

            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Severity</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;"><span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 3px;">{severity}</span></td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Alert Type</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{alert_type}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Agent</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{agent_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Environment</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{ENVIRONMENT}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Time</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{timestamp}</td>
                </tr>
                {f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Trace ID</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;"><code>{trace_id}</code></td></tr>' if trace_id else ''}
            </table>

            {metrics_html}
            {investigation_html}
            {error_html}
            {links_html}
        </div>

        <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 12px; color: #666;">
            <p style="margin: 0;">This alert was generated by GenAI Observability Platform ({ENVIRONMENT}).</p>
            <p style="margin: 5px 0 0 0;">To manage your notification preferences, visit <a href="{DASHBOARD_URL}/settings">Settings</a>.</p>
        </div>
    </body>
    </html>
    """

    # Plain text email body
    text_body = f"""
{title}
{'=' * len(title)}

{description}

Details:
  Severity: {severity}
  Alert Type: {alert_type}
  Agent: {agent_id}
  Environment: {ENVIRONMENT}
  Time: {timestamp}
  {f'Trace ID: {trace_id}' if trace_id else ''}

{metrics_text}
{investigation_text}
{error_text}

Links:
  View Agent: {DASHBOARD_URL}/agents/{agent_id}
  {f'View Trace: {DASHBOARD_URL}/traces/{trace_id}' if trace_id else ''}
  Dashboard: {DASHBOARD_URL}

---
This alert was generated by GenAI Observability Platform ({ENVIRONMENT}).
    """

    return subject, html_body, text_body


def send_email(recipients: list[str], subject: str, html_body: str, text_body: str) -> dict:
    """
    Send email via Amazon SES.
    """
    try:
        response = ses_client.send_email(
            Source=SENDER_EMAIL,
            Destination={
                'ToAddresses': recipients
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        print(f"Email sent successfully: {response['MessageId']}")
        return response

    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise


def build_daily_report_email(summary: dict, recipients: list[str]) -> None:
    """
    Build and send a daily summary report email.
    """
    date = summary.get('date', datetime.utcnow().strftime('%Y-%m-%d'))

    subject = f"📊 GenAI Observability Daily Report - {date}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0;">📊 Daily Observability Report</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">{date}</p>
        </div>

        <div style="border: 1px solid #ddd; border-top: none; padding: 30px;">
            <div style="display: flex; justify-content: space-around; text-align: center; margin-bottom: 30px;">
                <div style="flex: 1; padding: 15px;">
                    <div style="font-size: 36px; font-weight: bold; color: #667eea;">{summary.get('total_traces', 0):,}</div>
                    <div style="color: #666; font-size: 14px;">Total Traces</div>
                </div>
                <div style="flex: 1; padding: 15px; border-left: 1px solid #eee; border-right: 1px solid #eee;">
                    <div style="font-size: 36px; font-weight: bold; color: {'#28a745' if summary.get('success_rate', 0) > 0.95 else '#ffc107'};">{summary.get('success_rate', 0):.1%}</div>
                    <div style="color: #666; font-size: 14px;">Success Rate</div>
                </div>
                <div style="flex: 1; padding: 15px;">
                    <div style="font-size: 36px; font-weight: bold; color: #764ba2;">${summary.get('total_cost', 0):.2f}</div>
                    <div style="color: #666; font-size: 14px;">Total Cost</div>
                </div>
            </div>

            <h3 style="border-bottom: 2px solid #667eea; padding-bottom: 10px;">Summary Statistics</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 10px; border-bottom: 1px solid #eee;">Active Agents</td><td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{summary.get('active_agents', 0)}</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #eee;">Total Alerts</td><td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{summary.get('total_alerts', 0)}</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #eee;">Critical Alerts</td><td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold; color: #dc3545;">{summary.get('critical_alerts', 0)}</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #eee;">Avg Latency (P50)</td><td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{summary.get('avg_latency_ms', 0):.0f}ms</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #eee;">P95 Latency</td><td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{summary.get('p95_latency_ms', 0):.0f}ms</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #eee;">Total Tokens</td><td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{summary.get('total_tokens', 0):,}</td></tr>
                <tr><td style="padding: 10px;">LLM Calls</td><td style="padding: 10px; text-align: right; font-weight: bold;">{summary.get('llm_calls', 0):,}</td></tr>
            </table>

            <div style="margin-top: 30px; text-align: center;">
                <a href="{DASHBOARD_URL}/reports/{date}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">View Full Report</a>
            </div>
        </div>

        <div style="margin-top: 20px; padding: 15px; text-align: center; font-size: 12px; color: #666;">
            <p>GenAI Observability Platform ({ENVIRONMENT})</p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
GenAI Observability Daily Report - {date}
==========================================

Summary:
  Total Traces: {summary.get('total_traces', 0):,}
  Success Rate: {summary.get('success_rate', 0):.1%}
  Total Cost: ${summary.get('total_cost', 0):.2f}
  Active Agents: {summary.get('active_agents', 0)}
  Total Alerts: {summary.get('total_alerts', 0)}
  Critical Alerts: {summary.get('critical_alerts', 0)}
  Avg Latency: {summary.get('avg_latency_ms', 0):.0f}ms
  P95 Latency: {summary.get('p95_latency_ms', 0):.0f}ms
  Total Tokens: {summary.get('total_tokens', 0):,}

View full report: {DASHBOARD_URL}/reports/{date}
    """

    send_email(recipients, subject, html_body, text_body)
