# GenAI Observability Platform - Deployment Guide

## Prerequisites

### AWS Account Setup

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Python 3.11+** installed
4. **Node.js 18+** installed (for frontend)
5. **Docker** installed (for local development)

### Required IAM Permissions

The deploying user/role needs permissions for:
- CloudFormation (full access)
- IAM (create roles and policies)
- Lambda, API Gateway, Kinesis, DynamoDB
- S3, RDS, OpenSearch, Timestream
- Cognito, SNS, SES
- Step Functions, Glue
- CloudWatch, Secrets Manager

### External Services (Optional)

- **Slack**: Webhook URL for notifications
- **PagerDuty**: Integration key for incidents
- **Microsoft Teams**: Webhook URL for notifications
- **Amazon SES**: Verified domain/email for notifications

## Deployment Steps

### Step 1: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/your-org/genai-observability-platform.git
cd genai-observability-platform

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### Step 2: Configure Environment Variables

Edit `.env` with your settings:

```bash
# Required
AWS_REGION=us-east-1
ENVIRONMENT=dev  # dev, staging, prod
PROJECT_NAME=genai-observability

# Database
DB_MASTER_USERNAME=obsadmin
DB_MASTER_PASSWORD=<strong-password-here>

# Optional: Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
PAGERDUTY_INTEGRATION_KEY=...
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
ALERT_EMAIL=alerts@yourcompany.com
SENDER_EMAIL=observability@yourcompany.com

# Optional: Cognito
COGNITO_CALLBACK_URLS=https://dashboard.yourcompany.com/auth/callback
COGNITO_DOMAIN_PREFIX=yourcompany-observability
```

### Step 3: Create S3 Bucket for Templates

```bash
# Create bucket for CloudFormation templates
aws s3 mb s3://genai-observability-templates-${AWS_ACCOUNT_ID}

# Upload templates
aws s3 sync infrastructure/ s3://genai-observability-templates-${AWS_ACCOUNT_ID}/infrastructure/
```

### Step 4: Package Lambda Functions

```bash
# Run the packaging script
cd lambda
./package.sh

# Upload Lambda packages to S3
aws s3 sync dist/ s3://genai-observability-templates-${AWS_ACCOUNT_ID}/lambda/
```

### Step 5: Upload Glue Scripts

```bash
# Upload Glue ETL scripts
aws s3 sync glue/ s3://genai-observability-data-${ENVIRONMENT}/glue-scripts/
```

### Step 6: Create Secrets

```bash
# Create Slack webhook secret
aws secretsmanager create-secret \
    --name genai-observability/slack-webhook \
    --secret-string '{"webhook_url":"'${SLACK_WEBHOOK_URL}'"}'

# Create PagerDuty secret
aws secretsmanager create-secret \
    --name genai-observability/pagerduty-key \
    --secret-string '{"integration_key":"'${PAGERDUTY_INTEGRATION_KEY}'"}'

# Create database credentials secret (auto-created by RDS, but can pre-create)
aws secretsmanager create-secret \
    --name genai-observability/rds-credentials \
    --secret-string '{"username":"'${DB_MASTER_USERNAME}'","password":"'${DB_MASTER_PASSWORD}'"}'
```

### Step 7: Deploy Infrastructure

```bash
cd infrastructure

# Deploy using the deployment script
./deploy.sh deploy ${ENVIRONMENT}

# Or manually with CloudFormation
aws cloudformation deploy \
    --template-file main.yaml \
    --stack-name genai-observability-${ENVIRONMENT} \
    --parameter-overrides \
        Environment=${ENVIRONMENT} \
        ProjectName=genai-observability \
        DBMasterUsername=${DB_MASTER_USERNAME} \
        DBMasterPassword=${DB_MASTER_PASSWORD} \
        AlertEmail=${ALERT_EMAIL} \
        TemplatesBucketName=genai-observability-templates-${AWS_ACCOUNT_ID} \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --tags Environment=${ENVIRONMENT} Project=genai-observability
```

### Step 8: Run Database Migrations

```bash
# Get RDS endpoint from CloudFormation outputs
RDS_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name genai-observability-${ENVIRONMENT} \
    --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' \
    --output text)

# Run migrations
cd database
psql -h ${RDS_ENDPOINT} -U ${DB_MASTER_USERNAME} -d observability -f migrations/001_initial_schema.sql
psql -h ${RDS_ENDPOINT} -U ${DB_MASTER_USERNAME} -d observability -f migrations/002_add_llm_investigation.sql
```

### Step 9: Deploy Portal API

```bash
cd api

# Build Docker image
docker build -t genai-observability-api:${ENVIRONMENT} .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
docker tag genai-observability-api:${ENVIRONMENT} ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/genai-observability-api:${ENVIRONMENT}
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/genai-observability-api:${ENVIRONMENT}

# Deploy to ECS/Fargate (or Lambda)
# ... (depends on your deployment target)
```

### Step 10: Deploy Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Deploy to S3 + CloudFront (or your preferred hosting)
aws s3 sync dist/ s3://genai-observability-frontend-${ENVIRONMENT}/

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
    --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} \
    --paths "/*"
```

### Step 11: Verify Deployment

```bash
# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name genai-observability-${ENVIRONMENT} \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

# Test health endpoint
curl ${API_ENDPOINT}/health

# Expected response:
# {"status":"healthy","version":"1.0.0","environment":"dev"}
```

## Post-Deployment Configuration

### Create Initial Admin User

```bash
# Create admin user in Cognito
aws cognito-idp admin-create-user \
    --user-pool-id ${USER_POOL_ID} \
    --username admin@yourcompany.com \
    --user-attributes Name=email,Value=admin@yourcompany.com Name=name,Value="Platform Admin" \
    --temporary-password "TempPassword123!"

