#!/bin/bash
#
# GenAI Observability Platform - Deployment Script
#
# Usage:
#   ./deploy.sh <environment> [action]
#
# Examples:
#   ./deploy.sh dev deploy        # Deploy to dev environment
#   ./deploy.sh staging deploy    # Deploy to staging
#   ./deploy.sh dev delete        # Delete dev stack
#

set -e

# Configuration
PROJECT_NAME="genai-observability"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <environment> [action]"
    echo "  environment: dev, staging, or prod"
    echo "  action: deploy (default), delete, or status"
    exit 1
fi

ENVIRONMENT=$1
ACTION=${2:-deploy}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
    exit 1
fi

# Stack names
TEMPLATES_BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-templates-$(aws sts get-caller-identity --query Account --output text)"
MAIN_STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

#============================================================================
# Deploy Action
#============================================================================
deploy() {
    log_info "Deploying GenAI Observability Platform to ${ENVIRONMENT}..."

    # Step 1: Create S3 bucket for templates (if it doesn't exist)
    log_info "Creating/verifying templates bucket: ${TEMPLATES_BUCKET}"
    if ! aws s3 ls "s3://${TEMPLATES_BUCKET}" 2>/dev/null; then
        aws s3 mb "s3://${TEMPLATES_BUCKET}" --region ${AWS_REGION}
        aws s3api put-bucket-versioning \
            --bucket ${TEMPLATES_BUCKET} \
            --versioning-configuration Status=Enabled
    fi

    # Step 2: Upload CloudFormation templates
    log_info "Uploading CloudFormation templates..."
    aws s3 sync . "s3://${TEMPLATES_BUCKET}/infrastructure/" \
        --exclude "*" \
        --include "*.yaml" \
        --delete

    # Step 3: Get parameters
    log_info "Configuring deployment parameters..."

    # Prompt for RDS password if not set
    if [ -z "$DB_PASSWORD" ]; then
        read -sp "Enter RDS master password (min 8 chars): " DB_PASSWORD
        echo
    fi

    # Optional: Alert email
    if [ -z "$ALERT_EMAIL" ]; then
        read -p "Enter alert email (or press Enter to skip): " ALERT_EMAIL
    fi

    # Step 4: Deploy individual stacks in order (for better error handling)
    log_info "Deploying Core infrastructure..."
    aws cloudformation deploy \
        --template-file core.yaml \
        --stack-name "${MAIN_STACK_NAME}-core" \
        --parameter-overrides \
            Environment=${ENVIRONMENT} \
            ProjectName=${PROJECT_NAME} \
        --capabilities CAPABILITY_NAMED_IAM \
        --region ${AWS_REGION} \
        --no-fail-on-empty-changeset

    log_info "Deploying Storage infrastructure..."
    aws cloudformation deploy \
        --template-file storage.yaml \
        --stack-name "${MAIN_STACK_NAME}-storage" \
        --parameter-overrides \
            Environment=${ENVIRONMENT} \
            ProjectName=${PROJECT_NAME} \
            DBMasterUsername=obsadmin \
            DBMasterPassword="${DB_PASSWORD}" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region ${AWS_REGION} \
        --no-fail-on-empty-changeset

    log_info "Deploying Notification infrastructure..."
    aws cloudformation deploy \
        --template-file notifications.yaml \
        --stack-name "${MAIN_STACK_NAME}-notifications" \
        --parameter-overrides \
            Environment=${ENVIRONMENT} \
            ProjectName=${PROJECT_NAME} \
            AlertEmail="${ALERT_EMAIL}" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region ${AWS_REGION} \
        --no-fail-on-empty-changeset

    log_info "Deploying Ingestion infrastructure..."
    aws cloudformation deploy \
        --template-file ingestion.yaml \
        --stack-name "${MAIN_STACK_NAME}-ingestion" \
        --parameter-overrides \
            Environment=${ENVIRONMENT} \
            ProjectName=${PROJECT_NAME} \
        --capabilities CAPABILITY_NAMED_IAM \
        --region ${AWS_REGION} \
        --no-fail-on-empty-changeset

    log_info "Deploying Processing infrastructure..."
    aws cloudformation deploy \
        --template-file processing.yaml \
        --stack-name "${MAIN_STACK_NAME}-processing" \
        --parameter-overrides \
            Environment=${ENVIRONMENT} \
            ProjectName=${PROJECT_NAME} \
        --capabilities CAPABILITY_NAMED_IAM \
        --region ${AWS_REGION} \
        --no-fail-on-empty-changeset

    # Step 5: Get outputs
    log_info "Deployment complete! Getting stack outputs..."
    echo ""
    echo "=========================================="
    echo "  GenAI Observability Platform Deployed"
    echo "=========================================="
    echo ""

    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name "${MAIN_STACK_NAME}-ingestion" \
        --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
        --output text \
        --region ${AWS_REGION})

    echo "API Endpoint: ${API_ENDPOINT}"
    echo ""
    echo "Next steps:"
    echo "1. Update Secrets Manager with your API keys:"
    echo "   - Anthropic API key: ${PROJECT_NAME}/${ENVIRONMENT}/anthropic-api-key"
    echo "   - Slack webhook: ${PROJECT_NAME}/${ENVIRONMENT}/slack-webhook"
    echo "   - PagerDuty key: ${PROJECT_NAME}/${ENVIRONMENT}/pagerduty-key"
    echo ""
    echo "2. Configure the SDK:"
    echo "   export GENAI_OBS_ENDPOINT='${API_ENDPOINT}'"
    echo "   export GENAI_OBS_API_KEY='your-api-key'"
    echo "   export GENAI_OBS_AGENT_ID='your-agent-id'"
    echo ""
}

