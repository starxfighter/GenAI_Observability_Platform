# Secrets Module - AWS Secrets Manager

# =============================================================================
# ANTHROPIC API KEY
# =============================================================================

resource "aws_secretsmanager_secret" "anthropic" {
  name                    = "${var.name_prefix}/anthropic-api-key"
  description             = "Anthropic API key for Claude"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-anthropic-api-key"
  })
}

resource "aws_secretsmanager_secret_version" "anthropic" {
  secret_id = aws_secretsmanager_secret.anthropic.id
  secret_string = jsonencode({
    api_key = var.anthropic_api_key
  })
}

# =============================================================================
# SLACK WEBHOOK
# =============================================================================

resource "aws_secretsmanager_secret" "slack" {
  count = var.slack_webhook_url != "" ? 1 : 0

  name                    = "${var.name_prefix}/slack-webhook"
  description             = "Slack webhook URL for notifications"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-slack-webhook"
  })
}

resource "aws_secretsmanager_secret_version" "slack" {
  count = var.slack_webhook_url != "" ? 1 : 0

  secret_id = aws_secretsmanager_secret.slack[0].id
  secret_string = jsonencode({
    webhook_url = var.slack_webhook_url
  })
}

# =============================================================================
# PAGERDUTY INTEGRATION KEY
# =============================================================================

resource "aws_secretsmanager_secret" "pagerduty" {
  count = var.pagerduty_key != "" ? 1 : 0

  name                    = "${var.name_prefix}/pagerduty-key"
  description             = "PagerDuty integration key"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-pagerduty-key"
  })
}

resource "aws_secretsmanager_secret_version" "pagerduty" {
  count = var.pagerduty_key != "" ? 1 : 0

  secret_id = aws_secretsmanager_secret.pagerduty[0].id
  secret_string = jsonencode({
    integration_key = var.pagerduty_key
  })
}

# =============================================================================
# DATABASE CREDENTIALS
# =============================================================================

resource "aws_secretsmanager_secret" "database" {
  name                    = "${var.name_prefix}/database-credentials"
  description             = "Database credentials"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-database-credentials"
  })
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    username = "dbadmin"
    password = random_password.database.result
  })
}

resource "random_password" "database" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# =============================================================================
# OPENSEARCH CREDENTIALS
# =============================================================================

resource "aws_secretsmanager_secret" "opensearch" {
  name                    = "${var.name_prefix}/opensearch-credentials"
  description             = "OpenSearch credentials"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-opensearch-credentials"
  })
}

resource "aws_secretsmanager_secret_version" "opensearch" {
  secret_id = aws_secretsmanager_secret.opensearch.id
  secret_string = jsonencode({
    username = "admin"
    password = random_password.opensearch.result
  })
}

resource "random_password" "opensearch" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# =============================================================================
# JWT SECRET
# =============================================================================

resource "aws_secretsmanager_secret" "jwt" {
  name                    = "${var.name_prefix}/jwt-secret"
  description             = "JWT signing secret"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-jwt-secret"
  })
}

resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id = aws_secretsmanager_secret.jwt.id
  secret_string = jsonencode({
    secret = random_password.jwt.result
  })
}

resource "random_password" "jwt" {
  length  = 64
  special = false
}
