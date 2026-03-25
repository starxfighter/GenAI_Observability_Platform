# GenAI Observability Platform - Terraform Deployment

This directory contains Terraform configurations for deploying the GenAI Observability Platform infrastructure on AWS.

## Architecture

```
                              ┌─────────────────┐
                              │       WAF       │
                              └────────┬────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────┐
│                              API Gateway (HTTP)                              │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Cognito (Authentication)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
┌───────────────┐          ┌─────────────────────┐          ┌───────────────┐
│  EventBridge  │◀────────▶│   Lambda Functions  │◀────────▶│Step Functions │
│  (Event Bus)  │          │  (10 functions)     │          │ (Workflows)   │
└───────────────┘          └─────────────────────┘          └───────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐          ┌─────────────────────┐          ┌───────────────┐
│   DynamoDB    │          │     Timestream      │          │  OpenSearch   │
│  (9 tables)   │          │   (time series)     │          │   (search)    │
└───────────────┘          └─────────────────────┘          └───────────────┘
        │                              │                              │
        └──────────────────────────────┼──────────────────────────────┘
                                       │
┌─────────────────────┐                │                ┌─────────────────────┐
│   RDS Aurora        │◀───────────────┼───────────────▶│   ElastiCache       │
│   (PostgreSQL)      │                │                │   (Redis)           │
└─────────────────────┘                │                └─────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Kinesis Data Streams + Firehose                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
┌───────────────┐          ┌─────────────────────┐          ┌───────────────┐
│   S3 Buckets  │◀────────▶│    Glue ETL Jobs    │◀────────▶│  AWS Backup   │
│ (data, logs)  │          │  (analytics)        │          │   (vault)     │
└───────────────┘          └─────────────────────┘          └───────────────┘

                    ┌─────────────────────────────────┐
                    │     Portal (ECS + CloudFront)   │
                    │  ┌───────────┐  ┌────────────┐  │
                    │  │  FastAPI  │  │   React    │  │
                    │  │  (ECS)    │  │ (CloudFront│  │
                    │  └───────────┘  └────────────┘  │
                    └─────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
             ┌───────────┐      ┌───────────┐      ┌───────────┐
             │  Bastion  │      │   CI/CD   │      │  VPC Flow │
             │   Host    │      │ (Pipeline)│      │   Logs    │
             └───────────┘      └───────────┘      └───────────┘
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.5.0
3. **Anthropic API Key** for Claude integration
4. **(Optional)** Custom domain with ACM certificate
5. **(Optional)** SSO provider credentials (Google, Okta, or SAML)

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Create Variables File

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
environment    = "dev"
aws_region     = "us-east-1"
anthropic_api_key = "sk-ant-xxx..."

# Database passwords (use strong passwords!)
opensearch_master_password = "YourStrongPassword123!"
rds_master_password        = "YourStrongPassword456!"
```

### 3. Plan and Apply

```bash
# Preview changes
terraform plan

# Apply changes
terraform apply
```

### 4. Get Outputs

```bash
terraform output

# Get specific output
terraform output api_endpoint
terraform output frontend_configuration
```

## Module Structure

```
terraform/
├── main.tf                 # Root module orchestration
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── terraform.tfvars.example
└── modules/
    ├── vpc/                # VPC, subnets, security groups, flow logs
    ├── dynamodb/           # DynamoDB tables
    ├── timestream/         # Timestream database
    ├── opensearch/         # OpenSearch cluster
    ├── rds/                # Aurora PostgreSQL
    ├── s3/                 # S3 buckets
    ├── kinesis/            # Kinesis streams + Firehose
    ├── lambda/             # Lambda functions
    ├── api-gateway/        # HTTP API (for SDK ingestion)
    ├── cognito/            # User authentication
    ├── secrets/            # Secrets Manager
    ├── iam/                # IAM roles and policies
    ├── monitoring/         # CloudWatch alarms + dashboard
    ├── portal/             # FastAPI + React (ECS, CloudFront, ALB)
    ├── waf/                # Web Application Firewall
    ├── backup/             # AWS Backup plans and vault
    ├── glue/               # Glue ETL jobs and crawlers
    ├── eventbridge/        # EventBridge event bus and rules
    ├── stepfunctions/      # Step Functions workflows
    ├── elasticache/        # ElastiCache Redis cluster
    ├── bastion/            # Bastion host for database access
    └── cicd/               # CI/CD pipeline (CodePipeline/CodeBuild)
```

## Environment Configuration

### Development (dev)

```hcl
environment         = "dev"
single_nat_gateway  = true
opensearch_instance_type = "t3.medium.search"
opensearch_instance_count = 1
rds_instance_count  = 1
kinesis_shard_count = 1
```

