# GenAI Observability Platform - Main Terraform Configuration
# This is the root module that orchestrates all infrastructure components

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Backend configuration - uncomment and configure for your environment
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "genai-observability/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-state-lock"
  #   encrypt        = true
  # }
}

# Primary region provider
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "genai-observability"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Secondary region provider for multi-region deployment
provider "aws" {
  alias  = "secondary"
  region = var.secondary_region

  default_tags {
    tags = {
      Project     = "genai-observability"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# US-East-1 provider for CloudFront WAF (must be in us-east-1)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "genai-observability"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  name_prefix = "genai-obs-${var.environment}"
  common_tags = {
    Project     = "genai-observability"
    Environment = var.environment
  }
}

# =============================================================================
# VPC AND NETWORKING
# =============================================================================

module "vpc" {
  source = "./modules/vpc"

  name_prefix        = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  environment        = var.environment

  enable_nat_gateway = var.enable_nat_gateway
  single_nat_gateway = var.single_nat_gateway

  # VPC Flow Logs
  enable_flow_logs         = var.enable_flow_logs
  flow_logs_retention_days = var.flow_logs_retention_days

  tags = local.common_tags
}

# =============================================================================
# DYNAMODB TABLES
# =============================================================================

module "dynamodb" {
  source = "./modules/dynamodb"

  name_prefix = local.name_prefix
  environment = var.environment

  # Enable point-in-time recovery for production
  enable_point_in_time_recovery = var.environment == "prod"

  # Enable global tables for multi-region
  enable_global_tables = var.enable_multi_region
  replica_regions      = var.enable_multi_region ? [var.secondary_region] : []

  tags = local.common_tags
}

# =============================================================================
# TIMESTREAM DATABASE
# =============================================================================

module "timestream" {
  source = "./modules/timestream"

  name_prefix = local.name_prefix
  environment = var.environment

  # Retention settings
  memory_retention_hours  = var.timestream_memory_retention_hours
  magnetic_retention_days = var.timestream_magnetic_retention_days

  tags = local.common_tags
}

# =============================================================================
# OPENSEARCH CLUSTER
# =============================================================================

module "opensearch" {
  source = "./modules/opensearch"

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.opensearch_security_group_id]

  instance_type  = var.opensearch_instance_type
  instance_count = var.opensearch_instance_count
  volume_size    = var.opensearch_volume_size

  master_user_name     = var.opensearch_master_user
  master_user_password = var.opensearch_master_password

  tags = local.common_tags
}

# =============================================================================
# RDS AURORA POSTGRESQL
# =============================================================================

module "rds" {
  source = "./modules/rds"

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.rds_security_group_id]

  instance_class = var.rds_instance_class
  instance_count = var.rds_instance_count

  database_name   = var.rds_database_name
  master_username = var.rds_master_username
  master_password = var.rds_master_password

  backup_retention_period = var.environment == "prod" ? 30 : 7
  deletion_protection     = var.environment == "prod"

  tags = local.common_tags
}

# =============================================================================
# S3 BUCKETS
# =============================================================================

module "s3" {
  source = "./modules/s3"

  name_prefix = local.name_prefix
  environment = var.environment
  account_id  = data.aws_caller_identity.current.account_id

  # Enable replication for multi-region
  enable_replication   = var.enable_multi_region
  replication_region   = var.secondary_region

  # Lifecycle rules
  archive_after_days = var.s3_archive_after_days
  expire_after_days  = var.s3_expire_after_days

  tags = local.common_tags
}

# =============================================================================
# KINESIS STREAMS
# =============================================================================

module "kinesis" {
  source = "./modules/kinesis"

  name_prefix = local.name_prefix
  environment = var.environment

  shard_count      = var.kinesis_shard_count
  retention_period = var.kinesis_retention_hours

  # S3 bucket for Firehose delivery
  s3_bucket_arn = module.s3.data_bucket_arn

  # Enable enhanced fan-out for production
  enable_enhanced_fanout = var.environment == "prod"

  tags = local.common_tags
}

# =============================================================================
# LAMBDA FUNCTIONS
# =============================================================================

