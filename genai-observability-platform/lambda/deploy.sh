#!/bin/bash
#
# Deploy script for GenAI Observability Platform Lambda functions
#
# Usage:
#   ./deploy.sh [function_name]              # Deploy specific function
#   ./deploy.sh all                          # Deploy all functions
#   ./deploy.sh layer                        # Deploy shared layer
#   ./deploy.sh status                       # Show deployment status
#
# Environment Variables:
#   AWS_REGION          - AWS region (default: us-east-1)
#   ENVIRONMENT         - Environment name (default: dev)
#   S3_BUCKET           - S3 bucket for Lambda artifacts
#   STACK_NAME          - CloudFormation stack name prefix
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
S3_BUCKET="${S3_BUCKET:-}"
STACK_NAME="${STACK_NAME:-genai-observability}"

# Lambda function configuration
declare -A FUNCTION_NAMES=(
    ["authorizer"]="${STACK_NAME}-${ENVIRONMENT}-authorizer"
    ["ingestion"]="${STACK_NAME}-${ENVIRONMENT}-ingestion"
    ["health"]="${STACK_NAME}-${ENVIRONMENT}-health"
    ["stream_processor"]="${STACK_NAME}-${ENVIRONMENT}-stream-processor"
    ["anomaly_detector"]="${STACK_NAME}-${ENVIRONMENT}-anomaly-detector"
    ["llm_investigator"]="${STACK_NAME}-${ENVIRONMENT}-llm-investigator"
    ["slack_formatter"]="${STACK_NAME}-${ENVIRONMENT}-slack-formatter"
    ["pagerduty_formatter"]="${STACK_NAME}-${ENVIRONMENT}-pagerduty-formatter"
    ["alert_deduplicator"]="${STACK_NAME}-${ENVIRONMENT}-alert-deduplicator"
)

LAYER_NAME="${STACK_NAME}-${ENVIRONMENT}-observability-common"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi

    # Check S3 bucket is set
    if [ -z "${S3_BUCKET}" ]; then
        log_error "S3_BUCKET environment variable not set"
        echo "Please set S3_BUCKET to the bucket where Lambda artifacts should be stored"
        exit 1
    fi

    # Check if build artifacts exist
    if [ ! -d "${DIST_DIR}" ]; then
        log_error "Build artifacts not found. Run ./build.sh first"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# Upload artifact to S3
upload_to_s3() {
    local local_path=$1
    local s3_key=$2

    log_info "Uploading ${local_path} to s3://${S3_BUCKET}/${s3_key}"

    aws s3 cp "${local_path}" "s3://${S3_BUCKET}/${s3_key}" \
        --region "${AWS_REGION}" \
        --quiet

    echo "s3://${S3_BUCKET}/${s3_key}"
}

# Deploy shared layer
deploy_layer() {
    log_step "Deploying shared layer..."

    local layer_zip="${DIST_DIR}/layers/observability-common-layer.zip"

    if [ ! -f "${layer_zip}" ]; then
        log_error "Layer artifact not found: ${layer_zip}"
        log_warn "Run ./build.sh layer first"
        return 1
    fi

    # Upload to S3
    local timestamp=$(date +%Y%m%d%H%M%S)
    local s3_key="lambda-layers/observability-common-${timestamp}.zip"
    upload_to_s3 "${layer_zip}" "${s3_key}"

    # Publish layer version
    log_info "Publishing layer version..."
    local layer_arn=$(aws lambda publish-layer-version \
        --layer-name "${LAYER_NAME}" \
        --description "GenAI Observability shared utilities" \
        --content "S3Bucket=${S3_BUCKET},S3Key=${s3_key}" \
        --compatible-runtimes python3.11 python3.12 \
        --region "${AWS_REGION}" \
        --query 'LayerVersionArn' \
        --output text)

    log_info "Layer deployed: ${layer_arn}"
    echo "${layer_arn}"
}

# Deploy a single Lambda function
deploy_function() {
    local func_key=$1
    local func_name="${FUNCTION_NAMES[${func_key}]}"
    local func_zip="${DIST_DIR}/functions/${func_key}.zip"

    if [ -z "${func_name}" ]; then
        log_error "Unknown function: ${func_key}"
        return 1
    fi

    if [ ! -f "${func_zip}" ]; then
        log_error "Function artifact not found: ${func_zip}"
        log_warn "Run ./build.sh ${func_key} first"
        return 1
    fi

    log_step "Deploying function: ${func_key} -> ${func_name}"

    # Upload to S3
    local timestamp=$(date +%Y%m%d%H%M%S)
    local s3_key="lambda-functions/${func_key}-${timestamp}.zip"
    upload_to_s3 "${func_zip}" "${s3_key}"

    # Check if function exists
    if aws lambda get-function --function-name "${func_name}" --region "${AWS_REGION}" &> /dev/null; then
        # Update existing function
        log_info "Updating existing function..."
        aws lambda update-function-code \
            --function-name "${func_name}" \
            --s3-bucket "${S3_BUCKET}" \
            --s3-key "${s3_key}" \
            --region "${AWS_REGION}" \
            --query 'FunctionArn' \
            --output text

        # Wait for update to complete
        aws lambda wait function-updated \
            --function-name "${func_name}" \
            --region "${AWS_REGION}"

        log_info "Function updated: ${func_name}"
    else
        log_warn "Function ${func_name} does not exist. Deploy infrastructure first."
        return 1
    fi
}

