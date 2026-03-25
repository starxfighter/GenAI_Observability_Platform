# Secrets Module - Outputs

output "anthropic_secret_arn" {
  description = "Anthropic API key secret ARN"
  value       = aws_secretsmanager_secret.anthropic.arn
}

output "slack_secret_arn" {
  description = "Slack webhook secret ARN"
  value       = var.slack_webhook_url != "" ? aws_secretsmanager_secret.slack[0].arn : null
}

output "pagerduty_secret_arn" {
  description = "PagerDuty key secret ARN"
  value       = var.pagerduty_key != "" ? aws_secretsmanager_secret.pagerduty[0].arn : null
}

output "database_secret_arn" {
  description = "Database credentials secret ARN"
  value       = aws_secretsmanager_secret.database.arn
}

output "opensearch_secret_arn" {
  description = "OpenSearch credentials secret ARN"
  value       = aws_secretsmanager_secret.opensearch.arn
}

output "jwt_secret_arn" {
  description = "JWT secret ARN"
  value       = aws_secretsmanager_secret.jwt.arn
}

output "all_secret_arns" {
  description = "All secret ARNs"
  value = compact([
    aws_secretsmanager_secret.anthropic.arn,
    var.slack_webhook_url != "" ? aws_secretsmanager_secret.slack[0].arn : "",
    var.pagerduty_key != "" ? aws_secretsmanager_secret.pagerduty[0].arn : "",
    aws_secretsmanager_secret.database.arn,
    aws_secretsmanager_secret.opensearch.arn,
    aws_secretsmanager_secret.jwt.arn,
  ])
}