module "lambda" {
  source = "./modules/lambda"

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.lambda_security_group_id]

  # Dependencies
  dynamodb_table_arns   = module.dynamodb.table_arns
  timestream_table_arn  = module.timestream.table_arn
  opensearch_endpoint   = module.opensearch.endpoint
  kinesis_stream_arn    = module.kinesis.events_stream_arn
  s3_bucket_arn         = module.s3.data_bucket_arn
  secrets_manager_arns  = [module.secrets.anthropic_secret_arn]

  # Configuration
  anthropic_api_key_secret_arn = module.secrets.anthropic_secret_arn
  log_retention_days           = var.lambda_log_retention_days

  tags = local.common_tags
}

# =============================================================================
# API GATEWAY
# =============================================================================

module "api_gateway" {
  source = "./modules/api-gateway"

  name_prefix = local.name_prefix
  environment = var.environment

  # Lambda integrations
  lambda_functions = module.lambda.function_arns

  # Cognito authorizer
  cognito_user_pool_arn = module.cognito.user_pool_arn

  # Custom domain (optional)
  domain_name     = var.api_domain_name
  certificate_arn = var.api_certificate_arn

  # Throttling
  throttle_rate_limit  = var.api_throttle_rate_limit
  throttle_burst_limit = var.api_throttle_burst_limit

  tags = local.common_tags
}

# =============================================================================
# COGNITO USER POOL
# =============================================================================

module "cognito" {
  source = "./modules/cognito"

  name_prefix = local.name_prefix
  environment = var.environment

  # Callback URLs for SSO
  callback_urls = var.cognito_callback_urls
  logout_urls   = var.cognito_logout_urls

  # SSO providers
  enable_google    = var.enable_google_sso
  google_client_id = var.google_client_id
  google_client_secret = var.google_client_secret

  enable_okta        = var.enable_okta_sso
  okta_client_id     = var.okta_client_id
  okta_client_secret = var.okta_client_secret
  okta_issuer_url    = var.okta_issuer_url

  # SAML
  enable_saml          = var.enable_saml_sso
  saml_metadata_url    = var.saml_metadata_url
  saml_provider_name   = var.saml_provider_name

  tags = local.common_tags
}

# =============================================================================
# SECRETS MANAGER
# =============================================================================

module "secrets" {
  source = "./modules/secrets"

  name_prefix = local.name_prefix
  environment = var.environment

  anthropic_api_key = var.anthropic_api_key
  slack_webhook_url = var.slack_webhook_url
  pagerduty_key     = var.pagerduty_integration_key

  tags = local.common_tags
}

# =============================================================================
# MONITORING AND ALARMS
# =============================================================================

module "monitoring" {
  source = "./modules/monitoring"

  name_prefix = local.name_prefix
  environment = var.environment

  # Resources to monitor
  lambda_function_names = module.lambda.function_names
  api_gateway_id        = module.api_gateway.api_id
  dynamodb_table_names  = module.dynamodb.table_names
  kinesis_stream_name   = module.kinesis.events_stream_name
  opensearch_domain     = module.opensearch.domain_name
  rds_cluster_id        = module.rds.cluster_identifier

  # Alert configuration
  alert_email           = var.alert_email
  slack_webhook_url     = var.slack_webhook_url
  pagerduty_endpoint    = var.pagerduty_endpoint

  # Thresholds
  lambda_error_threshold      = var.lambda_error_threshold
  api_latency_threshold_ms    = var.api_latency_threshold_ms
  dynamodb_throttle_threshold = var.dynamodb_throttle_threshold

  tags = local.common_tags
}

# =============================================================================
# IAM ROLES AND POLICIES
# =============================================================================

module "iam" {
  source = "./modules/iam"

  name_prefix = local.name_prefix
  environment = var.environment
  account_id  = data.aws_caller_identity.current.account_id
  region      = var.aws_region

  # Resource ARNs for policies
  dynamodb_table_arns  = module.dynamodb.table_arns
  s3_bucket_arns       = [module.s3.data_bucket_arn, module.s3.logs_bucket_arn]
  kinesis_stream_arns  = [module.kinesis.events_stream_arn]
  secrets_manager_arns = module.secrets.all_secret_arns

