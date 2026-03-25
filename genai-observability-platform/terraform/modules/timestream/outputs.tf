# Timestream Module - Outputs

output "database_name" {
  description = "Timestream database name"
  value       = aws_timestreamwrite_database.main.database_name
}

output "database_arn" {
  description = "Timestream database ARN"
  value       = aws_timestreamwrite_database.main.arn
}

output "table_name" {
  description = "Metrics table name"
  value       = aws_timestreamwrite_table.metrics.table_name
}

output "table_arn" {
  description = "Metrics table ARN"
  value       = aws_timestreamwrite_table.metrics.arn
}

output "events_table_name" {
  description = "Events table name"
  value       = aws_timestreamwrite_table.events.table_name
}

output "events_table_arn" {
  description = "Events table ARN"
  value       = aws_timestreamwrite_table.events.arn
}
