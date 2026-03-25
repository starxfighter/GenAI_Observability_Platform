# CI/CD Module - CodePipeline and CodeBuild

# =============================================================================
# S3 BUCKET FOR ARTIFACTS
# =============================================================================

resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.name_prefix}-cicd-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-cicd-artifacts"
  })
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# CODEBUILD PROJECT - API
# =============================================================================

resource "aws_codebuild_project" "api" {
  name          = "${var.name_prefix}-api-build"
  description   = "Build and deploy API Docker image"
  build_timeout = 30
  service_role  = aws_iam_role.codebuild.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_MEDIUM"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true  # Required for Docker

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "ECR_REPOSITORY"
      value = var.ecr_repository_url
    }

    environment_variable {
      name  = "ECS_CLUSTER"
      value = var.ecs_cluster_name
    }

    environment_variable {
      name  = "ECS_SERVICE"
      value = var.ecs_service_name
    }

    environment_variable {
      name  = "ENVIRONMENT"
      value = var.environment
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = <<-EOF
      version: 0.2
      phases:
        pre_build:
          commands:
            - echo Logging in to Amazon ECR...
            - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY
            - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
            - IMAGE_TAG=$${COMMIT_HASH:=latest}
        build:
          commands:
            - echo Build started on `date`
            - echo Building the Docker image...
            - cd api
            - docker build -t $ECR_REPOSITORY:latest .
            - docker tag $ECR_REPOSITORY:latest $ECR_REPOSITORY:$IMAGE_TAG
        post_build:
          commands:
            - echo Build completed on `date`
            - echo Pushing the Docker image...
            - docker push $ECR_REPOSITORY:latest
            - docker push $ECR_REPOSITORY:$IMAGE_TAG
            - echo Writing image definitions file...
            - printf '[{"name":"api","imageUri":"%s"}]' $ECR_REPOSITORY:$IMAGE_TAG > imagedefinitions.json
      artifacts:
        files:
          - imagedefinitions.json
    EOF
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebuild.name
      stream_name = "api-build"
    }
  }

  tags = var.tags
}

# =============================================================================
# CODEBUILD PROJECT - FRONTEND
# =============================================================================

resource "aws_codebuild_project" "frontend" {
  name          = "${var.name_prefix}-frontend-build"
  description   = "Build and deploy React frontend"
  build_timeout = 20
  service_role  = aws_iam_role.codebuild.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "S3_BUCKET"
      value = var.frontend_bucket_name
    }

    environment_variable {
      name  = "CLOUDFRONT_DISTRIBUTION_ID"
      value = var.cloudfront_distribution_id
    }

    environment_variable {
      name  = "VITE_API_URL"
      value = var.api_url
    }

    environment_variable {
      name  = "VITE_COGNITO_USER_POOL_ID"
      value = var.cognito_user_pool_id
    }

    environment_variable {
      name  = "VITE_COGNITO_CLIENT_ID"
      value = var.cognito_client_id
    }

    environment_variable {
      name  = "VITE_REGION"
      value = data.aws_region.current.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = <<-EOF
      version: 0.2
      phases:
        install:
          runtime-versions:
            nodejs: 18
          commands:
            - cd frontend
            - npm ci
        build:
          commands:
            - echo Build started on `date`
            - npm run build
        post_build:
          commands:
            - echo Deploying to S3...
            - aws s3 sync dist/ s3://$S3_BUCKET/ --delete
            - echo Invalidating CloudFront cache...
            - aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DISTRIBUTION_ID --paths "/*"
      artifacts:
        files:
          - frontend/dist/**/*
        base-directory: frontend
    EOF
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebuild.name
      stream_name = "frontend-build"
    }
  }

  tags = var.tags
}

# =============================================================================
# CODEBUILD PROJECT - LAMBDA
# =============================================================================

