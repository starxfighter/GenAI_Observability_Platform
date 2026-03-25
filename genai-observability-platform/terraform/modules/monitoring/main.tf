# Monitoring Module - CloudWatch Alarms and Dashboards

# =============================================================================
# SNS TOPICS
# =============================================================================

resource "aws_sns_topic" "alerts" {
  name = "${var.name_prefix}-alerts"

  tags = var.tags
}

resource "aws_sns_topic_subscription" "email" {
  count = var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_sns_topic_subscription" "slack" {
  count = var.slack_webhook_url != "" ? 1 : 0

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}

# =============================================================================
# LAMBDA ALARMS
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = toset(values(var.lambda_function_names))

  alarm_name          = "${var.name_prefix}-${each.value}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.lambda_error_threshold
  alarm_description   = "Lambda function ${each.value} error rate"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.value
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = toset(values(var.lambda_function_names))

  alarm_name          = "${var.name_prefix}-${each.value}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 30000 # 30 seconds
  alarm_description   = "Lambda function ${each.value} duration"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.value
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# =============================================================================
# API GATEWAY ALARMS
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "${var.name_prefix}-api-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "API Gateway 5XX errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = var.api_gateway_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_latency" {
  alarm_name          = "${var.name_prefix}-api-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "p95"
  threshold           = var.api_latency_threshold_ms
  alarm_description   = "API Gateway p95 latency"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = var.api_gateway_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# =============================================================================
# DYNAMODB ALARMS
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  for_each = toset(values(var.dynamodb_table_names))

  alarm_name          = "${var.name_prefix}-${each.value}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = var.dynamodb_throttle_threshold
  alarm_description   = "DynamoDB table ${each.value} throttles"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = each.value
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# =============================================================================
# KINESIS ALARMS
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age" {
  alarm_name          = "${var.name_prefix}-kinesis-iterator-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = 300
  statistic           = "Maximum"
  threshold           = 60000 # 1 minute
  alarm_description   = "Kinesis iterator age (processing lag)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StreamName = var.kinesis_stream_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# =============================================================================
# OPENSEARCH ALARMS
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "opensearch_cluster_status" {
  alarm_name          = "${var.name_prefix}-opensearch-cluster-status"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ClusterStatus.green"
  namespace           = "AWS/ES"
  period              = 300
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "OpenSearch cluster not green"
  treat_missing_data  = "breaching"

  dimensions = {
    DomainName = var.opensearch_domain
    ClientId   = data.aws_caller_identity.current.account_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "opensearch_storage" {
  alarm_name          = "${var.name_prefix}-opensearch-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/ES"
  period              = 300
  statistic           = "Minimum"
  threshold           = 10000 # 10 GB
  alarm_description   = "OpenSearch free storage low"
  treat_missing_data  = "breaching"

  dimensions = {
    DomainName = var.opensearch_domain
    ClientId   = data.aws_caller_identity.current.account_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# =============================================================================
# RDS ALARMS
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.name_prefix}-rds-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBClusterIdentifier = var.rds_cluster_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${var.name_prefix}-rds-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 100
  alarm_description   = "RDS connection count high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBClusterIdentifier = var.rds_cluster_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# =============================================================================
# CLOUDWATCH DASHBOARD
# =============================================================================

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 1
        properties = {
          markdown = "# GenAI Observability Platform - ${var.environment}"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 1
        width  = 8
        height = 6
        properties = {
          title  = "API Gateway Requests"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", var.api_gateway_id, { stat = "Sum" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 1
        width  = 8
        height = 6
        properties = {
          title  = "API Gateway Latency"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiId", var.api_gateway_id, { stat = "p50" }],
            ["...", { stat = "p95" }],
            ["...", { stat = "p99" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 1
        width  = 8
        height = 6
        properties = {
          title  = "API Gateway Errors"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/ApiGateway", "4XXError", "ApiId", var.api_gateway_id, { stat = "Sum" }],
            [".", "5XXError", ".", ".", { stat = "Sum" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 7
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Invocations"
          region = data.aws_region.current.name
          metrics = [
            for name in values(var.lambda_function_names) :
            ["AWS/Lambda", "Invocations", "FunctionName", name, { stat = "Sum" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 7
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Errors"
          region = data.aws_region.current.name
          metrics = [
            for name in values(var.lambda_function_names) :
            ["AWS/Lambda", "Errors", "FunctionName", name, { stat = "Sum" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 13
        width  = 8
        height = 6
        properties = {
          title  = "Kinesis Records"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/Kinesis", "IncomingRecords", "StreamName", var.kinesis_stream_name, { stat = "Sum" }],
            [".", "GetRecords.Records", ".", ".", { stat = "Sum" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 13
        width  = 8
        height = 6
        properties = {
          title  = "DynamoDB Consumed Capacity"
          region = data.aws_region.current.name
          metrics = [
            for name in values(var.dynamodb_table_names) :
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", name, { stat = "Sum" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 13
        width  = 8
        height = 6
        properties = {
          title  = "RDS Performance"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBClusterIdentifier", var.rds_cluster_id, { stat = "Average" }],
            [".", "DatabaseConnections", ".", ".", { stat = "Average" }]
          ]
          period = 300
        }
      }
    ]
  })
}

# =============================================================================
# DATA SOURCES
# =============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
