# GenAI Observability Platform - Infrastructure

AWS CloudFormation templates for deploying the GenAI Observability Platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GenAI Observability Platform                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐ │
│  │   SDK/Agent  │────▶│  API Gateway │────▶│     Kinesis Stream       │ │
│  └──────────────┘     └──────────────┘     └───────────┬──────────────┘ │
│                                                         │                 │
│                                                         ▼                 │
│  ┌──────────────────────────────────────────────────────────────────────┐│
│  │                      Stream Processor Lambda                          ││
│  │  - Routes events to appropriate storage                               ││
│  │  - Triggers anomaly detection                                         ││
│  └───────┬──────────────────┬──────────────────┬────────────────────────┘│
│          │                  │                  │                          │
│          ▼                  ▼                  ▼                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                  │
│  │  OpenSearch  │   │  Timestream  │   │  DynamoDB    │                  │
│  │  (Traces)    │   │  (Metrics)   │   │  (Errors)    │                  │
│  └──────────────┘   └──────────────┘   └──────┬───────┘                  │
│                                                │                          │
│                                                ▼                          │
│  ┌──────────────────────────────────────────────────────────────────────┐│
│  │                     Anomaly Detector Lambda                           ││
│  │  - Checks error rates                                                 ││
│  │  - Monitors latency thresholds                                        ││
│  └───────────────────────────────┬──────────────────────────────────────┘│
│                                  │                                        │
│                                  ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐│
│  │                    LLM Investigator Lambda                            ││
│  │  - Gathers context from all data sources                              ││
│  │  - Calls Claude for root cause analysis                               ││
│  │  - Stores investigation results                                       ││
│  └───────────────────────────────┬──────────────────────────────────────┘│
│                                  │                                        │
│                                  ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐│
│  │                         SNS Topics                                    ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────────────┐       ││
│  │  │Critical │  │Warning  │  │  Info   │  │Investigation      │       ││
│  │  │ Alerts  │  │ Alerts  │  │ Alerts  │  │    Results        │       ││
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └─────────┬─────────┘       ││
│  └───────┼────────────┼────────────┼─────────────────┼──────────────────┘│
│          │            │            │                 │                    │
│          ▼            ▼            ▼                 ▼                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                      │
│  │    Slack     │ │  PagerDuty   │ │    Email     │                      │
│  │  Formatter   │ │  Formatter   │ │              │                      │
│  └──────────────┘ └──────────────┘ └──────────────┘                      │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Stack Structure

| Stack | Description | Resources |
|-------|-------------|-----------|
| `core.yaml` | VPC, IAM roles, security groups, secrets | VPC, Subnets, NAT Gateway, IAM Roles, Security Groups, Secrets Manager |
| `storage.yaml` | Data storage services | S3, DynamoDB, Timestream, OpenSearch Serverless, RDS Aurora |
| `ingestion.yaml` | API and event ingestion | API Gateway, Kinesis, Ingestion Lambda, Authorizer Lambda |
| `processing.yaml` | Event processing and analysis | Stream Processor, Anomaly Detector, LLM Investigator |
| `notifications.yaml` | Alert routing and formatting | SNS Topics, Slack/PagerDuty Formatters, Alert Deduplicator |
| `main.yaml` | Orchestrates nested stacks | References all above stacks |

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **AWS Account** with permissions to create:
   - VPC, Subnets, NAT Gateway
   - Lambda, API Gateway, Kinesis
   - DynamoDB, S3, RDS Aurora, Timestream
   - OpenSearch Serverless
   - SNS, Secrets Manager
   - IAM Roles and Policies

3. **Anthropic API Key** (for LLM investigation)
4. **Slack Webhook URL** (optional, for Slack notifications)
5. **PagerDuty Integration Key** (optional, for PagerDuty alerts)

## Deployment

### Quick Deploy

```bash
# Set environment variables
export AWS_REGION=us-east-1
export DB_PASSWORD="your-secure-password"  # Min 8 characters
export ALERT_EMAIL="alerts@yourcompany.com"  # Optional

# Deploy to dev
cd infrastructure
chmod +x deploy.sh
./deploy.sh dev deploy
```

### Manual Deployment (Step by Step)

```bash
# 1. Deploy Core infrastructure
aws cloudformation deploy \
  --template-file core.yaml \
  --stack-name genai-observability-dev-core \
  --parameter-overrides Environment=dev ProjectName=genai-observability \
  --capabilities CAPABILITY_NAMED_IAM

# 2. Deploy Storage infrastructure
aws cloudformation deploy \
  --template-file storage.yaml \
  --stack-name genai-observability-dev-storage \
  --parameter-overrides \
    Environment=dev \
    ProjectName=genai-observability \
    DBMasterUsername=obsadmin \
    DBMasterPassword=YourPassword123 \
  --capabilities CAPABILITY_NAMED_IAM

# 3. Deploy Notifications
aws cloudformation deploy \
  --template-file notifications.yaml \
  --stack-name genai-observability-dev-notifications \
  --parameter-overrides Environment=dev ProjectName=genai-observability \
  --capabilities CAPABILITY_NAMED_IAM

# 4. Deploy Ingestion
aws cloudformation deploy \
  --template-file ingestion.yaml \
  --stack-name genai-observability-dev-ingestion \
  --parameter-overrides Environment=dev ProjectName=genai-observability \
  --capabilities CAPABILITY_NAMED_IAM

# 5. Deploy Processing
aws cloudformation deploy \
  --template-file processing.yaml \
  --stack-name genai-observability-dev-processing \
  --parameter-overrides Environment=dev ProjectName=genai-observability \
  --capabilities CAPABILITY_NAMED_IAM
```

