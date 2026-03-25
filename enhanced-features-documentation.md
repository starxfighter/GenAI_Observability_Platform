# GenAI Observability Platform - Enhanced Features Documentation

## 🚀 New Features Overview

This enhanced architecture adds three major capabilities:

1. **LLM-Powered Intelligence** - Automated root cause analysis and incident investigation
2. **Smart Notification Platform** - Multi-channel alerts with SNS integration
3. **Agent/MCP Registration Portal** - Self-service management console
4. **Enhanced Error Investigation** - Dedicated error tracking and correlation

---

## 1. LLM-Powered Intelligence System

### Overview

The LLM Intelligence system uses Claude Sonnet 4 to automatically investigate anomalies, errors, and incidents, providing human-readable explanations and remediation suggestions.

### Architecture Components

#### A. Investigation Lambda Function

```python
# lambda/llm_investigator/handler.py

import boto3
import json
from anthropic import Anthropic
from datetime import datetime, timedelta

class LLMInvestigator:
    def __init__(self):
        self.anthropic = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
        self.opensearch = boto3.client('opensearchserverless')
        self.dynamodb = boto3.resource('dynamodb')
        self.error_table = self.dynamodb.Table('genai-error-store')
    
    def investigate_anomaly(self, event_data: dict):
        """
        Main investigation function triggered by anomaly detection
        
        Args:
            event_data: {
                'anomaly_type': 'high_error_rate',
                'agent_id': 'sales-agent',
                'execution_id': 'abc-123',
                'timestamp': '2025-01-15T10:30:00Z',
                'severity': 'critical',
                'metrics': {...}
            }
        """
        
        # Step 1: Gather context
        context = self._gather_investigation_context(event_data)
        
        # Step 2: Query similar past incidents
        similar_incidents = self._find_similar_incidents(event_data)
        
        # Step 3: Build comprehensive prompt
        prompt = self._build_investigation_prompt(context, similar_incidents)
        
        # Step 4: Call Claude for analysis
        analysis = self._call_claude_for_analysis(prompt)
        
        # Step 5: Store results
        self._store_investigation_results(event_data, analysis)
        
        # Step 6: Send to notification system
        self._send_to_notifications(event_data, analysis)
        
        return analysis
    
    def _gather_investigation_context(self, event_data: dict) -> dict:
        """Gather all relevant context for the incident"""
        
        context = {
            'event': event_data,
            'traces': [],
            'logs': [],
            'metrics': {},
            'recent_changes': []
        }
        
        execution_id = event_data.get('execution_id')
        agent_id = event_data.get('agent_id')
        
        # Get execution trace from OpenSearch
        trace_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"execution_id": execution_id}},
                        {"range": {
                            "timestamp": {
                                "gte": "now-1h",
                                "lte": "now"
                            }
                        }}
                    ]
                }
            },
            "sort": [{"timestamp": "asc"}],
            "size": 100
        }
        
        traces_response = self.opensearch.search(
            index='traces-*',
            body=trace_query
        )
        
        context['traces'] = [hit['_source'] for hit in traces_response['hits']['hits']]
        
        # Get error logs
        error_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"agent_id": agent_id}},
                        {"term": {"event_type": "error"}},
                        {"range": {
                            "timestamp": {
                                "gte": "now-24h",
                                "lte": "now"
                            }
                        }}
                    ]
                }
            },
            "size": 20
        }
        
        errors_response = self.opensearch.search(
            index='errors-*',
            body=error_query
        )
        
        context['logs'] = [hit['_source'] for hit in errors_response['hits']['hits']]
        
        # Get recent metrics from Timestream
        metrics_query = f"""
        SELECT 
            measure_name,
            measure_value::double as value,
            time
        FROM "GenAIObservability"."LatencyMetrics"
        WHERE agent_id = '{agent_id}'
            AND time >= ago(1h)
        ORDER BY time DESC
        LIMIT 100
        """
        
        timestream = boto3.client('timestream-query')
        metrics_response = timestream.query(QueryString=metrics_query)
        
        context['metrics'] = self._parse_timestream_results(metrics_response)
        
        # Check for recent deployments or config changes
        # Query RDS for agent configuration history
        context['recent_changes'] = self._get_recent_changes(agent_id)
        
        return context
    
    def _find_similar_incidents(self, event_data: dict) -> list:
        """Find similar past incidents using vector similarity"""
        
        # Query error store for similar errors
        agent_id = event_data.get('agent_id')
        error_type = event_data.get('anomaly_type')
        
        response = self.error_table.query(
            IndexName='agent-error-index',
            KeyConditionExpression='agent_id = :agent_id',
            FilterExpression='error_type = :error_type',
            ExpressionAttributeValues={
                ':agent_id': agent_id,
                ':error_type': error_type
            },
            Limit=10,
            ScanIndexForward=False  # Most recent first
        )
        
        similar = []
        for item in response.get('Items', []):
            if item.get('resolution_status') == 'resolved':
                similar.append({
                    'error_id': item['error_id'],
                    'description': item['error_description'],
                    'resolution': item['resolution'],
                    'root_cause': item.get('root_cause', 'Unknown'),
                    'resolved_at': item['resolved_at']
                })
        
        return similar
    
    def _build_investigation_prompt(self, context: dict, similar_incidents: list) -> str:
        """Build comprehensive prompt for Claude"""
        
        prompt = f"""You are an expert DevOps engineer investigating a production incident in a GenAI observability system.

## Incident Details
- **Agent ID**: {context['event']['agent_id']}
- **Anomaly Type**: {context['event']['anomaly_type']}
- **Severity**: {context['event']['severity']}
- **Timestamp**: {context['event']['timestamp']}

## Execution Trace
The following trace shows the sequence of events leading to the incident:

```json
{json.dumps(context['traces'][:10], indent=2)}
```

## Error Logs
Recent errors from this agent:

```json
{json.dumps(context['logs'][:5], indent=2)}
```

## Performance Metrics
Recent latency and throughput metrics:

```json
{json.dumps(context['metrics'], indent=2)}
```

## Recent Changes
Changes made in the last 24 hours:

```json
{json.dumps(context['recent_changes'], indent=2)}
```

## Similar Past Incidents
We found {len(similar_incidents)} similar incidents that were previously resolved:

{self._format_similar_incidents(similar_incidents)}

## Your Task

Please analyze this incident and provide:

1. **Root Cause Analysis**: What is the most likely root cause of this incident?
2. **Evidence**: What specific evidence from the traces, logs, or metrics supports your conclusion?
3. **Impact Assessment**: How severe is this issue and how many users/agents are affected?
4. **Remediation Steps**: Provide 3-5 concrete steps to resolve this issue, in priority order
5. **Prevention**: What can be done to prevent this from happening again?
6. **Similar Incidents**: How does this relate to the similar past incidents? Can we apply any of those resolutions?

Please structure your response in clear sections with actionable information that can be shared with the on-call engineer.
"""
        return prompt
    
    def _call_claude_for_analysis(self, prompt: str) -> dict:
        """Call Claude API for analysis"""
        
        message = self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.3,  # Lower temperature for more focused analysis
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        analysis_text = message.content[0].text
        
        # Parse the structured response
        # Claude's response is in markdown format with sections
        # We parse it into a structured dict
        
        analysis = {
            'raw_analysis': analysis_text,
            'timestamp': datetime.utcnow().isoformat(),
            'model': 'claude-sonnet-4-20250514',
            'sections': self._parse_analysis_sections(analysis_text),
            'token_usage': {
                'input': message.usage.input_tokens,
                'output': message.usage.output_tokens
            }
        }
        
        return analysis
    
    def _parse_analysis_sections(self, text: str) -> dict:
        """Parse Claude's markdown response into structured sections"""
        
        sections = {
            'root_cause': '',
            'evidence': '',
            'impact': '',
            'remediation': [],
            'prevention': '',
            'similar_incidents_analysis': ''
        }
        
        current_section = None
        lines = text.split('\n')
        
        for line in lines:
            # Detect section headers
            if '**Root Cause' in line or '## Root Cause' in line:
                current_section = 'root_cause'
            elif '**Evidence' in line or '## Evidence' in line:
                current_section = 'evidence'
            elif '**Impact' in line or '## Impact' in line:
                current_section = 'impact'
            elif '**Remediation' in line or '## Remediation' in line:
                current_section = 'remediation'
            elif '**Prevention' in line or '## Prevention' in line:
                current_section = 'prevention'
            elif '**Similar' in line or '## Similar' in line:
                current_section = 'similar_incidents_analysis'
            elif current_section:
                # Add content to current section
                if current_section == 'remediation':
                    # Parse as list items
                    if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '*')):
                        sections['remediation'].append(line.strip())
                else:
                    sections[current_section] += line + '\n'
        
        # Clean up sections
        for key in sections:
            if isinstance(sections[key], str):
                sections[key] = sections[key].strip()
        
        return sections
    
    def _store_investigation_results(self, event_data: dict, analysis: dict):
        """Store investigation results in DynamoDB"""
        
        error_id = f"{event_data['agent_id']}-{event_data['execution_id']}"
        
        self.error_table.put_item(
            Item={
                'error_id': error_id,
                'agent_id': event_data['agent_id'],
                'execution_id': event_data.get('execution_id'),
                'timestamp': event_data['timestamp'],
                'error_type': event_data['anomaly_type'],
                'severity': event_data['severity'],
                'llm_analysis': analysis['raw_analysis'],
                'root_cause': analysis['sections']['root_cause'],
                'remediation_steps': analysis['sections']['remediation'],
                'impact_assessment': analysis['sections']['impact'],
                'prevention_notes': analysis['sections']['prevention'],
                'investigation_timestamp': analysis['timestamp'],
                'model_used': analysis['model'],
                'token_usage': analysis['token_usage'],
                'resolution_status': 'open',
                'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
            }
        )
    
    def _send_to_notifications(self, event_data: dict, analysis: dict):
        """Send investigation results to notification system"""
        
        sns = boto3.client('sns')
        
        # Build rich notification message
        message = self._build_notification_message(event_data, analysis)
        
        # Determine topic based on severity
        topic_map = {
            'critical': os.environ['SNS_CRITICAL_TOPIC_ARN'],
            'warning': os.environ['SNS_WARNING_TOPIC_ARN'],
            'info': os.environ['SNS_INFO_TOPIC_ARN']
        }
        
        topic_arn = topic_map.get(event_data['severity'], topic_map['info'])
        
        # Publish to SNS
        sns.publish(
            TopicArn=topic_arn,
            Subject=f"[{event_data['severity'].upper()}] Incident Investigation: {event_data['agent_id']}",
            Message=json.dumps(message),
            MessageAttributes={
                'severity': {
                    'DataType': 'String',
                    'StringValue': event_data['severity']
                },
                'agent_id': {
                    'DataType': 'String',
                    'StringValue': event_data['agent_id']
                },
                'has_investigation': {
                    'DataType': 'String',
                    'StringValue': 'true'
                }
            }
        )
    
    def _build_notification_message(self, event_data: dict, analysis: dict) -> dict:
        """Build structured notification message"""
        
        return {
            'notification_type': 'incident_investigation',
            'incident': {
                'agent_id': event_data['agent_id'],
                'execution_id': event_data.get('execution_id'),
                'anomaly_type': event_data['anomaly_type'],
                'severity': event_data['severity'],
                'timestamp': event_data['timestamp']
            },
            'investigation': {
                'summary': self._create_executive_summary(analysis),
                'root_cause': analysis['sections']['root_cause'],
                'impact': analysis['sections']['impact'],
                'immediate_actions': analysis['sections']['remediation'][:3],
                'prevention': analysis['sections']['prevention']
            },
            'links': {
                'dashboard': f"https://observability.example.com/investigations/{event_data['agent_id']}",
                'traces': f"https://observability.example.com/traces/{event_data.get('execution_id')}",
                'agent_details': f"https://observability.example.com/agents/{event_data['agent_id']}"
            }
        }
    
    def _create_executive_summary(self, analysis: dict) -> str:
        """Create a short executive summary of the incident"""
        
        root_cause = analysis['sections']['root_cause']
        impact = analysis['sections']['impact']
        
        # Extract key points
        summary_lines = []
        
        # First 2 sentences of root cause
        root_sentences = root_cause.split('.')[:2]
        if root_sentences:
            summary_lines.append(' '.join(root_sentences) + '.')
        
        # First sentence of impact
        impact_sentences = impact.split('.')[:1]
        if impact_sentences:
            summary_lines.append(' '.join(impact_sentences) + '.')
        
        return ' '.join(summary_lines)
    
    def _format_similar_incidents(self, similar_incidents: list) -> str:
        """Format similar incidents for prompt"""
        
        if not similar_incidents:
            return "No similar incidents found in the past 90 days."
        
        formatted = []
        for idx, incident in enumerate(similar_incidents, 1):
            formatted.append(f"""
### Similar Incident #{idx}
- **Description**: {incident['description']}
- **Root Cause**: {incident['root_cause']}
- **Resolution**: {incident['resolution']}
- **Resolved**: {incident['resolved_at']}
""")
        
        return '\n'.join(formatted)
    
    def _get_recent_changes(self, agent_id: str) -> list:
        """Get recent configuration changes from RDS"""
        
        # This would query your RDS database for recent changes
        # Placeholder implementation
        return []
    
    def _parse_timestream_results(self, response: dict) -> dict:
        """Parse Timestream query results"""
        
        metrics = {}
        for row in response.get('Rows', []):
            measure = row['Data'][0]['ScalarValue']
            value = float(row['Data'][1]['ScalarValue'])
            timestamp = row['Data'][2]['ScalarValue']
            
            if measure not in metrics:
                metrics[measure] = []
            
            metrics[measure].append({
                'value': value,
                'timestamp': timestamp
            })
        
        return metrics


def lambda_handler(event, context):
    """Lambda handler for LLM investigation"""
    
    investigator = LLMInvestigator()
    
    # Event from Step Functions or direct invoke
    event_data = event.get('detail', event)
    
    try:
        analysis = investigator.investigate_anomaly(event_data)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'investigation_complete',
                'analysis': analysis
            })
        }
    
    except Exception as e:
        print(f"Investigation failed: {str(e)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'investigation_failed',
                'error': str(e)
            })
        }
```

