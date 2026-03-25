# GenAI Observability Platform - Input Variables

# =============================================================================
# GENERAL
# =============================================================================

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "Primary AWS region"
  type        = string
  default     = "us-east-1"
}

variable "secondary_region" {
  description = "Secondary AWS region for multi-region deployment"
  type        = string
  default     = "us-west-2"
}

variable "enable_multi_region" {
  description = "Enable multi-region deployment"
  type        = bool
  default     = false
}

# =============================================================================
# VPC AND NETWORKING
# =============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use single NAT Gateway (cost savings for non-prod)"
  type        = bool
  default     = true
}

# =============================================================================
# DYNAMODB
# =============================================================================

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode (PROVISIONED or PAY_PER_REQUEST)"
  type        = string
  default     = "PAY_PER_REQUEST"
}

# =============================================================================
# TIMESTREAM
# =============================================================================

variable "timestream_memory_retention_hours" {
  description = "Hours to retain data in Timestream memory store"
  type        = number
  default     = 24
}

variable "timestream_magnetic_retention_days" {
  description = "Days to retain data in Timestream magnetic store"
  type        = number
  default     = 365
}

# =============================================================================
# OPENSEARCH
# =============================================================================

variable "opensearch_instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "t3.medium.search"
}

variable "opensearch_instance_count" {
  description = "Number of OpenSearch instances"
  type        = number
  default     = 2
}

variable "opensearch_volume_size" {
  description = "EBS volume size for OpenSearch (GB)"
  type        = number
  default     = 100
}

variable "opensearch_master_user" {
  description = "OpenSearch master username"
  type        = string
  default     = "admin"
}

variable "opensearch_master_password" {
  description = "OpenSearch master password"
  type        = string
  sensitive   = true
}

# =============================================================================
# RDS AURORA
# =============================================================================

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_instance_count" {
  description = "Number of RDS instances"
  type        = number
  default     = 2
}

variable "rds_database_name" {
  description = "Database name"
  type        = string
  default     = "observability"
}

variable "rds_master_username" {
  description = "RDS master username"
  type        = string
  default     = "dbadmin"
}

variable "rds_master_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

# =============================================================================
# S3
# =============================================================================

variable "s3_archive_after_days" {
  description = "Days before archiving to Glacier"
  type        = number
  default     = 90
}

variable "s3_expire_after_days" {
  description = "Days before expiring objects"
  type        = number
  default     = 365
}

# =============================================================================
# KINESIS
# =============================================================================

variable "kinesis_shard_count" {
  description = "Number of Kinesis shards"
  type        = number
  default     = 2
}

variable "kinesis_retention_hours" {
  description = "Kinesis data retention period (hours)"
  type        = number
  default     = 24
}

# =============================================================================
# LAMBDA
# =============================================================================

variable "lambda_log_retention_days" {
  description = "CloudWatch log retention for Lambda functions"
  type        = number
  default     = 14
}

# =============================================================================
# API GATEWAY
# =============================================================================

variable "api_domain_name" {
  description = "Custom domain name for API (optional)"
  type        = string
  default     = ""
}

variable "api_certificate_arn" {
  description = "ACM certificate ARN for custom domain"
  type        = string
  default     = ""
}

variable "api_throttle_rate_limit" {
  description = "API Gateway throttle rate limit (requests/second)"
  type        = number
  default     = 1000
}

variable "api_throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 2000
}

# =============================================================================
# COGNITO
# =============================================================================

variable "cognito_callback_urls" {
  description = "Allowed callback URLs for Cognito"
  type        = list(string)
  default     = ["http://localhost:3000/callback"]
}

variable "cognito_logout_urls" {
  description = "Allowed logout URLs for Cognito"
  type        = list(string)
  default     = ["http://localhost:3000"]
}

# SSO - Google
variable "enable_google_sso" {
  description = "Enable Google SSO"
  type        = bool
  default     = false
}

variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
  default     = ""
}

variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
  default     = ""
}

# SSO - Okta
variable "enable_okta_sso" {
  description = "Enable Okta SSO"
  type        = bool
  default     = false
}

variable "okta_client_id" {
  description = "Okta OAuth client ID"
  type        = string
  default     = ""
}

variable "okta_client_secret" {
  description = "Okta OAuth client secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "okta_issuer_url" {
  description = "Okta issuer URL"
  type        = string
  default     = ""
}

# SSO - SAML
variable "enable_saml_sso" {
  description = "Enable SAML SSO"
  type        = bool
  default     = false
}

variable "saml_metadata_url" {
  description = "SAML IdP metadata URL"
  type        = string
  default     = ""
}

variable "saml_provider_name" {
  description = "SAML provider name"
  type        = string
  default     = "Enterprise"
}

