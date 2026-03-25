# Kinesis Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "shard_count" {
  description = "Number of shards (0 for on-demand)"
  type        = number
  default     = 2
}

variable "retention_period" {
  description = "Data retention period (hours)"
  type        = number
  default     = 24
}

variable "s3_bucket_arn" {
  description = "S3 bucket ARN for Firehose delivery"
  type        = string
  default     = ""
}

variable "enable_enhanced_fanout" {
  description = "Enable enhanced fan-out consumer"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
