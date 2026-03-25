# GenAI Observability Platform - Lambda Functions

This directory contains the Lambda functions for the GenAI Observability Platform.

## Directory Structure

```
lambda/
├── shared/                      # Shared utilities (Lambda Layer)
│   ├── observability_common/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── clients.py          # AWS client management
│   │   ├── models.py           # Data models
│   │   ├── storage.py          # Storage operations
│   │   └── logging.py          # Structured logging
│   └── requirements.txt
├── authorizer/                  # API Gateway authorizer
│   ├── handler.py
│   └── requirements.txt
├── ingestion/                   # Event ingestion
│   ├── handler.py
│   └── requirements.txt
├── stream_processor/            # Kinesis stream processor
│   ├── handler.py
│   └── requirements.txt
├── anomaly_detector/            # Anomaly detection
│   ├── handler.py
│   └── requirements.txt
├── llm_investigator/            # LLM-powered investigation
│   ├── handler.py
│   └── requirements.txt
├── slack_formatter/             # Slack notifications
│   ├── handler.py
│   └── requirements.txt
├── pagerduty_formatter/         # PagerDuty integration
│   ├── handler.py
│   └── requirements.txt
├── alert_deduplicator/          # Alert deduplication
│   ├── handler.py
│   └── requirements.txt
├── build.sh                     # Build script
├── deploy.sh                    # Deployment script
├── Makefile                     # Make targets
└── README.md                    # This file
```

## Functions Overview

### Ingestion Functions

| Function | Description | Trigger |
|----------|-------------|---------|
| `authorizer` | Validates API keys from DynamoDB | API Gateway |
| `ingestion` | Receives events, writes to Kinesis/S3 | API Gateway |

### Processing Functions

| Function | Description | Trigger |
|----------|-------------|---------|
| `stream_processor` | Routes events to OpenSearch/Timestream/DynamoDB | Kinesis |
| `anomaly_detector` | Detects error rate and latency anomalies | EventBridge (scheduled) |
| `llm_investigator` | Uses Claude for root cause analysis | Lambda (async) |

### Notification Functions

| Function | Description | Trigger |
|----------|-------------|---------|
| `slack_formatter` | Formats alerts for Slack Block Kit | SNS |
| `pagerduty_formatter` | Formats alerts for PagerDuty Events API | SNS |
| `alert_deduplicator` | Prevents duplicate alerts using fingerprinting | Direct/SNS |

## Building

### Prerequisites

- Python 3.11 or 3.12
- pip
- zip
- AWS CLI (for deployment)

### Build Commands

```bash
# Build all functions
make build

# Build specific function
make build-ingestion

# Build shared layer only
make build-layer

# Clean build artifacts
make clean
```

### Manual Build

```bash
# Build all
./build.sh all

# Build specific function
./build.sh ingestion

# Build layer only
./build.sh layer

# Clean
./build.sh clean
```

## Deploying

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. S3 bucket for Lambda artifacts
3. Infrastructure deployed (CloudFormation stacks)

### Environment Variables

```bash
export AWS_REGION=us-east-1
export ENVIRONMENT=dev
export S3_BUCKET=my-lambda-artifacts-bucket
export STACK_NAME=genai-observability
```

### Deploy Commands

```bash
# Deploy all functions
make deploy

# Deploy specific function
make deploy-ingestion

# Deploy layer only
make deploy-layer

# Check deployment status
make status
```

### Manual Deployment

```bash
# Deploy all
./deploy.sh all

# Deploy specific function
./deploy.sh ingestion

# Deploy layer
./deploy.sh layer

# Check status
./deploy.sh status
```

## Development

### Local Testing

Each function can be tested locally using AWS SAM or by importing the handler directly:

```python
from ingestion.handler import handler

event = {
    "body": '{"events": [{"event_type": "execution_start"}]}',
    "headers": {"x-api-key": "test-key"}
}
context = {}

result = handler(event, context)
print(result)
```

### Testing with SAM

```bash
# Install SAM CLI
pip install aws-sam-cli

# Create template.yaml for local testing
# Then invoke locally
sam local invoke IngestionFunction -e events/sample-event.json
```

### Linting and Formatting

