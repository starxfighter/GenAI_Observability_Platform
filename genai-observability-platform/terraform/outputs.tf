# GenAI Observability Platform - Outputs

# =============================================================================
# VPC OUTPUTS
# =============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

# =============================================================================
# API GATEWAY OUTPUTS
# =============================================================================

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.api_endpoint
}

output "api_id" {
  description = "API Gateway ID"
  value       = module.api_gateway.api_id
}

output "api_custom_domain" {
  description = "Custom domain name (if configured)"
  value       = var.api_domain_name != "" ? var.api_domain_name : null
}

# =============================================================================
# COGNITO OUTPUTS
# =============================================================================

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = module.cognito.user_pool_client_id
}

output "cognito_domain" {
  description = "Cognito domain"
  value       = module.cognito.domain
}

output "cognito_identity_pool_id" {
  description = "Cognito Identity Pool ID"
  value       = module.cognito.identity_pool_id
}

# =============================================================================
# DATABASE OUTPUTS
# =============================================================================

output "dynamodb_table_names" {
  description = "DynamoDB table names"
  value       = module.dynamodb.table_names
}

output "dynamodb_table_arns" {
  description = "DynamoDB table ARNs"
  value       = module.dynamodb.table_arns
}

output "timestream_database_name" {
  description = "Timestream database name"
  value       = module.timestream.database_name
}

output "timestream_table_name" {
  description = "Timestream table name"
  value       = module.timestream.table_name
}

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint"
  value       = module.opensearch.endpoint
  sensitive   = true
}

output "opensearch_dashboard_endpoint" {
  description = "OpenSearch Dashboards endpoint"
  value       = module.opensearch.dashboard_endpoint
  sensitive   = true
}

output "rds_cluster_endpoint" {
  description = "RDS Aurora cluster endpoint"
  value       = module.rds.cluster_endpoint
  sensitive   = true
}

output "rds_reader_endpoint" {
  description = "RDS Aurora reader endpoint"
  value       = module.rds.reader_endpoint
  sensitive   = true
}

# =============================================================================
# S3 OUTPUTS
# =============================================================================

output "s3_data_bucket" {
  description = "S3 data bucket name"
  value       = module.s3.data_bucket_name
}

output "s3_logs_bucket" {
  description = "S3 logs bucket name"
  value       = module.s3.logs_bucket_name
}

output "s3_artifacts_bucket" {
  description = "S3 artifacts bucket name"
  value       = module.s3.artifacts_bucket_name
}

# =============================================================================
# KINESIS OUTPUTS
# =============================================================================

output "kinesis_events_stream_name" {
  description = "Kinesis events stream name"
  value       = module.kinesis.events_stream_name
}

output "kinesis_events_stream_arn" {
  description = "Kinesis events stream ARN"
  value       = module.kinesis.events_stream_arn
}

# =============================================================================
# LAMBDA OUTPUTS
# =============================================================================

output "lambda_function_names" {
  description = "Lambda function names"
  value       = module.lambda.function_names
}

output "lambda_function_arns" {
  description = "Lambda function ARNs"
  value       = module.lambda.function_arns
}

# =============================================================================
# MONITORING OUTPUTS
# =============================================================================

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.monitoring.dashboard_url
}

output "sns_alerts_topic_arn" {
  description = "SNS alerts topic ARN"
  value       = module.monitoring.alerts_topic_arn
}

# =============================================================================
# SDK CONFIGURATION OUTPUT
# =============================================================================

output "sdk_configuration" {
  description = "Configuration for the Python SDK"
  value = {
    api_endpoint = module.api_gateway.api_endpoint
    region       = var.aws_region
    environment  = var.environment
  }
}

# =============================================================================
# FRONTEND CONFIGURATION OUTPUT
# =============================================================================

output "frontend_configuration" {
  description = "Configuration for the frontend application"
  value = {
    api_endpoint           = module.portal.api_endpoint
    cognito_user_pool_id   = module.cognito.user_pool_id
    cognito_client_id      = module.cognito.user_pool_client_id
    cognito_domain         = module.cognito.domain
    region                 = var.aws_region
  }
}

# =============================================================================
# PORTAL OUTPUTS
# =============================================================================

output "portal_api_endpoint" {
  description = "Portal API endpoint"
  value       = module.portal.api_endpoint
}