#### B. Configuration Assistant (Portal Feature)

```python
# portal/llm_config_assistant.py

class ConfigurationAssistant:
    """LLM-powered configuration assistant for agent/MCP registration"""
    
    def __init__(self):
        self.anthropic = Anthropic()
    
    def assist_configuration(self, user_input: dict) -> dict:
        """
        Help users configure their agents/MCP servers
        
        Args:
            user_input: {
                'agent_type': 'langchain',
                'deployment': 'lambda',
                'requirements': 'I need to track token usage and costs',
                'current_config': {...}
            }
        """
        
        prompt = f"""You are a helpful assistant helping a developer configure observability for their GenAI agent.

**Agent Information:**
- Type: {user_input.get('agent_type')}
- Deployment: {user_input.get('deployment')}

**User Requirements:**
{user_input.get('requirements')}

**Current Configuration (if any):**
```json
{json.dumps(user_input.get('current_config', {}), indent=2)}
```

Please provide:

1. **Recommended Configuration**: A complete, ready-to-use configuration
2. **Installation Steps**: Step-by-step instructions for their deployment type
3. **Environment Variables**: Required env vars with explanations
4. **Code Example**: A practical code snippet showing how to integrate the SDK
5. **Best Practices**: 3-5 tips for optimal observability

Format your response in clear sections that can be displayed in a web interface.
"""
        
        message = self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {
            'guidance': message.content[0].text,
            'confidence': 'high'
        }
```

