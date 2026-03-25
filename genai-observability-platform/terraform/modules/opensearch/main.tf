# OpenSearch Module - Search and Analytics Cluster

# =============================================================================
# OPENSEARCH DOMAIN
# =============================================================================

resource "aws_opensearch_domain" "main" {
  domain_name    = "${var.name_prefix}-search"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type            = var.instance_type
    instance_count           = var.instance_count
    zone_awareness_enabled   = var.instance_count > 1
    dedicated_master_enabled = var.instance_count >= 3

    dynamic "zone_awareness_config" {
      for_each = var.instance_count > 1 ? [1] : []
      content {
        availability_zone_count = min(var.instance_count, 3)
      }
    }

    dynamic "dedicated_master_config" {
      for_each = var.instance_count >= 3 ? [1] : []
      content {
        dedicated_master_enabled = true
        dedicated_master_type    = var.instance_type
        dedicated_master_count   = 3
      }
    }
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.volume_size
    throughput  = 125
    iops        = 3000
  }

  vpc_options {
    subnet_ids         = slice(var.subnet_ids, 0, min(length(var.subnet_ids), var.instance_count > 1 ? 2 : 1))
    security_group_ids = var.security_group_ids
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = var.master_user_name
      master_user_password = var.master_user_password
    }
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch.arn
    log_type                 = "INDEX_SLOW_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch.arn
    log_type                 = "SEARCH_SLOW_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch.arn
    log_type                 = "ES_APPLICATION_LOGS"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-search"
  })

  depends_on = [aws_cloudwatch_log_resource_policy.opensearch]
}

# =============================================================================
# CLOUDWATCH LOG GROUP
# =============================================================================

resource "aws_cloudwatch_log_group" "opensearch" {
  name              = "/aws/opensearch/${var.name_prefix}-search"
  retention_in_days = 14

  tags = var.tags
}

resource "aws_cloudwatch_log_resource_policy" "opensearch" {
  policy_name = "${var.name_prefix}-opensearch-logs"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "es.amazonaws.com"
        }
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "${aws_cloudwatch_log_group.opensearch.arn}:*"
      }
    ]
  })
}

# =============================================================================
# ACCESS POLICY
# =============================================================================

resource "aws_opensearch_domain_policy" "main" {
  domain_name = aws_opensearch_domain.main.domain_name

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action   = "es:*"
        Resource = "${aws_opensearch_domain.main.arn}/*"
      }
    ]
  })
}