# Add to Admins group
aws cognito-idp admin-add-user-to-group \
    --user-pool-id ${USER_POOL_ID} \
    --username admin@yourcompany.com \
    --group-name Admins
```

### Create First API Key

```bash
# Use the CLI or API to create an API key
genai-obs configure
genai-obs api-keys create --name "First Agent" --agent test-agent

# Or via API
curl -X POST ${API_ENDPOINT}/api/v1/api-keys \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"name": "First Agent", "agent_id": "test-agent"}'
```

### Configure Alert Rules

```bash
# Create default alert rules
genai-obs alerts rules create \
    --name "High Error Rate" \
    --type error_rate \
    --threshold 0.05 \
    --severity high

genai-obs alerts rules create \
    --name "High Latency" \
    --type latency \
    --threshold 5000 \
    --severity medium
```

## Environment-Specific Configuration

### Development

```yaml
# Lower resource allocation
KinesisShardCount: 1
RDSInstanceClass: db.t3.medium
OpenSearchInstanceType: t3.small.search

# Shorter retention
DynamoDBTTLHours: 12
S3RetentionDays: 30
```

### Staging

```yaml
# Medium resource allocation
KinesisShardCount: 2
RDSInstanceClass: db.r6g.large
OpenSearchInstanceType: r6g.large.search

# Standard retention
DynamoDBTTLHours: 24
S3RetentionDays: 90
```

### Production

```yaml
# Full resource allocation
KinesisShardCount: 5
RDSInstanceClass: db.r6g.xlarge
OpenSearchInstanceType: r6g.xlarge.search

# Extended retention
DynamoDBTTLHours: 48
S3RetentionDays: 365

# Enable:
# - Multi-AZ for RDS
# - Cross-region replication for S3
# - Enhanced monitoring
```

## Upgrade Procedures

### Rolling Update

```bash
# Update CloudFormation stack
aws cloudformation update-stack \
    --stack-name genai-observability-${ENVIRONMENT} \
    --template-url https://genai-observability-templates.s3.amazonaws.com/infrastructure/main.yaml \
    --parameters ParameterKey=Environment,UsePreviousValue=true \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM

# Monitor update progress
aws cloudformation describe-stack-events \
    --stack-name genai-observability-${ENVIRONMENT} \
    --query 'StackEvents[?ResourceStatus==`UPDATE_IN_PROGRESS` || ResourceStatus==`UPDATE_COMPLETE`]'
```

### Database Migrations

```bash
# Always backup before migration
aws rds create-db-cluster-snapshot \
    --db-cluster-identifier genai-observability-${ENVIRONMENT} \
    --db-cluster-snapshot-identifier pre-migration-$(date +%Y%m%d)

# Run new migrations
psql -h ${RDS_ENDPOINT} -U ${DB_MASTER_USERNAME} -d observability -f migrations/003_new_feature.sql
```

## Rollback Procedures

### CloudFormation Rollback

```bash
# Automatic rollback on failure is enabled by default
# Manual rollback to previous version:
aws cloudformation rollback-stack \
    --stack-name genai-observability-${ENVIRONMENT}
```

### Database Rollback

```bash
# Restore from snapshot
aws rds restore-db-cluster-from-snapshot \
    --db-cluster-identifier genai-observability-${ENVIRONMENT}-restored \
    --snapshot-identifier pre-migration-20240115 \
    --engine aurora-postgresql
```

## Troubleshooting

### Common Issues

#### Lambda Timeout Errors

```bash
# Check CloudWatch logs
aws logs filter-log-events \
    --log-group-name /aws/lambda/genai-observability-${ENVIRONMENT}-ingestion \
    --filter-pattern "Task timed out"

# Solution: Increase Lambda timeout or memory
```

#### Kinesis Iterator Age High

```bash
# Check iterator age metric
aws cloudwatch get-metric-statistics \
    --namespace AWS/Kinesis \
    --metric-name GetRecords.IteratorAgeMilliseconds \
    --dimensions Name=StreamName,Value=genai-observability-${ENVIRONMENT}-events \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Maximum

# Solution: Add more shards or increase Lambda concurrency
```

#### OpenSearch Cluster Yellow/Red

```bash
# Check cluster health
curl -X GET "https://${OPENSEARCH_ENDPOINT}/_cluster/health?pretty"

# Solution: Check disk space, add data nodes if needed
```

### Log Locations

| Component | Log Location |
|-----------|--------------|
| Ingestion Lambda | `/aws/lambda/genai-observability-${ENV}-ingestion` |
| Stream Processor | `/aws/lambda/genai-observability-${ENV}-stream-processor` |
| Anomaly Detector | `/aws/lambda/genai-observability-${ENV}-anomaly-detector` |
| Step Functions | `/aws/stepfunctions/genai-observability-${ENV}-daily-pipeline` |
| API Gateway | API Gateway access logs (if enabled) |

## Security Checklist

- [ ] VPC endpoints configured for AWS services
- [ ] Security groups restrict access to minimum required
- [ ] RDS not publicly accessible
- [ ] Secrets stored in Secrets Manager (not environment variables)
- [ ] API keys rotated every 90 days
- [ ] CloudTrail enabled for audit logging
- [ ] WAF rules configured for API Gateway
- [ ] Encryption at rest enabled for all data stores
- [ ] Encryption in transit (TLS 1.2+) enforced