### LLM Use Cases

#### 1. Root Cause Analysis
- Analyzes execution traces, error logs, and metrics
- Correlates multiple data sources
- Identifies patterns humans might miss

#### 2. Incident Summarization
- Converts technical details into executive summaries
- Generates actionable remediation steps
- Creates incident reports automatically

#### 3. Configuration Assistance
- Guides users through agent setup
- Suggests optimal configurations
- Explains complex settings in simple terms

#### 4. Query Assistance
- Natural language to SQL/GraphQL conversion
- Helps users explore their data
- Suggests relevant queries

#### 5. Pattern Recognition
- Identifies recurring error patterns
- Groups similar incidents
- Learns from past resolutions

### Cost Considerations

**LLM API Costs:**
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens

**Typical Investigation:**
- Input: ~4,000 tokens (context + similar incidents)
- Output: ~1,500 tokens (analysis)
- Cost per investigation: ~$0.03

**Monthly Estimate:**
- 100 investigations/day = 3,000/month
- Total: ~$90/month for LLM analysis

**Optimization Strategies:**
1. Only trigger for high-severity incidents
2. Cache similar incident lookups
3. Use smart prompting to reduce token usage
4. Implement token budgets per investigation

---

## 2. Smart Notification Platform

### Architecture

The notification system uses SNS as the central routing hub, with Lambda functions formatting messages for each channel.

