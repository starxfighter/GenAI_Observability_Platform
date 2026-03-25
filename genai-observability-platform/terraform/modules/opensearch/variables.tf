# OpenSearch Module - Variables

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
  description = "Subnet IDs"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "instance_type" {
  description = "Instance type"
  type        = string
  default     = "t3.medium.search"
}

variable "instance_count" {
  description = "Number of instances"
  type        = number
  default     = 2
}

variable "volume_size" {
  description = "EBS volume size (GB)"
  type        = number
  default     = 100
}

variable "master_user_name" {
  description = "Master username"
  type        = string
}

variable "master_user_password" {
  description = "Master password"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
