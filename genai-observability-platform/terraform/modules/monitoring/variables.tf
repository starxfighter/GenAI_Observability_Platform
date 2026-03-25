# Monitoring Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "lambda_function_names" {
  description = "Map of Lambda function names"
  type        = map(string)
}

variable "api_gateway_id" {
  description = "API Gateway ID"
  type        = string
}

variable "dynamodb_table_names" {
  description = "Map of DynamoDB table names"
  type        = map(string)
}

variable "kinesis_stream_name" {
  description = "Kinesis stream name"
  type        = string
}

variable "opensearch_domain" {
  description = "OpenSearch domain name"
  type        = string
}

variable "rds_cluster_id" {
  description = "RDS cluster identifier"
  type        = string
}

variable "alert_email" {
  description = "Email for alerts"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL"
  type        = string
  default     = ""
}

variable "pagerduty_endpoint" {
  description = "PagerDuty endpoint"
  type        = string
  default     = ""
}

variable "lambda_error_threshold" {
  description = "Lambda error threshold"
  type        = number
  default     = 10
}

variable "api_latency_threshold_ms" {
  description = "API latency threshold (ms)"
  type        = number
  default     = 1000
}

variable "dynamodb_throttle_threshold" {
  description = "DynamoDB throttle threshold"
  type        = number
  default     = 5
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
