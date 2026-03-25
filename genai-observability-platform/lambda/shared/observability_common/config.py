"""
Configuration management for Lambda functions.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Configuration loaded from environment variables."""

    # Environment
    environment: str = field(default_factory=lambda: os.environ.get("ENVIRONMENT", "dev"))
    aws_region: str = field(default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1"))

    # Kinesis
    events_stream_name: str = field(
        default_factory=lambda: os.environ.get("EVENTS_STREAM_NAME", "")
    )

    # Storage - S3
    raw_data_bucket: str = field(
        default_factory=lambda: os.environ.get("RAW_DATA_BUCKET", "")
    )
    processed_data_bucket: str = field(
        default_factory=lambda: os.environ.get("PROCESSED_DATA_BUCKET", "")
    )

    # Storage - DynamoDB
    error_store_table: str = field(
        default_factory=lambda: os.environ.get("ERROR_STORE_TABLE", "")
    )
    alert_cache_table: str = field(
        default_factory=lambda: os.environ.get("ALERT_CACHE_TABLE", "")
    )
    agent_metadata_table: str = field(
        default_factory=lambda: os.environ.get("AGENT_METADATA_TABLE", "")
    )
    investigation_results_table: str = field(
        default_factory=lambda: os.environ.get("INVESTIGATION_RESULTS_TABLE", "")
    )

    # Storage - Timestream
    timestream_database: str = field(
        default_factory=lambda: os.environ.get("TIMESTREAM_DATABASE", "")
    )
    timestream_latency_table: str = field(
        default_factory=lambda: os.environ.get("TIMESTREAM_LATENCY_TABLE", "latency-metrics")
    )
    timestream_token_table: str = field(
        default_factory=lambda: os.environ.get("TIMESTREAM_TOKEN_TABLE", "token-metrics")
    )
    timestream_cost_table: str = field(
        default_factory=lambda: os.environ.get("TIMESTREAM_COST_TABLE", "cost-metrics")
    )

    # Storage - OpenSearch
    opensearch_endpoint: str = field(
        default_factory=lambda: os.environ.get("OPENSEARCH_ENDPOINT", "")
    )

    # SNS Topics
    critical_sns_topic: str = field(
        default_factory=lambda: os.environ.get("CRITICAL_SNS_TOPIC", "")
    )
    warning_sns_topic: str = field(
        default_factory=lambda: os.environ.get("WARNING_SNS_TOPIC", "")
    )
    info_sns_topic: str = field(
        default_factory=lambda: os.environ.get("INFO_SNS_TOPIC", "")
    )
    investigation_sns_topic: str = field(
        default_factory=lambda: os.environ.get("INVESTIGATION_SNS_TOPIC", "")
    )
    notification_topic: str = field(
        default_factory=lambda: os.environ.get("NOTIFICATION_TOPIC", "")
    )

    # Lambda functions
    anomaly_detector_function: str = field(
        default_factory=lambda: os.environ.get("ANOMALY_DETECTOR_FUNCTION", "")
    )
    investigation_function: str = field(
        default_factory=lambda: os.environ.get("INVESTIGATION_FUNCTION", "")
    )

    # Secrets ARNs
    anthropic_secret_arn: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_SECRET_ARN", "")
    )
    slack_secret_arn: str = field(
        default_factory=lambda: os.environ.get("SLACK_SECRET_ARN", "")
    )
    pagerduty_secret_arn: str = field(
        default_factory=lambda: os.environ.get("PAGERDUTY_SECRET_ARN", "")
    )

    # Anomaly detection thresholds
    error_rate_threshold: float = field(
        default_factory=lambda: float(os.environ.get("ERROR_RATE_THRESHOLD", "0.1"))
    )
    latency_threshold_ms: float = field(
        default_factory=lambda: float(os.environ.get("LATENCY_THRESHOLD_MS", "5000"))
    )
    error_count_threshold: int = field(
        default_factory=lambda: int(os.environ.get("ERROR_COUNT_THRESHOLD", "5"))
    )

    # Deduplication
    dedup_window_hours: int = field(
        default_factory=lambda: int(os.environ.get("DEDUP_WINDOW_HOURS", "24"))
    )

    # TTL for stored data (in days)
    error_ttl_days: int = field(
        default_factory=lambda: int(os.environ.get("ERROR_TTL_DAYS", "90"))
    )
    investigation_ttl_days: int = field(
        default_factory=lambda: int(os.environ.get("INVESTIGATION_TTL_DAYS", "90"))
    )
    alert_cache_ttl_days: int = field(
        default_factory=lambda: int(os.environ.get("ALERT_CACHE_TTL_DAYS", "7"))
    )

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment."""
        return cls()

    def get_sns_topic_for_severity(self, severity: str) -> str:
        """Get the appropriate SNS topic ARN for a severity level."""
        topic_map = {
            "critical": self.critical_sns_topic,
            "warning": self.warning_sns_topic,
            "info": self.info_sns_topic,
        }
        return topic_map.get(severity.lower(), self.info_sns_topic)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config
