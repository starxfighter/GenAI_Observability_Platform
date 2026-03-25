# Portal Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS"
  type        = list(string)
}

# =============================================================================
# ECS CONFIGURATION
# =============================================================================

variable "api_cpu" {
  description = "API task CPU units"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "API task memory (MB)"
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Desired number of API tasks"
  type        = number
  default     = 2
}

variable "api_min_count" {
  description = "Minimum number of API tasks"
  type        = number
  default     = 1
}

variable "api_max_count" {
  description = "Maximum number of API tasks"
  type        = number
  default     = 10
}

# =============================================================================
# DOMAINS AND CERTIFICATES
# =============================================================================

variable "api_domain" {
  description = "Custom domain for API"
  type        = string
  default     = ""
}

variable "frontend_domain" {
  description = "Custom domain for frontend"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for API (must be in same region)"
  type        = string
}

variable "frontend_certificate_arn" {
  description = "ACM certificate ARN for CloudFront (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID"
  type        = string
  default     = ""
}

variable "cors_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

# =============================================================================
# DATABASE CONNECTIONS
# =============================================================================

variable "dynamodb_tables" {
  description = "DynamoDB table names"
  type = object({
    traces         = string
    spans          = string
    agents         = string
    alerts         = string
    investigations = string
    remediations   = string
    integrations   = string
    api_keys       = string
    saved_queries  = string
  })
}

variable "dynamodb_table_arns" {
  description = "DynamoDB table ARNs"
  type        = list(string)
}

variable "timestream_database" {
  description = "Timestream database name"
  type        = string
}

variable "timestream_table" {
  description = "Timestream table name"
  type        = string
}

variable "opensearch_endpoint" {
  description = "OpenSearch endpoint"
  type        = string
}

variable "rds_endpoint" {
  description = "RDS endpoint"
  type        = string
}

variable "rds_database" {
  description = "RDS database name"
  type        = string
}

variable "kinesis_stream" {
  description = "Kinesis stream name"
  type        = string
}

variable "kinesis_stream_arn" {
  description = "Kinesis stream ARN"
  type        = string
}

variable "s3_bucket_arn" {
  description = "S3 bucket ARN"
  type        = string
}

# =============================================================================
# SECRETS
# =============================================================================

variable "jwt_secret_arn" {
  description = "JWT secret ARN"
  type        = string
}

variable "anthropic_secret_arn" {
  description = "Anthropic API key secret ARN"
  type        = string
}

variable "database_secret_arn" {
  description = "Database credentials secret ARN"
  type        = string
}

variable "opensearch_secret_arn" {
  description = "OpenSearch credentials secret ARN"
  type        = string
}

# =============================================================================
# COGNITO
# =============================================================================

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  type        = string
}

variable "cognito_client_id" {
  description = "Cognito Client ID"
  type        = string
}

# =============================================================================
# LAMBDA
# =============================================================================

variable "lambda_arns" {
  description = "Lambda function ARNs for invocation"
  type        = list(string)
  default     = []
}

# =============================================================================
# LOGGING
# =============================================================================

variable "log_retention_days" {
  description = "CloudWatch log retention (days)"
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
