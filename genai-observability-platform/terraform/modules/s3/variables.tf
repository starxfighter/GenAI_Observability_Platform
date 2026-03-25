# S3 Module - Variables

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

variable "enable_replication" {
  description = "Enable cross-region replication"
  type        = bool
  default     = false
}

variable "replication_region" {
  description = "Replication destination region"
  type        = string
  default     = ""
}

variable "archive_after_days" {
  description = "Days before archiving to Glacier"
  type        = number
  default     = 90
}

variable "expire_after_days" {
  description = "Days before expiring objects"
  type        = number
  default     = 365
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
