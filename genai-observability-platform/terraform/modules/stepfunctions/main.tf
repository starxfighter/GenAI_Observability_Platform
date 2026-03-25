# Step Functions Module - Workflow Orchestration

# =============================================================================
# REMEDIATION WORKFLOW STATE MACHINE
# =============================================================================

resource "aws_sfn_state_machine" "remediation" {
  name     = "${var.name_prefix}-remediation-workflow"
  role_arn = aws_iam_role.stepfunctions.arn

  definition = jsonencode({
    Comment = "Autonomous remediation workflow with approval gates"
    StartAt = "GenerateRemediationPlan"
    States = {
      GenerateRemediationPlan = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.autonomous_remediation
          Payload = {
            "action"    = "generate_plan"
            "alert_id.$" = "$.alert_id"
            "anomaly.$"  = "$.anomaly"
          }
        }
        ResultPath = "$.plan"
        Next       = "CheckAutoApproval"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "NotifyFailure"
          ResultPath  = "$.error"
        }]
      }

      CheckAutoApproval = {
        Type = "Choice"
        Choices = [{
          Variable      = "$.plan.Payload.auto_approve"
          BooleanEquals = true
          Next          = "ExecuteRemediation"
        }]
        Default = "WaitForApproval"
      }

      WaitForApproval = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = var.lambda_arns.integration_hub
          Payload = {
            "action"      = "request_approval"
            "plan.$"      = "$.plan.Payload"
            "task_token.$" = "$$.Task.Token"
          }
        }
        ResultPath     = "$.approval"
        TimeoutSeconds = 86400  # 24 hours
        Next           = "CheckApprovalDecision"
        Catch = [{
          ErrorEquals = ["States.Timeout"]
          Next        = "ApprovalTimeout"
          ResultPath  = "$.error"
        }, {
          ErrorEquals = ["States.ALL"]
          Next        = "NotifyFailure"
          ResultPath  = "$.error"
        }]
      }

      CheckApprovalDecision = {
        Type = "Choice"
        Choices = [{
          Variable      = "$.approval.approved"
          BooleanEquals = true
          Next          = "ExecuteRemediation"
        }]
        Default = "RemediationRejected"
      }

      ExecuteRemediation = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.autonomous_remediation
          Payload = {
            "action"  = "execute"
            "plan.$"  = "$.plan.Payload"
          }
        }
        ResultPath = "$.execution"
        Next       = "VerifyRemediation"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "RollbackRemediation"
          ResultPath  = "$.error"
        }]
      }

      VerifyRemediation = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.autonomous_remediation
          Payload = {
            "action"        = "verify"
            "execution.$"   = "$.execution.Payload"
          }
        }
        ResultPath = "$.verification"
        Next       = "CheckVerificationResult"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "RollbackRemediation"
          ResultPath  = "$.error"
        }]
      }

      CheckVerificationResult = {
        Type = "Choice"
        Choices = [{
          Variable      = "$.verification.Payload.success"
          BooleanEquals = true
          Next          = "NotifySuccess"
        }]
        Default = "RollbackRemediation"
      }

      RollbackRemediation = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.autonomous_remediation
          Payload = {
            "action"      = "rollback"
            "execution.$" = "$.execution.Payload"
            "error.$"     = "$.error"
          }
        }
        ResultPath = "$.rollback"
        Next       = "NotifyRollback"
      }

      NotifySuccess = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.alert_router
          Payload = {
            "action"  = "notify"
            "type"    = "remediation_success"
            "data.$"  = "$"
          }
        }
        End = true
      }

      NotifyRollback = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.alert_router
          Payload = {
            "action"  = "notify"
            "type"    = "remediation_rollback"
            "data.$"  = "$"
          }
        }
        End = true
      }

      NotifyFailure = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.alert_router
          Payload = {
            "action"  = "notify"
            "type"    = "remediation_failure"
            "data.$"  = "$"
          }
        }
        End = true
      }

      RemediationRejected = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.alert_router
          Payload = {
            "action"  = "notify"
            "type"    = "remediation_rejected"
            "data.$"  = "$"
          }
        }
        End = true
      }

      ApprovalTimeout = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.alert_router
          Payload = {
            "action"  = "notify"
            "type"    = "approval_timeout"
            "data.$"  = "$"
          }
        }
        End = true
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.stepfunctions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-remediation-workflow"
  })
}