### Staging (staging)

```hcl
environment         = "staging"
single_nat_gateway  = true
opensearch_instance_type = "t3.medium.search"
opensearch_instance_count = 2
rds_instance_count  = 2
kinesis_shard_count = 2
```

### Production (prod)

```hcl
environment         = "prod"
single_nat_gateway  = false  # HA NAT Gateway
enable_multi_region = true
opensearch_instance_type = "r6g.large.search"
opensearch_instance_count = 3
rds_instance_count  = 3
kinesis_shard_count = 4

# Security
waf_rate_limit     = 5000
waf_api_rate_limit = 20000
enable_flow_logs   = true
flow_logs_retention_days = 30

# Backup
backup_daily_retention_days   = 14
backup_weekly_retention_days  = 60
backup_monthly_retention_days = 730  # 2 years
enable_backup_vault_lock      = true

# Caching
elasticache_node_type  = "cache.r6g.large"
elasticache_num_nodes  = 2

# Access
enable_bastion = true

# CI/CD
enable_cicd = true
```

## Multi-Region Deployment

Enable multi-region for high availability:

```hcl
enable_multi_region = true
aws_region          = "us-east-1"
secondary_region    = "us-west-2"
```

This enables:
- DynamoDB global tables
- S3 cross-region replication
- Cross-region IAM roles

## SSO Configuration

### Google

```hcl
enable_google_sso    = true
google_client_id     = "your-client-id.apps.googleusercontent.com"
google_client_secret = "your-client-secret"
```

### Okta

```hcl
enable_okta_sso    = true
okta_client_id     = "your-okta-client-id"
okta_client_secret = "your-okta-client-secret"
okta_issuer_url    = "https://your-org.okta.com"
```

### SAML

```hcl
enable_saml_sso    = true
saml_metadata_url  = "https://idp.example.com/metadata"
saml_provider_name = "Enterprise"
```

## Custom Domain

To use a custom domain:

1. Create ACM certificate in the same region:
   ```bash
   aws acm request-certificate \
     --domain-name api.observability.example.com \
     --validation-method DNS
   ```

2. Validate the certificate (DNS or email)

3. Configure Terraform:
   ```hcl
   api_domain_name     = "api.observability.example.com"
   api_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/abc123"
   ```

4. Create CNAME record pointing to the API Gateway domain

## Deploying the Portal

The portal consists of:
- **FastAPI Backend**: Runs on ECS Fargate behind an Application Load Balancer
- **React Frontend**: Static files on S3 served via CloudFront

### 1. Build and Push API Docker Image

```bash
# Navigate to API directory
cd api

# Build Docker image
docker build -t genai-obs-api .

# Get ECR repository URL from Terraform
ECR_URL=$(terraform -chdir=../terraform output -raw portal_ecr_repository)

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URL

# Tag and push
docker tag genai-obs-api:latest $ECR_URL:latest
docker push $ECR_URL:latest

# Force new deployment
aws ecs update-service \
  --cluster $(terraform -chdir=../terraform output -raw portal_ecs_cluster) \
  --service $(terraform -chdir=../terraform output -raw portal_ecs_service) \
  --force-new-deployment
```

### 2. Build and Deploy Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Get S3 bucket and CloudFront distribution
BUCKET=$(terraform -chdir=../terraform output -raw portal_frontend_bucket)
CF_DIST=$(terraform -chdir=../terraform output -raw portal_cloudfront_distribution_id)

# Sync to S3
aws s3 sync dist/ s3://$BUCKET/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id $CF_DIST --paths "/*"
```

### 3. Configure Frontend Environment

Create `frontend/.env.production`:

```env
VITE_API_URL=https://api.observability.example.com
VITE_COGNITO_USER_POOL_ID=us-east-1_xxxxxx
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxx
VITE_COGNITO_DOMAIN=genai-obs-xxxx.auth.us-east-1.amazoncognito.com
VITE_REGION=us-east-1
```

Or use Terraform outputs:

```bash
terraform output frontend_configuration
```

### Portal Custom Domains

To use custom domains:

1. **API Domain** - Certificate must be in the same region:
   ```hcl
   portal_api_domain      = "api.observability.example.com"
   portal_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/abc123"
   ```

2. **Frontend Domain** - Certificate must be in us-east-1 (CloudFront requirement):
   ```hcl
   portal_frontend_domain          = "observability.example.com"
   portal_frontend_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/def456"
   ```

3. **Automatic DNS** - If using Route53:
   ```hcl
   route53_zone_id = "Z1234567890ABC"
   ```

### Portal Scaling

Default configuration scales automatically based on CPU/memory:

```hcl
portal_api_min_count = 1   # Minimum tasks
portal_api_max_count = 10  # Maximum tasks
```

Production recommendations:
```hcl
portal_api_cpu           = 1024  # 1 vCPU
portal_api_memory        = 2048  # 2 GB
portal_api_desired_count = 3
portal_api_min_count     = 2
portal_api_max_count     = 20
```

## Deploying Lambda Code

The Terraform creates Lambda functions with placeholder code. Deploy actual code:

### Using AWS CLI

```bash
cd lambda/stream_processor
zip -r function.zip .
aws lambda update-function-code \
  --function-name genai-obs-dev-stream_processor \
  --zip-file fileb://function.zip