#============================================================================
# Delete Action
#============================================================================
delete_stack() {
    log_warn "Deleting GenAI Observability Platform from ${ENVIRONMENT}..."
    read -p "Are you sure? This will delete all data! (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Deletion cancelled."
        exit 0
    fi

    # Delete in reverse order
    log_info "Deleting Processing stack..."
    aws cloudformation delete-stack --stack-name "${MAIN_STACK_NAME}-processing" --region ${AWS_REGION} 2>/dev/null || true
    aws cloudformation wait stack-delete-complete --stack-name "${MAIN_STACK_NAME}-processing" --region ${AWS_REGION} 2>/dev/null || true

    log_info "Deleting Ingestion stack..."
    aws cloudformation delete-stack --stack-name "${MAIN_STACK_NAME}-ingestion" --region ${AWS_REGION} 2>/dev/null || true
    aws cloudformation wait stack-delete-complete --stack-name "${MAIN_STACK_NAME}-ingestion" --region ${AWS_REGION} 2>/dev/null || true

    log_info "Deleting Notification stack..."
    aws cloudformation delete-stack --stack-name "${MAIN_STACK_NAME}-notifications" --region ${AWS_REGION} 2>/dev/null || true
    aws cloudformation wait stack-delete-complete --stack-name "${MAIN_STACK_NAME}-notifications" --region ${AWS_REGION} 2>/dev/null || true

    log_info "Deleting Storage stack..."
    aws cloudformation delete-stack --stack-name "${MAIN_STACK_NAME}-storage" --region ${AWS_REGION} 2>/dev/null || true
    aws cloudformation wait stack-delete-complete --stack-name "${MAIN_STACK_NAME}-storage" --region ${AWS_REGION} 2>/dev/null || true

    log_info "Deleting Core stack..."
    aws cloudformation delete-stack --stack-name "${MAIN_STACK_NAME}-core" --region ${AWS_REGION} 2>/dev/null || true
    aws cloudformation wait stack-delete-complete --stack-name "${MAIN_STACK_NAME}-core" --region ${AWS_REGION} 2>/dev/null || true

    log_info "All stacks deleted."
}

#============================================================================
# Status Action
#============================================================================
status() {
    log_info "Checking status of GenAI Observability Platform in ${ENVIRONMENT}..."
    echo ""

    for stack in "core" "storage" "notifications" "ingestion" "processing"; do
        stack_name="${MAIN_STACK_NAME}-${stack}"
        status=$(aws cloudformation describe-stacks \
            --stack-name ${stack_name} \
            --query "Stacks[0].StackStatus" \
            --output text \
            --region ${AWS_REGION} 2>/dev/null || echo "NOT_FOUND")

        if [ "$status" == "CREATE_COMPLETE" ] || [ "$status" == "UPDATE_COMPLETE" ]; then
            echo -e "  ${GREEN}✓${NC} ${stack}: ${status}"
        elif [ "$status" == "NOT_FOUND" ]; then
            echo -e "  ${YELLOW}○${NC} ${stack}: Not deployed"
        else
            echo -e "  ${RED}✗${NC} ${stack}: ${status}"
        fi
    done
    echo ""
}

#============================================================================
# Main
#============================================================================
case $ACTION in
    deploy)
        deploy
        ;;
    delete)
        delete_stack
        ;;
    status)
        status
        ;;
    *)
        log_error "Unknown action: $ACTION"
        echo "Valid actions: deploy, delete, status"
        exit 1
        ;;
esac