### SNS Topic Structure

```yaml
# infrastructure/sns-topics.yaml

Resources:
  # Critical Alerts (P1)
  CriticalAlertsTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: genai-alerts-critical
      DisplayName: GenAI Critical Alerts
      Subscriptions:
        - Protocol: lambda
          Endpoint: !GetAtt SlackFormatterLambda.Arn
        - Protocol: lambda
          Endpoint: !GetAtt PagerDutyFormatterLambda.Arn
        - Protocol: lambda
          Endpoint: !GetAtt TeamsFormatterLambda.Arn
      
      # Apply filter policy
      FilterPolicyScope: MessageAttributes
  
  # Warning Alerts (P2)
  WarningAlertsTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: genai-alerts-warning
      DisplayName: GenAI Warning Alerts
      Subscriptions:
        - Protocol: lambda
          Endpoint: !GetAtt SlackFormatterLambda.Arn
        - Protocol: email
          Endpoint: team-genai@example.com
  
  # Info Alerts (P3)
  InfoAlertsTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: genai-alerts-info
      DisplayName: GenAI Info Alerts
      Subscriptions:
        - Protocol: lambda
          Endpoint: !GetAtt SlackFormatterLambda.Arn
  
  # Investigation Results
  InvestigationResultsTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: genai-investigation-results
      DisplayName: GenAI Investigation Results
      Subscriptions:
        - Protocol: lambda
          Endpoint: !GetAtt SlackFormatterLambda.Arn
        - Protocol: lambda
          Endpoint: !GetAtt EmailFormatterLambda.Arn
```

### Notification Formatters

#### A. Slack Formatter

```python
# lambda/formatters/slack_formatter.py

import json
import requests
from datetime import datetime

class SlackFormatter:
    def __init__(self):
        self.webhook_url = os.environ['SLACK_WEBHOOK_URL']
        self.channel_map = {
            'critical': '#genai-critical-alerts',
            'warning': '#genai-warnings',
            'info': '#genai-monitoring'
        }
    
    def format_and_send(self, sns_message: dict):
        """Format SNS message as Slack block kit and send"""
        
        message_data = json.loads(sns_message['Message'])
        severity = sns_message['MessageAttributes']['severity']['Value']
        
        # Determine emoji and color
        emoji_map = {
            'critical': ':rotating_light:',
            'warning': ':warning:',
            'info': ':information_source:'
        }
        
        color_map = {
            'critical': '#FF0000',
            'warning': '#FFA500',
            'info': '#0000FF'
        }
        
        # Build Slack blocks
        blocks = self._build_slack_blocks(message_data, severity)
        
        # Send to Slack
        payload = {
            'channel': self.channel_map[severity],
            'username': 'GenAI Observability',
            'icon_emoji': emoji_map[severity],
            'attachments': [{
                'color': color_map[severity],
                'blocks': blocks
            }]
        }
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        return response.status_code == 200
    
    def _build_slack_blocks(self, message: dict, severity: str) -> list:
        """Build Slack block kit message"""
        
        incident = message.get('incident', {})
        investigation = message.get('investigation', {})
        links = message.get('links', {})
        
        blocks = [
            # Header
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f"🚨 {severity.upper()}: {incident.get('anomaly_type', 'Incident')}",
                    'emoji': True
                }
            },
            # Context
            {
                'type': 'section',
                'fields': [
                    {
                        'type': 'mrkdwn',
                        'text': f"*Agent:*\n{incident.get('agent_id')}"
                    },
                    {
                        'type': 'mrkdwn',
                        'text': f"*Time:*\n{self._format_timestamp(incident.get('timestamp'))}"
                    }
                ]
            }
        ]
        
        # Add investigation summary if available
        if investigation:
            blocks.append({'type': 'divider'})
            blocks.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*🤖 AI Investigation Summary*\n{investigation.get('summary', 'No summary available')}"
                }
            })
            
            # Root cause
            if investigation.get('root_cause'):
                blocks.append({
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f"*Root Cause:*\n{self._truncate(investigation['root_cause'], 500)}"
                    }
                })
            
            # Immediate actions
            if investigation.get('immediate_actions'):
                actions_text = '\n'.join([f"• {action}" for action in investigation['immediate_actions'][:3]])
                blocks.append({
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f"*Immediate Actions:*\n{actions_text}"
                    }
                })
        
        # Links
        if links:
            blocks.append({'type': 'divider'})
            blocks.append({
                'type': 'actions',
                'elements': [
                    {
                        'type': 'button',
                        'text': {
                            'type': 'plain_text',
                            'text': 'View Dashboard'
                        },
                        'url': links.get('dashboard'),
                        'style': 'primary'
                    },
                    {
                        'type': 'button',
                        'text': {
                            'type': 'plain_text',
                            'text': 'View Traces'
                        },
                        'url': links.get('traces')
                    },
                    {
                        'type': 'button',
                        'text': {
                            'type': 'plain_text',
                            'text': 'Agent Details'
                        },
                        'url': links.get('agent_details')
                    }
                ]
            })
        
        return blocks
    
    def _format_timestamp(self, iso_timestamp: str) -> str:
        """Format timestamp for Slack"""
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        return f"<!date^{int(dt.timestamp())}^{{date_short_pretty}} at {{time}}|{iso_timestamp}>"
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + '...'


def lambda_handler(event, context):
    """Lambda handler for Slack formatting"""
    
    formatter = SlackFormatter()
    
    for record in event['Records']:
        sns_message = record['Sns']
        try:
            success = formatter.format_and_send(sns_message)
            if not success:
                print(f"Failed to send to Slack: {sns_message}")
        except Exception as e:
            print(f"Error formatting Slack message: {str(e)}")
    
    return {'statusCode': 200}
```