```

### Using CI/CD

See the deployment role created by the IAM module for GitHub Actions / CodeBuild.

## Cost Estimation

| Component | Dev (Monthly) | Staging (Monthly) | Prod (Monthly) |
|-----------|---------------|-------------------|----------------|
| VPC + NAT | ~$35 | ~$35 | ~$100 |
| DynamoDB | ~$25 | ~$50 | ~$200 |
| Timestream | ~$50 | ~$100 | ~$300 |
| OpenSearch | ~$150 | ~$300 | ~$800 |
| RDS Aurora | ~$75 | ~$150 | ~$400 |
| Kinesis | ~$25 | ~$50 | ~$150 |
| Lambda | ~$10 | ~$30 | ~$85 |
| API Gateway | ~$5 | ~$15 | ~$50 |
| S3 | ~$10 | ~$25 | ~$100 |
| ECS Fargate | ~$30 | ~$60 | ~$200 |
| ALB | ~$20 | ~$20 | ~$25 |
| CloudFront | ~$5 | ~$10 | ~$50 |
| **WAF** | ~$10 | ~$15 | ~$30 |
| **ElastiCache** | ~$15 | ~$30 | ~$100 |
| **Glue** | ~$5 | ~$15 | ~$50 |
| **Step Functions** | ~$5 | ~$10 | ~$25 |
| **EventBridge** | ~$2 | ~$5 | ~$15 |
| **AWS Backup** | ~$10 | ~$25 | ~$75 |
| **Bastion** | ~$5 | ~$5 | ~$10 |
| **CI/CD** | ~$5 | ~$10 | ~$25 |
| **Total** | **~$532** | **~$1,010** | **~$2,790** |

*Estimates based on moderate usage. Actual costs vary.*

## State Management

### Remote State (Recommended)

Create S3 bucket and DynamoDB table for state:

```bash
aws s3 mb s3://your-terraform-state-bucket
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

Uncomment backend configuration in `main.tf`:

```hcl
backend "s3" {
  bucket         = "your-terraform-state-bucket"
  key            = "genai-observability/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "terraform-state-lock"
  encrypt        = true
}
```

## Destroying Infrastructure

```bash
# Destroy all resources
terraform destroy

# Destroy specific module
terraform destroy -target=module.opensearch
```

**Warning**: Production environments have deletion protection enabled. Disable it first:

```hcl
deletion_protection = false
```

## Troubleshooting

### OpenSearch Access Denied

Ensure your IP is in the access policy or connect via VPC.

### Lambda Timeout

Increase timeout in the Lambda module or check VPC connectivity.

### DynamoDB Throttling

Switch to on-demand billing or increase provisioned capacity.

### Cognito Callback Errors

Ensure callback URLs match exactly, including trailing slashes.

## Security Features

### Web Application Firewall (WAF)

WAF is automatically deployed for CloudFront, ALB, and API Gateway:

```hcl
# Rate limiting
waf_rate_limit     = 2000   # Requests per 5 minutes per IP
waf_api_rate_limit = 10000  # Higher limit for API calls

# Geo-blocking (optional)
waf_blocked_countries = ["CN", "RU", "KP"]
```

Protected against:
- SQL injection attacks
- Cross-site scripting (XSS)
- Known bad inputs
- Rate limiting / DDoS protection

### VPC Flow Logs

VPC Flow Logs capture network traffic for security analysis:

```hcl
enable_flow_logs         = true
flow_logs_retention_days = 14  # 30 for production
```

Logs are stored in CloudWatch and S3 for analysis.

## Backup and Recovery

### AWS Backup

Automated backup plans for DynamoDB and RDS:

```hcl
backup_daily_retention_days   = 7    # Keep daily backups for 7 days
backup_weekly_retention_days  = 30   # Keep weekly backups for 30 days
backup_monthly_retention_days = 365  # Keep monthly backups for 1 year

# Enable vault lock for compliance (prevents backup deletion)
enable_backup_vault_lock = true  # For production compliance
```