```bash
# Run linting
make lint

# Format code
make format

# Run tests
make test
```

## Configuration

### Environment Variables

Each function uses environment variables for configuration. These are set via CloudFormation:

**Common Variables:**
- `ENVIRONMENT` - Environment name (dev, staging, prod)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARN, ERROR)

**Function-Specific Variables:**

| Function | Key Variables |
|----------|---------------|
| `authorizer` | `API_KEYS_TABLE` |
| `ingestion` | `KINESIS_STREAM`, `RAW_EVENTS_BUCKET` |
| `stream_processor` | `OPENSEARCH_ENDPOINT`, `TIMESTREAM_DATABASE`, `ERROR_STORE_TABLE` |
| `anomaly_detector` | `TIMESTREAM_DATABASE`, `ERROR_STORE_TABLE`, `INVESTIGATION_FUNCTION` |
| `llm_investigator` | `ANTHROPIC_SECRET_ARN`, `INVESTIGATION_RESULTS_TABLE`, `NOTIFICATION_TOPIC` |
| `slack_formatter` | `SLACK_SECRET_ARN` |
| `pagerduty_formatter` | `PAGERDUTY_SECRET_ARN` |
| `alert_deduplicator` | `ALERT_CACHE_TABLE`, `CRITICAL_TOPIC_ARN`, `WARNING_TOPIC_ARN` |

## Architecture

```
                                    ┌─────────────────┐
                                    │   API Gateway   │
                                    └────────┬────────┘
                                             │
                           ┌─────────────────┼─────────────────┐
                           │                 │                 │
                    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
                    │  Authorizer │   │  Ingestion  │   │   Health    │
                    └─────────────┘   └──────┬──────┘   └─────────────┘
                                             │
                                      ┌──────▼──────┐
                                      │   Kinesis   │
                                      └──────┬──────┘
                                             │
                                      ┌──────▼──────┐
                                      │   Stream    │
                                      │  Processor  │
                                      └──────┬──────┘
                           ┌─────────────────┼─────────────────┐
                           │                 │                 │
                    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
                    │ OpenSearch  │   │  Timestream │   │  DynamoDB   │
                    └─────────────┘   └─────────────┘   └─────────────┘
                                             │
                                      ┌──────▼──────┐
                                      │  Anomaly    │◄─── EventBridge
                                      │  Detector   │     (scheduled)
                                      └──────┬──────┘
                           ┌─────────────────┼─────────────────┐
                           │                 │                 │
                    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
                    │     LLM     │   │    SNS      │   │    SNS      │
                    │ Investigator│   │  Critical   │   │   Warning   │
                    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
                           │                 │                 │
                           │          ┌──────▼──────┐          │
                           │          │    Alert    │          │
                           │          │ Deduplicator│          │
                           │          └──────┬──────┘          │
                           │                 │                 │
                    ┌──────▼─────────────────▼─────────────────▼──────┐
                    │                   SNS Fan-out                   │
                    └──────────────────────┬──────────────────────────┘
                                           │
                           ┌───────────────┼───────────────┐
                           │               │               │
                    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
                    │    Slack    │ │  PagerDuty  │ │   Email     │
                    │  Formatter  │ │  Formatter  │ │    (SNS)    │
                    └─────────────┘ └─────────────┘ └─────────────┘
```

## Troubleshooting

### Common Issues

1. **Build fails with pip errors**
   - Ensure Python 3.11+ is installed
   - Try `pip install --upgrade pip`

2. **Deploy fails with credentials error**
   - Run `aws sts get-caller-identity` to verify credentials
   - Check IAM permissions for Lambda deployment

3. **Function not found during deploy**
   - Deploy infrastructure first using CloudFormation
   - Check STACK_NAME and ENVIRONMENT match the deployed stack

4. **Layer not attached to function**
   - Re-deploy the function after deploying the layer
   - Check CloudFormation outputs for layer ARN

### Viewing Logs

```bash
# View function logs
aws logs tail /aws/lambda/genai-observability-dev-ingestion --follow

# Filter for errors
aws logs filter-log-events \
    --log-group-name /aws/lambda/genai-observability-dev-ingestion \
    --filter-pattern "ERROR"
```
