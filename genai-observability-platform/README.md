# GenAI Observability Platform

A comprehensive, enterprise-grade observability platform for monitoring, tracing, and debugging GenAI agents at scale.

## Key Features

### Core Observability
- **Distributed Tracing**: Track execution flow across agent components with span-level detail
- **LLM Monitoring**: Monitor token usage, latency, costs, and model performance
- **Anomaly Detection**: Automatic detection of errors, latency spikes, and unusual patterns
- **AI-Powered Investigation**: Claude-powered root cause analysis with actionable recommendations

### Natural Language Query (NLQ)
- **Conversational Interface**: Query observability data using natural language
- **Smart Suggestions**: Context-aware query suggestions and follow-ups
- **Saved Queries**: Save and share frequently used queries

### Autonomous Remediation
- **AI-Generated Action Plans**: Automatic remediation recommendations based on anomalies
- **Approval Workflow**: Configurable approval gates before execution
- **Safe Rollback**: Built-in rollback capabilities for all remediation actions
- **Audit Trail**: Complete history of all remediation activities

### SSO Authentication
- **OIDC Support**: Google, Okta, Azure AD, Auth0 integration
- **SAML 2.0**: Enterprise SAML with Single Logout (SLO) support
- **Token Revocation**: Secure session termination across providers

### Integration Hub
- **Ticketing**: Jira, ServiceNow integration for issue management
- **Notifications**: Slack, Microsoft Teams, PagerDuty alerting
- **Version Control**: GitHub integration for automated PR creation
- **Bi-directional Sync**: Keep external systems in sync with observability data

### Enterprise Features
- **Multi-Region Support**: Geographic routing with automatic failover
- **PII Redaction**: Configurable sensitive data detection and masking
- **OpenTelemetry Export**: Standard OTLP, Jaeger, Zipkin export
- **Real-time Dashboard**: Visual analytics, trace exploration, and cost management
- **CLI Tools**: Full command-line interface for automation and scripting
- **Self-Service Portal**: Agent registration, API key management, and team administration

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VISUALIZATION (React Dashboard, CLI)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                    API LAYER (FastAPI, WebSocket, GraphQL)                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│              PROCESSING (Stream Processor, Anomaly Detection, LLM)           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│          STORAGE (DynamoDB, Timestream, OpenSearch, RDS Aurora, S3)          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                  INGESTION (API Gateway, Kinesis, Firehose)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                      COLLECTION (Python SDK, Integrations)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Description | Location |
|-----------|-------------|----------|
| **SDK** | Python SDK for instrumenting agents | `sdk/python/` |
| **Infrastructure** | AWS CloudFormation templates | `infrastructure/` |
| **Lambda** | Serverless processing functions | `lambda/` |
| **Glue ETL** | Batch processing jobs | `glue/` |
| **Frontend** | React dashboard | `frontend/` |
| **API** | FastAPI portal backend | `api/` |
| **CLI** | Command-line interface | `cli/` |
| **Database** | RDS schema migrations | `database/` |

## Quick Start

### 1. Deploy Infrastructure

```bash
cd infrastructure
./deploy.sh deploy dev
```

### 2. Install SDK

```bash
pip install genai-observability
```

### 3. Instrument Your Agent

```python
from genai_observability import init, get_tracer

# Initialize
init(
    endpoint="https://your-api-endpoint",
    api_key="your-api-key",
    agent_id="my-agent",
)

tracer = get_tracer()

# Trace execution
with tracer.trace(name="process_request") as ctx:
    # LLM call tracing
    with tracer.llm_span(name="call_claude", parent=ctx, model="claude-sonnet-4-20250514"):
        response = anthropic.messages.create(...)

    # Tool call tracing
    with tracer.tool_span(name="search_database", parent=ctx):
        results = database.search(...)
```

### 4. Install CLI

```bash
pip install genai-obs-cli
genai-obs configure
```

### 5. View Traces

```bash
# Via CLI
genai-obs traces list --agent my-agent

# Via Dashboard
cd frontend
npm install && npm run dev
# Open http://localhost:3000
```

## Running Tests

```bash
# All tests
./scripts/run-tests.sh

# SDK tests
cd sdk/python && pytest

# Lambda tests
cd lambda && pytest

# API tests
cd api && pytest
```

## Documentation

### Getting Started
- [Deployment Guide](docs/deployment-guide.md) - Step-by-step deployment instructions
- [SDK Documentation](sdk/python/README.md) - How to instrument your agents

### Architecture & Design
- [Architecture Documentation](docs/architecture.md) - Detailed system architecture
- [API Reference](docs/api/openapi.yaml) - OpenAPI specification

### Operations
- [Operations Runbook](docs/operations-runbook.md) - Troubleshooting and maintenance
- [CLI Documentation](cli/README.md) - Command-line interface usage

### Component Guides
- [Infrastructure Guide](infrastructure/README.md) - CloudFormation templates
- [Lambda Functions](lambda/README.md) - Serverless functions
- [Frontend Guide](frontend/README.md) - React dashboard
- [API Documentation](api/README.md) - Portal API

## Environment Support

| Environment | Description | Use Case |
|-------------|-------------|----------|
| `dev` | Development | Local testing, feature development |
| `staging` | Staging | Integration testing, QA |
| `prod` | Production | Live workloads |

## Cost Estimation

For 10M events/day:

| Component | Monthly Cost |
|-----------|-------------|
| API Gateway + Lambda | ~$85 |
| Kinesis | ~$150 |
| DynamoDB | ~$200 |
| Timestream | ~$300 |
| OpenSearch | ~$500 |
| RDS Aurora | ~$400 |
| S3 + Glue | ~$150 |
| LLM Investigation | ~$500 |
| **Total** | **~$2,300/month** |

## Security

### Authentication
- **SSO/OIDC**: Google, Okta, Azure AD, Auth0 with token revocation
- **SAML 2.0**: Enterprise SSO with Single Logout (SLO) support
- **API Keys**: Agent authentication with scoped permissions
- **JWT Tokens**: Stateless session management

### Authorization
- **RBAC**: Role-based access control (admin, user, viewer)
- **Team Isolation**: Multi-tenant data separation
- **Scoped API Keys**: Per-agent permission boundaries

### Data Protection
- **Encryption**: TLS 1.2+ in transit, AES-256 at rest
- **PII Redaction**: Automatic detection and masking of sensitive data
- **Audit Logging**: Full audit trail via CloudTrail
- **Secrets Management**: AWS Secrets Manager for credentials

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/genai-observability/issues)
- **Documentation**: [docs/](docs/)
- **Slack**: #genai-observability (internal)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://reactjs.org/)
- [AWS CDK/CloudFormation](https://aws.amazon.com/cloudformation/)
- [Anthropic Claude](https://www.anthropic.com/)
