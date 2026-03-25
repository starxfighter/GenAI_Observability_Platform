# GenAI Observability Platform - Enhanced Features Quick Reference

## 📋 What's New

This enhanced architecture adds **intelligent automation** and **self-service capabilities** to the GenAI observability platform.

---

## 🎯 Three Major Additions

### 1. 🤖 LLM-Powered Intelligence
**What it does:** Automatically investigates incidents using Claude Sonnet 4

**Key Features:**
- Analyzes error logs, traces, and metrics automatically
- Provides human-readable root cause analysis
- Suggests remediation steps
- Links similar past incidents
- Creates executive summaries

**When it triggers:**
- High-severity errors (automatic)
- Anomalies detected (automatic)
- Manual investigation requests (on-demand)

**Cost:** ~$0.03 per investigation = ~$90/month for 100 investigations/day

**Example output:**
```
Root Cause: Database connection pool exhaustion due to 
unclosed connections in MCP database-server

Evidence: 
- Latency spike from 200ms → 5000ms at 10:30 AM
- Error logs show "connection timeout" 47 times
- Similar incident resolved 2 weeks ago with same pattern

Immediate Actions:
1. Restart database-server MCP server
2. Review connection pooling configuration
3. Add connection cleanup in error handlers

Prevention: Implement connection pool monitoring with 
alerts at 80% capacity
```

---

### 2. 🔔 Smart Notification Platform
**What it does:** Routes alerts to the right people through the right channels

**Supported Channels:**
- **Slack** - Rich block kit messages with buttons
- **PagerDuty** - Auto-creates incidents for P1/P2
- **Microsoft Teams** - Adaptive cards with actions
- **Email** - HTML formatted with investigation details

**Smart Features:**
- **Severity-based routing** (Critical → page on-call, Warning → Slack, Info → email)
- **Alert deduplication** (prevents duplicate alerts for 24 hours)
- **Team routing** (routes to correct team based on agent ownership)
- **Rich formatting** (includes LLM analysis, links to dashboards)

**Architecture:**
```
Anomaly Detector → SNS Topic Router → Formatter Lambdas → Channels
                         ↓
                  (severity filter)
                         ↓
                  Critical/Warning/Info topics
```

**Configuration Example:**
```python
# In RDS notification_routes table
{
    'team': 'Platform Engineering',
    'severity': 'critical',
    'agent_pattern': '.*',
    'channels': ['slack', 'pagerduty', 'email']
}
```

---

### 3. 🎛️ Registration Portal
**What it does:** Self-service console for registering agents and MCP servers

**Key Capabilities:**

**A. Agent Registration**
- Fill out simple form (name, type, deployment, team)
- Get API key (shown once, securely hashed in storage)
- Receive LLM-generated setup guide
- Download SDK and code examples

**B. LLM Configuration Wizard**
```
User: "I need to track token usage for my LangChain agent on Lambda"

Portal: [Generates complete guide]
1. Install SDK: pip install genai-observability-sdk
2. Set environment variables: OBSERVABILITY_API_ENDPOINT=...
3. Code example: [shows complete integration code]
4. Testing: [shows how to verify it works]
```

**C. Health Checks**
- Validates agent is sending data
- Checks configuration correctness
- Verifies connectivity
- Sets performance baselines

**D. Team Management**
- RBAC (role-based access control)
- Cost center allocation
- Alert routing configuration
- Dashboard customization

**Portal Stack:**
- Frontend: React + TypeScript (CloudFront + S3)
- Backend: FastAPI Python (ECS Fargate)
- Database: RDS Aurora (shared with main system)
- LLM: Claude Sonnet 4 for assistance

---

## 🔧 How They Work Together

### Scenario: Critical Error Occurs

```
1. Agent throws error
   ↓
2. SDK captures stack trace, context
   ↓
3. Ingestion Lambda categorizes as critical
   ↓
4. Real-time processor detects anomaly
   ↓
5. Anomaly detector triggers LLM investigator
   ↓
6. LLM Investigator:
   - Gathers traces from OpenSearch
   - Gets error logs
   - Checks metrics from Timestream
   - Finds similar past incidents
   - Calls Claude API for analysis
   ↓
7. SNS Topic Router receives results
   ↓
8. Notification formatters send to:
   - Slack (#genai-critical-alerts) with rich message
   - PagerDuty (creates P1 incident, pages on-call)
   - Email (to team distribution list)
   ↓
9. On-call engineer:
   - Gets paged by PagerDuty
   - Opens Slack, sees LLM analysis
   - Clicks "View Dashboard" button
   - Sees full investigation with remediation steps
   - Follows steps to resolve
   ↓
10. Marks incident as resolved in portal
    ↓
11. System learns from resolution
```

---

## 📊 Data Flows