Backup schedule:
- **Daily**: Every day at 5:00 AM UTC
- **Weekly**: Every Sunday at 5:00 AM UTC
- **Monthly**: First day of month at 5:00 AM UTC

## Event-Driven Architecture

### EventBridge

Custom event bus for platform events:

```hcl
eventbridge_archive_retention_days = 30  # Keep event archive for 30 days
```

Configured event rules:
- `anomaly_detected` - Triggers investigation workflow
- `alert_created` - Routes to notification channels
- `remediation_approved` - Starts remediation execution
- `integration_sync` - Syncs with external systems
- `daily_report` - Generates daily reports

### Step Functions

Workflow orchestration for complex operations:

**Remediation Workflow:**
1. Generate remediation plan (Claude AI)
2. Check auto-approval thresholds
3. Wait for manual approval (if needed)
4. Execute remediation actions
5. Verify remediation success
6. Send notifications

**Investigation Workflow:**
1. Gather context (parallel: logs, metrics, traces, similar incidents)
2. Analyze with Claude AI
3. Generate investigation report
4. Store investigation results
5. Notify relevant teams

## Caching

### ElastiCache (Redis)

Redis cluster for caching and session storage:

```hcl
elasticache_node_type  = "cache.t3.micro"  # Use cache.r6g for production
elasticache_num_nodes  = 1                  # Use 2+ for production HA
elasticache_auth_token = "your-strong-redis-password"
```

Features:
- TLS encryption in transit
- At-rest encryption
- AUTH token authentication
- CloudWatch alarms for memory/CPU

## ETL and Analytics

### Glue ETL

Automated ETL jobs for data processing:

**Daily Aggregation**: Aggregates daily metrics and events
**Anomaly Report**: Generates anomaly analysis reports
**Data Compaction**: Compacts small files for query performance
**Cost Analysis**: Analyzes platform usage and costs

Glue workflow runs automatically via scheduled triggers.

## Database Access

### Bastion Host

Secure access to private databases:

```hcl
enable_bastion = true

# Restrict SSH access to your IP
bastion_allowed_cidr_blocks = ["1.2.3.4/32"]

# Or use SSM Session Manager (recommended, no SSH key needed)
bastion_ssh_public_key = ""  # Leave empty for SSM-only access
```

Connect via SSM Session Manager:
```bash
# Get connect command from Terraform
terraform output bastion_ssm_connect_command

# Connect
aws ssm start-session --target i-1234567890abcdef0
```

Pre-installed tools on bastion:
- PostgreSQL client
- MySQL client
- Redis CLI
- jq, htop, curl

## CI/CD Pipeline

### CodePipeline

Automated deployment pipeline:

```hcl
enable_cicd = true

# Create CodeStar connection first (manual step in AWS Console)
codestar_connection_arn = "arn:aws:codestar-connections:us-east-1:123456789012:connection/abc123"
github_repository       = "your-org/genai-observability-platform"
github_branch           = "main"
```

Pipeline stages:
1. **Source**: Pull from GitHub (via CodeStar connection)
2. **Build**: Parallel builds for API, Frontend, and Lambda
3. **Deploy**: Deploy to ECS, S3/CloudFront, and Lambda

### Setting Up CodeStar Connection

1. Go to AWS Console > Developer Tools > Connections
2. Create connection for GitHub
3. Authorize access to your repository
4. Copy the connection ARN to `terraform.tfvars`

### Manual Deployment (Alternative)

If not using CI/CD, deploy manually:

```bash
# API
docker build -t api ./api
docker push $(terraform output -raw portal_ecr_repository):latest
aws ecs update-service --cluster $(terraform output -raw portal_ecs_cluster) \
  --service $(terraform output -raw portal_ecs_service) --force-new-deployment

# Frontend
cd frontend && npm run build
aws s3 sync dist/ s3://$(terraform output -raw portal_frontend_bucket)/ --delete
aws cloudfront create-invalidation --distribution-id $(terraform output -raw portal_cloudfront_distribution_id) --paths "/*"
```

## Security Best Practices

1. **Use strong passwords** for databases and OpenSearch
2. **Enable MFA** for IAM users with console access
3. **Rotate secrets** regularly using Secrets Manager rotation
4. **Enable VPC Flow Logs** for network monitoring (enabled by default)
5. **Use least privilege** IAM policies
6. **Enable CloudTrail** for API auditing
7. **Review security groups** - minimize open ports
8. **Enable WAF** for all public endpoints (enabled by default)
9. **Use bastion with SSM** instead of SSH keys when possible
10. **Enable backup vault lock** for compliance requirements

## Support

- **Documentation**: See main project README
- **Issues**: Create an issue in the repository
- **Updates**: Run `terraform plan` periodically to check for drift
