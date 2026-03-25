# IAM Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "dynamodb_table_arns" {
  description = "DynamoDB table ARNs"
  type        = list(string)
}

variable "s3_bucket_arns" {
  description = "S3 bucket ARNs"
  type        = list(string)
}

variable "kinesis_stream_arns" {
  description = "Kinesis stream ARNs"
  type        = list(string)
}

variable "secrets_manager_arns" {
  description = "Secrets Manager ARNs"
  type        = list(string)
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
