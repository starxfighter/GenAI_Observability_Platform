# GenAI Observability Platform - Architecture Documentation

## Overview

The GenAI Observability Platform is a comprehensive solution for monitoring, tracing, and debugging GenAI agents in production environments. It provides real-time observability, anomaly detection, LLM-powered investigation, and multi-channel alerting.

## Design Principles

1. **Scalability**: Designed for 10M+ events/day with horizontal scaling
2. **Low Latency**: Sub-second ingestion with real-time processing
3. **Cost Efficiency**: Dual-path architecture (hot/cold) optimizes storage costs
4. **Extensibility**: Modular design allows easy integration of new features
5. **Security**: Multi-tenant isolation with RBAC and API key management

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LAYER 6: VISUALIZATION                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   React     │  │  Grafana    │  │ QuickSight  │  │    CLI Tools        │ │
│  │  Dashboard  │  │  Dashboards │  │   Reports   │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                             LAYER 5: API                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │    Portal API       │  │   WebSocket API     │  │   GraphQL API       │  │
│  │    (FastAPI)        │  │   (Real-time)       │  │   (AppSync)         │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LAYER 4: PROCESSING                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   Stream     │  │   Anomaly    │  │     LLM      │  │   Step Functions │ │
│  │  Processor   │  │  Detector    │  │ Investigator │  │   + Glue ETL     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LAYER 3: STORAGE                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐│
│  │  DynamoDB  │  │ Timestream │  │ OpenSearch │  │    RDS     │  │   S3   ││
│  │  (Hot)     │  │ (Metrics)  │  │ (Search)   │  │ (Analytics)│  │ (Cold) ││
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LAYER 2: INGESTION                                  │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │    API Gateway      │  │   Kinesis Stream    │  │   Kinesis Firehose  │  │
│  │    + Lambda         │  │   (Fan-out)         │  │   (S3 Delivery)     │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LAYER 1: COLLECTION                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │   Python SDK        │  │   LangChain         │  │     CrewAI          │  │
│  │                     │  │   Integration       │  │   Integration       │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Real-time (Hot Path)

```
Agent → SDK → API Gateway → Ingestion Lambda → Kinesis Stream
                                                      │
                    ┌─────────────────────────────────┼─────────────────────────┐
                    ▼                                 ▼                         ▼
              Stream Processor              Anomaly Detector            Firehose → S3
                    │                             │
                    ▼                             ▼
            ┌───────────────┐            ┌───────────────┐
            │   DynamoDB    │            │ LLM Investigator
            │   Timestream  │            │      │
            │   OpenSearch  │            │      ▼
            └───────────────┘            │ Alert Deduplicator
                                         │      │
                                         │      ▼
                                         │ SNS → Formatters → Slack/Teams/PagerDuty/Email
                                         └───────────────────────────────────────────────
```

### Batch (Cold Path)

```
S3 (Raw Events) → EventBridge (2 AM UTC) → Step Functions
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    ▼                            ▼                            ▼
            Token Aggregation          Tool Analytics              Cost Analysis
                    │                            │                            │
                    └────────────────────────────┼────────────────────────────┘
                                                 ▼
                    ┌────────────────────────────┼────────────────────────────┐
                    ▼                            ▼                            ▼
            Error Patterns           Trace Reconstruction              RDS Aurora
                    │                            │                            │
                    └────────────────────────────┴────────────────────────────┘
```

## Component Details

### 1. Collection Layer

#### Python SDK
- **Purpose**: Instrument GenAI agents with minimal code changes
- **Features**:
  - Context managers for tracing
  - Automatic LLM call instrumentation
  - Tool execution tracking
  - Async support
  - Batched event export

```python
from genai_observability import init, get_tracer

init(endpoint="https://api.example.com", api_key="...", agent_id="my-agent")
tracer = get_tracer()

with tracer.trace("process_request") as ctx:
    with tracer.llm_span("call_claude", parent=ctx, model="claude-sonnet-4-20250514"):
        response = anthropic.messages.create(...)
```

### 2. Ingestion Layer

#### API Gateway + Lambda Authorizer
- **Endpoint**: `POST /v1/events`
- **Authentication**: API key in `X-API-Key` header
- **Rate Limiting**: 1000 requests/minute per API key
- **Payload**: JSON array of events (max 100 per batch)

#### Kinesis Data Stream
- **Shards**: 2-10 based on throughput
- **Retention**: 24 hours
- **Fan-out**: Enhanced fan-out for parallel consumers

### 3. Storage Layer

| Store | Purpose | Retention | Access Pattern |
|-------|---------|-----------|----------------|
| DynamoDB | Hot traces, alerts | 24 hours (TTL) | Point lookups, recent queries |
| Timestream | Time-series metrics | 90 days | Aggregations, trends |
| OpenSearch | Full-text search | 30 days | Complex queries, trace search |
| RDS Aurora | Analytics, config | Unlimited | Joins, reports, RBAC |
| S3 | Cold storage | 1 year | Batch processing, compliance |

### 4. Processing Layer

#### Stream Processor
- Processes Kinesis records in real-time
- Writes to DynamoDB, Timestream, OpenSearch
- Extracts metrics from events

