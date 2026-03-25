#!/bin/bash
#
# Run all tests for the GenAI Observability Platform
#
# Usage:
#   ./run-tests.sh           # Run all tests
#   ./run-tests.sh sdk       # Run SDK tests only
#   ./run-tests.sh lambda    # Run Lambda tests only
#   ./run-tests.sh api       # Run API tests only
#   ./run-tests.sh coverage  # Run all tests with coverage
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

run_sdk_tests() {
    log_step "Running SDK tests..."
    cd "${PROJECT_ROOT}/sdk/python"

    if [ ! -d ".venv" ]; then
        python -m venv .venv
    fi

    source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
    pip install -e ".[dev]" -q

    if [ "$1" == "coverage" ]; then
        pytest --cov=genai_observability --cov-report=html --cov-report=term-missing
    else
        pytest -v
    fi

    deactivate 2>/dev/null || true
    cd "${PROJECT_ROOT}"
}

run_lambda_tests() {
    log_step "Running Lambda tests..."
    cd "${PROJECT_ROOT}/lambda"

    if [ ! -d ".venv" ]; then
        python -m venv .venv
    fi

    source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
    pip install -r requirements-test.txt -q
    pip install -r shared/requirements.txt -q

    # Add Lambda handlers to path
    export PYTHONPATH="${PROJECT_ROOT}/lambda:${PROJECT_ROOT}/lambda/shared:${PYTHONPATH}"

    if [ "$1" == "coverage" ]; then
        pytest --cov=. --cov-report=html --cov-report=term-missing
    else
        pytest -v
    fi

    deactivate 2>/dev/null || true
    cd "${PROJECT_ROOT}"
}

run_api_tests() {
    log_step "Running API tests..."
    cd "${PROJECT_ROOT}/api"

    if [ ! -d ".venv" ]; then
        python -m venv .venv
    fi

    source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
    pip install -e ".[dev]" -q

    if [ "$1" == "coverage" ]; then
        pytest --cov=observability_api --cov-report=html --cov-report=term-missing
    else
        pytest -v
    fi

    deactivate 2>/dev/null || true
    cd "${PROJECT_ROOT}"
}

run_all_tests() {
    local coverage_flag="$1"

    log_info "Running all tests for GenAI Observability Platform"
    echo ""

    run_sdk_tests "$coverage_flag"
    echo ""

    run_lambda_tests "$coverage_flag"
    echo ""

    run_api_tests "$coverage_flag"
    echo ""

    log_info "All tests completed!"
}

# Main
case "${1:-all}" in
    sdk)
        run_sdk_tests "$2"
        ;;
    lambda)
        run_lambda_tests "$2"
        ;;
    api)
        run_api_tests "$2"
        ;;
    coverage)
        run_all_tests "coverage"
        ;;
    all)
        run_all_tests "$2"
        ;;
    *)
        echo "Usage: $0 [sdk|lambda|api|coverage|all]"
        exit 1
        ;;
esac