### Investigation Flow
```
Error/Anomaly → OpenSearch (traces)
             → Timestream (metrics)
             → DynamoDB (errors)
             → RDS (similar incidents)
                    ↓
             LLM Investigator
             (Claude Sonnet 4)
                    ↓
             Analysis Results
                    ↓
             ├─→ DynamoDB (storage)
             ├─→ SNS (notifications)
             └─→ Dashboard (display)
```

### Notification Flow
```
Alert Event → SNS Topic Router
                    ↓
         (filters by severity)
                    ↓
         ├─→ Slack Formatter → Slack API
         ├─→ PagerDuty Formatter → PagerDuty API
         ├─→ Teams Formatter → Teams Webhook
         └─→ Email Formatter → SES
```

### Registration Flow
```
User → Portal UI → FastAPI Backend
                        ↓
                   Generate API Key
                        ↓
                   Store in RDS
                        ↓
                   LLM Config Assistant
                   (Claude Sonnet 4)
                        ↓
                   Setup Guide
                        ↓
                   Return to User
```

---

## 💰 Cost Analysis

### Base System (Original)
**$1,900/month** for 10M events/day

### Enhanced Features
- LLM Investigation: **+$90/month**
- Error Storage (DynamoDB): **+$80/month**
- Notification Platform: **+$30/month**
- Registration Portal: **+$120/month**
- Additional Lambda: **+$50/month**

### Total Enhanced System
**$2,270/month** for 10M events/day

### ROI Calculation
**Time Savings:**
- MTTR reduced from 45 min → 10 min (75% reduction)
- 100 incidents/month × 35 min saved = 58 hours/month
- At $100/hour engineer time = **$5,800/month value**

**Additional Benefits:**
- Faster onboarding (self-service portal)
- Reduced alert fatigue
- Better incident documentation
- Improved system reliability

**Net Value: $5,800 - $370 = $5,430/month positive ROI**

---

## 🚀 Quick Start for Enhanced Features

### Enable LLM Investigation

```bash
# 1. Set Anthropic API key
aws secretsmanager create-secret \
  --name genai-obs-anthropic-key \
  --secret-string "sk-ant-..."

# 2. Deploy LLM investigator Lambda
aws lambda create-function \
  --function-name genai-llm-investigator \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --environment Variables={ANTHROPIC_API_KEY=sk-ant-...}

# 3. Update anomaly detector to trigger investigation
# (Modify existing Lambda to invoke LLM investigator for critical)
```

### Configure Notifications

```bash
# 1. Create Slack webhook
# Go to Slack: Apps → Incoming Webhooks → Add to Channel

# 2. Store webhook URL
aws secretsmanager create-secret \
  --name slack-webhook-url \
  --secret-string "https://hooks.slack.com/..."

# 3. Deploy SNS topics and formatters
aws cloudformation deploy \
  --template-file infrastructure/notifications.yaml \
  --stack-name genai-notifications
```

### Deploy Registration Portal

```bash
# 1. Build and push Docker image
cd portal
docker build -t genai-portal .
docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/genai-portal

# 2. Deploy to ECS
aws ecs create-service \
  --cluster genai-cluster \
  --service-name portal \
  --task-definition genai-portal

# 3. Frontend to S3/CloudFront
cd frontend && npm run build
aws s3 sync build/ s3://genai-portal-frontend/
```

---

## 🎨 UI Screenshots (Conceptual)

### Investigation Dashboard
```
╔══════════════════════════════════════════════════════════╗
║  🔍 Incident Investigation: sales-agent-error-2025-01-15 ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  🤖 AI Analysis (Claude Sonnet 4)                        ║
║  ┌────────────────────────────────────────────────────┐ ║
║  │ Root Cause: Database connection pool exhaustion    │ ║
║  │                                                     │ ║
║  │ The agent is not properly closing database         │ ║
║  │ connections after MCP tool calls...                │ ║
║  └────────────────────────────────────────────────────┘ ║
║                                                          ║
║  📊 Impact: HIGH - 47 failed requests in 10 minutes     ║
║                                                          ║
║  🔧 Immediate Actions:                                   ║
║  ☐ 1. Restart database-server MCP                       ║
║  ☐ 2. Review connection pool config                     ║
║  ☐ 3. Add connection cleanup                            ║
║                                                          ║
║  📎 Similar Incidents: 2 found                           ║
║  └─ incident-2025-01-01 (resolved with connection fix)  ║
║                                                          ║
║  [View Traces] [View Logs] [Mark Resolved]              ║
╚══════════════════════════════════════════════════════════╝
```

### Slack Notification
```
🚨 CRITICAL: high_error_rate - sales-agent

Agent: sales-agent
Time: Today at 10:30 AM

🤖 AI Investigation Summary
The agent is experiencing database connection pool 
exhaustion due to unclosed connections...

Root Cause: Improper connection handling in MCP calls

Immediate Actions:
• Restart database-server MCP
• Review connection pooling configuration  
• Add connection cleanup in error handlers

[View Dashboard] [View Traces] [Agent Details]
```

