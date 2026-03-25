# EventBridge Module - Outputs

output "event_bus_name" {
  description = "Event bus name"
  value       = aws_cloudwatch_event_bus.main.name
}

output "event_bus_arn" {
  description = "Event bus ARN"
  value       = aws_cloudwatch_event_bus.main.arn
}

output "rule_arns" {
  description = "Event rule ARNs"
  value = {
    anomaly_detected     = aws_cloudwatch_event_rule.anomaly_detected.arn
    alert_created        = aws_cloudwatch_event_rule.alert_created.arn
    remediation_approved = aws_cloudwatch_event_rule.remediation_approved.arn
    integration_sync     = aws_cloudwatch_event_rule.integration_sync.arn
    daily_report         = aws_cloudwatch_event_rule.daily_report.arn
  }
}

output "archive_name" {
  description = "Event archive name"
  value       = aws_cloudwatch_event_archive.main.name
}
