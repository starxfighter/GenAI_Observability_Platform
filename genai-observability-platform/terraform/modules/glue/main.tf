# Glue ETL Module - Batch Processing Jobs

# =============================================================================
# GLUE DATABASE
# =============================================================================

resource "aws_glue_catalog_database" "main" {
  name        = replace("${var.name_prefix}-observability", "-", "_")
  description = "GenAI Observability Platform data catalog"
}

# =============================================================================
# GLUE CRAWLER - S3 Data
# =============================================================================

resource "aws_glue_crawler" "events" {
  name          = "${var.name_prefix}-events-crawler"
  database_name = aws_glue_catalog_database.main.name
  role          = var.glue_role_arn
  schedule      = "cron(0 1 * * ? *)"  # Daily at 1 AM UTC

  s3_target {
    path = "s3://${var.s3_bucket_name}/events/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
    }
  })

  tags = var.tags
}

resource "aws_glue_crawler" "traces" {
  name          = "${var.name_prefix}-traces-crawler"
  database_name = aws_glue_catalog_database.main.name
  role          = var.glue_role_arn
  schedule      = "cron(0 1 * * ? *)"

  s3_target {
    path = "s3://${var.s3_bucket_name}/traces/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  tags = var.tags
}

# =============================================================================
# GLUE JOB - DAILY AGGREGATION
# =============================================================================

resource "aws_glue_job" "daily_aggregation" {
  name     = "${var.name_prefix}-daily-aggregation"
  role_arn = var.glue_role_arn

  glue_version      = "4.0"
  worker_type       = var.environment == "prod" ? "G.1X" : "G.025X"
  number_of_workers = var.environment == "prod" ? 4 : 2

  command {
    name            = "glueetl"
    script_location = "s3://${var.scripts_bucket}/glue/daily_aggregation.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--TempDir"                          = "s3://${var.s3_bucket_name}/temp/"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://${var.s3_bucket_name}/spark-logs/"
    "--SOURCE_DATABASE"                  = aws_glue_catalog_database.main.name
    "--TARGET_BUCKET"                    = var.s3_bucket_name
    "--ENVIRONMENT"                      = var.environment
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = var.tags
}

# =============================================================================
# GLUE JOB - ANOMALY REPORT GENERATION
# =============================================================================

resource "aws_glue_job" "anomaly_report" {
  name     = "${var.name_prefix}-anomaly-report"
  role_arn = var.glue_role_arn

  glue_version      = "4.0"
  worker_type       = "G.025X"
  number_of_workers = 2

  command {
    name            = "glueetl"
    script_location = "s3://${var.scripts_bucket}/glue/anomaly_report.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://${var.s3_bucket_name}/temp/"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--SOURCE_DATABASE"                  = aws_glue_catalog_database.main.name
    "--TARGET_BUCKET"                    = var.s3_bucket_name
    "--TIMESTREAM_DATABASE"              = var.timestream_database
    "--ENVIRONMENT"                      = var.environment
  }

  tags = var.tags
}

# =============================================================================
# GLUE JOB - DATA COMPACTION
# =============================================================================

resource "aws_glue_job" "data_compaction" {
  name     = "${var.name_prefix}-data-compaction"
  role_arn = var.glue_role_arn

  glue_version      = "4.0"
  worker_type       = var.environment == "prod" ? "G.1X" : "G.025X"
  number_of_workers = var.environment == "prod" ? 4 : 2

  command {
    name            = "glueetl"
    script_location = "s3://${var.scripts_bucket}/glue/data_compaction.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--TempDir"                          = "s3://${var.s3_bucket_name}/temp/"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--SOURCE_BUCKET"                    = var.s3_bucket_name
    "--TARGET_BUCKET"                    = var.s3_bucket_name
    "--ENVIRONMENT"                      = var.environment
  }

  tags = var.tags
}

# =============================================================================
# GLUE JOB - COST ANALYSIS
# =============================================================================

resource "aws_glue_job" "cost_analysis" {
  name     = "${var.name_prefix}-cost-analysis"
  role_arn = var.glue_role_arn

  glue_version      = "4.0"
  worker_type       = "G.025X"
  number_of_workers = 2

  command {
    name            = "glueetl"
    script_location = "s3://${var.scripts_bucket}/glue/cost_analysis.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://${var.s3_bucket_name}/temp/"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--SOURCE_DATABASE"                  = aws_glue_catalog_database.main.name
    "--TARGET_BUCKET"                    = var.s3_bucket_name
    "--ENVIRONMENT"                      = var.environment
  }

  tags = var.tags
}

# =============================================================================
# GLUE TRIGGERS
# =============================================================================

resource "aws_glue_trigger" "daily_aggregation" {
  name     = "${var.name_prefix}-daily-trigger"
  type     = "SCHEDULED"
  schedule = "cron(0 2 * * ? *)"  # 2 AM UTC daily

  actions {
    job_name = aws_glue_job.daily_aggregation.name
  }

  tags = var.tags
}

resource "aws_glue_trigger" "weekly_compaction" {
  name     = "${var.name_prefix}-weekly-compaction"
  type     = "SCHEDULED"
  schedule = "cron(0 4 ? * SUN *)"  # 4 AM UTC Sundays

  actions {
    job_name = aws_glue_job.data_compaction.name
  }

  tags = var.tags
}

# =============================================================================
# GLUE WORKFLOW
# =============================================================================

resource "aws_glue_workflow" "etl" {
  name        = "${var.name_prefix}-etl-workflow"
  description = "Daily ETL workflow for observability data"

  tags = var.tags
}