# =============================================================================
# INVESTIGATION WORKFLOW STATE MACHINE
# =============================================================================

resource "aws_sfn_state_machine" "investigation" {
  name     = "${var.name_prefix}-investigation-workflow"
  role_arn = aws_iam_role.stepfunctions.arn

  definition = jsonencode({
    Comment = "AI-powered investigation workflow"
    StartAt = "GatherContext"
    States = {
      GatherContext = {
        Type     = "Parallel"
        Branches = [
          {
            StartAt = "GetTraces"
            States = {
              GetTraces = {
                Type     = "Task"
                Resource = "arn:aws:states:::lambda:invoke"
                Parameters = {
                  FunctionName = var.lambda_arns.stream_processor
                  Payload = {
                    "action"    = "get_traces"
                    "agent_id.$" = "$.agent_id"
                    "time_range.$" = "$.time_range"
                  }
                }
                End = true
              }
            }
          },
          {
            StartAt = "GetMetrics"
            States = {
              GetMetrics = {
                Type     = "Task"
                Resource = "arn:aws:states:::lambda:invoke"
                Parameters = {
                  FunctionName = var.lambda_arns.anomaly_detector
                  Payload = {
                    "action"    = "get_metrics"
                    "agent_id.$" = "$.agent_id"
                    "time_range.$" = "$.time_range"
                  }
                }
                End = true
              }
            }
          },
          {
            StartAt = "GetRecentAlerts"
            States = {
              GetRecentAlerts = {
                Type     = "Task"
                Resource = "arn:aws:states:::lambda:invoke"
                Parameters = {
                  FunctionName = var.lambda_arns.alert_router
                  Payload = {
                    "action"    = "get_recent"
                    "agent_id.$" = "$.agent_id"
                  }
                }
                End = true
              }
            }
          }
        ]
        ResultPath = "$.context"
        Next       = "AnalyzeWithClaude"
      }

      AnalyzeWithClaude = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.llm_investigator
          Payload = {
            "action"    = "analyze"
            "anomaly.$" = "$.anomaly"
            "context.$" = "$.context"
          }
        }
        ResultPath = "$.analysis"
        Next       = "GenerateReport"
      }

      GenerateReport = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.llm_investigator
          Payload = {
            "action"     = "generate_report"
            "analysis.$" = "$.analysis.Payload"
          }
        }
        ResultPath = "$.report"
        Next       = "StoreInvestigation"
      }

      StoreInvestigation = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:putItem"
        Parameters = {
          TableName = var.investigations_table
          Item = {
            "investigation_id" = { "S.$" = "$.investigation_id" }
            "alert_id"         = { "S.$" = "$.alert_id" }
            "status"           = { "S" = "completed" }
            "analysis"         = { "S.$" = "States.JsonToString($.analysis.Payload)" }
            "report"           = { "S.$" = "States.JsonToString($.report.Payload)" }
            "created_at"       = { "S.$" = "$$.State.EnteredTime" }
          }
        }
        ResultPath = "$.stored"
        Next       = "NotifyComplete"
      }

      NotifyComplete = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.lambda_arns.alert_router
          Payload = {
            "action" = "notify"
            "type"   = "investigation_complete"
            "data.$" = "$"
          }
        }
        End = true
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.stepfunctions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-investigation-workflow"
  })
}

# =============================================================================
# CLOUDWATCH LOG GROUP
# =============================================================================

resource "aws_cloudwatch_log_group" "stepfunctions" {
  name              = "/aws/stepfunctions/${var.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# =============================================================================
# IAM ROLE FOR STEP FUNCTIONS
# =============================================================================

resource "aws_iam_role" "stepfunctions" {
  name = "${var.name_prefix}-stepfunctions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "stepfunctions" {
  name = "${var.name_prefix}-stepfunctions-policy"
  role = aws_iam_role.stepfunctions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = values(var.lambda_arns)
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [var.investigations_table_arn]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}
