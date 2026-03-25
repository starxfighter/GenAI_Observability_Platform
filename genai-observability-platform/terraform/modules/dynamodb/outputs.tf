# DynamoDB Module - Outputs

output "table_names" {
  description = "DynamoDB table names"
  value = {
    traces         = aws_dynamodb_table.traces.name
    spans          = aws_dynamodb_table.spans.name
    agents         = aws_dynamodb_table.agents.name
    alerts         = aws_dynamodb_table.alerts.name
    investigations = aws_dynamodb_table.investigations.name
    remediations   = aws_dynamodb_table.remediations.name
    integrations   = aws_dynamodb_table.integrations.name
    api_keys       = aws_dynamodb_table.api_keys.name
    saved_queries  = aws_dynamodb_table.saved_queries.name
  }
}

output "table_arns" {
  description = "DynamoDB table ARNs"
  value = [
    aws_dynamodb_table.traces.arn,
    aws_dynamodb_table.spans.arn,
    aws_dynamodb_table.agents.arn,
    aws_dynamodb_table.alerts.arn,
    aws_dynamodb_table.investigations.arn,
    aws_dynamodb_table.remediations.arn,
    aws_dynamodb_table.integrations.arn,
    aws_dynamodb_table.api_keys.arn,
    aws_dynamodb_table.saved_queries.arn,
  ]
}

output "traces_table_name" {
  description = "Traces table name"
  value       = aws_dynamodb_table.traces.name
}

output "agents_table_name" {
  description = "Agents table name"
  value       = aws_dynamodb_table.agents.name
}

output "alerts_table_name" {
  description = "Alerts table name"
  value       = aws_dynamodb_table.alerts.name
}
