# Timestream Module - Time Series Database

# =============================================================================
# TIMESTREAM DATABASE
# =============================================================================

resource "aws_timestreamwrite_database" "main" {
  database_name = "${var.name_prefix}-metrics"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-metrics"
  })
}

# =============================================================================
# METRICS TABLE
# =============================================================================

resource "aws_timestreamwrite_table" "metrics" {
  database_name = aws_timestreamwrite_database.main.database_name
  table_name    = "metrics"

  retention_properties {
    memory_store_retention_period_in_hours  = var.memory_retention_hours
    magnetic_store_retention_period_in_days = var.magnetic_retention_days
  }

  magnetic_store_write_properties {
    enable_magnetic_store_writes = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-metrics"
  })
}

# =============================================================================
# EVENTS TABLE
# =============================================================================

resource "aws_timestreamwrite_table" "events" {
  database_name = aws_timestreamwrite_database.main.database_name
  table_name    = "events"

  retention_properties {
    memory_store_retention_period_in_hours  = var.memory_retention_hours
    magnetic_store_retention_period_in_days = var.magnetic_retention_days
  }

  magnetic_store_write_properties {
    enable_magnetic_store_writes = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-events"
  })
}
