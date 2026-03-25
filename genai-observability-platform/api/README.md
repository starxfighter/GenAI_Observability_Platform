# GenAI Observability Platform - Portal API

FastAPI-based REST API for the GenAI Observability Platform.

## Features

- **Traces API**: Query and manage execution traces
- **Agents API**: Register and manage agents
- **Alerts API**: View and manage alerts with investigations
- **Metrics API**: Dashboard metrics and time series data
- **Natural Language Query API**: Query data using natural language
- **Remediation API**: Autonomous remediation workflow management
- **Integrations API**: Third-party service integrations
- **SSO Authentication**: OIDC (Google, Okta, Azure AD, Auth0) and SAML 2.0
- **API Key Authentication**: Agent authentication support
- **OpenAPI Documentation**: Interactive API docs

## Tech Stack

- **FastAPI** - Web framework
- **Pydantic** - Data validation
- **boto3** - AWS SDK
- **OpenSearch** - Full-text search
- **Structlog** - Structured logging

## Getting Started

### Prerequisites

- Python 3.11+
- AWS credentials configured
- Infrastructure deployed (DynamoDB, Timestream, OpenSearch)

### Installation

```bash
# Install dependencies
pip install -e .

# For development
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file:

```env
OBSERVABILITY_ENVIRONMENT=dev
OBSERVABILITY_DEBUG=true
OBSERVABILITY_LOG_LEVEL=DEBUG
OBSERVABILITY_AWS_REGION=us-east-1

# DynamoDB Tables
OBSERVABILITY_TRACES_TABLE=genai-observability-traces
OBSERVABILITY_AGENTS_TABLE=genai-observability-agents
OBSERVABILITY_ALERTS_TABLE=genai-observability-alerts

# Timestream
OBSERVABILITY_TIMESTREAM_DATABASE=genai-observability
OBSERVABILITY_TIMESTREAM_TABLE=metrics

# OpenSearch
OBSERVABILITY_OPENSEARCH_ENDPOINT=your-opensearch-endpoint

# Authentication
OBSERVABILITY_JWT_SECRET_KEY=your-secret-key

# CORS
OBSERVABILITY_CORS_ORIGINS=["http://localhost:5173"]
```

### Running Locally

```bash
# Development server with auto-reload
uvicorn observability_api.main:app --reload --port 8000

# Or using the main module
python -m observability_api.main
```

### Docker

```bash
# Build image
docker build -t observability-api .

# Run container
docker run -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  observability-api

# Docker Compose (includes local AWS services)
docker-compose up
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/` | API info |

### Traces

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/traces` | List traces |
| GET | `/api/v1/traces/{trace_id}` | Get trace |
| POST | `/api/v1/traces` | Create trace |
| POST | `/api/v1/traces/{trace_id}/complete` | Complete trace |
| GET | `/api/v1/traces/{trace_id}/spans` | Get trace spans |

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/agents` | List agents |
| GET | `/api/v1/agents/{agent_id}` | Get agent |
| POST | `/api/v1/agents` | Register agent |
| PATCH | `/api/v1/agents/{agent_id}` | Update agent |
| DELETE | `/api/v1/agents/{agent_id}` | Delete agent |
| GET | `/api/v1/agents/{agent_id}/metrics` | Get agent metrics |
| POST | `/api/v1/agents/{agent_id}/heartbeat` | Agent heartbeat |

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/alerts` | List alerts |
| GET | `/api/v1/alerts/counts` | Get alert counts |
| GET | `/api/v1/alerts/{alert_id}` | Get alert |
| POST | `/api/v1/alerts` | Create alert |
| POST | `/api/v1/alerts/{alert_id}/acknowledge` | Acknowledge alert |
| POST | `/api/v1/alerts/{alert_id}/resolve` | Resolve alert |
| GET | `/api/v1/alerts/{alert_id}/investigation` | Get investigation |

### Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/metrics/dashboard` | Dashboard metrics |
| GET | `/api/v1/metrics/latency` | Latency time series |
| GET | `/api/v1/metrics/requests` | Request time series |
| GET | `/api/v1/metrics/errors` | Error time series |
| GET | `/api/v1/metrics/tokens` | Token usage |
| GET | `/api/v1/metrics/cost` | Cost breakdown |

### Natural Language Query

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/nlq` | Execute natural language query |
| GET | `/api/v1/nlq/suggestions` | Get query suggestions |
| GET | `/api/v1/nlq/history` | Get query history |
| POST | `/api/v1/nlq/saved` | Save a query |
| GET | `/api/v1/nlq/saved` | List saved queries |
| DELETE | `/api/v1/nlq/saved/{query_id}` | Delete saved query |
| GET | `/api/v1/nlq/examples` | Get query examples |

### Remediation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/remediation` | List remediations |
| GET | `/api/v1/remediation/{remediation_id}` | Get remediation details |
| POST | `/api/v1/remediation` | Create remediation plan |
| POST | `/api/v1/remediation/{remediation_id}/approve` | Approve remediation |
| POST | `/api/v1/remediation/{remediation_id}/reject` | Reject remediation |
| POST | `/api/v1/remediation/{remediation_id}/execute` | Execute remediation |
| POST | `/api/v1/remediation/{remediation_id}/rollback` | Rollback remediation |
| GET | `/api/v1/remediation/{remediation_id}/status` | Get execution status |

