# API Gateway Module - Outputs

output "api_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.main.id
}

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "api_arn" {
  description = "API Gateway ARN"
  value       = aws_apigatewayv2_api.main.arn
}

output "execution_arn" {
  description = "API Gateway execution ARN"
  value       = aws_apigatewayv2_api.main.execution_arn
}

output "stage_name" {
  description = "API Gateway stage name"
  value       = aws_apigatewayv2_stage.main.name
}

output "stage_arn" {
  description = "API Gateway stage ARN"
  value       = aws_apigatewayv2_stage.main.arn
}

output "custom_domain_name" {
  description = "Custom domain name"
  value       = var.domain_name != "" ? aws_apigatewayv2_domain_name.main[0].domain_name : null
}

output "custom_domain_target" {
  description = "Custom domain target for DNS"
  value       = var.domain_name != "" ? aws_apigatewayv2_domain_name.main[0].domain_name_configuration[0].target_domain_name : null
}