# Deploy all functions
deploy_all() {
    log_step "Deploying all Lambda functions..."

    # Deploy layer first
    local layer_arn
    layer_arn=$(deploy_layer)

    if [ $? -ne 0 ]; then
        log_error "Failed to deploy layer"
        return 1
    fi

    # Deploy each function
    local failed=0
    for func_key in "${!FUNCTION_NAMES[@]}"; do
        if ! deploy_function "${func_key}"; then
            log_error "Failed to deploy: ${func_key}"
            ((failed++))
        fi
    done

    if [ ${failed} -gt 0 ]; then
        log_warn "${failed} function(s) failed to deploy"
        return 1
    fi

    log_info "All functions deployed successfully!"
}

# Update function to use latest layer
update_function_layer() {
    local func_key=$1
    local layer_arn=$2
    local func_name="${FUNCTION_NAMES[${func_key}]}"

    if [ -z "${func_name}" ] || [ -z "${layer_arn}" ]; then
        return 1
    fi

    log_info "Updating ${func_name} to use layer..."

    aws lambda update-function-configuration \
        --function-name "${func_name}" \
        --layers "${layer_arn}" \
        --region "${AWS_REGION}" \
        --query 'FunctionArn' \
        --output text > /dev/null

    aws lambda wait function-updated \
        --function-name "${func_name}" \
        --region "${AWS_REGION}"
}

# Show deployment status
show_status() {
    log_step "Deployment Status"
    echo ""

    # Show layer info
    echo "Layer: ${LAYER_NAME}"
    echo "------"
    aws lambda list-layer-versions \
        --layer-name "${LAYER_NAME}" \
        --region "${AWS_REGION}" \
        --query 'LayerVersions[0].[Version,Description,CreatedDate]' \
        --output table 2>/dev/null || echo "  Layer not found"
    echo ""

    # Show function info
    echo "Functions:"
    echo "----------"
    for func_key in "${!FUNCTION_NAMES[@]}"; do
        local func_name="${FUNCTION_NAMES[${func_key}]}"
        printf "%-20s " "${func_key}:"

        local status=$(aws lambda get-function \
            --function-name "${func_name}" \
            --region "${AWS_REGION}" \
            --query 'Configuration.[State,LastModified]' \
            --output text 2>/dev/null)

        if [ -n "${status}" ]; then
            echo "${status}"
        else
            echo "NOT DEPLOYED"
        fi
    done
}

# Show help
show_help() {
    echo "GenAI Observability Platform - Lambda Deployment Script"
    echo ""
    echo "Usage: $0 [command|function_name]"
    echo ""
    echo "Commands:"
    echo "  all      - Deploy all functions and layer (default)"
    echo "  layer    - Deploy shared layer only"
    echo "  status   - Show deployment status"
    echo "  help     - Show this help message"
    echo ""
    echo "Functions:"
    for func_key in "${!FUNCTION_NAMES[@]}"; do
        echo "  ${func_key}"
    done
    echo ""
    echo "Environment Variables:"
    echo "  AWS_REGION   - AWS region (current: ${AWS_REGION})"
    echo "  ENVIRONMENT  - Environment name (current: ${ENVIRONMENT})"
    echo "  S3_BUCKET    - S3 bucket for artifacts (current: ${S3_BUCKET:-NOT SET})"
    echo "  STACK_NAME   - Stack name prefix (current: ${STACK_NAME})"
}

# Main
main() {
    local command=${1:-"all"}

    case "${command}" in
        help|--help|-h)
            show_help
            ;;
        status)
            show_status
            ;;
        layer)
            check_prerequisites
            deploy_layer
            ;;
        all)
            check_prerequisites
            deploy_all
            ;;
        *)
            # Check if it's a valid function name
            if [[ -v "FUNCTION_NAMES[${command}]" ]]; then
                check_prerequisites
                deploy_function "${command}"
            else
                log_error "Unknown command or function: ${command}"
                echo ""
                show_help
                exit 1
            fi
            ;;
    esac
}

main "$@"