#### B. PagerDuty Formatter

```python
# lambda/formatters/pagerduty_formatter.py

import requests
import json

class PagerDutyFormatter:
    def __init__(self):
        self.api_key = os.environ['PAGERDUTY_API_KEY']
        self.integration_key = os.environ['PAGERDUTY_INTEGRATION_KEY']
        self.api_url = 'https://events.pagerduty.com/v2/enqueue'
    
    def format_and_send(self, sns_message: dict):
        """Format and send to PagerDuty Events API"""
        
        message_data = json.loads(sns_message['Message'])
        severity = sns_message['MessageAttributes']['severity']['Value']
        
        # Only create incidents for critical and warning
        if severity not in ['critical', 'warning']:
            return True
        
        incident = message_data.get('incident', {})
        investigation = message_data.get('investigation', {})
        
        # Build PagerDuty event
        event = {
            'routing_key': self.integration_key,
            'event_action': 'trigger',
            'dedup_key': f"{incident.get('agent_id')}-{incident.get('anomaly_type')}",
            'payload': {
                'summary': f"{severity.upper()}: {incident.get('anomaly_type')} - {incident.get('agent_id')}",
                'source': 'GenAI Observability Platform',
                'severity': self._map_severity(severity),
                'timestamp': incident.get('timestamp'),
                'custom_details': {
                    'agent_id': incident.get('agent_id'),
                    'execution_id': incident.get('execution_id'),
                    'anomaly_type': incident.get('anomaly_type'),
                    'root_cause': investigation.get('root_cause', 'Under investigation'),
                    'immediate_actions': investigation.get('immediate_actions', []),
                    'dashboard_url': message_data.get('links', {}).get('dashboard')
                }
            },
            'links': [
                {
                    'href': message_data.get('links', {}).get('dashboard'),
                    'text': 'View in Dashboard'
                },
                {
                    'href': message_data.get('links', {}).get('traces'),
                    'text': 'View Execution Traces'
                }
            ]
        }
        
        # Send to PagerDuty
        response = requests.post(
            self.api_url,
            json=event,
            headers={
                'Content-Type': 'application/json'
            }
        )
        
        return response.status_code == 202
    
    def _map_severity(self, severity: str) -> str:
        """Map our severity to PagerDuty severity"""
        mapping = {
            'critical': 'critical',
            'warning': 'warning',
            'info': 'info'
        }
        return mapping.get(severity, 'info')


def lambda_handler(event, context):
    """Lambda handler for PagerDuty formatting"""
    
    formatter = PagerDutyFormatter()
    
    for record in event['Records']:
        sns_message = record['Sns']
        try:
            success = formatter.format_and_send(sns_message)
            if not success:
                print(f"Failed to send to PagerDuty: {sns_message}")
        except Exception as e:
            print(f"Error formatting PagerDuty message: {str(e)}")
    
    return {'statusCode': 200}
```

### Alert Deduplication

```python
# lambda/alert_deduplicator.py

import boto3
from datetime import datetime, timedelta
import hashlib
import json

class AlertDeduplicator:
    """Prevent alert fatigue by deduplicating similar alerts"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.alert_cache = self.dynamodb.Table('genai-alert-cache')
    
    def should_send_alert(self, alert_data: dict, window_hours: int = 24) -> bool:
        """
        Check if we should send this alert or if it's a duplicate
        
        Returns:
            True if alert should be sent, False if it's a duplicate
        """
        
        # Generate alert fingerprint
        fingerprint = self._generate_fingerprint(alert_data)
        
        # Check cache
        try:
            response = self.alert_cache.get_item(
                Key={'alert_fingerprint': fingerprint}
            )
            
            if 'Item' in response:
                # Check if within dedup window
                last_sent = datetime.fromisoformat(response['Item']['last_sent'])
                if datetime.utcnow() - last_sent < timedelta(hours=window_hours):
                    # Update count but don't send
                    self._increment_count(fingerprint)
                    return False
            
            # Send alert and cache it
            self._cache_alert(fingerprint, alert_data)
            return True
            
        except Exception as e:
            print(f"Error checking alert cache: {str(e)}")
            # If cache check fails, send the alert
            return True
    
    def _generate_fingerprint(self, alert_data: dict) -> str:
        """Generate unique fingerprint for alert"""
        
        # Use agent_id, anomaly_type, and root cause for fingerprinting
        fingerprint_components = [
            alert_data.get('incident', {}).get('agent_id', ''),
            alert_data.get('incident', {}).get('anomaly_type', ''),
            alert_data.get('investigation', {}).get('root_cause', '')[:100]  # First 100 chars
        ]
        
        fingerprint_string = '|'.join(fingerprint_components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    def _cache_alert(self, fingerprint: str, alert_data: dict):
        """Cache the alert"""
        
        self.alert_cache.put_item(
            Item={
                'alert_fingerprint': fingerprint,
                'last_sent': datetime.utcnow().isoformat(),
                'alert_data': json.dumps(alert_data),
                'count': 1,
                'ttl': int((datetime.utcnow() + timedelta(days=7)).timestamp())
            }
        )
    
    def _increment_count(self, fingerprint: str):
        """Increment duplicate count"""
        
        self.alert_cache.update_item(
            Key={'alert_fingerprint': fingerprint},
            UpdateExpression='SET #count = #count + :inc',
            ExpressionAttributeNames={'#count': 'count'},
            ExpressionAttributeValues={':inc': 1}
        )
```