## Post-Deployment Configuration

### 1. Update Secrets

After deployment, update the placeholder secrets with real values:

```bash
# Anthropic API Key
aws secretsmanager put-secret-value \
  --secret-id genai-observability/dev/anthropic-api-key \
  --secret-string '{"api_key": "sk-ant-your-actual-key"}'

# Slack Webhook
aws secretsmanager put-secret-value \
  --secret-id genai-observability/dev/slack-webhook \
  --secret-string '{"webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"}'

# PagerDuty Key
aws secretsmanager put-secret-value \
  --secret-id genai-observability/dev/pagerduty-key \
  --secret-string '{"integration_key": "your-pagerduty-integration-key"}'
```

### 2. Initialize Database Schema

Connect to RDS and run the schema initialization:

```sql
-- Agent registration table
CREATE TABLE agents (
    agent_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    agent_type VARCHAR(50),
    deployment_type VARCHAR(50),
    description TEXT,
    team_name VARCHAR(100),
    cost_center VARCHAR(50),
    alert_email VARCHAR(200),
    configuration JSONB,
    api_key_hash VARCHAR(64),
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Notification routing rules
CREATE TABLE notification_routes (
    route_id SERIAL PRIMARY KEY,
    team_name VARCHAR(100),
    severity_level VARCHAR(20),
    agent_pattern VARCHAR(200),
    notification_channels JSONB,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_agents_team ON agents(team_name);
CREATE INDEX idx_agents_api_key_hash ON agents(api_key_hash);
```

### 3. Register Your First Agent

```bash
# Get the API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name genai-observability-dev-ingestion \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text)

echo "API Endpoint: $API_ENDPOINT"
```

## Configuration

### Environment Variables for SDK

```bash
export GENAI_OBS_ENDPOINT="https://xxx.execute-api.us-east-1.amazonaws.com/dev"
export GENAI_OBS_API_KEY="your-api-key"
export GENAI_OBS_AGENT_ID="your-agent-id"
export GENAI_OBS_AGENT_TYPE="langchain"  # or crewai, custom
export GENAI_OBS_ENVIRONMENT="production"
```

### Scaling Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `KinesisShardCount` | 2 | Number of Kinesis shards (each handles ~1MB/s) |
| `DBInstanceClass` | db.serverless | RDS Aurora Serverless v2 |
| Timestream retention | 24h memory, 365d magnetic | Metrics retention |
| OpenSearch | Serverless | Auto-scales based on usage |

## Estimated Costs

| Service | Estimated Monthly Cost |
|---------|----------------------|
| VPC + NAT Gateway | ~$35 |
| API Gateway | ~$3.50 per million requests |
| Kinesis (2 shards) | ~$30 |
| Lambda | ~$50 (depends on invocations) |
| DynamoDB (on-demand) | ~$80 |
| Timestream | ~$50 |
| OpenSearch Serverless | ~$700 (minimum) |
| RDS Aurora Serverless | ~$100 |
| S3 | ~$5 |
| **Total** | **~$1,050-1,500/month** |

> Note: OpenSearch Serverless has a minimum cost. For lower-cost dev environments, consider using a managed OpenSearch domain instead.

## Monitoring

### CloudWatch Dashboards

The deployment creates CloudWatch alarms for:
- Ingestion Lambda errors
- Kinesis iterator age (processing lag)
- API Gateway 5xx errors

### Key Metrics to Watch

- `AWS/Lambda/Errors` - Lambda function errors
- `AWS/Kinesis/GetRecords.IteratorAgeMilliseconds` - Processing lag
- `AWS/ApiGateway/5XXError` - API errors
- Custom metrics in Timestream

## Troubleshooting

### Common Issues

**1. OpenSearch access denied**
```bash
# Check the data access policy includes your Lambda role
aws opensearchserverless get-access-policy --name genai-observability-dev-access --type data
```

**2. Lambda timeout**
```bash
# Increase Lambda timeout in the template or via console
aws lambda update-function-configuration \
  --function-name genai-observability-dev-stream-processor \
  --timeout 300
```

**3. Kinesis throttling**
```bash
# Increase shard count
aws kinesis update-shard-count \
  --stream-name genai-observability-dev-events \
  --target-shard-count 4 \
  --scaling-type UNIFORM_SCALING
```

## Cleanup

```bash
# Delete all stacks
./deploy.sh dev delete

# Or manually delete in reverse order
aws cloudformation delete-stack --stack-name genai-observability-dev-processing
aws cloudformation delete-stack --stack-name genai-observability-dev-ingestion
aws cloudformation delete-stack --stack-name genai-observability-dev-notifications
aws cloudformation delete-stack --stack-name genai-observability-dev-storage
aws cloudformation delete-stack --stack-name genai-observability-dev-core
```

> **Warning**: Deleting the storage stack will delete all data including S3 buckets, DynamoDB tables, and the RDS database.

## Security Considerations

1. **API Keys**: Stored as SHA-256 hashes, never in plaintext
2. **Secrets**: All sensitive data in AWS Secrets Manager
3. **VPC**: Lambda functions run in private subnets
4. **Encryption**: All data encrypted at rest (S3, DynamoDB, RDS, OpenSearch)
5. **IAM**: Least-privilege policies for all roles
