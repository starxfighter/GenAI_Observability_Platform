# Glue ETL Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "glue_role_arn" {
  description = "IAM role ARN for Glue jobs"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name for data"
  type        = string
}

variable "scripts_bucket" {
  description = "S3 bucket for Glue scripts"
  type        = string
}

variable "timestream_database" {
  description = "Timestream database name"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