  tags = local.common_tags
}

# =============================================================================
# PORTAL (FastAPI Backend + React Frontend)
# =============================================================================

module "portal" {
  source = "./modules/portal"

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids

  # ECS Configuration
  api_cpu           = var.portal_api_cpu
  api_memory        = var.portal_api_memory
  api_desired_count = var.portal_api_desired_count
  api_min_count     = var.portal_api_min_count
  api_max_count     = var.portal_api_max_count

  # Domains
  api_domain               = var.portal_api_domain
  frontend_domain          = var.portal_frontend_domain
  certificate_arn          = var.portal_certificate_arn
  frontend_certificate_arn = var.portal_frontend_certificate_arn
  route53_zone_id          = var.route53_zone_id
  cors_origins             = var.cors_origins

  # Database connections
  dynamodb_tables = module.dynamodb.table_names
  dynamodb_table_arns = module.dynamodb.table_arns
  timestream_database = module.timestream.database_name
  timestream_table    = module.timestream.table_name
  opensearch_endpoint = module.opensearch.endpoint
  rds_endpoint        = module.rds.cluster_endpoint
  rds_database        = module.rds.database_name
  kinesis_stream      = module.kinesis.events_stream_name
  kinesis_stream_arn  = module.kinesis.events_stream_arn
  s3_bucket_arn       = module.s3.data_bucket_arn

  # Secrets
  jwt_secret_arn        = module.secrets.jwt_secret_arn
  anthropic_secret_arn  = module.secrets.anthropic_secret_arn
  database_secret_arn   = module.secrets.database_secret_arn
  opensearch_secret_arn = module.secrets.opensearch_secret_arn

  # Cognito
  cognito_user_pool_id = module.cognito.user_pool_id
  cognito_client_id    = module.cognito.user_pool_client_id

  # Lambda
  lambda_arns = values(module.lambda.function_arns)

  # Logging
  log_retention_days = var.lambda_log_retention_days

  tags = local.common_tags
}

# =============================================================================
# WAF (Web Application Firewall)
# =============================================================================

module "waf" {
  source = "./modules/waf"

  providers = {
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix = local.name_prefix
  environment = var.environment

  # Rate limiting
  rate_limit     = var.waf_rate_limit
  api_rate_limit = var.waf_api_rate_limit

  # Geo blocking (optional)
  blocked_countries = var.waf_blocked_countries

  # Associate with resources
  alb_arn               = module.portal.alb_arn
  api_gateway_stage_arn = module.api_gateway.stage_arn

  tags = local.common_tags
}

# =============================================================================
# AWS BACKUP
# =============================================================================

module "backup" {
  source = "./modules/backup"

  name_prefix = local.name_prefix
  environment = var.environment

  # Resources to backup
  dynamodb_table_arns = module.dynamodb.table_arns
  rds_cluster_arn     = module.rds.cluster_arn

  # Retention policies
  daily_retention_days   = var.backup_daily_retention_days
  weekly_retention_days  = var.backup_weekly_retention_days
  monthly_retention_days = var.backup_monthly_retention_days

  # Notifications
  sns_topic_arn = module.monitoring.alerts_topic_arn

  # Compliance (optional)
  enable_vault_lock = var.environment == "prod" && var.enable_backup_vault_lock

  tags = local.common_tags
}

# =============================================================================
# GLUE ETL
# =============================================================================

module "glue" {
  source = "./modules/glue"

  name_prefix = local.name_prefix
  environment = var.environment

  # Data sources
  s3_bucket_name      = module.s3.data_bucket_name
  scripts_bucket      = module.s3.artifacts_bucket_name
  timestream_database = module.timestream.database_name

  # IAM
  glue_role_arn = module.iam.glue_role_arn

  tags = local.common_tags
}

# =============================================================================
# STEP FUNCTIONS
# =============================================================================

module "stepfunctions" {
  source = "./modules/stepfunctions"

  name_prefix = local.name_prefix
  environment = var.environment

