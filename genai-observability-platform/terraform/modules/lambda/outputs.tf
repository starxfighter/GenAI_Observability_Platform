# Lambda Module - Outputs

output "function_names" {
  description = "Lambda function names"
  value       = { for k, v in aws_lambda_function.functions : k => v.function_name }
}

output "function_arns" {
  description = "Lambda function ARNs"
  value       = { for k, v in aws_lambda_function.functions : k => v.arn }
}

output "function_invoke_arns" {
  description = "Lambda function invoke ARNs"
  value       = { for k, v in aws_lambda_function.functions : k => v.invoke_arn }
}

output "execution_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda.arn
}

output "dlq_arn" {
  description = "Dead letter queue ARN"
  value       = aws_sqs_queue.dlq.arn
}
