# VPC Flow Logs

# =============================================================================
# FLOW LOGS - TO CLOUDWATCH
# =============================================================================

resource "aws_flow_log" "main" {
  count = var.enable_flow_logs ? 1 : 0

  iam_role_arn    = aws_iam_role.flow_logs[0].arn
  log_destination = aws_cloudwatch_log_group.flow_logs[0].arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-flow-logs"
  })
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name              = "/aws/vpc/flow-logs/${var.name_prefix}"
  retention_in_days = var.flow_logs_retention_days

  tags = var.tags
}

# =============================================================================
# FLOW LOGS - TO S3 (Optional - for long-term storage)
# =============================================================================

resource "aws_flow_log" "s3" {
  count = var.enable_flow_logs && var.flow_logs_s3_bucket_arn != "" ? 1 : 0

  log_destination      = var.flow_logs_s3_bucket_arn
  log_destination_type = "s3"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.main.id

  destination_options {
    file_format        = "parquet"
    per_hour_partition = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-flow-logs-s3"
  })
}

# =============================================================================
# IAM ROLE FOR FLOW LOGS
# =============================================================================

resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name = "${var.name_prefix}-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name = "${var.name_prefix}-flow-logs-policy"
  role = aws_iam_role.flow_logs[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      }
    ]
  })
}

# =============================================================================
# CLOUDWATCH INSIGHTS QUERY (for easy analysis)
# =============================================================================

resource "aws_cloudwatch_query_definition" "rejected_traffic" {
  count = var.enable_flow_logs ? 1 : 0

  name = "${var.name_prefix}/VPC/Rejected-Traffic"

  log_group_names = [aws_cloudwatch_log_group.flow_logs[0].name]

  query_string = <<-EOF
    fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action
    | filter action = "REJECT"
    | sort @timestamp desc
    | limit 100
  EOF
}

resource "aws_cloudwatch_query_definition" "top_talkers" {
  count = var.enable_flow_logs ? 1 : 0

  name = "${var.name_prefix}/VPC/Top-Talkers"

  log_group_names = [aws_cloudwatch_log_group.flow_logs[0].name]

  query_string = <<-EOF
    fields srcAddr, dstAddr
    | stats sum(bytes) as totalBytes by srcAddr, dstAddr
    | sort totalBytes desc
    | limit 20
  EOF
}