### Notification Routing Rules

Stored in RDS configuration:

```sql
-- Notification routing configuration

CREATE TABLE notification_routes (
    route_id SERIAL PRIMARY KEY,
    team_name VARCHAR(100),
    severity_level VARCHAR(20),  -- critical, warning, info
    agent_pattern VARCHAR(200),  -- Regex pattern for agent_id
    notification_channels JSONB,  -- ['slack', 'pagerduty', 'email']
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Example routes
INSERT INTO notification_routes (team_name, severity_level, agent_pattern, notification_channels) VALUES
('Platform Engineering', 'critical', '.*', '["slack", "pagerduty", "email"]'),
('Data Science', 'critical', 'ml-.*', '["slack", "pagerduty"]'),
('Customer Success', 'warning', 'customer-.*', '["slack", "email"]');
```

---

## 3. Agent/MCP Registration Portal

### Architecture

A self-service web portal built with React + FastAPI backend, integrated with LLM for configuration assistance.

### Backend API

```python
# portal/api/main.py

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional, List
import boto3
import secrets
from anthropic import Anthropic

app = FastAPI(title="GenAI Observability Portal API")

# Authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class AgentRegistration(BaseModel):
    name: str
    agent_type: str  # langchain, crewai, custom, etc.
    deployment_type: str  # lambda, ecs, ec2, k8s
    description: Optional[str] = None
    team_name: str
    cost_center: Optional[str] = None
    alert_email: str
    configuration: Optional[dict] = {}

class MCPServerRegistration(BaseModel):
    name: str
    server_type: str  # database, api, tool
    transport: str  # http, sse, stdio
    endpoint_url: Optional[str] = None
    description: Optional[str] = None
    team_name: str

class ConfigurationRequest(BaseModel):
    agent_type: str
    deployment_type: str
    requirements: str
    current_config: Optional[dict] = {}


class PortalService:
    def __init__(self):
        self.rds = boto3.client('rds-data')
        self.secrets = boto3.client('secretsmanager')
        self.anthropic = Anthropic()
        self.db_cluster_arn = os.environ['DB_CLUSTER_ARN']
        self.db_secret_arn = os.environ['DB_SECRET_ARN']
    
    def register_agent(self, registration: AgentRegistration, user_id: str) -> dict:
        """Register a new agent"""
        
        # Generate API key
        api_key = self._generate_api_key()
        
        # Store in RDS
        sql = """
        INSERT INTO agents (
            name, agent_type, deployment_type, description, 
            team_name, cost_center, alert_email, configuration,
            api_key_hash, created_by, created_at
        ) VALUES (
            :name, :agent_type, :deployment_type, :description,
            :team_name, :cost_center, :alert_email, :configuration,
            :api_key_hash, :user_id, NOW()
        ) RETURNING agent_id
        """
        
        response = self.rds.execute_statement(
            resourceArn=self.db_cluster_arn,
            secretArn=self.db_secret_arn,
            sql=sql,
            parameters=[
                {'name': 'name', 'value': {'stringValue': registration.name}},
                {'name': 'agent_type', 'value': {'stringValue': registration.agent_type}},
                {'name': 'deployment_type', 'value': {'stringValue': registration.deployment_type}},
                {'name': 'description', 'value': {'stringValue': registration.description or ''}},
                {'name': 'team_name', 'value': {'stringValue': registration.team_name}},
                {'name': 'cost_center', 'value': {'stringValue': registration.cost_center or ''}},
                {'name': 'alert_email', 'value': {'stringValue': registration.alert_email}},
                {'name': 'configuration', 'value': {'stringValue': json.dumps(registration.configuration)}},
                {'name': 'api_key_hash', 'value': {'stringValue': self._hash_api_key(api_key)}},
                {'name': 'user_id', 'value': {'stringValue': user_id}}
            ]
        )
        
        agent_id = response['records'][0][0]['stringValue']
        
        # Generate configuration guide
        config_guide = self._generate_config_guide(registration, api_key)
        
        return {
            'agent_id': agent_id,
            'api_key': api_key,  # Only shown once!
            'configuration_guide': config_guide
        }
    
    def _generate_config_guide(self, registration: AgentRegistration, api_key: str) -> dict:
        """Generate LLM-powered configuration guide"""
        
        prompt = f"""Generate a comprehensive setup guide for a GenAI agent with the following details:

**Agent Information:**
- Name: {registration.name}
- Type: {registration.agent_type}
- Deployment: {registration.deployment_type}
- Team: {registration.team_name}

**API Key:** {api_key}

Please provide:

1. **Quick Start**: A 3-step quick start guide
2. **Installation Commands**: Exact commands to run for their deployment type
3. **Code Example**: A complete, runnable code example showing SDK integration
4. **Environment Variables**: All required environment variables with values
5. **Testing**: How to verify the setup is working
6. **Next Steps**: What to do after basic setup

Make this practical and copy-paste ready for a developer.
"""
        
        message = self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {
            'guide_text': message.content[0].text,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _generate_api_key(self) -> str:
        """Generate secure API key"""
        return f"genai_obs_{secrets.token_urlsafe(32)}"
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()


# API Endpoints

portal_service = PortalService()

@app.post("/api/v1/agents/register")
async def register_agent(
    registration: AgentRegistration,
    token: str = Depends(oauth2_scheme)
):
    """Register a new agent"""
    
    user_id = verify_token(token)  # Implement token verification
    
    try:
        result = portal_service.register_agent(registration, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents")
async def list_agents(
    team_name: Optional[str] = None,
    token: str = Depends(oauth2_scheme)
):
    """List registered agents"""
    
    # Implementation
    pass

@app.post("/api/v1/configuration/assist")
async def get_configuration_assistance(
    request: ConfigurationRequest,
    token: str = Depends(oauth2_scheme)
):
    """Get LLM-powered configuration assistance"""
    
    assistant = ConfigurationAssistant()
    guidance = assistant.assist_configuration(request.dict())
    
    return guidance

@app.post("/api/v1/agents/{agent_id}/health-check")
async def run_health_check(
    agent_id: str,
    token: str = Depends(oauth2_scheme)
):
    """Run health check for an agent"""
    
    # Verify agent is sending data
    # Check last event timestamp
    # Validate configuration
    
    pass

@app.get("/api/v1/sdk/download")
async def download_sdk(
    language: str = "python",
    token: str = Depends(oauth2_scheme)
):
    """Download SDK package"""
    
    # Return pre-built SDK package or installation instructions
    pass
```

