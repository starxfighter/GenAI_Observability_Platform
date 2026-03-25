# S3 Module - Outputs

output "data_bucket_name" {
  description = "Data bucket name"
  value       = aws_s3_bucket.data.id
}

output "data_bucket_arn" {
  description = "Data bucket ARN"
  value       = aws_s3_bucket.data.arn
}

output "logs_bucket_name" {
  description = "Logs bucket name"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "Logs bucket ARN"
  value       = aws_s3_bucket.logs.arn
}

output "artifacts_bucket_name" {
  description = "Artifacts bucket name"
  value       = aws_s3_bucket.artifacts.id
}

output "artifacts_bucket_arn" {
  description = "Artifacts bucket ARN"
  value       = aws_s3_bucket.artifacts.arn
}
