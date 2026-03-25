# RDS Module - Aurora PostgreSQL Cluster

# =============================================================================
# DB SUBNET GROUP
# =============================================================================

resource "aws_db_subnet_group" "main" {
  name       = "${var.name_prefix}-db-subnet"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-db-subnet"
  })
}

# =============================================================================
# PARAMETER GROUP
# =============================================================================

resource "aws_rds_cluster_parameter_group" "main" {
  name   = "${var.name_prefix}-aurora-pg15"
  family = "aurora-postgresql15"

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  tags = var.tags
}

resource "aws_db_parameter_group" "main" {
  name   = "${var.name_prefix}-aurora-pg15-instance"
  family = "aurora-postgresql15"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  tags = var.tags
}

# =============================================================================
# AURORA CLUSTER
# =============================================================================

resource "aws_rds_cluster" "main" {
  cluster_identifier = "${var.name_prefix}-aurora"
  engine             = "aurora-postgresql"
  engine_version     = "15.4"
  engine_mode        = "provisioned"

  database_name   = var.database_name
  master_username = var.master_username
  master_password = var.master_password

  db_subnet_group_name            = aws_db_subnet_group.main.name
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.main.name
  vpc_security_group_ids          = var.security_group_ids

  storage_encrypted = true
  storage_type      = "aurora-iopt1"

  backup_retention_period = var.backup_retention_period
  preferred_backup_window = "03:00-04:00"

  deletion_protection = var.deletion_protection
  skip_final_snapshot = var.environment != "prod"

  final_snapshot_identifier = var.environment == "prod" ? "${var.name_prefix}-final-${formatdate("YYYY-MM-DD", timestamp())}" : null

  enabled_cloudwatch_logs_exports = ["postgresql"]

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = var.environment == "prod" ? 16 : 4
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-aurora"
  })

  lifecycle {
    ignore_changes = [final_snapshot_identifier]
  }
}

# =============================================================================
# AURORA INSTANCES
# =============================================================================

resource "aws_rds_cluster_instance" "main" {
  count = var.instance_count

  identifier         = "${var.name_prefix}-aurora-${count.index + 1}"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version

  db_parameter_group_name = aws_db_parameter_group.main.name

  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-aurora-${count.index + 1}"
  })
}

# =============================================================================
# IAM ROLE FOR ENHANCED MONITORING
# =============================================================================

resource "aws_iam_role" "rds_monitoring" {
  name = "${var.name_prefix}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
