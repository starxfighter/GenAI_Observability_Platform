"""Application configuration."""

from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="OBSERVABILITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "GenAI Observability API"
    environment: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = False
    log_level: str = "INFO"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # AWS
    aws_region: str = "us-east-1"

    # DynamoDB Tables
    traces_table: str = "genai-observability-traces"
    agents_table: str = "genai-observability-agents"
    alerts_table: str = "genai-observability-alerts"
    api_keys_table: str = "genai-observability-api-keys"
    investigations_table: str = "genai-observability-investigations"
    remediations_table: str = "genai-observability-remediations"
    integrations_table: str = "genai-observability-integrations"

    # Timestream
    timestream_database: str = "genai-observability"
    timestream_table: str = "metrics"

    # OpenSearch
    opensearch_endpoint: str = ""
    opensearch_index_prefix: str = "observability"

    # S3
    raw_events_bucket: str = "genai-observability-raw-events"

    # Authentication - JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # SSO - Google OIDC
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None

    # SSO - Okta OIDC
    okta_domain: Optional[str] = None
    okta_client_id: Optional[str] = None
    okta_client_secret: Optional[str] = None

    # SSO - Azure AD OIDC
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None

    # SSO - Auth0 OIDC
    auth0_domain: Optional[str] = None
    auth0_client_id: Optional[str] = None
    auth0_client_secret: Optional[str] = None

    # SSO - SAML
    saml_idp_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_slo_url: Optional[str] = None
    saml_certificate: Optional[str] = None
    saml_sp_entity_id: Optional[str] = None

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Integrations
    jira_default_project: Optional[str] = None
    slack_default_channel: Optional[str] = None
    pagerduty_routing_key: Optional[str] = None

    # Natural Language Query
    nlq_model: str = "claude-3-sonnet"
    nlq_max_tokens: int = 4096

    # PII Redaction
    pii_redaction_enabled: bool = True
    pii_redaction_strategy: Literal["mask", "hash", "remove"] = "mask"

    # Multi-Region
    primary_region: str = "us-east-1"
    secondary_region: str = "us-west-2"
    enable_multi_region: bool = False
    routing_strategy: Literal["failover", "round_robin", "latency_based"] = "failover"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
