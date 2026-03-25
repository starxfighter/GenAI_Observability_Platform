# Bastion Host Module - Outputs

output "instance_id" {
  description = "Bastion instance ID"
  value       = aws_instance.bastion.id
}

output "public_ip" {
  description = "Bastion public IP"
  value       = var.assign_elastic_ip ? aws_eip.bastion[0].public_ip : aws_instance.bastion.public_ip
}

output "private_ip" {
  description = "Bastion private IP"
  value       = aws_instance.bastion.private_ip
}

output "security_group_id" {
  description = "Bastion security group ID"
  value       = aws_security_group.bastion.id
}

output "ssm_connect_command" {
  description = "Command to connect via SSM"
  value       = "aws ssm start-session --target ${aws_instance.bastion.id}"
}

output "ssh_connect_command" {
  description = "Command to connect via SSH"
  value       = var.ssh_public_key != "" ? "ssh -i <key-file> ec2-user@${var.assign_elastic_ip ? aws_eip.bastion[0].public_ip : aws_instance.bastion.public_ip}" : "Use SSM Session Manager instead"
}
