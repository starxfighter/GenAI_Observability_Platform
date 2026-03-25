# API Gateway Module - REST API

# =============================================================================
# HTTP API (API Gateway v2)
# =============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.name_prefix}-api"
  protocol_type = "HTTP"
  description   = "GenAI Observability Platform API"

  cors_configuration {
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers     = ["Content-Type", "Authorization", "X-API-Key"]
    expose_headers    = ["X-Request-Id"]
    max_age           = 3600
    allow_credentials = false
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api"
  })
}

# =============================================================================
# STAGES
# =============================================================================

resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_rate_limit  = var.throttle_rate_limit
    throttling_burst_limit = var.throttle_burst_limit
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      integrationLatency = "$context.integrationLatency"
    })
  }

  tags = var.tags
}

# =============================================================================
# AUTHORIZER
# =============================================================================

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-authorizer"

  jwt_configuration {
    audience = [var.cognito_user_pool_client_id]
    issuer   = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${var.cognito_user_pool_id}"
  }
}

# =============================================================================
# LAMBDA INTEGRATIONS
# =============================================================================

resource "aws_apigatewayv2_integration" "lambda" {
  for_each = var.lambda_functions

  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = each.value
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# =============================================================================
# ROUTES
# =============================================================================

# Traces routes
resource "aws_apigatewayv2_route" "traces_list" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/traces"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  target             = "integrations/${aws_apigatewayv2_integration.lambda["stream_processor"].id}"
}

resource "aws_apigatewayv2_route" "traces_get" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/traces/{traceId}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  target             = "integrations/${aws_apigatewayv2_integration.lambda["stream_processor"].id}"
}

# Agents routes
resource "aws_apigatewayv2_route" "agents_list" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/agents"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  target             = "integrations/${aws_apigatewayv2_integration.lambda["stream_processor"].id}"
}

# Alerts routes
resource "aws_apigatewayv2_route" "alerts_list" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/alerts"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  target             = "integrations/${aws_apigatewayv2_integration.lambda["anomaly_detector"].id}"
}

resource "aws_apigatewayv2_route" "alerts_investigate" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/alerts/{alertId}/investigation"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  target             = "integrations/${aws_apigatewayv2_integration.lambda["llm_investigator"].id}"
}

# NL Query routes
resource "aws_apigatewayv2_route" "nlq_query" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /api/v1/nlq"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  target             = "integrations/${aws_apigatewayv2_integration.lambda["nl_query"].id}"
}

# Remediation routes
resource "aws_apigatewayv2_route" "remediation_list" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/remediation"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  target             = "integrations/${aws_apigatewayv2_integration.lambda["autonomous_remediation"].id}"
}

resource "aws_apigatewayv2_route" "remediation_execute" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /api/v1/remediation/{remediationId}/execute"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  target             = "integrations/${aws_apigatewayv2_integration.lambda["autonomous_remediation"].id}"
}

# Integrations routes
resource "aws_apigatewayv2_route" "integrations_list" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/integrations"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  target             = "integrations/${aws_apigatewayv2_integration.lambda["integration_hub"].id}"
}

# Events ingestion (API Key auth)
resource "aws_apigatewayv2_route" "events_ingest" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /api/v1/events"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["stream_processor"].id}"
}

# =============================================================================
# LAMBDA PERMISSIONS
# =============================================================================

resource "aws_lambda_permission" "api_gateway" {
  for_each = var.lambda_functions

  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = split(":", each.value)[6] # Extract function name from ARN
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# =============================================================================
# CLOUDWATCH LOG GROUP
# =============================================================================

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigateway/${var.name_prefix}-api"
  retention_in_days = 14

  tags = var.tags
}

# =============================================================================
# CUSTOM DOMAIN (Optional)
# =============================================================================

resource "aws_apigatewayv2_domain_name" "main" {
  count = var.domain_name != "" ? 1 : 0

  domain_name = var.domain_name

  domain_name_configuration {
    certificate_arn = var.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = var.tags
}

resource "aws_apigatewayv2_api_mapping" "main" {
  count = var.domain_name != "" ? 1 : 0

  api_id      = aws_apigatewayv2_api.main.id
  domain_name = aws_apigatewayv2_domain_name.main[0].id
  stage       = aws_apigatewayv2_stage.main.id
}

# =============================================================================
# DATA SOURCES
# =============================================================================

data "aws_region" "current" {}