# =============================================================================
# SECRETS
# =============================================================================

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pagerduty_integration_key" {
  description = "PagerDuty integration key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pagerduty_endpoint" {
  description = "PagerDuty events endpoint"
  type        = string
  default     = "https://events.pagerduty.com/v2/enqueue"
}

# =============================================================================
# MONITORING
# =============================================================================

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = ""
}

variable "lambda_error_threshold" {
  description = "Lambda error count threshold for alarms"
  type        = number
  default     = 10
}

variable "api_latency_threshold_ms" {
  description = "API latency threshold (ms) for alarms"
  type        = number
  default     = 1000
}

variable "dynamodb_throttle_threshold" {
  description = "DynamoDB throttle threshold for alarms"
  type        = number
  default     = 5
}

# =============================================================================
# PORTAL (FastAPI + React)
# =============================================================================

variable "portal_api_cpu" {
  description = "Portal API CPU units"
  type        = number
  default     = 512
}

variable "portal_api_memory" {
  description = "Portal API memory (MB)"
  type        = number
  default     = 1024
}

variable "portal_api_desired_count" {
  description = "Portal API desired task count"
  type        = number
  default     = 2
}

variable "portal_api_min_count" {
  description = "Portal API minimum task count"
  type        = number
  default     = 1
}

variable "portal_api_max_count" {
  description = "Portal API maximum task count"
  type        = number
  default     = 10
}

variable "portal_api_domain" {
  description = "Custom domain for Portal API"
  type        = string
  default     = ""
}

variable "portal_frontend_domain" {
  description = "Custom domain for Portal Frontend"
  type        = string
  default     = ""
}

variable "portal_certificate_arn" {
  description = "ACM certificate ARN for Portal API (same region)"
  type        = string
  default     = ""
}

variable "portal_frontend_certificate_arn" {
  description = "ACM certificate ARN for CloudFront (us-east-1)"
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID for DNS records"
  type        = string
  default     = ""
}

variable "cors_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

# =============================================================================
# WAF (Web Application Firewall)
# =============================================================================

variable "waf_rate_limit" {
  description = "WAF rate limit (requests per 5 minutes per IP)"
  type        = number
  default     = 2000
}

variable "waf_api_rate_limit" {
  description = "WAF API rate limit (requests per 5 minutes per IP)"
  type        = number
  default     = 10000
}

variable "waf_blocked_countries" {
  description = "List of country codes to block (e.g., ['CN', 'RU'])"
  type        = list(string)
  default     = []
}

# =============================================================================
# AWS BACKUP
# =============================================================================

variable "backup_daily_retention_days" {
  description = "Days to retain daily backups"
  type        = number
  default     = 7
}

variable "backup_weekly_retention_days" {
  description = "Days to retain weekly backups"
  type        = number
  default     = 30
}

variable "backup_monthly_retention_days" {
  description = "Days to retain monthly backups"
  type        = number
  default     = 365
}

variable "enable_backup_vault_lock" {
  description = "Enable backup vault lock (compliance)"
  type        = bool
  default     = false
}

# =============================================================================
# EVENTBRIDGE
# =============================================================================

variable "eventbridge_archive_retention_days" {
  description = "EventBridge event archive retention days"
  type        = number
  default     = 30
}

# =============================================================================
# ELASTICACHE (REDIS)
# =============================================================================

variable "elasticache_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "elasticache_num_nodes" {
  description = "Number of ElastiCache nodes"
  type        = number
  default     = 1
}

variable "elasticache_auth_token" {
  description = "ElastiCache Redis AUTH token (password)"
  type        = string
  sensitive   = true
  default     = ""
}

# =============================================================================
# BASTION HOST
# =============================================================================

variable "enable_bastion" {
  description = "Enable bastion host for database access"
  type        = bool
  default     = false
}

variable "bastion_allowed_cidr_blocks" {
  description = "CIDR blocks allowed to SSH to bastion"
  type        = list(string)
  default     = []
}

variable "bastion_ssh_public_key" {
  description = "SSH public key for bastion access (optional, SSM preferred)"
  type        = string
  default     = ""
}

variable "bastion_instance_type" {
  description = "Bastion instance type"
  type        = string
  default     = "t3.micro"
}

# =============================================================================
# CI/CD PIPELINE
# =============================================================================

variable "enable_cicd" {
  description = "Enable CI/CD pipeline"
  type        = bool
  default     = false
}

variable "codestar_connection_arn" {
  description = "CodeStar connection ARN for GitHub"
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository (owner/repo)"
  type        = string
  default     = ""
}

variable "github_branch" {
  description = "GitHub branch to deploy"
  type        = string
  default     = "main"
}

# =============================================================================
# VPC FLOW LOGS
# =============================================================================

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "flow_logs_retention_days" {
  description = "Flow logs retention in days"
  type        = number
  default     = 14
}
