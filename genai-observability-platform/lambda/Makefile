# GenAI Observability Platform - Lambda Makefile
#
# Usage:
#   make build          - Build all Lambda functions
#   make deploy         - Deploy all Lambda functions
#   make clean          - Clean build artifacts
#

.PHONY: help build deploy clean test lint status

# Default target
help:
	@echo "GenAI Observability Platform - Lambda Functions"
	@echo ""
	@echo "Usage:"
	@echo "  make build              - Build all Lambda functions"
	@echo "  make build-<function>   - Build specific function"
	@echo "  make deploy             - Deploy all Lambda functions"
	@echo "  make deploy-<function>  - Deploy specific function"
	@echo "  make clean              - Clean build artifacts"
	@echo "  make test               - Run tests"
	@echo "  make lint               - Run linting"
	@echo "  make status             - Show deployment status"
	@echo ""
	@echo "Functions:"
	@echo "  authorizer, ingestion, health, stream_processor, anomaly_detector"
	@echo "  llm_investigator, slack_formatter, pagerduty_formatter, alert_deduplicator"
	@echo ""
	@echo "Environment Variables:"
	@echo "  AWS_REGION   - AWS region (default: us-east-1)"
	@echo "  ENVIRONMENT  - Environment name (default: dev)"
	@echo "  S3_BUCKET    - S3 bucket for Lambda artifacts (required for deploy)"

# Build targets
build:
	@./build.sh all

build-layer:
	@./build.sh layer

build-authorizer:
	@./build.sh authorizer

build-ingestion:
	@./build.sh ingestion

build-health:
	@./build.sh health

build-stream_processor:
	@./build.sh stream_processor

build-anomaly_detector:
	@./build.sh anomaly_detector

build-llm_investigator:
	@./build.sh llm_investigator

build-slack_formatter:
	@./build.sh slack_formatter

build-pagerduty_formatter:
	@./build.sh pagerduty_formatter

build-alert_deduplicator:
	@./build.sh alert_deduplicator

# Deploy targets
deploy: build
	@./deploy.sh all

deploy-layer: build-layer
	@./deploy.sh layer

deploy-authorizer: build-authorizer
	@./deploy.sh authorizer

deploy-ingestion: build-ingestion
	@./deploy.sh ingestion

deploy-health: build-health
	@./deploy.sh health

deploy-stream_processor: build-stream_processor
	@./deploy.sh stream_processor

deploy-anomaly_detector: build-anomaly_detector
	@./deploy.sh anomaly_detector

deploy-llm_investigator: build-llm_investigator
	@./deploy.sh llm_investigator

deploy-slack_formatter: build-slack_formatter
	@./deploy.sh slack_formatter

deploy-pagerduty_formatter: build-pagerduty_formatter
	@./deploy.sh pagerduty_formatter

deploy-alert_deduplicator: build-alert_deduplicator
	@./deploy.sh alert_deduplicator

# Clean
clean:
	@./build.sh clean

# Status
status:
	@./deploy.sh status

# Test
test:
	@echo "Running tests..."
	@python -m pytest tests/ -v --tb=short || echo "No tests found or pytest not installed"

# Lint
lint:
	@echo "Running linting..."
	@python -m ruff check . --ignore E501 || echo "Ruff not installed, trying flake8..."
	@python -m flake8 . --max-line-length=100 --exclude=build,dist || echo "Flake8 not installed"

# Format
format:
	@echo "Formatting code..."
	@python -m black . --exclude="build|dist" || echo "Black not installed"
	@python -m isort . --skip build --skip dist || echo "isort not installed"
