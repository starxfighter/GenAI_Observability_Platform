# WAF Module - Outputs

output "cloudfront_web_acl_arn" {
  description = "CloudFront WAF Web ACL ARN"
  value       = aws_wafv2_web_acl.cloudfront.arn
}

output "alb_web_acl_arn" {
  description = "ALB WAF Web ACL ARN"
  value       = aws_wafv2_web_acl.alb.arn
}

output "api_gateway_web_acl_arn" {
  description = "API Gateway WAF Web ACL ARN"
  value       = aws_wafv2_web_acl.api_gateway.arn
}

output "waf_log_group_name" {
  description = "WAF CloudWatch Log Group name"
  value       = aws_cloudwatch_log_group.waf.name
}
