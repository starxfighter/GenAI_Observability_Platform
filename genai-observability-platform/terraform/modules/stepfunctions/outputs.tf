# Step Functions Module - Outputs

output "remediation_state_machine_arn" {
  description = "Remediation workflow state machine ARN"
  value       = aws_sfn_state_machine.remediation.arn
}

output "remediation_state_machine_name" {
  description = "Remediation workflow state machine name"
  value       = aws_sfn_state_machine.remediation.name
}

output "investigation_state_machine_arn" {
  description = "Investigation workflow state machine ARN"
  value       = aws_sfn_state_machine.investigation.arn
}

output "investigation_state_machine_name" {
  description = "Investigation workflow state machine name"
  value       = aws_sfn_state_machine.investigation.name
}

output "execution_role_arn" {
  description = "Step Functions execution role ARN"
  value       = aws_iam_role.stepfunctions.arn
}
