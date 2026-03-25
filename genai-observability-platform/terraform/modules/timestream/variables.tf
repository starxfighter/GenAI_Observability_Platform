# Timestream Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "memory_retention_hours" {
  description = "Hours to retain data in memory store"
  type        = number
  default     = 24
}

variable "magnetic_retention_days" {
  description = "Days to retain data in magnetic store"
  type        = number
  default     = 365
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