  # Lambda functions
  lambda_arns = {
    autonomous_remediation = module.lambda.function_arns["autonomous_remediation"]
    llm_investigator       = module.lambda.function_arns["llm_investigator"]
    alert_router           = module.lambda.function_arns["alert_router"]
    integration_hub        = module.lambda.function_arns["integration_hub"]
    stream_processor       = module.lambda.function_arns["stream_processor"]
    anomaly_detector       = module.lambda.function_arns["anomaly_detector"]
  }

  # DynamoDB
  investigations_table     = module.dynamodb.table_names.investigations
  investigations_table_arn = module.dynamodb.table_arns[4] # investigations table

  # Logging
  log_retention_days = var.lambda_log_retention_days

  tags = local.common_tags
}

# =============================================================================
# EVENTBRIDGE
# =============================================================================

module "eventbridge" {
  source = "./modules/eventbridge"

  name_prefix = local.name_prefix
  environment = var.environment

  # Lambda targets
  lambda_arns = {
    llm_investigator       = module.lambda.function_arns["llm_investigator"]
    alert_router           = module.lambda.function_arns["alert_router"]
    autonomous_remediation = module.lambda.function_arns["autonomous_remediation"]
    integration_hub        = module.lambda.function_arns["integration_hub"]
    nl_query               = module.lambda.function_arns["nl_query"]
  }

  # Step Functions target
  step_functions_arn = module.stepfunctions.remediation_state_machine_arn

  # Archive
  archive_retention_days = var.eventbridge_archive_retention_days

  tags = local.common_tags
}

# =============================================================================
# ELASTICACHE (REDIS)
# =============================================================================

module "elasticache" {
  source = "./modules/elasticache"

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

  # Security
  allowed_security_groups = [
    module.vpc.lambda_security_group_id,
    module.portal.ecs_security_group_id
  ]

  # Configuration
  node_type       = var.elasticache_node_type
  num_cache_nodes = var.elasticache_num_nodes
  auth_token      = var.elasticache_auth_token

  # Notifications
  sns_topic_arn = module.monitoring.alerts_topic_arn

  tags = local.common_tags
}

# =============================================================================
# BASTION HOST
# =============================================================================

module "bastion" {
  source = "./modules/bastion"
  count  = var.enable_bastion ? 1 : 0

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_id    = module.vpc.vpc_id
  subnet_id = module.vpc.public_subnet_ids[0]

  # Access control
  allowed_cidr_blocks = var.bastion_allowed_cidr_blocks
  ssh_public_key      = var.bastion_ssh_public_key

  # Instance
  instance_type     = var.bastion_instance_type
  assign_elastic_ip = var.environment == "prod"

  # Notifications
  sns_topic_arn = module.monitoring.alerts_topic_arn

  tags = local.common_tags
}

# =============================================================================
# CI/CD PIPELINE
# =============================================================================

module "cicd" {
  source = "./modules/cicd"
  count  = var.enable_cicd ? 1 : 0

  name_prefix = local.name_prefix
  environment = var.environment

  # GitHub
  codestar_connection_arn = var.codestar_connection_arn
  github_repository       = var.github_repository
  github_branch           = var.github_branch

  # ECR
  ecr_repository_url = module.portal.ecr_repository_url
  ecr_repository_arn = module.portal.ecr_repository_arn

  # ECS
  ecs_cluster_name = module.portal.ecs_cluster_name
  ecs_service_name = module.portal.ecs_service_name

  # Frontend
  frontend_bucket_name       = module.portal.frontend_bucket_name
  cloudfront_distribution_id = module.portal.cloudfront_distribution_id
  api_url                    = module.portal.api_endpoint

  # Cognito
  cognito_user_pool_id = module.cognito.user_pool_id
  cognito_client_id    = module.cognito.user_pool_client_id

  tags = local.common_tags
}

# =============================================================================
# VPC FLOW LOGS (Enable via VPC module)
# =============================================================================

# Note: VPC Flow Logs are now configurable via the VPC module
# Set enable_flow_logs = true in terraform.tfvars to enable

# =============================================================================
# DATA SOURCES
# =============================================================================

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}