### Registration Portal
```
╔════════════════════════════════════════════════════════╗
║  🎛️ Register New Agent                                 ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  Agent Name: [customer-support-agent_______________]  ║
║                                                        ║
║  Agent Type: [LangChain ▼]                            ║
║                                                        ║
║  Deployment: [AWS Lambda ▼]                           ║
║                                                        ║
║  Team:       [Customer Success_________________]      ║
║                                                        ║
║  Alert Email: [team@example.com________________]      ║
║                                                        ║
║  💡 Need help? Ask our AI assistant                   ║
║     [What configuration do I need?]                   ║
║                                                        ║
║  [Register Agent]                                     ║
╚════════════════════════════════════════════════════════╝

After registration:
╔════════════════════════════════════════════════════════╗
║  ✅ Registration Successful!                           ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  ⚠️ Save Your API Key (shown once):                   ║
║  genai_obs_abc123xyz789...                            ║
║  [Copy to Clipboard]                                  ║
║                                                        ║
║  📖 Setup Instructions:                                ║
║  ┌──────────────────────────────────────────────────┐ ║
║  │ Quick Start:                                      │ ║
║  │                                                   │ ║
║  │ 1. Install SDK:                                  │ ║
║  │    pip install genai-observability-sdk           │ ║
║  │                                                   │ ║
║  │ 2. Set environment:                              │ ║
║  │    export OBSERVABILITY_API_ENDPOINT=...         │ ║
║  │    export AGENT_ID=customer-support-agent        │ ║
║  │                                                   │ ║
║  │ 3. Add to your code:                             │ ║
║  │    from genai_observability import ...           │ ║
║  │    [Full code example provided]                  │ ║
║  └──────────────────────────────────────────────────┘ ║
║                                                        ║
║  [Download SDK] [View Dashboard] [Test Connection]    ║
╚════════════════════════════════════════════════════════╝
```

---

## 🔐 Security Best Practices

### API Keys
- ✅ Generated with crypto-secure random
- ✅ Hashed before storage (SHA-256)
- ✅ Shown only once at creation
- ✅ Rotated every 90 days
- ✅ Can be revoked instantly

### LLM Data
- ✅ No PII in prompts (configurable redaction)
- ✅ Audit trail for all LLM queries
- ✅ Option for private Claude deployment
- ✅ Data retention policies

### Notifications
- ✅ Webhook URLs encrypted at rest
- ✅ TLS 1.3 for all channels
- ✅ Message signing for webhooks
- ✅ Rate limiting per channel

---

## 📈 Monitoring the Monitors

**Yes, we monitor the observability system itself!**

```yaml
Key Metrics:
  - LLM investigation success rate
  - Notification delivery rate
  - Portal API response times
  - Error storage capacity
  - SNS topic throughput

Alarms:
  - LLM investigation failures > 5 in 5 min
  - Notification delivery failures > 10 in 15 min
  - Portal API 5xx errors > 50 in 5 min
  - SNS throttling detected
```

---

## 🎓 Training Resources

### For Developers
- **SDK Integration Guide**: How to instrument your agent
- **Configuration Best Practices**: Optimal settings
- **Troubleshooting Guide**: Common issues and fixes

### For Operators
- **Investigation Playbook**: How to use LLM insights
- **Alert Response Guide**: Handling different severity levels
- **Portal Administration**: Managing teams and access

### For Executives
- **Dashboard Overview**: Key metrics explained
- **Cost Management**: Understanding and optimizing costs
- **ROI Report**: Business value demonstration

---

## 🆘 Support

### Documentation
- Architecture diagrams (this document)
- API documentation (OpenAPI spec)
- SDK documentation (Python/TypeScript)
- Video tutorials

### Channels
- Slack: #genai-observability-support
- Email: genai-obs-support@example.com
- On-call: PagerDuty escalation

### Office Hours
- Weekly: Wednesdays 2-3 PM PT
- Monthly: Architecture review (last Friday)

---

## 🔮 Roadmap

**Q1 2025** ✅ (Current)
- LLM-powered investigation
- Smart notifications
- Registration portal

**Q2 2025** 🚧 (Planned)
- Automated remediation (LLM generates and executes fixes)
- Predictive anomaly detection
- Multi-model LLM support (A/B testing)

**Q3 2025** 📋 (Planned)
- Integration hub (Jira, ServiceNow, GitHub)
- Custom alert rules engine
- Advanced cost optimization

**Q4 2025** 💭 (Ideas)
- Autonomous healing agents
- Natural language query interface
- Multi-region deployment

---

**Questions? Reach out to the Platform Engineering team!**

**Document Version:** 2.0  
**Last Updated:** January 2025
