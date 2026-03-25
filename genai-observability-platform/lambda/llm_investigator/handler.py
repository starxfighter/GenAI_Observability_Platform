"""
LLM Investigator Lambda

Uses Claude to investigate anomalies and provide root cause analysis.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3

# Configuration
ANTHROPIC_SECRET_ARN = os.environ.get("ANTHROPIC_SECRET_ARN", "")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
TIMESTREAM_DATABASE = os.environ.get("TIMESTREAM_DATABASE", "")
TIMESTREAM_TABLE = os.environ.get("TIMESTREAM_LATENCY_TABLE", "latency-metrics")
ERROR_STORE_TABLE = os.environ.get("ERROR_STORE_TABLE", "")
INVESTIGATION_RESULTS_TABLE = os.environ.get("INVESTIGATION_RESULTS_TABLE", "")
NOTIFICATION_TOPIC = os.environ.get("NOTIFICATION_TOPIC", "")

# Model configuration
MODEL_ID = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4000"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.3"))

# Initialize clients
secrets = boto3.client("secretsmanager")
dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")
timestream_query = boto3.client("timestream-query")

# Cached Anthropic client
_anthropic_client = None


def get_anthropic_client():
    """Get or create Anthropic client."""
    global _anthropic_client

    if _anthropic_client is None and ANTHROPIC_SECRET_ARN:
        try:
            secret_response = secrets.get_secret_value(SecretId=ANTHROPIC_SECRET_ARN)
            api_key = json.loads(secret_response["SecretString"])["api_key"]

            from anthropic import Anthropic

            _anthropic_client = Anthropic(api_key=api_key)
        except Exception as e:
            print(f"Error initializing Anthropic client: {e}")
            return None

    return _anthropic_client


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for LLM investigation.

    Args:
        event: Anomaly event from anomaly detector
        context: Lambda context

    Returns:
        Investigation result
    """
    investigation_id = str(uuid.uuid4())
    agent_id = event.get("agent_id", "unknown")
    anomaly_type = event.get("anomaly_type", "unknown")
    severity = event.get("severity", "unknown")

    print(f"Starting investigation {investigation_id} for {agent_id}")

    try:
        # Gather context
        context_data = gather_investigation_context(event)

        # Find similar past incidents
        similar_incidents = find_similar_incidents(agent_id, anomaly_type)

        # Build prompt and call Claude
        analysis = call_claude_for_analysis(event, context_data, similar_incidents)

        # Store results
        store_investigation_results(investigation_id, event, analysis)

        # Send notification with investigation results
        send_investigation_notification(investigation_id, event, analysis)

        return {
            "statusCode": 200,
            "investigation_id": investigation_id,
            "agent_id": agent_id,
            "root_cause_identified": bool(analysis.get("sections", {}).get("root_cause")),
        }

    except Exception as e:
        print(f"Investigation failed: {e}")
        return {
            "statusCode": 500,
            "investigation_id": investigation_id,
            "error": str(e),
        }


