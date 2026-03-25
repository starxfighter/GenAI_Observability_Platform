#!/bin/bash
#
# Build script for GenAI Observability Platform Lambda functions
#
# Usage:
#   ./build.sh [function_name]     # Build specific function
#   ./build.sh all                 # Build all functions
#   ./build.sh clean               # Clean build artifacts
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
DIST_DIR="${SCRIPT_DIR}/dist"

# Lambda functions to build
FUNCTIONS=(
    "authorizer"
    "ingestion"
    "health"
    "stream_processor"
    "anomaly_detector"
    "llm_investigator"
    "slack_formatter"
    "pagerduty_formatter"
    "alert_deduplicator"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Clean build artifacts
clean() {
    log_info "Cleaning build artifacts..."
    rm -rf "${BUILD_DIR}"
    rm -rf "${DIST_DIR}"
    log_info "Clean complete"
}

# Build shared layer
build_shared_layer() {
    log_info "Building shared layer..."

    local layer_build="${BUILD_DIR}/layers/observability-common"
    local layer_dist="${DIST_DIR}/layers"

    mkdir -p "${layer_build}/python"
    mkdir -p "${layer_dist}"

    # Copy shared code
    cp -r "${SCRIPT_DIR}/shared/observability_common" "${layer_build}/python/"

    # Install shared dependencies
    if [ -f "${SCRIPT_DIR}/shared/requirements.txt" ]; then
        pip install -r "${SCRIPT_DIR}/shared/requirements.txt" \
            -t "${layer_build}/python" \
            --quiet \
            --upgrade
    fi

    # Remove unnecessary files
    find "${layer_build}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${layer_build}" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "${layer_build}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
    find "${layer_build}" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

    # Create zip
    cd "${layer_build}"
    zip -r "${layer_dist}/observability-common-layer.zip" . -q
    cd "${SCRIPT_DIR}"

    log_info "Shared layer built: ${layer_dist}/observability-common-layer.zip"
}

# Build a single Lambda function
build_function() {
    local func_name=$1
    local func_dir="${SCRIPT_DIR}/${func_name}"

    if [ ! -d "${func_dir}" ]; then
        log_error "Function directory not found: ${func_dir}"
        return 1
    fi

    log_info "Building function: ${func_name}"

    local func_build="${BUILD_DIR}/functions/${func_name}"
    local func_dist="${DIST_DIR}/functions"

    mkdir -p "${func_build}"
    mkdir -p "${func_dist}"

    # Copy function code
    cp "${func_dir}/handler.py" "${func_build}/"

    # Copy any additional Python files
    find "${func_dir}" -name "*.py" -not -name "handler.py" -exec cp {} "${func_build}/" \; 2>/dev/null || true

    # Install function-specific dependencies
    if [ -f "${func_dir}/requirements.txt" ]; then
        # Filter out boto3 as it's provided by Lambda runtime
        grep -v "^boto3" "${func_dir}/requirements.txt" > "${func_build}/requirements_filtered.txt" 2>/dev/null || true

        if [ -s "${func_build}/requirements_filtered.txt" ]; then
            pip install -r "${func_build}/requirements_filtered.txt" \
                -t "${func_build}" \
                --quiet \
                --upgrade
        fi
        rm -f "${func_build}/requirements_filtered.txt"
    fi

    # Remove unnecessary files
    find "${func_build}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${func_build}" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "${func_build}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
    find "${func_build}" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

    # Create zip
    cd "${func_build}"
    zip -r "${func_dist}/${func_name}.zip" . -q
    cd "${SCRIPT_DIR}"

    local zip_size=$(du -h "${func_dist}/${func_name}.zip" | cut -f1)
    log_info "Function built: ${func_dist}/${func_name}.zip (${zip_size})"
}

# Build all functions
build_all() {
    log_info "Building all Lambda functions..."

    # Build shared layer first
    build_shared_layer

    # Build each function
    for func in "${FUNCTIONS[@]}"; do
        build_function "${func}"
    done

    log_info "All functions built successfully!"

    # Print summary
    echo ""
    echo "Build Summary:"
    echo "=============="
    echo "Layer:"
    ls -lh "${DIST_DIR}/layers/" 2>/dev/null || echo "  No layers found"
    echo ""
    echo "Functions:"
    ls -lh "${DIST_DIR}/functions/" 2>/dev/null || echo "  No functions found"
}

# Main
main() {
    local command=${1:-"all"}

    case "${command}" in
        clean)
            clean
            ;;
        all)
            clean
            build_all
            ;;
        layer)
            build_shared_layer
            ;;
        *)
            # Check if it's a valid function name
            if [[ " ${FUNCTIONS[*]} " =~ " ${command} " ]]; then
                build_function "${command}"
            else
                log_error "Unknown command or function: ${command}"
                echo ""
                echo "Usage: $0 [command|function_name]"
                echo ""
                echo "Commands:"
                echo "  all    - Build all functions (default)"
                echo "  clean  - Clean build artifacts"
                echo "  layer  - Build shared layer only"
                echo ""
                echo "Functions:"
                for func in "${FUNCTIONS[@]}"; do
                    echo "  ${func}"
                done
                exit 1
            fi
            ;;
    esac
}

main "$@"
