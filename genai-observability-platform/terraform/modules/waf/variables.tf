# WAF Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "rate_limit" {
  description = "Rate limit for requests per 5 minutes per IP"
  type        = number
  default     = 2000
}

variable "api_rate_limit" {
  description = "Rate limit for API requests per 5 minutes per IP"
  type        = number
  default     = 10000
}

variable "blocked_countries" {
  description = "List of country codes to block"
  type        = list(string)
  default     = []
}

variable "alb_arn" {
  description = "ALB ARN to associate with WAF"
  type        = string
  default     = ""
}

variable "api_gateway_stage_arn" {
  description = "API Gateway stage ARN to associate with WAF"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
