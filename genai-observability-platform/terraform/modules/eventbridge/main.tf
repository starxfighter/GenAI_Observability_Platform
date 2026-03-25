# EventBridge Module - Event-Driven Architecture

# =============================================================================
# EVENT BUS
# =============================================================================

resource "aws_cloudwatch_event_bus" "main" {
  name = "${var.name_prefix}-events"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-events"
  })
}

# =============================================================================
# EVENT RULES - ANOMALY DETECTED
# =============================================================================

resource "aws_cloudwatch_event_rule" "anomaly_detected" {
  name           = "${var.name_prefix}-anomaly-detected"
  description    = "Triggered when an anomaly is detected"
  event_bus_name = aws_cloudwatch_event_bus.main.name

  event_pattern = jsonencode({
    source      = ["genai.observability"]
    detail-type = ["Anomaly Detected"]
  })

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "anomaly_to_investigator" {
  rule           = aws_cloudwatch_event_rule.anomaly_detected.name
  event_bus_name = aws_cloudwatch_event_bus.main.name
  target_id      = "invoke-investigator"
  arn            = var.lambda_arns.llm_investigator

  input_transformer {
    input_paths = {
      anomalyId   = "$.detail.anomaly_id"
      agentId     = "$.detail.agent_id"
      severity    = "$.detail.severity"
      description = "$.detail.description"
    }
    input_template = <<-EOF
      {
        "action": "investigate",
        "anomaly_id": <anomalyId>,
        "agent_id": <agentId>,
        "severity": <severity>,
        "description": <description>
      }
    EOF
  }
}

# =============================================================================
# EVENT RULES - ALERT CREATED
# =============================================================================

resource "aws_cloudwatch_event_rule" "alert_created" {
  name           = "${var.name_prefix}-alert-created"
  description    = "Triggered when a new alert is created"
  event_bus_name = aws_cloudwatch_event_bus.main.name

  event_pattern = jsonencode({
    source      = ["genai.observability"]
    detail-type = ["Alert Created"]
  })

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "alert_to_router" {
  rule           = aws_cloudwatch_event_rule.alert_created.name
  event_bus_name = aws_cloudwatch_event_bus.main.name
  target_id      = "invoke-alert-router"
  arn            = var.lambda_arns.alert_router
}

# =============================================================================
# EVENT RULES - REMEDIATION APPROVED
# =============================================================================

resource "aws_cloudwatch_event_rule" "remediation_approved" {
  name           = "${var.name_prefix}-remediation-approved"
  description    = "Triggered when a remediation is approved"
  event_bus_name = aws_cloudwatch_event_bus.main.name

  event_pattern = jsonencode({
    source      = ["genai.observability"]
    detail-type = ["Remediation Approved"]
  })

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "remediation_to_executor" {
  rule           = aws_cloudwatch_event_rule.remediation_approved.name
  event_bus_name = aws_cloudwatch_event_bus.main.name
  target_id      = "invoke-remediation"
  arn            = var.lambda_arns.autonomous_remediation
}

# Step Functions for complex remediation workflows
resource "aws_cloudwatch_event_target" "remediation_to_stepfunctions" {
  count = var.step_functions_arn != "" ? 1 : 0

  rule           = aws_cloudwatch_event_rule.remediation_approved.name
  event_bus_name = aws_cloudwatch_event_bus.main.name
  target_id      = "start-remediation-workflow"
  arn            = var.step_functions_arn
  role_arn       = aws_iam_role.eventbridge.arn
}

# =============================================================================
# EVENT RULES - INTEGRATION SYNC
# =============================================================================

resource "aws_cloudwatch_event_rule" "integration_sync" {
  name                = "${var.name_prefix}-integration-sync"
  description         = "Scheduled sync with external integrations"
  schedule_expression = "rate(5 minutes)"

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "sync_to_integration_hub" {
  rule      = aws_cloudwatch_event_rule.integration_sync.name
  target_id = "invoke-integration-hub"
  arn       = var.lambda_arns.integration_hub

  input = jsonencode({
    action = "sync_all"
  })
}

# =============================================================================
# EVENT RULES - DAILY REPORT
# =============================================================================

resource "aws_cloudwatch_event_rule" "daily_report" {
  name                = "${var.name_prefix}-daily-report"
  description         = "Generate daily observability report"
  schedule_expression = "cron(0 8 * * ? *)"  # 8 AM UTC daily

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "daily_report_to_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_report.name
  target_id = "generate-daily-report"
  arn       = var.lambda_arns.nl_query

  input = jsonencode({
    action = "generate_daily_report"
  })
}

# =============================================================================
# EVENT ARCHIVE
# =============================================================================

resource "aws_cloudwatch_event_archive" "main" {
  name             = "${var.name_prefix}-archive"
  event_source_arn = aws_cloudwatch_event_bus.main.arn
  retention_days   = var.archive_retention_days

  event_pattern = jsonencode({
    source = ["genai.observability"]
  })
}

# =============================================================================
# LAMBDA PERMISSIONS
# =============================================================================

resource "aws_lambda_permission" "eventbridge_investigator" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_arns.llm_investigator
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.anomaly_detected.arn
}

resource "aws_lambda_permission" "eventbridge_alert_router" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_arns.alert_router
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.alert_created.arn
}

resource "aws_lambda_permission" "eventbridge_remediation" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_arns.autonomous_remediation
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.remediation_approved.arn
}

resource "aws_lambda_permission" "eventbridge_integration" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_arns.integration_hub
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.integration_sync.arn
}

resource "aws_lambda_permission" "eventbridge_nl_query" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_arns.nl_query
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_report.arn
}

# =============================================================================
# IAM ROLE FOR EVENTBRIDGE
# =============================================================================

resource "aws_iam_role" "eventbridge" {
  name = "${var.name_prefix}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "eventbridge" {
  name = "${var.name_prefix}-eventbridge-policy"
  role = aws_iam_role.eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = var.step_functions_arn != "" ? [var.step_functions_arn] : ["*"]
      }
    ]
  })
}
