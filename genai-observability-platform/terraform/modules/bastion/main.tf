# Bastion Host Module - Secure Access to Private Resources

# =============================================================================
# SECURITY GROUP
# =============================================================================

resource "aws_security_group" "bastion" {
  name_prefix = "${var.name_prefix}-bastion-"
  description = "Security group for bastion host"
  vpc_id      = var.vpc_id

  # SSH access (consider restricting to specific IPs)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "SSH access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-bastion-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# IAM ROLE FOR SSM
# =============================================================================

resource "aws_iam_role" "bastion" {
  name = "${var.name_prefix}-bastion-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.bastion.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "bastion" {
  name = "${var.name_prefix}-bastion-profile"
  role = aws_iam_role.bastion.name
}

# =============================================================================
# KEY PAIR (Optional - SSM preferred)
# =============================================================================

resource "aws_key_pair" "bastion" {
  count = var.ssh_public_key != "" ? 1 : 0

  key_name   = "${var.name_prefix}-bastion-key"
  public_key = var.ssh_public_key

  tags = var.tags
}

# =============================================================================
# EC2 INSTANCE
# =============================================================================

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.bastion.id]
  iam_instance_profile   = aws_iam_instance_profile.bastion.name
  key_name               = var.ssh_public_key != "" ? aws_key_pair.bastion[0].key_name : null

  associate_public_ip_address = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # IMDSv2
    http_put_response_hop_limit = 1
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    # Update system
    dnf update -y

    # Install useful tools
    dnf install -y postgresql15 mysql redis6 jq htop

    # Install AWS CLI v2 (if not present)
    if ! command -v aws &> /dev/null; then
      curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
      unzip awscliv2.zip
      ./aws/install
      rm -rf aws awscliv2.zip
    fi

    # Configure SSM agent
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent

    # Security hardening
    echo "AllowTcpForwarding yes" >> /etc/ssh/sshd_config
    systemctl restart sshd
  EOF
  )

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-bastion"
  })

  lifecycle {
    ignore_changes = [ami]
  }
}

# =============================================================================
# ELASTIC IP (Optional)
# =============================================================================

resource "aws_eip" "bastion" {
  count = var.assign_elastic_ip ? 1 : 0

  instance = aws_instance.bastion.id
  domain   = "vpc"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-bastion-eip"
  })
}

# =============================================================================
# CLOUDWATCH ALARMS
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "bastion_cpu" {
  alarm_name          = "${var.name_prefix}-bastion-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Bastion host CPU high"
  treat_missing_data  = "breaching"

  dimensions = {
    InstanceId = aws_instance.bastion.id
  }

  alarm_actions = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "bastion_status" {
  alarm_name          = "${var.name_prefix}-bastion-status"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "Bastion host status check failed"
  treat_missing_data  = "breaching"

  dimensions = {
    InstanceId = aws_instance.bastion.id
  }

  alarm_actions = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  tags = var.tags
}
