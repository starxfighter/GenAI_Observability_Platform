# EventBridge Module - Variables

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
    llm_investigator       = string
    alert_router           = string
    autonomous_remediation = string
    integration_hub        = string
    nl_query               = string
  })
}

variable "step_functions_arn" {
  description = "Step Functions state machine ARN"
  type        = string
  default     = ""
}

variable "archive_retention_days" {
  description = "Event archive retention days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
