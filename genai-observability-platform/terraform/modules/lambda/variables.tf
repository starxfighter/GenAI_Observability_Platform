# Lambda Module - Variables

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

variable "subnet_ids" {
  description = "Subnet IDs for Lambda VPC config"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs for Lambda"
  type        = list(string)
}

variable "dynamodb_table_arns" {
  description = "DynamoDB table ARNs"
  type        = list(string)
}

variable "timestream_table_arn" {
  description = "Timestream table ARN"
  type        = string
}

variable "opensearch_endpoint" {
  description = "OpenSearch endpoint"
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

variable "secrets_manager_arns" {
  description = "Secrets Manager ARNs"
  type        = list(string)
}

variable "anthropic_api_key_secret_arn" {
  description = "Anthropic API key secret ARN"
  type        = string
}

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
