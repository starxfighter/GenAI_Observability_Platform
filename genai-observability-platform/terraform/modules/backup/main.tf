# AWS Backup Module - Automated Backups

# =============================================================================
# BACKUP VAULT
# =============================================================================

resource "aws_backup_vault" "main" {
  name = "${var.name_prefix}-vault"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vault"
  })
}

# =============================================================================
# BACKUP PLAN
# =============================================================================

resource "aws_backup_plan" "main" {
  name = "${var.name_prefix}-backup-plan"

  # Daily backup rule
  rule {
    rule_name         = "daily-backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 5 ? * * *)"  # 5 AM UTC daily

    lifecycle {
      delete_after = var.daily_retention_days
    }

    recovery_point_tags = {
      Environment = var.environment
      BackupType  = "daily"
    }
  }

  # Weekly backup rule
  rule {
    rule_name         = "weekly-backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 5 ? * SUN *)"  # 5 AM UTC Sunday

    lifecycle {
      delete_after       = var.weekly_retention_days
      cold_storage_after = var.environment == "prod" ? 30 : null
    }

    recovery_point_tags = {
      Environment = var.environment
      BackupType  = "weekly"
    }
  }

  # Monthly backup rule (production only)
  dynamic "rule" {
    for_each = var.environment == "prod" ? [1] : []
    content {
      rule_name         = "monthly-backup"
      target_vault_name = aws_backup_vault.main.name
      schedule          = "cron(0 5 1 * ? *)"  # 5 AM UTC 1st of month

      lifecycle {
        delete_after       = var.monthly_retention_days
        cold_storage_after = 90
      }

      recovery_point_tags = {
        Environment = var.environment
        BackupType  = "monthly"
      }
    }
  }

  tags = var.tags
}

# =============================================================================
# BACKUP SELECTION - DYNAMODB
# =============================================================================

resource "aws_backup_selection" "dynamodb" {
  name         = "${var.name_prefix}-dynamodb"
  iam_role_arn = aws_iam_role.backup.arn
  plan_id      = aws_backup_plan.main.id

  resources = var.dynamodb_table_arns
}

# =============================================================================
# BACKUP SELECTION - RDS
# =============================================================================

resource "aws_backup_selection" "rds" {
  count = var.rds_cluster_arn != "" ? 1 : 0

  name         = "${var.name_prefix}-rds"
  iam_role_arn = aws_iam_role.backup.arn
  plan_id      = aws_backup_plan.main.id

  resources = [var.rds_cluster_arn]
}

# =============================================================================
# BACKUP SELECTION - EFS (if any)
# =============================================================================

resource "aws_backup_selection" "efs" {
  count = length(var.efs_arns) > 0 ? 1 : 0

  name         = "${var.name_prefix}-efs"
  iam_role_arn = aws_iam_role.backup.arn
  plan_id      = aws_backup_plan.main.id

  resources = var.efs_arns
}

# =============================================================================
# IAM ROLE FOR BACKUP
# =============================================================================

resource "aws_iam_role" "backup" {
  name = "${var.name_prefix}-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "restore" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

# Additional policy for DynamoDB backups
resource "aws_iam_role_policy" "backup_dynamodb" {
  name = "${var.name_prefix}-backup-dynamodb"
  role = aws_iam_role.backup.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:StartAwsBackupJob",
          "dynamodb:DescribeTable",
          "dynamodb:CreateBackup",
          "dynamodb:DeleteBackup",
          "dynamodb:DescribeBackup",
          "dynamodb:ListBackups",
          "dynamodb:RestoreTableFromAwsBackup"
        ]
        Resource = var.dynamodb_table_arns
      }
    ]
  })
}

# =============================================================================
# BACKUP VAULT NOTIFICATIONS
# =============================================================================

resource "aws_backup_vault_notifications" "main" {
  count = var.sns_topic_arn != "" ? 1 : 0

  backup_vault_name   = aws_backup_vault.main.name
  sns_topic_arn       = var.sns_topic_arn
  backup_vault_events = [
    "BACKUP_JOB_FAILED",
    "RESTORE_JOB_FAILED",
    "COPY_JOB_FAILED",
    "RECOVERY_POINT_MODIFIED"
  ]
}

# =============================================================================
# BACKUP VAULT LOCK (Production only - compliance)
# =============================================================================

resource "aws_backup_vault_lock_configuration" "main" {
  count = var.environment == "prod" && var.enable_vault_lock ? 1 : 0

  backup_vault_name   = aws_backup_vault.main.name
  min_retention_days  = 7
  max_retention_days  = 365
  changeable_for_days = 3  # Grace period before lock becomes immutable
}
