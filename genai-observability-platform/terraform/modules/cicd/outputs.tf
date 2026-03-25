# CI/CD Module - Outputs

output "pipeline_name" {
  description = "CodePipeline name"
  value       = aws_codepipeline.main.name
}

output "pipeline_arn" {
  description = "CodePipeline ARN"
  value       = aws_codepipeline.main.arn
}

output "artifacts_bucket" {
  description = "CI/CD artifacts S3 bucket"
  value       = aws_s3_bucket.artifacts.id
}

output "codebuild_project_names" {
  description = "CodeBuild project names"
  value = {
    api      = aws_codebuild_project.api.name
    frontend = aws_codebuild_project.frontend.name
    lambda   = aws_codebuild_project.lambda.name
  }
}

output "codebuild_role_arn" {
  description = "CodeBuild IAM role ARN"
  value       = aws_iam_role.codebuild.arn
}

output "codepipeline_role_arn" {
  description = "CodePipeline IAM role ARN"
  value       = aws_iam_role.codepipeline.arn
}
