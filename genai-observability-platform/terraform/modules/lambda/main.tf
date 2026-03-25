# Lambda Module - Serverless Functions

locals {
  lambda_functions = {
    stream_processor = {
      description = "Process incoming events from Kinesis"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 512
      timeout     = 60
      source_dir  = "stream_processor"
    }
    anomaly_detector = {
      description = "Detect anomalies in metrics"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 1024
      timeout     = 120
      source_dir  = "anomaly_detector"
    }
    llm_investigator = {
      description = "AI-powered investigation using Claude"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 2048
      timeout     = 300
      source_dir  = "llm_investigator"
    }
    alert_router = {
      description = "Route alerts to notification channels"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 256
      timeout     = 30
      source_dir  = "alert_router"
    }
    autonomous_remediation = {
      description = "Execute autonomous remediation actions"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 1024
      timeout     = 300
      source_dir  = "autonomous_remediation"
    }
    integration_hub = {
      description = "Manage third-party integrations"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 512
      timeout     = 60
      source_dir  = "integration_hub"
    }
    nl_query = {
      description = "Natural language query processor"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 2048
      timeout     = 120
      source_dir  = "nl_query"
    }
    pii_redaction = {
      description = "Redact PII from data"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 512
      timeout     = 60
      source_dir  = "pii_redaction"
    }
    slack_formatter = {
      description = "Format alerts for Slack"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 256
      timeout     = 30
      source_dir  = "slack_formatter"
    }
    pagerduty_formatter = {
      description = "Format alerts for PagerDuty"
      handler     = "handler.lambda_handler"
      runtime     = "python3.11"
      memory      = 256
      timeout     = 30
      source_dir  = "pagerduty_formatter"
    }
  }

  common_environment = {
    ENVIRONMENT            = var.environment
    LOG_LEVEL              = var.environment == "prod" ? "INFO" : "DEBUG"
    OPENSEARCH_ENDPOINT    = var.opensearch_endpoint
    ANTHROPIC_SECRET_ARN   = var.anthropic_api_key_secret_arn
  }
}

# =============================================================================
# IAM ROLE FOR LAMBDA
# =============================================================================

resource "aws_iam_role" "lambda" {
  name = "${var.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "lambda" {
  name = "${var.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = var.dynamodb_table_arns
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [for arn in var.dynamodb_table_arns : "${arn}/index/*"]
      },
      {
        Effect = "Allow"
        Action = [
          "timestream:WriteRecords",
          "timestream:DescribeEndpoints"
        ]
        Resource = [var.timestream_table_arn]
      },
      {
        Effect = "Allow"
        Action = [
          "timestream:DescribeEndpoints"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:ListShards",
          "kinesis:ListStreams",
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ]
        Resource = [var.kinesis_stream_arn]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = ["${var.s3_bucket_arn}/*"]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = var.secrets_manager_arns
      },
      {
        Effect = "Allow"
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpDelete"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:UpdateService"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# =============================================================================
# LAMBDA FUNCTIONS
# =============================================================================

resource "aws_lambda_function" "functions" {
  for_each = local.lambda_functions

  function_name = "${var.name_prefix}-${each.key}"
  description   = each.value.description
  role          = aws_iam_role.lambda.arn
  handler       = each.value.handler
  runtime       = each.value.runtime
  memory_size   = each.value.memory
  timeout       = each.value.timeout

  filename         = data.archive_file.lambda[each.key].output_path
  source_code_hash = data.archive_file.lambda[each.key].output_base64sha256

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  environment {
    variables = merge(local.common_environment, {
      FUNCTION_NAME = each.key
    })
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}"
    Function = each.key
  })
}

# =============================================================================
# LAMBDA ARCHIVES (placeholder - replace with actual deployment packages)
# =============================================================================

data "archive_file" "lambda" {
  for_each = local.lambda_functions

  type        = "zip"
  output_path = "${path.module}/archives/${each.key}.zip"

  source {
    content  = <<-EOF
      def lambda_handler(event, context):
          """Placeholder handler - deploy actual code via CI/CD"""
          return {"statusCode": 200, "body": "Placeholder for ${each.key}"}
    EOF
    filename = "handler.py"
  }
}

# =============================================================================
# CLOUDWATCH LOG GROUPS
# =============================================================================

resource "aws_cloudwatch_log_group" "lambda" {
  for_each = local.lambda_functions

  name              = "/aws/lambda/${var.name_prefix}-${each.key}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# =============================================================================
# KINESIS EVENT SOURCE MAPPING
# =============================================================================

resource "aws_lambda_event_source_mapping" "kinesis" {
  event_source_arn  = var.kinesis_stream_arn
  function_name     = aws_lambda_function.functions["stream_processor"].arn
  starting_position = "LATEST"
  batch_size        = 100

  maximum_batching_window_in_seconds = 5
  parallelization_factor             = 10
  maximum_retry_attempts             = 3

  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.dlq.arn
    }
  }
}

# =============================================================================
# DEAD LETTER QUEUE
# =============================================================================

resource "aws_sqs_queue" "dlq" {
  name = "${var.name_prefix}-lambda-dlq"

  message_retention_seconds = 1209600 # 14 days

  tags = var.tags
}

resource "aws_iam_role_policy" "lambda_sqs" {
  name = "${var.name_prefix}-lambda-sqs"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = [aws_sqs_queue.dlq.arn]
      }
    ]
  })
}