### Frontend Portal (React)

```typescript
// portal/frontend/src/components/AgentRegistration.tsx

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation } from 'react-query';
import axios from 'axios';

interface AgentRegistrationForm {
  name: string;
  agent_type: string;
  deployment_type: string;
  description?: string;
  team_name: string;
  cost_center?: string;
  alert_email: string;
}

export const AgentRegistrationWizard: React.FC = () => {
  const [step, setStep] = useState(1);
  const [registrationResult, setRegistrationResult] = useState<any>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<AgentRegistrationForm>();
  
  const registerMutation = useMutation(
    (data: AgentRegistrationForm) => 
      axios.post('/api/v1/agents/register', data),
    {
      onSuccess: (response) => {
        setRegistrationResult(response.data);
        setStep(4); // Go to success step
      }
    }
  );
  
  const onSubmit = (data: AgentRegistrationForm) => {
    registerMutation.mutate(data);
  };
  
  return (
    <div className="registration-wizard">
      {step === 1 && (
        <div className="step-1">
          <h2>Register Your Agent</h2>
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="form-group">
              <label>Agent Name</label>
              <input
                {...register('name', { required: true })}
                placeholder="e.g., customer-support-agent"
              />
              {errors.name && <span className="error">Name is required</span>}
            </div>
            
            <div className="form-group">
              <label>Agent Type</label>
              <select {...register('agent_type', { required: true })}>
                <option value="langchain">LangChain</option>
                <option value="crewai">CrewAI</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Deployment Type</label>
              <select {...register('deployment_type', { required: true })}>
                <option value="lambda">AWS Lambda</option>
                <option value="ecs">ECS/Fargate</option>
                <option value="ec2">EC2</option>
                <option value="k8s">Kubernetes</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Team Name</label>
              <input {...register('team_name', { required: true })} />
            </div>
            
            <div className="form-group">
              <label>Alert Email</label>
              <input
                type="email"
                {...register('alert_email', { required: true })}
              />
            </div>
            
            <button type="submit" className="btn-primary">
              Register Agent
            </button>
          </form>
        </div>
      )}
      
      {step === 4 && registrationResult && (
        <div className="step-success">
          <h2>✅ Agent Registered Successfully!</h2>
          
          <div className="api-key-display">
            <h3>⚠️ Save Your API Key</h3>
            <p>This will only be shown once:</p>
            <code className="api-key">
              {registrationResult.api_key}
            </code>
            <button onClick={() => navigator.clipboard.writeText(registrationResult.api_key)}>
              Copy to Clipboard
            </button>
          </div>
          
          <div className="configuration-guide">
            <h3>Setup Instructions</h3>
            <div 
              dangerouslySetInnerHTML={{ 
                __html: marked(registrationResult.configuration_guide.guide_text)
              }} 
            />
          </div>
          
          <div className="next-steps">
            <button onClick={() => downloadSDK()}>Download SDK</button>
            <button onClick={() => navigateToDashboard()}>View Dashboard</button>
          </div>
        </div>
      )}
    </div>
  );
};
```

### Portal Features Summary

1. **Self-Service Registration**
   - Agent registration
   - MCP server registration
   - API key generation
   - Automatic configuration

2. **LLM Configuration Wizard**
   - Interactive setup guidance
   - Code generation
   - Best practices suggestions
   - Troubleshooting help

3. **Health Checks**
   - Connectivity validation
   - Data flow verification
   - Configuration testing
   - Performance baseline

4. **Team Management**
   - RBAC (Role-Based Access Control)
   - Team dashboards
   - Cost allocation
   - Alert routing

5. **SDK Management**
   - Download center
   - Version management
   - Update notifications
   - Integration testing tools

---

## 4. Enhanced Error Investigation

### Error Storage Schema

