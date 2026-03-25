# Kinesis Module - Event Streaming

# =============================================================================
# EVENTS STREAM
# =============================================================================

resource "aws_kinesis_stream" "events" {
  name             = "${var.name_prefix}-events"
  retention_period = var.retention_period

  stream_mode_details {
    stream_mode = var.shard_count > 0 ? "PROVISIONED" : "ON_DEMAND"
  }

  shard_count = var.shard_count > 0 ? var.shard_count : null

  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-events"
  })
}

# =============================================================================
# FIREHOSE DELIVERY STREAM (to S3)
# =============================================================================

resource "aws_kinesis_firehose_delivery_stream" "s3" {
  name        = "${var.name_prefix}-events-to-s3"
  destination = "extended_s3"

  kinesis_source_configuration {
    kinesis_stream_arn = aws_kinesis_stream.events.arn
    role_arn           = aws_iam_role.firehose.arn
  }

  extended_s3_configuration {
    role_arn            = aws_iam_role.firehose.arn
    bucket_arn          = var.s3_bucket_arn
    prefix              = "events/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
    error_output_prefix = "errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"

    buffering_size     = 64
    buffering_interval = 60

    compression_format = "GZIP"

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose.name
      log_stream_name = "S3Delivery"
    }

    processing_configuration {
      enabled = true

      processors {
        type = "RecordDeAggregation"

        parameters {
          parameter_name  = "SubRecordType"
          parameter_value = "JSON"
        }
      }
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-events-to-s3"
  })
}

# =============================================================================
# IAM ROLE FOR FIREHOSE
# =============================================================================

resource "aws_iam_role" "firehose" {
  name = "${var.name_prefix}-firehose"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "firehose.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "firehose" {
  name = "${var.name_prefix}-firehose"
  role = aws_iam_role.firehose.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords",
          "kinesis:ListShards"
        ]
        Resource = [aws_kinesis_stream.events.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:AbortMultipartUpload",
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
          "s3:PutObject"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents"
        ]
        Resource = ["${aws_cloudwatch_log_group.firehose.arn}:*"]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = ["*"]
        Condition = {
          StringEquals = {
            "kms:ViaService" = "kinesis.${data.aws_region.current.name}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# =============================================================================
# CLOUDWATCH LOG GROUP
# =============================================================================

resource "aws_cloudwatch_log_group" "firehose" {
  name              = "/aws/kinesisfirehose/${var.name_prefix}-events-to-s3"
  retention_in_days = 14

  tags = var.tags
}

# =============================================================================
# ENHANCED FAN-OUT CONSUMER (Optional)
# =============================================================================

resource "aws_kinesis_stream_consumer" "lambda" {
  count = var.enable_enhanced_fanout ? 1 : 0

  name       = "${var.name_prefix}-lambda-consumer"
  stream_arn = aws_kinesis_stream.events.arn
}

# =============================================================================
# DATA SOURCES
# =============================================================================

data "aws_region" "current" {}
