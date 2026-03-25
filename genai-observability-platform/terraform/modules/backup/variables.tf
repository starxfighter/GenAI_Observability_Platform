# AWS Backup Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "dynamodb_table_arns" {
  description = "DynamoDB table ARNs to backup"
  type        = list(string)
}

variable "rds_cluster_arn" {
  description = "RDS cluster ARN to backup"
  type        = string
  default     = ""
}

variable "efs_arns" {
  description = "EFS filesystem ARNs to backup"
  type        = list(string)
  default     = []
}

variable "daily_retention_days" {
  description = "Days to retain daily backups"
  type        = number
  default     = 7
}

variable "weekly_retention_days" {
  description = "Days to retain weekly backups"
  type        = number
  default     = 30
}

variable "monthly_retention_days" {
  description = "Days to retain monthly backups"
  type        = number
  default     = 365
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for backup notifications"
  type        = string
  default     = ""
}

variable "enable_vault_lock" {
  description = "Enable backup vault lock (compliance)"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
