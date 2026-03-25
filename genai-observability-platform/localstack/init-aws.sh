#!/bin/bash
# Initialize LocalStack with required AWS resources

set -e

echo "Initializing LocalStack AWS resources..."

# Wait for LocalStack to be ready
awslocal --version

# ============================================================
# S3 Buckets
# ============================================================
echo "Creating S3 buckets..."

awslocal s3 mb s3://genai-observability-traces-local
awslocal s3 mb s3://genai-observability-artifacts-local
awslocal s3 mb s3://genai-observability-frontend-local

# ============================================================
# DynamoDB Tables
# ============================================================
echo "Creating DynamoDB tables..."

# WebSocket Connections Table
awslocal dynamodb create-table \
    --table-name genai-obs-connections-local \
    --attribute-definitions \
        AttributeName=connection_id,AttributeType=S \
        AttributeName=agent_id,AttributeType=S \
        AttributeName=team_id,AttributeType=S \
    --key-schema \
        AttributeName=connection_id,KeyType=HASH \
    --global-secondary-indexes \
        "[{\"IndexName\": \"AgentIndex\", \"KeySchema\": [{\"AttributeName\": \"agent_id\", \"KeyType\": \"HASH\"}], \"Projection\": {\"ProjectionType\": \"ALL\"}, \"ProvisionedThroughput\": {\"ReadCapacityUnits\": 5, \"WriteCapacityUnits\": 5}}, {\"IndexName\": \"TeamIndex\", \"KeySchema\": [{\"AttributeName\": \"team_id\", \"KeyType\": \"HASH\"}], \"Projection\": {\"ProjectionType\": \"ALL\"}, \"ProvisionedThroughput\": {\"ReadCapacityUnits\": 5, \"WriteCapacityUnits\": 5}}]" \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

# Traces Table (for quick lookups)
awslocal dynamodb create-table \
    --table-name genai-obs-traces-local \
    --attribute-definitions \
        AttributeName=trace_id,AttributeType=S \
        AttributeName=agent_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=trace_id,KeyType=HASH \
    --global-secondary-indexes \
        "[{\"IndexName\": \"AgentTimestampIndex\", \"KeySchema\": [{\"AttributeName\": \"agent_id\", \"KeyType\": \"HASH\"}, {\"AttributeName\": \"timestamp\", \"KeyType\": \"RANGE\"}], \"Projection\": {\"ProjectionType\": \"ALL\"}, \"ProvisionedThroughput\": {\"ReadCapacityUnits\": 10, \"WriteCapacityUnits\": 10}}]" \
    --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10

# ============================================================
# SQS Queues
# ============================================================
echo "Creating SQS queues..."

awslocal sqs create-queue --queue-name genai-obs-trace-processing-local
awslocal sqs create-queue --queue-name genai-obs-alerts-local
awslocal sqs create-queue --queue-name genai-obs-notifications-local

# Dead letter queues
awslocal sqs create-queue --queue-name genai-obs-trace-processing-dlq-local
awslocal sqs create-queue --queue-name genai-obs-alerts-dlq-local

# ============================================================
# SNS Topics
# ============================================================
echo "Creating SNS topics..."

awslocal sns create-topic --name genai-obs-alerts-local
awslocal sns create-topic --name genai-obs-metrics-local

# ============================================================
# Kinesis Streams
# ============================================================
echo "Creating Kinesis streams..."

awslocal kinesis create-stream \
    --stream-name genai-obs-telemetry-local \
    --shard-count 2

awslocal kinesis create-stream \
    --stream-name genai-obs-events-local \
    --shard-count 1

# ============================================================
# Kinesis Firehose Delivery Streams
# ============================================================
echo "Creating Firehose delivery streams..."

awslocal firehose create-delivery-stream \
    --delivery-stream-name genai-obs-traces-firehose-local \
    --s3-destination-configuration \
        RoleARN=arn:aws:iam::000000000000:role/firehose-role,\
BucketARN=arn:aws:s3:::genai-observability-traces-local,\
Prefix=traces/

# ============================================================
# Secrets Manager
# ============================================================
echo "Creating secrets..."

awslocal secretsmanager create-secret \
    --name genai-obs/local/db-credentials \
    --secret-string '{"username":"postgres","password":"localdev123","host":"postgres","port":"5432","dbname":"genai_observability"}'

awslocal secretsmanager create-secret \
    --name genai-obs/local/api-secrets \
    --secret-string '{"jwt_secret":"local-dev-secret-change-in-prod","encryption_key":"local-encryption-key-32chars!!!"}'

echo "LocalStack initialization complete!"
echo ""
echo "Resources created:"
echo "  - S3 buckets: genai-observability-traces-local, genai-observability-artifacts-local, genai-observability-frontend-local"
echo "  - DynamoDB tables: genai-obs-connections-local, genai-obs-traces-local"
echo "  - SQS queues: genai-obs-trace-processing-local, genai-obs-alerts-local, genai-obs-notifications-local"
echo "  - SNS topics: genai-obs-alerts-local, genai-obs-metrics-local"
echo "  - Kinesis streams: genai-obs-telemetry-local, genai-obs-events-local"
echo "  - Firehose: genai-obs-traces-firehose-local"
