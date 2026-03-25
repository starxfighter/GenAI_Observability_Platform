# IAM Module - Outputs

output "api_service_role_arn" {
  description = "API service role ARN"
  value       = aws_iam_role.api_service.arn
}

output "deployment_role_arn" {
  description = "Deployment role ARN"
  value       = aws_iam_role.deployment.arn
}

output "glue_role_arn" {
  description = "Glue ETL role ARN"
  value       = aws_iam_role.glue.arn
}

output "cross_region_role_arn" {
  description = "Cross-region role ARN"
  value       = aws_iam_role.cross_region.arn
}