### Integrations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/integrations` | List integrations |
| GET | `/api/v1/integrations/types` | Get available types |
| GET | `/api/v1/integrations/{integration_id}` | Get integration |
| POST | `/api/v1/integrations` | Create integration |
| PUT | `/api/v1/integrations/{integration_id}` | Update integration |
| DELETE | `/api/v1/integrations/{integration_id}` | Delete integration |
| POST | `/api/v1/integrations/{integration_id}/test` | Test connection |
| POST | `/api/v1/integrations/{integration_id}/sync` | Sync data |

### SSO Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/auth/providers` | List auth providers |
| GET | `/api/v1/auth/login/{provider}/url` | Get login URL |
| POST | `/api/v1/auth/callback/{provider}` | Handle OAuth callback |
| GET | `/api/v1/auth/me` | Get current user |
| POST | `/api/v1/auth/logout` | Logout (OIDC revocation) |
| GET | `/api/v1/auth/saml/metadata` | Get SAML SP metadata |
| POST | `/api/v1/auth/logout/saml` | Initiate SAML logout |
| POST | `/api/v1/auth/logout/saml/callback` | Handle SAML SLO response |

## Authentication

### API Key

Include the API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: obs_your_api_key" http://localhost:8000/api/v1/traces
```

### JWT Token

Include the JWT token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer your_jwt_token" http://localhost:8000/api/v1/traces
```

### SSO Authentication

The API supports multiple SSO providers:

**OIDC Providers:**
- Google
- Okta
- Azure AD
- Auth0

**SAML 2.0:**
- Enterprise SAML with Single Logout (SLO) support

#### SSO Configuration

Add SSO settings to your `.env` file:

```env
# Google OIDC
OBSERVABILITY_GOOGLE_CLIENT_ID=your-client-id
OBSERVABILITY_GOOGLE_CLIENT_SECRET=your-client-secret

# Okta OIDC
OBSERVABILITY_OKTA_CLIENT_ID=your-client-id
OBSERVABILITY_OKTA_CLIENT_SECRET=your-client-secret
OBSERVABILITY_OKTA_ISSUER=https://your-org.okta.com

# Azure AD OIDC
OBSERVABILITY_AZURE_AD_CLIENT_ID=your-client-id
OBSERVABILITY_AZURE_AD_CLIENT_SECRET=your-client-secret
OBSERVABILITY_AZURE_AD_TENANT_ID=your-tenant-id

# Auth0 OIDC
OBSERVABILITY_AUTH0_CLIENT_ID=your-client-id
OBSERVABILITY_AUTH0_CLIENT_SECRET=your-client-secret
OBSERVABILITY_AUTH0_DOMAIN=your-domain.auth0.com

# SAML
OBSERVABILITY_SAML_IDP_METADATA_URL=https://idp.example.com/metadata
OBSERVABILITY_SAML_SP_ENTITY_ID=genai-observability
OBSERVABILITY_SAML_ACS_URL=https://api.example.com/api/v1/auth/saml/acs
```

## Project Structure

```
api/
├── src/
│   └── observability_api/
│       ├── __init__.py
│       ├── main.py              # Application entry point
│       ├── config.py            # Configuration
│       ├── auth.py              # Authentication
│       ├── models/              # Pydantic models
│       │   ├── agents.py
│       │   ├── alerts.py
│       │   ├── auth.py
│       │   ├── common.py
│       │   ├── metrics.py
│       │   └── traces.py
│       ├── db/                  # Database clients
│       │   ├── dynamodb.py
│       │   ├── opensearch.py
│       │   └── timestream.py
│       ├── services/            # Business logic
│       │   ├── agents.py
│       │   ├── alerts.py
│       │   ├── metrics.py
│       │   └── traces.py
│       └── routes/              # API routes
│           ├── agents.py
│           ├── alerts.py
│           ├── health.py
│           ├── metrics.py
│           └── traces.py
├── tests/                       # Tests
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Development

### Running Tests

```bash
pytest
pytest --cov=observability_api
```

### Linting

```bash
ruff check .
mypy src/
```

### Formatting

```bash
ruff format .
```

## Deployment

### AWS Lambda (with Mangum)

```python
# For Lambda deployment, add to main.py:
from mangum import Mangum
handler = Mangum(app)
```

### ECS/Fargate

Use the provided Dockerfile with ECS task definitions.

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: observability-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: observability-api
  template:
    metadata:
      labels:
        app: observability-api
    spec:
      containers:
      - name: api
        image: your-registry/observability-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: OBSERVABILITY_ENVIRONMENT
          value: "prod"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```