resource "aws_codebuild_project" "lambda" {
  name          = "${var.name_prefix}-lambda-build"
  description   = "Build and deploy Lambda functions"
  build_timeout = 20
  service_role  = aws_iam_role.codebuild.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "LAMBDA_PREFIX"
      value = var.name_prefix
    }

    environment_variable {
      name  = "ARTIFACTS_BUCKET"
      value = aws_s3_bucket.artifacts.id
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = <<-EOF
      version: 0.2
      phases:
        install:
          runtime-versions:
            python: 3.11
          commands:
            - pip install --upgrade pip
        build:
          commands:
            - echo Building Lambda functions...
            - cd lambda
            - |
              for dir in */; do
                if [ -f "$dir/requirements.txt" ]; then
                  echo "Building $dir"
                  cd "$dir"
                  pip install -r requirements.txt -t .
                  zip -r "../$${dir%/}.zip" .
                  cd ..
                fi
              done
        post_build:
          commands:
            - echo Deploying Lambda functions...
            - |
              for zip in *.zip; do
                func_name="$LAMBDA_PREFIX-$${zip%.zip}"
                echo "Updating $func_name"
                aws lambda update-function-code --function-name "$func_name" --zip-file "fileb://$zip" || true
              done
      artifacts:
        files:
          - lambda/*.zip
    EOF
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebuild.name
      stream_name = "lambda-build"
    }
  }

  tags = var.tags
}

# =============================================================================
# CODEPIPELINE
# =============================================================================

resource "aws_codepipeline" "main" {
  name     = "${var.name_prefix}-pipeline"
  role_arn = aws_iam_role.codepipeline.arn

  artifact_store {
    location = aws_s3_bucket.artifacts.id
    type     = "S3"
  }

  # Source Stage
  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = var.codestar_connection_arn
        FullRepositoryId = var.github_repository
        BranchName       = var.github_branch
      }
    }
  }

  # Build Stage
  stage {
    name = "Build"

    action {
      name             = "BuildAPI"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["api_build_output"]
      version          = "1"
      run_order        = 1

      configuration = {
        ProjectName = aws_codebuild_project.api.name
      }
    }

    action {
      name             = "BuildFrontend"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["frontend_build_output"]
      version          = "1"
      run_order        = 1

      configuration = {
        ProjectName = aws_codebuild_project.frontend.name
      }
    }

    action {
      name             = "BuildLambda"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["lambda_build_output"]
      version          = "1"
      run_order        = 1

      configuration = {
        ProjectName = aws_codebuild_project.lambda.name
      }
    }
  }

  # Deploy Stage
  stage {
    name = "Deploy"

    action {
      name            = "DeployAPI"
      category        = "Deploy"
      owner           = "AWS"
      provider        = "ECS"
      input_artifacts = ["api_build_output"]
      version         = "1"

      configuration = {
        ClusterName = var.ecs_cluster_name
        ServiceName = var.ecs_service_name
        FileName    = "imagedefinitions.json"
      }
    }
  }

  tags = var.tags
}

# =============================================================================
# CLOUDWATCH LOG GROUP
# =============================================================================

resource "aws_cloudwatch_log_group" "codebuild" {
  name              = "/aws/codebuild/${var.name_prefix}"
  retention_in_days = 14

  tags = var.tags
}

# =============================================================================
# IAM ROLE - CODEBUILD
# =============================================================================

resource "aws_iam_role" "codebuild" {
  name = "${var.name_prefix}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "codebuild" {
  name = "${var.name_prefix}-codebuild-policy"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.artifacts.arn}/*",
          "arn:aws:s3:::${var.frontend_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = var.ecr_repository_arn
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionCode"
        ]
        Resource = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.name_prefix}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudfront:CreateInvalidation"
        ]
        Resource = "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:distribution/${var.cloudfront_distribution_id}"
      }
    ]
  })
}

# =============================================================================
# IAM ROLE - CODEPIPELINE
# =============================================================================

resource "aws_iam_role" "codepipeline" {
  name = "${var.name_prefix}-codepipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codepipeline.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "codepipeline" {
  name = "${var.name_prefix}-codepipeline-policy"
  role = aws_iam_role.codepipeline.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:GetBucketVersioning",
          "s3:PutObject"
        ]
        Resource = [
          aws_s3_bucket.artifacts.arn,
          "${aws_s3_bucket.artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "codebuild:BatchGetBuilds",
          "codebuild:StartBuild"
        ]
        Resource = [
          aws_codebuild_project.api.arn,
          aws_codebuild_project.frontend.arn,
          aws_codebuild_project.lambda.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "codestar-connections:UseConnection"
        ]
        Resource = var.codestar_connection_arn
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = "*"
        Condition = {
          StringEqualsIfExists = {
            "iam:PassedToService" = ["ecs-tasks.amazonaws.com"]
          }
        }
      }
    ]
  })
}

# =============================================================================
# DATA SOURCES
# =============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
