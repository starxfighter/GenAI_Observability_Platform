# GenAI Observability Platform

An enterprise-grade observability and monitoring platform purpose-built for GenAI and LLM applications. Monitor AI agents, track LLM performance, detect anomalies, and automate remediation — all powered by Claude.

---

## Features

- **Distributed Tracing** — Span-level visibility into AI agent execution
- **LLM Metrics** — Token usage, latency, cost, and model performance tracking
- **Anomaly Detection** — Automatic detection of error spikes, latency issues, and unusual patterns
- **AI-Powered Investigation** — Root cause analysis via Claude (Anthropic API)
- **Autonomous Remediation** — Approval workflows with rollback capabilities
- **Natural Language Queries** — Query observability data in plain English
- **Real-Time Dashboards** — WebSocket-powered live updates
- **Multi-Tenant Security** — SSO, RBAC, PII redaction, WAF
- **External Integrations** — Slack, PagerDuty, Microsoft Teams, Jira, ServiceNow, GitHub

**Scale:** Designed for 10M+ events/day with sub-second ingestion and real-time processing.

---

## Architecture

The platform uses a dual-path architecture:

**Hot Path (Real-time)**
```
SDK → API Gateway → Kinesis → Stream Processor → DynamoDB / Timestream / OpenSearch → Dashboard
```

**Cold Path (Batch Analytics)**
```
S3 (raw events) → EventBridge → Step Functions → Glue ETL → RDS Aurora
```

**Alert Pipeline**
```
Anomaly Detector → SNS → LLM Investigator (Claude) → Deduplicator → Formatters → Slack / PagerDuty / Teams / Email
```

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript 5, Vite, Recharts, TailwindCSS, Zustand |
| **Backend API** | FastAPI, Pydantic, Python 3.11+, Structlog |
| **Event Processing** | AWS Kinesis, AWS Lambda (14 functions), AWS Step Functions, EventBridge |
| **Storage** | DynamoDB, Timestream, OpenSearch, RDS Aurora PostgreSQL, S3, ElastiCache |
| **Infrastructure** | CloudFormation (6 stacks), Terraform (22 modules), Docker, GitHub Actions |
| **Auth & Security** | AWS Cognito, JWT, AWS Secrets Manager, AWS WAF, IAM |
| **AI** | Anthropic Claude API (investigation & NLQ) |
| **Monitoring** | Prometheus, Grafana |

---

## Project Structure

```
genai-observability-platform/
├── api/                    # FastAPI backend (REST + WebSocket + worker)
├── frontend/               # React dashboard
├── cli/                    # Command-line interface
├── lambda/                 # 14 AWS Lambda functions
│   ├── ingestion/
│   ├── stream_processor/
│   ├── anomaly_detector/
│   ├── llm_investigator/
│   ├── alert_deduplicator/
│   ├── nl_query/
│   ├── pii_redactor/
│   ├── autonomous_remediation/
│   ├── integrations/
│   └── ...
├── infrastructure/         # CloudFormation IaC
├── terraform/              # Terraform IaC (22 modules)
├── database/               # PostgreSQL migrations
├── glue/                   # AWS Glue ETL jobs
├── sdk/                    # Python instrumentation SDK
├── examples/               # Basic and LangChain agent examples
├── docs/                   # Architecture, deployment, and operations guides
├── localstack/             # Local AWS emulation
├── .github/workflows/      # CI, deploy, and release pipelines
└── docker-compose.yaml     # Full local dev stack
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js (modern LTS)
- AWS CLI (for cloud deployment)

### Local Development

1. **Clone the repo**
   ```bash
   git clone https://github.com/starxfighter/GenAI_Observability_Platform.git
   cd GenAI_Observability_Platform
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start the full stack**
   ```bash
   docker-compose up
   ```

   This starts: PostgreSQL, Redis, LocalStack (AWS emulation), API, WebSocket server, Frontend, Prometheus, Grafana, and dev tools.

4. **Access the dashboard**
   - Frontend: http://localhost:3000
   - API docs: http://localhost:8000/docs
   - Grafana: http://localhost:3001

### Instrument Your Agent

```python
from genai_observability import ObservabilityClient

client = ObservabilityClient(api_key="your-api-key")

with client.trace("my-agent-run") as trace:
    with trace.span("llm-call") as span:
        response = your_llm_call()
        span.set_attribute("tokens", response.usage.total_tokens)
```

---

## Cloud Deployment

### CloudFormation

```bash
aws cloudformation deploy \
  --template-file infrastructure/main.yaml \
  --stack-name genai-observability \
  --capabilities CAPABILITY_IAM
```

### Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

See [`docs/deployment-guide.md`](genai-observability-platform/docs/deployment-guide.md) for full deployment instructions.

---

## CI/CD

Three GitHub Actions pipelines are included:

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yaml` | Push / PR | Lint, type check, test |
| `deploy.yaml` | Merge to main | Deploy to AWS |
| `release.yaml` | Tag push | Cut a versioned release |

---

## Cost Estimates

| Environment | Events/Day | Est. Monthly Cost |
|---|---|---|
| Development | < 100K | ~$50 |
| Staging | ~1M | ~$350 |
| Production | 10M+ | ~$2,790 |

---

## Documentation

- [`docs/architecture.md`](genai-observability-platform/docs/architecture.md) — System design and data flows
- [`docs/deployment-guide.md`](genai-observability-platform/docs/deployment-guide.md) — Setup and deployment
- [`docs/operations-runbook.md`](genai-observability-platform/docs/operations-runbook.md) — Troubleshooting and operations
- [`PLATFORM-OVERVIEW.md`](genai-observability-platform/PLATFORM-OVERVIEW.md) — Feature matrix and deployment options
- [`PROGRESS.md`](genai-observability-platform/PROGRESS.md) — Development status

---

## License

MIT