#### Anomaly Detector
- Statistical anomaly detection
- Configurable thresholds per agent
- Triggers LLM investigation for anomalies

#### LLM Investigator
- Uses Claude Sonnet 4 for root cause analysis
- Queries historical error patterns from RDS
- Generates actionable recommendations
- Cost: ~$0.03 per investigation

#### Step Functions + Glue ETL
- Daily batch processing at 2 AM UTC
- 5 parallel Glue jobs:
  1. **Token Aggregation**: Hourly/daily token usage
  2. **Tool Analytics**: Tool performance metrics
  3. **Cost Analysis**: Cost breakdown by dimension
  4. **Error Patterns**: Pattern extraction for LLM
  5. **Trace Reconstruction**: Full trace archival

### 5. API Layer

#### Portal API (FastAPI)
- RESTful API for dashboard
- JWT + API key authentication
- Endpoints: `/traces`, `/agents`, `/alerts`, `/metrics`

#### WebSocket API
- Real-time updates to dashboard
- Subscription-based (alerts, traces, metrics)
- Connection management with DynamoDB

### 6. Visualization Layer

#### React Dashboard
- Agent overview and health
- Trace timeline visualization
- Alert management
- Cost analytics

#### CLI Tools
- `genai-obs agents list`
- `genai-obs traces get <trace-id>`
- `genai-obs alerts ack <alert-id>`
- `genai-obs metrics summary`

## Security Architecture

### Authentication

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Users     │────▶│    Cognito      │────▶│   JWT Token     │
└─────────────────┘     └─────────────────┘     └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   SDK/Agents    │────▶│  API Gateway    │────▶│   API Key       │
└─────────────────┘     │  Authorizer     │     │  (SHA-256)      │
                        └─────────────────┘     └─────────────────┘
```

### Authorization (RBAC)

| Role | Permissions |
|------|-------------|
| Admin | Full access, user management |
| Team Admin | Manage team agents, alerts, API keys |
| Developer | Create agents, view traces, manage alerts |
| Viewer | Read-only access to assigned agents |

### Data Isolation

- **Team-based isolation**: Agents belong to teams
- **API key scoping**: Keys are scoped to specific agents
- **Query filtering**: All queries filtered by team/agent access

## Alerting Architecture

```
Anomaly Detected
       │
       ▼
┌──────────────────┐
│ Alert Deduplicator│ ← Fingerprint-based deduplication
└──────────────────┘   24-hour window
       │
       ▼
┌──────────────────┐
│   SNS Topics     │
│  Critical/Warning│
│  /Info           │
└──────────────────┘
       │
       ├──────────────────┬──────────────────┬──────────────────┐
       ▼                  ▼                  ▼                  ▼
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│   Slack    │     │  PagerDuty │     │   Teams    │     │   Email    │
│ Block Kit  │     │ Events v2  │     │  Adaptive  │     │   HTML     │
└────────────┘     └────────────┘     │   Cards    │     └────────────┘
                                      └────────────┘
```

## Scalability Considerations

### Horizontal Scaling

| Component | Scaling Mechanism |
|-----------|-------------------|
| API Gateway | Automatic |
| Lambda | Concurrent executions (1000 default) |
| Kinesis | Add shards |
| DynamoDB | On-demand capacity |
| OpenSearch | Add data nodes |

### Performance Targets

| Metric | Target |
|--------|--------|
| Event ingestion latency | < 100ms |
| Trace query (by ID) | < 50ms |
| Dashboard load | < 2s |
| Alert delivery | < 30s |

## Cost Estimation

For 10M events/day:

| Component | Monthly Cost |
|-----------|-------------|
| API Gateway | $35 |
| Lambda | $50 |
| Kinesis | $150 |
| DynamoDB | $200 |
| Timestream | $300 |
| OpenSearch | $500 |
| RDS Aurora | $400 |
| S3 | $50 |
| Glue ETL | $100 |
| LLM Investigation | $500 |
| **Total** | **~$2,300** |

## Disaster Recovery

### Backup Strategy

- **DynamoDB**: Point-in-time recovery enabled
- **RDS**: Automated backups, 7-day retention
- **S3**: Versioning enabled, cross-region replication (optional)
- **OpenSearch**: Automated snapshots to S3

### Recovery Objectives

- **RPO** (Recovery Point Objective): 1 hour
- **RTO** (Recovery Time Objective): 4 hours

## Monitoring the Platform

### CloudWatch Metrics

- Lambda invocations, errors, duration
- Kinesis iterator age, records
- DynamoDB consumed capacity
- API Gateway 4xx/5xx errors

### Alarms

- Lambda error rate > 1%
- Kinesis iterator age > 60 seconds
- DynamoDB throttling > 0
- OpenSearch cluster health != green

## Future Enhancements

1. **Multi-region deployment**: Active-active for global teams
2. **Custom dashboards**: User-defined metric visualizations
3. **Trace comparison**: Side-by-side trace analysis
4. **Cost forecasting**: ML-based cost predictions
5. **Automated remediation**: Self-healing based on known patterns
