# Step Functions Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "lambda_arns" {
  description = "Map of Lambda function ARNs"
  type = object({
    autonomous_remediation = string
    llm_investigator       = string
    alert_router           = string
    integration_hub        = string
    stream_processor       = string
    anomaly_detector       = string
  })
}

variable "investigations_table" {
  description = "DynamoDB investigations table name"
  type        = string
}

variable "investigations_table_arn" {
  description = "DynamoDB investigations table ARN"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention days"
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