def gather_investigation_context(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gather all relevant context for investigation.

    Args:
        event: Anomaly event

    Returns:
        Context data dictionary
    """
    agent_id = event.get("agent_id", "unknown")

    context = {
        "event": event,
        "recent_errors": [],
        "metrics": {},
        "traces": [],
    }

    # Get recent errors
    if ERROR_STORE_TABLE:
        try:
            table = dynamodb.Table(ERROR_STORE_TABLE)
            one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()

            response = table.query(
                IndexName="agent-timestamp-index",
                KeyConditionExpression="agent_id = :agent_id",
                ExpressionAttributeValues={":agent_id": agent_id},
                Limit=10,
                ScanIndexForward=False,
            )
            context["recent_errors"] = response.get("Items", [])
        except Exception as e:
            print(f"Error fetching recent errors: {e}")

    # Get recent metrics from Timestream
    if TIMESTREAM_DATABASE:
        try:
            query = f"""
            SELECT measure_name, AVG(measure_value::double) as avg_value,
                   MAX(measure_value::double) as max_value,
                   MIN(measure_value::double) as min_value
            FROM "{TIMESTREAM_DATABASE}"."{TIMESTREAM_TABLE}"
            WHERE agent_id = '{agent_id}'
                AND time >= ago(1h)
            GROUP BY measure_name
            """
            response = timestream_query.query(QueryString=query)

            for row in response.get("Rows", []):
                measure = row["Data"][0].get("ScalarValue", "unknown")
                context["metrics"][measure] = {
                    "avg": float(row["Data"][1].get("ScalarValue", 0)),
                    "max": float(row["Data"][2].get("ScalarValue", 0)),
                    "min": float(row["Data"][3].get("ScalarValue", 0)),
                }
        except Exception as e:
            print(f"Error fetching metrics: {e}")

    return context


def find_similar_incidents(agent_id: str, anomaly_type: str) -> List[Dict[str, Any]]:
    """
    Find similar past investigations.

    Args:
        agent_id: Agent identifier
        anomaly_type: Type of anomaly

    Returns:
        List of similar past investigations
    """
    if not INVESTIGATION_RESULTS_TABLE:
        return []

    try:
        table = dynamodb.Table(INVESTIGATION_RESULTS_TABLE)

        response = table.query(
            IndexName="agent-timestamp-index",
            KeyConditionExpression="agent_id = :agent_id",
            FilterExpression="anomaly_type = :anomaly_type AND resolution_status = :resolved",
            ExpressionAttributeValues={
                ":agent_id": agent_id,
                ":anomaly_type": anomaly_type,
                ":resolved": "resolved",
            },
            Limit=5,
            ScanIndexForward=False,
        )

        return [
            {
                "investigation_id": item.get("investigation_id"),
                "root_cause": item.get("root_cause", "Unknown"),
                "resolution": item.get("resolution_notes", "Unknown"),
                "resolved_at": item.get("resolved_at", "Unknown"),
            }
            for item in response.get("Items", [])
        ]

    except Exception as e:
        print(f"Error finding similar incidents: {e}")
        return []


def call_claude_for_analysis(
    event: Dict[str, Any],
    context: Dict[str, Any],
    similar_incidents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Call Claude API for incident analysis.

    Args:
        event: Anomaly event
        context: Investigation context
        similar_incidents: Similar past incidents

    Returns:
        Analysis result
    """
    client = get_anthropic_client()
    if client is None:
        return {
            "raw_analysis": "LLM analysis unavailable - Anthropic client not configured",
            "sections": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

    prompt = build_investigation_prompt(event, context, similar_incidents)

    try:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )

        analysis_text = message.content[0].text
        sections = parse_analysis_sections(analysis_text)

        return {
            "raw_analysis": analysis_text,
            "sections": sections,
            "timestamp": datetime.utcnow().isoformat(),
            "model": MODEL_ID,
            "token_usage": {
                "input": message.usage.input_tokens,
                "output": message.usage.output_tokens,
            },
        }

    except Exception as e:
        print(f"Error calling Claude: {e}")
        return {
            "raw_analysis": f"LLM analysis failed: {str(e)}",
            "sections": {},
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


def build_investigation_prompt(
    event: Dict[str, Any],
    context: Dict[str, Any],
    similar_incidents: List[Dict[str, Any]],
) -> str:
    """Build the investigation prompt for Claude."""

    # Format similar incidents
    similar_text = "No similar incidents found in the past 90 days."
    if similar_incidents:
        similar_text = "\n".join(
            [
                f"""
### Similar Incident #{i+1}
- **Root Cause**: {inc.get('root_cause', 'Unknown')}
- **Resolution**: {inc.get('resolution', 'Unknown')}
- **Resolved**: {inc.get('resolved_at', 'Unknown')}
"""
                for i, inc in enumerate(similar_incidents)
            ]
        )

    # Format recent errors
    errors_text = "No recent errors found."
    recent_errors = context.get("recent_errors", [])
    if recent_errors:
        errors_text = json.dumps(recent_errors[:5], indent=2, default=str)

    # Format metrics
    metrics_text = json.dumps(context.get("metrics", {}), indent=2)

    prompt = f"""You are an expert DevOps engineer investigating a production incident in a GenAI observability system.

## Incident Details
- **Agent ID**: {event.get('agent_id')}
- **Anomaly Type**: {event.get('anomaly_type')}
- **Severity**: {event.get('severity')}
- **Timestamp**: {event.get('timestamp')}

## Metrics
```json
{json.dumps(event.get('metrics', {}), indent=2)}
```

## Recent Errors
```json
{errors_text}
```

## Performance Metrics (Last Hour)
```json
{metrics_text}
```

## Similar Past Incidents ({len(similar_incidents)} found)
{similar_text}

## Your Task

Please analyze this incident and provide:

1. **Root Cause Analysis**: What is the most likely root cause of this incident?
2. **Evidence**: What specific evidence from the errors, metrics supports your conclusion?
3. **Impact Assessment**: How severe is this issue and how many users/agents are affected?
4. **Remediation Steps**: Provide 3-5 concrete steps to resolve this issue, in priority order
5. **Prevention**: What can be done to prevent this from happening again?
6. **Similar Incidents**: How does this relate to the similar past incidents? Can we apply any of those resolutions?

Please structure your response in clear sections with actionable information that can be shared with the on-call engineer.
"""

    return prompt


def parse_analysis_sections(text: str) -> Dict[str, Any]:
    """Parse Claude's markdown response into structured sections."""

    sections = {
        "root_cause": "",
        "evidence": "",
        "impact": "",
        "remediation": [],
        "prevention": "",
        "similar_incidents_analysis": "",
    }

    current_section = None
    lines = text.split("\n")

    for line in lines:
        line_lower = line.lower()

        # Detect section headers
        if "root cause" in line_lower:
            current_section = "root_cause"
        elif "evidence" in line_lower:
            current_section = "evidence"
        elif "impact" in line_lower:
            current_section = "impact"
        elif "remediation" in line_lower:
            current_section = "remediation"
        elif "prevention" in line_lower:
            current_section = "prevention"
        elif "similar" in line_lower:
            current_section = "similar_incidents_analysis"
        elif current_section:
            # Add content to current section
            if current_section == "remediation":
                # Parse as list items
                stripped = line.strip()
                if stripped.startswith(("1.", "2.", "3.", "4.", "5.", "-", "*")):
                    sections["remediation"].append(stripped)
            else:
                sections[current_section] += line + "\n"

    # Clean up sections
    for key in sections:
        if isinstance(sections[key], str):
            sections[key] = sections[key].strip()

    return sections


def store_investigation_results(
    investigation_id: str, event: Dict[str, Any], analysis: Dict[str, Any]
) -> None:
    """Store investigation results in DynamoDB."""

    if not INVESTIGATION_RESULTS_TABLE:
        print("INVESTIGATION_RESULTS_TABLE not configured")
        return

    try:
        table = dynamodb.Table(INVESTIGATION_RESULTS_TABLE)

        # Calculate TTL (90 days)
        ttl = int(datetime.utcnow().timestamp() + (90 * 24 * 60 * 60))

        item = {
            "investigation_id": investigation_id,
            "agent_id": event.get("agent_id", "unknown"),
            "anomaly_type": event.get("anomaly_type", "unknown"),
            "severity": event.get("severity", "unknown"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "llm_analysis": analysis.get("raw_analysis", ""),
            "root_cause": analysis.get("sections", {}).get("root_cause", ""),
            "remediation_steps": analysis.get("sections", {}).get("remediation", []),
            "impact_assessment": analysis.get("sections", {}).get("impact", ""),
            "prevention_notes": analysis.get("sections", {}).get("prevention", ""),
            "model_used": analysis.get("model", ""),
            "token_usage": analysis.get("token_usage", {}),
            "resolution_status": "open",
            "ttl": ttl,
        }

        table.put_item(Item=item)
        print(f"Investigation results stored: {investigation_id}")

    except Exception as e:
        print(f"Error storing investigation results: {e}")


def send_investigation_notification(
    investigation_id: str, event: Dict[str, Any], analysis: Dict[str, Any]
) -> None:
    """Send notification with investigation results."""

    if not NOTIFICATION_TOPIC:
        print("NOTIFICATION_TOPIC not configured")
        return

    try:
        sections = analysis.get("sections", {})

        # Create executive summary
        root_cause = sections.get("root_cause", "")
        summary = root_cause[:500] + "..." if len(root_cause) > 500 else root_cause

        message = {
            "notification_type": "incident_investigation",
            "investigation_id": investigation_id,
            "incident": {
                "agent_id": event.get("agent_id"),
                "anomaly_type": event.get("anomaly_type"),
                "severity": event.get("severity"),
                "timestamp": event.get("timestamp"),
            },
            "investigation": {
                "summary": summary,
                "root_cause": sections.get("root_cause", ""),
                "impact": sections.get("impact", ""),
                "immediate_actions": sections.get("remediation", [])[:3],
                "prevention": sections.get("prevention", ""),
            },
        }

        sns.publish(
            TopicArn=NOTIFICATION_TOPIC,
            Subject=f"Investigation Complete: {event.get('agent_id')}",
            Message=json.dumps(message, indent=2),
            MessageAttributes={
                "severity": {
                    "DataType": "String",
                    "StringValue": event.get("severity", "unknown"),
                },
                "has_investigation": {"DataType": "String", "StringValue": "true"},
                "investigation_id": {"DataType": "String", "StringValue": investigation_id},
            },
        )
        print(f"Investigation notification sent: {investigation_id}")

    except Exception as e:
        print(f"Error sending investigation notification: {e}")