output "portal_frontend_url" {
  description = "Portal frontend URL"
  value       = module.portal.frontend_url
}

output "portal_ecr_repository" {
  description = "ECR repository URL for Portal API"
  value       = module.portal.ecr_repository_url
}

output "portal_ecs_cluster" {
  description = "ECS cluster name"
  value       = module.portal.ecs_cluster_name
}

output "portal_ecs_service" {
  description = "ECS service name"
  value       = module.portal.ecs_service_name
}

output "portal_frontend_bucket" {
  description = "S3 bucket for frontend assets"
  value       = module.portal.frontend_bucket_name
}

output "portal_cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.portal.cloudfront_distribution_id
}

output "portal_alb_dns_name" {
  description = "ALB DNS name for API"
  value       = module.portal.alb_dns_name
}

# =============================================================================
# WAF OUTPUTS
# =============================================================================

output "waf_cloudfront_acl_arn" {
  description = "WAF Web ACL ARN for CloudFront"
  value       = module.waf.cloudfront_web_acl_arn
}

output "waf_alb_acl_arn" {
  description = "WAF Web ACL ARN for ALB"
  value       = module.waf.alb_web_acl_arn
}

output "waf_api_gateway_acl_arn" {
  description = "WAF Web ACL ARN for API Gateway"
  value       = module.waf.api_gateway_web_acl_arn
}

# =============================================================================
# BACKUP OUTPUTS
# =============================================================================

output "backup_vault_name" {
  description = "AWS Backup vault name"
  value       = module.backup.vault_name
}

output "backup_plan_id" {
  description = "AWS Backup plan ID"
  value       = module.backup.plan_id
}

# =============================================================================
# GLUE OUTPUTS
# =============================================================================

output "glue_database_name" {
  description = "Glue database name"
  value       = module.glue.database_name
}

output "glue_job_names" {
  description = "Glue job names"
  value       = module.glue.job_names
}

output "glue_workflow_name" {
  description = "Glue ETL workflow name"
  value       = module.glue.workflow_name
}

# =============================================================================
# EVENTBRIDGE OUTPUTS
# =============================================================================

output "eventbridge_bus_name" {
  description = "EventBridge event bus name"
  value       = module.eventbridge.event_bus_name
}

output "eventbridge_bus_arn" {
  description = "EventBridge event bus ARN"
  value       = module.eventbridge.event_bus_arn
}

# =============================================================================
# STEP FUNCTIONS OUTPUTS
# =============================================================================

output "stepfunctions_remediation_arn" {
  description = "Remediation workflow state machine ARN"
  value       = module.stepfunctions.remediation_state_machine_arn
}

output "stepfunctions_investigation_arn" {
  description = "Investigation workflow state machine ARN"
  value       = module.stepfunctions.investigation_state_machine_arn
}

# =============================================================================
# ELASTICACHE OUTPUTS
# =============================================================================

output "redis_primary_endpoint" {
  description = "Redis primary endpoint"
  value       = module.elasticache.primary_endpoint
  sensitive   = true
}

output "redis_reader_endpoint" {
  description = "Redis reader endpoint"
  value       = module.elasticache.reader_endpoint
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = module.elasticache.connection_string
  sensitive   = true
}

# =============================================================================
# BASTION OUTPUTS
# =============================================================================

output "bastion_instance_id" {
  description = "Bastion instance ID"
  value       = var.enable_bastion ? module.bastion[0].instance_id : null
}

output "bastion_public_ip" {
  description = "Bastion public IP"
  value       = var.enable_bastion ? module.bastion[0].public_ip : null
}

output "bastion_ssm_connect_command" {
  description = "Command to connect to bastion via SSM"
  value       = var.enable_bastion ? module.bastion[0].ssm_connect_command : null
}

# =============================================================================
# CI/CD OUTPUTS
# =============================================================================

output "cicd_pipeline_name" {
  description = "CodePipeline name"
  value       = var.enable_cicd ? module.cicd[0].pipeline_name : null
}

output "cicd_pipeline_arn" {
  description = "CodePipeline ARN"
  value       = var.enable_cicd ? module.cicd[0].pipeline_arn : null
}

output "cicd_artifacts_bucket" {
  description = "CI/CD artifacts S3 bucket"
  value       = var.enable_cicd ? module.cicd[0].artifacts_bucket : null
}
