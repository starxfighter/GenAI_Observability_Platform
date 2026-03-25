# DynamoDB Module - Tables for GenAI Observability Platform

# =============================================================================
# TRACES TABLE
# =============================================================================

resource "aws_dynamodb_table" "traces" {
  name         = "${var.name_prefix}-traces"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "trace_id"

  attribute {
    name = "trace_id"
    type = "S"
  }

  attribute {
    name = "agent_id"
    type = "S"
  }

  attribute {
    name = "start_time"
    type = "S"
  }

  global_secondary_index {
    name            = "agent-time-index"
    hash_key        = "agent_id"
    range_key       = "start_time"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  dynamic "replica" {
    for_each = var.enable_global_tables ? var.replica_regions : []
    content {
      region_name = replica.value
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-traces"
  })
}

# =============================================================================
# SPANS TABLE
# =============================================================================

resource "aws_dynamodb_table" "spans" {
  name         = "${var.name_prefix}-spans"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "trace_id"
  range_key    = "span_id"

  attribute {
    name = "trace_id"
    type = "S"
  }

  attribute {
    name = "span_id"
    type = "S"
  }

  attribute {
    name = "parent_span_id"
    type = "S"
  }

  global_secondary_index {
    name            = "parent-span-index"
    hash_key        = "trace_id"
    range_key       = "parent_span_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  dynamic "replica" {
    for_each = var.enable_global_tables ? var.replica_regions : []
    content {
      region_name = replica.value
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-spans"
  })
}

# =============================================================================
# AGENTS TABLE
# =============================================================================

resource "aws_dynamodb_table" "agents" {
  name         = "${var.name_prefix}-agents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "agent_id"

  attribute {
    name = "agent_id"
    type = "S"
  }

  attribute {
    name = "team_id"
    type = "S"
  }

  global_secondary_index {
    name            = "team-index"
    hash_key        = "team_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  dynamic "replica" {
    for_each = var.enable_global_tables ? var.replica_regions : []
    content {
      region_name = replica.value
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-agents"
  })
}

# =============================================================================
# ALERTS TABLE
# =============================================================================

resource "aws_dynamodb_table" "alerts" {
  name         = "${var.name_prefix}-alerts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "alert_id"

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "agent_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "agent-status-index"
    hash_key        = "agent_id"
    range_key       = "status"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "status-time-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  dynamic "replica" {
    for_each = var.enable_global_tables ? var.replica_regions : []
    content {
      region_name = replica.value
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alerts"
  })
}

# =============================================================================
# INVESTIGATIONS TABLE
# =============================================================================

resource "aws_dynamodb_table" "investigations" {
  name         = "${var.name_prefix}-investigations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "investigation_id"

  attribute {
    name = "investigation_id"
    type = "S"
  }

  attribute {
    name = "alert_id"
    type = "S"
  }

  global_secondary_index {
    name            = "alert-index"
    hash_key        = "alert_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  dynamic "replica" {
    for_each = var.enable_global_tables ? var.replica_regions : []
    content {
      region_name = replica.value
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-investigations"
  })
}

# =============================================================================
# REMEDIATIONS TABLE
# =============================================================================

resource "aws_dynamodb_table" "remediations" {
  name         = "${var.name_prefix}-remediations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "remediation_id"

  attribute {
    name = "remediation_id"
    type = "S"
  }

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "alert-index"
    hash_key        = "alert_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  dynamic "replica" {
    for_each = var.enable_global_tables ? var.replica_regions : []
    content {
      region_name = replica.value
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-remediations"
  })
}

# =============================================================================
# INTEGRATIONS TABLE
# =============================================================================

resource "aws_dynamodb_table" "integrations" {
  name         = "${var.name_prefix}-integrations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "integration_id"

  attribute {
    name = "integration_id"
    type = "S"
  }

  attribute {
    name = "team_id"
    type = "S"
  }

  attribute {
    name = "type"
    type = "S"
  }

  global_secondary_index {
    name            = "team-type-index"
    hash_key        = "team_id"
    range_key       = "type"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  dynamic "replica" {
    for_each = var.enable_global_tables ? var.replica_regions : []
    content {
      region_name = replica.value
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-integrations"
  })
}

# =============================================================================
# API KEYS TABLE
# =============================================================================

resource "aws_dynamodb_table" "api_keys" {
  name         = "${var.name_prefix}-api-keys"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "key_hash"

  attribute {
    name = "key_hash"
    type = "S"
  }

  attribute {
    name = "agent_id"
    type = "S"
  }

  global_secondary_index {
    name            = "agent-index"
    hash_key        = "agent_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  dynamic "replica" {
    for_each = var.enable_global_tables ? var.replica_regions : []
    content {
      region_name = replica.value
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-keys"
  })
}

# =============================================================================
# SAVED QUERIES TABLE (for NLQ)
# =============================================================================

resource "aws_dynamodb_table" "saved_queries" {
  name         = "${var.name_prefix}-saved-queries"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "query_id"

  attribute {
    name = "query_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  dynamic "replica" {
    for_each = var.enable_global_tables ? var.replica_regions : []
    content {
      region_name = replica.value
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-saved-queries"
  })
}