```sql
-- Error tracking tables in RDS

CREATE TABLE errors (
    error_id VARCHAR(100) PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    execution_id VARCHAR(100),
    timestamp TIMESTAMP NOT NULL,
    error_type VARCHAR(50),
    error_message TEXT,
    stack_trace TEXT,
    context JSONB,  -- Full error context
    severity VARCHAR(20),
    
    -- LLM Analysis
    llm_analysis TEXT,
    root_cause TEXT,
    remediation_steps JSONB,
    impact_assessment TEXT,
    prevention_notes TEXT,
    similar_error_ids TEXT[],
    
    -- Resolution tracking
    resolution_status VARCHAR(20) DEFAULT 'open',
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    resolution_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_agent_timestamp (agent_id, timestamp),
    INDEX idx_error_type (error_type),
    INDEX idx_resolution_status (resolution_status)
);

-- Error patterns (for ML-based detection)
CREATE TABLE error_patterns (
    pattern_id SERIAL PRIMARY KEY,
    pattern_signature VARCHAR(200) UNIQUE,
    error_type VARCHAR(50),
    frequency INT DEFAULT 1,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    affected_agents TEXT[],
    common_root_cause TEXT,
    common_resolution TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Investigation Dashboard

Web interface showing:
- Error timeline visualization
- Root cause analysis
- Similar incident history
- Remediation progress tracking
- Team collaboration features

---

## Cost Analysis

### Monthly Cost Breakdown (Enhanced System)

**Base System:** $1,900/month (from original architecture)

**New Components:**

1. **LLM Investigation:**
   - Claude API: ~$90/month (100 investigations/day)
   
2. **Error Storage (DynamoDB):**
   - Writes: ~$50/month
   - Reads: ~$20/month
   - Storage: ~$10/month
   
3. **Notification Services:**
   - SNS: ~$10/month (assuming 10K messages)
   - Lambda formatters: ~$20/month
   - External service costs (Slack/PagerDuty): Variable
   
4. **Registration Portal:**
   - ECS Fargate: ~$100/month (2 tasks)
   - ALB: ~$20/month
   - RDS (already included in base)
   
5. **Additional Lambda executions:**
   - ~$50/month

**Total Enhanced System: ~$2,270/month**

**ROI Justification:**
- Reduces MTTR by 60-80% (LLM investigation)
- Prevents alert fatigue (smart deduplication)
- Faster onboarding (self-service portal)
- Better incident documentation
- Estimated savings: 20-30 engineering hours/month

---

## Deployment Guide

### Phase 1: LLM Investigation (Week 1-2)

```bash
# 1. Deploy error storage
aws cloudformation deploy \
  --template-file infrastructure/error-storage.yaml \
  --stack-name genai-obs-error-storage

# 2. Deploy LLM investigation Lambda
cd lambda/llm_investigator
pip install -r requirements.txt -t package/
cd package && zip -r ../function.zip .
cd .. && zip -g function.zip handler.py

aws lambda create-function \
  --function-name genai-llm-investigator \
  --runtime python3.11 \
  --handler handler.lambda_handler \
  --role arn:aws:iam::ACCOUNT:role/genai-obs-lambda-role \
  --zip-file fileb://function.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={ANTHROPIC_API_KEY=sk-...}

# 3. Update anomaly detector to trigger investigation
# Modify existing anomaly detection Lambda to invoke LLM investigator
```

### Phase 2: Notification Platform (Week 3-4)

```bash
# 1. Create SNS topics
aws cloudformation deploy \
  --template-file infrastructure/sns-topics.yaml \
  --stack-name genai-obs-notifications

# 2. Deploy formatter Lambdas
# Deploy Slack formatter
# Deploy PagerDuty formatter
# Deploy Teams formatter

# 3. Configure webhooks
# Set up Slack webhook URL
# Configure PagerDuty integration key
# Set up Teams connector
```

### Phase 3: Registration Portal (Week 5-6)

```bash
# 1. Deploy backend API
cd portal/api
docker build -t genai-portal-api .
docker tag genai-portal-api:latest ACCOUNT.dkr.ecr.REGION.amazonaws.com/genai-portal-api:latest
docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/genai-portal-api:latest

# 2. Deploy to ECS
aws cloudformation deploy \
  --template-file infrastructure/portal-ecs.yaml \
  --stack-name genai-obs-portal

# 3. Deploy frontend
cd portal/frontend
npm run build
aws s3 sync build/ s3://genai-portal-frontend/
aws cloudfront create-invalidation --distribution-id DIST_ID --paths "/*"
```

---

## Security Considerations

### API Key Management
- Keys stored as hashed values only
- Rotation every 90 days
- Per-agent key isolation
- Audit logging for all key usage

### LLM Data Privacy
- No PII in investigation prompts
- Configurable data redaction
- Audit trail for LLM queries
- Option to use private Claude deployment

### Notification Security
- Webhook URL encryption
- TLS 1.3 for all communications
- Message signing
- Rate limiting per channel

---

## Monitoring the Observability System

**Meta-monitoring:** We need to monitor the monitoring system!

```yaml
# CloudWatch Alarms for the platform itself

Alarms:
  - Name: LLMInvestigationFailures
    Metric: Lambda Errors
    Threshold: > 5 in 5 minutes
    
  - Name: NotificationDeliveryFailures
    Metric: SNS Publish Failures
    Threshold: > 10 in 15 minutes
    
  - Name: PortalAPIErrors
    Metric: ALB 5xx Errors
    Threshold: > 50 in 5 minutes
```

---

## Next Steps / Future Enhancements

1. **Automated Remediation**
   - LLM generates runbooks
   - Auto-execute safe fixes
   - Rollback capabilities

2. **Predictive Analysis**
   - Forecast anomalies before they happen
   - Capacity planning recommendations
   - Trend analysis

3. **Multi-Model Support**
   - A/B test different LLM models
   - Cost vs. quality optimization
   - Specialized models for different incident types

4. **Integration Hub**
   - Jira ticket creation
   - ServiceNow integration
   - GitLab/GitHub issue linking

---

**Document Version:** 2.0 (Enhanced)  
**Last Updated:** 2025-01  
**Author:** Platform Engineering Team
