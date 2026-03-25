# Portal Module - Outputs

# =============================================================================
# ECR
# =============================================================================

output "ecr_repository_url" {
  description = "ECR repository URL for API"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.api.arn
}

# =============================================================================
# ECS
# =============================================================================

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.api.name
}

# =============================================================================
# LOAD BALANCER
# =============================================================================

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.api.dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID"
  value       = aws_lb.api.zone_id
}

output "alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.api.arn
}

output "api_endpoint" {
  description = "API endpoint URL"
  value       = var.api_domain != "" ? "https://${var.api_domain}" : "https://${aws_lb.api.dns_name}"
}

# =============================================================================
# CLOUDFRONT
# =============================================================================

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_domain_name" {
  description = "CloudFront domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "frontend_url" {
  description = "Frontend URL"
  value       = var.frontend_domain != "" ? "https://${var.frontend_domain}" : "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

# =============================================================================
# S3
# =============================================================================

output "frontend_bucket_name" {
  description = "Frontend S3 bucket name"
  value       = aws_s3_bucket.frontend.id
}

output "frontend_bucket_arn" {
  description = "Frontend S3 bucket ARN"
  value       = aws_s3_bucket.frontend.arn
}

# =============================================================================
# SECURITY GROUPS
# =============================================================================

output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "api_security_group_id" {
  description = "API security group ID"
  value       = aws_security_group.api.id
}

output "ecs_security_group_id" {
  description = "ECS tasks security group ID"
  value       = aws_security_group.api.id
}
