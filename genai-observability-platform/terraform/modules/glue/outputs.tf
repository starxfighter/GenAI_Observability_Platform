# Glue ETL Module - Outputs

output "database_name" {
  description = "Glue database name"
  value       = aws_glue_catalog_database.main.name
}

output "crawler_names" {
  description = "Glue crawler names"
  value = {
    events = aws_glue_crawler.events.name
    traces = aws_glue_crawler.traces.name
  }
}

output "job_names" {
  description = "Glue job names"
  value = {
    daily_aggregation = aws_glue_job.daily_aggregation.name
    anomaly_report    = aws_glue_job.anomaly_report.name
    data_compaction   = aws_glue_job.data_compaction.name
    cost_analysis     = aws_glue_job.cost_analysis.name
  }
}

output "workflow_name" {
  description = "Glue workflow name"
  value       = aws_glue_workflow.etl.name
}
