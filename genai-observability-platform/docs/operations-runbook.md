# GenAI Observability Platform - Operations Runbook

## Overview

This runbook provides procedures for operating and troubleshooting the GenAI Observability Platform in production.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring & Alerting](#monitoring--alerting)
3. [Common Issues & Resolutions](#common-issues--resolutions)
4. [Incident Response](#incident-response)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Scaling Procedures](#scaling-procedures)
7. [Backup & Recovery](#backup--recovery)

---

## Daily Operations

### Morning Checklist

- [ ] Check CloudWatch dashboard for overnight anomalies
- [ ] Verify daily ETL pipeline completed successfully
- [ ] Review critical alerts from overnight
- [ ] Check Kinesis iterator age (should be < 60s)
- [ ] Verify OpenSearch cluster health is green
- [ ] Check RDS CPU and connection count

### Health Check Commands

```bash
# Overall system health
curl -s https://api.observability.example.com/health | jq

# Check Lambda errors in last hour
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=genai-observability-prod-ingestion \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum

# Check Kinesis iterator age
aws cloudwatch get-metric-statistics \
    --namespace AWS/Kinesis \
    --metric-name GetRecords.IteratorAgeMilliseconds \
    --dimensions Name=StreamName,Value=genai-observability-prod-events \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Maximum

# Check OpenSearch cluster health
curl -s "https://opensearch-endpoint/_cluster/health?pretty"

# Check RDS status
aws rds describe-db-clusters \
    --db-cluster-identifier genai-observability-prod \
    --query 'DBClusters[0].Status'
```

### Daily ETL Pipeline Check

```bash
# Check Step Functions execution status
aws stepfunctions list-executions \
    --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:genai-observability-prod-daily-pipeline \
    --max-results 5 \
    --query 'executions[*].{name:name,status:status,startDate:startDate}'

# Check specific execution details
aws stepfunctions describe-execution \
    --execution-arn <execution-arn>

# View Glue job run history
aws glue get-job-runs \
    --job-name genai-observability-prod-token-aggregation \
    --max-results 5
```

---

## Monitoring & Alerting

### Key Metrics to Monitor

| Metric | Normal Range | Warning | Critical |
|--------|--------------|---------|----------|
| Ingestion Lambda Duration | < 1s | > 3s | > 10s |
| Kinesis Iterator Age | < 30s | > 60s | > 300s |
| DynamoDB Throttling | 0 | > 0 | > 10/min |
| OpenSearch Cluster Health | green | yellow | red |
| RDS CPU | < 70% | > 80% | > 95% |
| API Gateway 5xx | < 0.1% | > 1% | > 5% |
| Alert Processing Lag | < 30s | > 60s | > 300s |

### CloudWatch Alarms

```bash
# List all alarms and their states
aws cloudwatch describe-alarms \
    --alarm-name-prefix genai-observability-prod \
    --query 'MetricAlarms[*].{Name:AlarmName,State:StateValue}'

# Get alarm history
aws cloudwatch describe-alarm-history \
    --alarm-name genai-observability-prod-ingestion-errors \
    --history-item-type StateUpdate \
    --max-records 10
```

### Log Queries

```bash
# Find Lambda errors
aws logs filter-log-events \
    --log-group-name /aws/lambda/genai-observability-prod-ingestion \
    --filter-pattern "ERROR" \
    --start-time $(date -u -d '1 hour ago' +%s)000

# Find slow traces (> 10s)
aws logs filter-log-events \
    --log-group-name /aws/lambda/genai-observability-prod-stream-processor \
    --filter-pattern '{ $.duration_ms > 10000 }' \
    --start-time $(date -u -d '1 hour ago' +%s)000

# Find authentication failures
aws logs filter-log-events \
    --log-group-name /aws/lambda/genai-observability-prod-authorizer \
    --filter-pattern '"Unauthorized"' \
    --start-time $(date -u -d '1 hour ago' +%s)000
```

---

## Common Issues & Resolutions

### Issue: High Kinesis Iterator Age

**Symptoms:**
- Iterator age > 60 seconds
- Events appearing delayed in dashboard
- CloudWatch alarm triggered

**Diagnosis:**
```bash
# Check consumer Lambda errors
aws logs filter-log-events \
    --log-group-name /aws/lambda/genai-observability-prod-stream-processor \
    --filter-pattern "ERROR" \
    --start-time $(date -u -d '30 minutes ago' +%s)000

# Check Lambda concurrent executions
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name ConcurrentExecutions \
    --dimensions Name=FunctionName,Value=genai-observability-prod-stream-processor \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Maximum
```

**Resolution:**
1. If Lambda errors: Fix the error (see logs)
2. If at concurrency limit: Increase reserved concurrency
3. If sustained high throughput: Add Kinesis shards

```bash
# Increase Lambda concurrency
aws lambda put-function-concurrency \
    --function-name genai-observability-prod-stream-processor \
    --reserved-concurrent-executions 200

# Add Kinesis shards
aws kinesis update-shard-count \
    --stream-name genai-observability-prod-events \
    --target-shard-count 4 \
    --scaling-type UNIFORM_SCALING
```

---

### Issue: OpenSearch Cluster Yellow/Red

**Symptoms:**
- Cluster health not green
- Search queries slow or failing
- Dashboard search not working

**Diagnosis:**
```bash
# Check cluster health
curl -s "https://opensearch-endpoint/_cluster/health?pretty"

# Check disk usage
curl -s "https://opensearch-endpoint/_cat/allocation?v"

# Check pending tasks
curl -s "https://opensearch-endpoint/_cluster/pending_tasks?pretty"

# Check shard status
curl -s "https://opensearch-endpoint/_cat/shards?v&h=index,shard,prirep,state,docs,store,node"
```

**Resolution:**

For Yellow (unassigned replicas):
```bash
# Check why shards are unassigned
curl -s "https://opensearch-endpoint/_cluster/allocation/explain?pretty"

# Usually resolves itself; if not, check node count
```

For Red (unassigned primaries):
```bash
# Identify unassigned shards
curl -s "https://opensearch-endpoint/_cat/shards?h=index,shard,prirep,state&s=state"

# If disk full, increase disk or delete old indices
curl -X DELETE "https://opensearch-endpoint/traces-2024.01.*"

# Force allocate shard (last resort)
curl -X POST "https://opensearch-endpoint/_cluster/reroute" -H 'Content-Type: application/json' -d'
{
  "commands": [{
    "allocate_stale_primary": {
      "index": "traces-2024.01.15",
      "shard": 0,
      "node": "node-1",
      "accept_data_loss": true
    }
  }]
}'
```

---

### Issue: DynamoDB Throttling

**Symptoms:**
- ProvisionedThroughputExceededException errors
- Slow writes to hot path
- Data loss if not retried

**Diagnosis:**
```bash
# Check consumed vs provisioned capacity
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name ConsumedWriteCapacityUnits \
    --dimensions Name=TableName,Value=genai-observability-prod-traces \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Sum
```

**Resolution:**

If using provisioned capacity:
```bash
# Increase write capacity
aws dynamodb update-table \
    --table-name genai-observability-prod-traces \
    --provisioned-throughput ReadCapacityUnits=100,WriteCapacityUnits=500
```

Switch to on-demand (recommended):
```bash
aws dynamodb update-table \
    --table-name genai-observability-prod-traces \
    --billing-mode PAY_PER_REQUEST
```

---

### Issue: RDS Connection Exhaustion

**Symptoms:**
- "too many connections" errors
- API requests timing out
- Glue jobs failing

**Diagnosis:**
```bash
# Check current connections
aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name DatabaseConnections \
    --dimensions Name=DBClusterIdentifier,Value=genai-observability-prod \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Maximum

# Connect and check active queries
psql -h rds-endpoint -U admin -d observability -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC
LIMIT 20;"
```

**Resolution:**
```bash
# Kill long-running queries
psql -h rds-endpoint -U admin -d observability -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE duration > interval '5 minutes'
AND state != 'idle';"

# If persistent, increase max_connections (requires reboot)
aws rds modify-db-cluster-parameter-group \
    --db-cluster-parameter-group-name genai-observability-prod \
    --parameters "ParameterName=max_connections,ParameterValue=500,ApplyMethod=pending-reboot"
```

---

### Issue: Daily ETL Pipeline Failed

**Symptoms:**
- Step Functions execution failed
- Missing data in RDS analytics tables
- Cost/metrics reports incomplete

**Diagnosis:**
```bash
# Get failed execution details
aws stepfunctions describe-execution \
    --execution-arn <execution-arn>

# Check which Glue job failed
aws glue get-job-run \
    --job-name genai-observability-prod-token-aggregation \
    --run-id <run-id>

# View Glue job logs
aws logs filter-log-events \
    --log-group-name /aws-glue/jobs/error \
    --filter-pattern "genai-observability-prod-token-aggregation"
```

**Resolution:**
```bash
# Manually trigger the pipeline
aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:genai-observability-prod-daily-pipeline \
    --input '{"manual_trigger": true, "date": "2024-01-15"}'

# Or run individual Glue job
aws glue start-job-run \
    --job-name genai-observability-prod-token-aggregation \
    --arguments '{"--EXECUTION_DATE":"2024-01-15T02:00:00Z"}'
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| SEV1 | Complete outage | 15 minutes | API down, data loss |
| SEV2 | Major degradation | 30 minutes | High latency, partial outage |
| SEV3 | Minor issues | 4 hours | Single agent affected |
| SEV4 | Cosmetic | Next business day | Dashboard UI glitch |

### Incident Response Checklist

1. **Acknowledge** - Confirm incident, notify stakeholders
2. **Assess** - Determine scope and severity
3. **Mitigate** - Apply immediate fixes
4. **Communicate** - Update status page
5. **Resolve** - Implement permanent fix
6. **Review** - Post-incident review

### Communication Templates

**Initial Response:**
```
[INCIDENT] GenAI Observability Platform
Status: Investigating
Impact: <description>
Started: <time>
Next Update: <time>
```

**Resolution:**
```
[RESOLVED] GenAI Observability Platform
Issue: <description>
Impact: <details>
Duration: <time>
Root Cause: <cause>
Resolution: <fix>
```

---

## Maintenance Procedures

### Index Rotation (OpenSearch)

Runs automatically via Index Lifecycle Management, but manual rotation:

```bash
# Create new index
curl -X PUT "https://opensearch-endpoint/traces-$(date +%Y.%m.%d)" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1
  }
}'

# Update alias
curl -X POST "https://opensearch-endpoint/_aliases" -H 'Content-Type: application/json' -d'
{
  "actions": [
    { "remove": { "index": "traces-*", "alias": "traces-write" }},
    { "add": { "index": "traces-'$(date +%Y.%m.%d)'", "alias": "traces-write" }}
  ]
}'

# Delete old indices (> 30 days)
curl -X DELETE "https://opensearch-endpoint/traces-$(date -d '30 days ago' +%Y.%m)*"
```

### API Key Rotation

```bash
# List keys expiring soon
genai-obs api-keys list --expiring-within 7d

# Rotate key
genai-obs api-keys rotate <key-id> --grace-period 24
```

### Database Maintenance

```bash
# Run VACUUM ANALYZE (weekly)
psql -h rds-endpoint -U admin -d observability -c "VACUUM ANALYZE;"

# Check table bloat
psql -h rds-endpoint -U admin -d observability -c "
SELECT schemaname, relname, n_dead_tup, n_live_tup,
       round(n_dead_tup * 100.0 / nullif(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 10;"
```

---

## Scaling Procedures

### Horizontal Scaling

**Add Kinesis Shards:**
```bash
aws kinesis update-shard-count \
    --stream-name genai-observability-prod-events \
    --target-shard-count <new-count> \
    --scaling-type UNIFORM_SCALING
```

**Add OpenSearch Data Nodes:**
```bash
aws opensearch update-domain-config \
    --domain-name genai-observability-prod \
    --cluster-config '{"InstanceCount": <new-count>}'
```

**Add RDS Read Replicas:**
```bash
aws rds create-db-instance \
    --db-instance-identifier genai-observability-prod-reader-2 \
    --db-cluster-identifier genai-observability-prod \
    --db-instance-class db.r6g.large \
    --engine aurora-postgresql
```

### Vertical Scaling

**Upgrade RDS Instance Class:**
```bash
aws rds modify-db-cluster \
    --db-cluster-identifier genai-observability-prod \
    --apply-immediately \
    --db-cluster-instance-class db.r6g.xlarge
```

**Upgrade OpenSearch Instance Type:**
```bash
aws opensearch update-domain-config \
    --domain-name genai-observability-prod \
    --cluster-config '{"InstanceType": "r6g.xlarge.search"}'
```

---

## Backup & Recovery

### Backup Status Check

```bash
# RDS automated backups
aws rds describe-db-cluster-snapshots \
    --db-cluster-identifier genai-observability-prod \
    --snapshot-type automated \
    --query 'DBClusterSnapshots[*].{ID:DBClusterSnapshotIdentifier,Time:SnapshotCreateTime,Status:Status}'

# S3 versioning status
aws s3api get-bucket-versioning --bucket genai-observability-data-prod

# OpenSearch snapshots
curl -s "https://opensearch-endpoint/_snapshot/automated/_all?pretty" | jq '.snapshots[-5:]'
```

### Recovery Procedures

**Restore RDS from Snapshot:**
```bash
aws rds restore-db-cluster-from-snapshot \
    --db-cluster-identifier genai-observability-prod-restored \
    --snapshot-identifier <snapshot-id> \
    --engine aurora-postgresql \
    --vpc-security-group-ids <sg-id>
```

**Restore S3 Object:**
```bash
# List versions
aws s3api list-object-versions \
    --bucket genai-observability-data-prod \
    --prefix raw/events/2024/01/15 \
    --max-keys 10

# Restore specific version
aws s3api copy-object \
    --bucket genai-observability-data-prod \
    --copy-source "genai-observability-data-prod/raw/events/2024/01/15/events.json?versionId=<version-id>" \
    --key raw/events/2024/01/15/events.json
```

**Restore OpenSearch Index:**
```bash
curl -X POST "https://opensearch-endpoint/_snapshot/automated/<snapshot-name>/_restore" -H 'Content-Type: application/json' -d'
{
  "indices": "traces-2024.01.15",
  "rename_pattern": "(.+)",
  "rename_replacement": "restored-$1"
}'
```

---

## Contacts

| Role | Name | Contact |
|------|------|---------|
| On-Call Engineer | Rotating | PagerDuty |
| Platform Lead | TBD | email@example.com |
| AWS Support | - | AWS Console |

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2024-01-15 | 1.0 | Platform Team | Initial version |
