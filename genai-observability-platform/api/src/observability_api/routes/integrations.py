"""
Integrations API Routes

Provides endpoints for managing third-party integrations including:
- Jira, ServiceNow, GitHub issue tracking
- Slack, PagerDuty, Microsoft Teams notifications
- Integration configuration, testing, and syncing
"""

import logging
from datetime import datetime
from typing import Optional, List, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Pydantic Models
# ============================================

IntegrationType = Literal["jira", "servicenow", "github", "slack", "pagerduty", "teams"]
IntegrationStatus = Literal["connected", "disconnected", "error"]


class Integration(BaseModel):
    """Integration configuration."""
    integration_id: str
    type: IntegrationType
    name: str
    enabled: bool = True
    config: dict = Field(default_factory=dict)
    status: IntegrationStatus = "disconnected"
    last_sync: Optional[str] = None
    created_at: str
    error_message: Optional[str] = None


class CreateIntegrationRequest(BaseModel):
    """Request to create a new integration."""
    type: IntegrationType
    name: str
    config: dict = Field(default_factory=dict)


class UpdateIntegrationRequest(BaseModel):
    """Request to update an integration."""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[dict] = None


class TestResult(BaseModel):
    """Result of testing an integration."""
    success: bool
    message: str


class SyncResult(BaseModel):
    """Result of syncing an integration."""
    success: bool
    synced_at: str


class CreateIssueRequest(BaseModel):
    """Request to create an external issue."""
    alert_id: str
    issue_type: Optional[str] = None
    priority: Optional[str] = None


class CreateIssueResponse(BaseModel):
    """Response from creating an external issue."""
    external_id: str
    url: str


# ============================================
# In-memory storage (replace with DynamoDB in production)
# ============================================

_integrations: dict[str, Integration] = {}


def _init_demo_data():
    """Initialize demo integration data."""
    if _integrations:
        return

    demo_integrations = [
        Integration(
            integration_id="int_001",
            type="jira",
            name="Production Jira",
            enabled=True,
            config={"base_url": "https://company.atlassian.net", "project_key": "OBS"},
            status="connected",
            last_sync=datetime.utcnow().isoformat(),
            created_at=datetime.utcnow().isoformat(),
        ),
        Integration(
            integration_id="int_002",
            type="slack",
            name="Engineering Alerts",
            enabled=True,
            config={"channel": "#alerts"},
            status="connected",
            last_sync=datetime.utcnow().isoformat(),
            created_at=datetime.utcnow().isoformat(),
        ),
        Integration(
            integration_id="int_003",
            type="pagerduty",
            name="On-Call Alerts",
            enabled=True,
            config={"service_id": "P123ABC"},
            status="error",
            error_message="API key expired. Please update credentials.",
            created_at=datetime.utcnow().isoformat(),
        ),
        Integration(
            integration_id="int_004",
            type="github",
            name="Platform Repo",
            enabled=False,
            config={"owner": "company", "repo": "platform"},
            status="disconnected",
            created_at=datetime.utcnow().isoformat(),
        ),
    ]

    for integration in demo_integrations:
        _integrations[integration.integration_id] = integration


# ============================================
# API Endpoints
# ============================================

@router.get("", response_model=List[Integration])
async def list_integrations(
    type: Optional[IntegrationType] = Query(None),
    status: Optional[IntegrationStatus] = Query(None),
    enabled: Optional[bool] = Query(None),
):
    """
    List all integrations with optional filtering.

    Args:
        type: Filter by integration type
        status: Filter by connection status
        enabled: Filter by enabled state
    """
    _init_demo_data()

    items = list(_integrations.values())

    if type:
        items = [i for i in items if i.type == type]
    if status:
        items = [i for i in items if i.status == status]
    if enabled is not None:
        items = [i for i in items if i.enabled == enabled]

    return items


@router.get("/{integration_id}", response_model=Integration)
async def get_integration(integration_id: str):
    """Get a specific integration by ID."""
    _init_demo_data()

    if integration_id not in _integrations:
        raise HTTPException(status_code=404, detail="Integration not found")

    return _integrations[integration_id]


@router.post("", response_model=Integration)
async def create_integration(request: CreateIntegrationRequest):
    """Create a new integration."""
    integration_id = f"int_{uuid4().hex[:8]}"

    # Validate configuration based on type
    required_fields = {
        "jira": ["base_url", "username", "api_token", "project_key"],
        "servicenow": ["instance_url", "username", "password"],
        "github": ["token", "owner", "repo"],
        "slack": ["webhook_url"],
        "pagerduty": ["api_key", "service_id"],
        "teams": ["webhook_url"],
    }

    # For demo, we won't strictly enforce required fields
    # In production, validate all required fields are present

    integration = Integration(
        integration_id=integration_id,
        type=request.type,
        name=request.name,
        enabled=True,
        config=request.config,
        status="disconnected",
        created_at=datetime.utcnow().isoformat(),
    )

    _integrations[integration_id] = integration
    logger.info(f"Created integration {integration_id} of type {request.type}")

    return integration


@router.patch("/{integration_id}", response_model=Integration)
async def update_integration(integration_id: str, request: UpdateIntegrationRequest):
    """Update an existing integration."""
    _init_demo_data()

    if integration_id not in _integrations:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration = _integrations[integration_id]

    if request.name is not None:
        integration.name = request.name
    if request.enabled is not None:
        integration.enabled = request.enabled
    if request.config is not None:
        integration.config.update(request.config)

    logger.info(f"Updated integration {integration_id}")
    return integration


@router.delete("/{integration_id}")
async def delete_integration(integration_id: str):
    """Delete an integration."""
    _init_demo_data()

    if integration_id not in _integrations:
        raise HTTPException(status_code=404, detail="Integration not found")

    del _integrations[integration_id]
    logger.info(f"Deleted integration {integration_id}")

    return {"message": "Integration deleted successfully"}


@router.post("/{integration_id}/test", response_model=TestResult)
async def test_integration(integration_id: str):
    """
    Test connectivity for an integration.

    Validates credentials and connectivity to the external service.
    """
    _init_demo_data()

    if integration_id not in _integrations:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration = _integrations[integration_id]

    # In production, actually test the connection
    # For demo, simulate based on current status
    if integration.status == "error":
        integration.status = "connected"
        integration.error_message = None
        return TestResult(success=True, message="Connection restored successfully")
    elif integration.status == "disconnected":
        integration.status = "connected"
        return TestResult(success=True, message="Connection established successfully")
    else:
        return TestResult(success=True, message="Connection verified successfully")


@router.post("/{integration_id}/sync", response_model=SyncResult)
async def sync_integration(integration_id: str):
    """
    Sync data with an integration.

    For bidirectional integrations, this syncs state between
    the observability platform and the external service.
    """
    _init_demo_data()

    if integration_id not in _integrations:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration = _integrations[integration_id]

    if not integration.enabled:
        raise HTTPException(status_code=400, detail="Integration is disabled")

    if integration.status != "connected":
        raise HTTPException(status_code=400, detail="Integration is not connected")

    # In production, perform actual sync
    synced_at = datetime.utcnow().isoformat()
    integration.last_sync = synced_at

    logger.info(f"Synced integration {integration_id}")
    return SyncResult(success=True, synced_at=synced_at)


@router.post("/{integration_id}/issues", response_model=CreateIssueResponse)
async def create_external_issue(integration_id: str, request: CreateIssueRequest):
    """
    Create an issue in the external system linked to an alert.

    Supported for: jira, servicenow, github
    """
    _init_demo_data()

    if integration_id not in _integrations:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration = _integrations[integration_id]

    if integration.type not in ["jira", "servicenow", "github"]:
        raise HTTPException(
            status_code=400,
            detail=f"Issue creation not supported for {integration.type}"
        )

    if not integration.enabled:
        raise HTTPException(status_code=400, detail="Integration is disabled")

    if integration.status != "connected":
        raise HTTPException(status_code=400, detail="Integration is not connected")

    # In production, actually create the issue via the integration Lambda
    external_id = f"{integration.type.upper()}-{uuid4().hex[:6].upper()}"

    # Generate appropriate URL based on type
    if integration.type == "jira":
        base_url = integration.config.get("base_url", "https://example.atlassian.net")
        url = f"{base_url}/browse/{external_id}"
    elif integration.type == "github":
        owner = integration.config.get("owner", "example")
        repo = integration.config.get("repo", "repo")
        url = f"https://github.com/{owner}/{repo}/issues/{external_id.split('-')[1]}"
    else:  # servicenow
        instance_url = integration.config.get("instance_url", "https://example.service-now.com")
        url = f"{instance_url}/nav_to.do?uri=incident.do?sys_id={external_id}"

    logger.info(f"Created external issue {external_id} for alert {request.alert_id}")

    return CreateIssueResponse(external_id=external_id, url=url)


@router.post("/{integration_id}/notify")
async def send_notification(
    integration_id: str,
    message: str = Query(...),
    severity: str = Query("info"),
    alert_id: Optional[str] = Query(None),
):
    """
    Send a notification via the integration.

    Supported for: slack, pagerduty, teams
    """
    _init_demo_data()

    if integration_id not in _integrations:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration = _integrations[integration_id]

    if integration.type not in ["slack", "pagerduty", "teams"]:
        raise HTTPException(
            status_code=400,
            detail=f"Notifications not supported for {integration.type}"
        )

    if not integration.enabled:
        raise HTTPException(status_code=400, detail="Integration is disabled")

    if integration.status != "connected":
        raise HTTPException(status_code=400, detail="Integration is not connected")

    # In production, actually send the notification via the integration Lambda
    logger.info(f"Sent notification via {integration.type} integration {integration_id}")

    return {
        "success": True,
        "message": "Notification sent successfully",
        "integration": integration.name,
        "channel": integration.type,
    }


@router.get("/types/available")
async def list_available_types():
    """List all available integration types with their configuration requirements."""
    return {
        "jira": {
            "name": "Jira",
            "description": "Create and sync issues with Atlassian Jira",
            "category": "issue_tracking",
            "required_fields": ["base_url", "username", "api_token", "project_key"],
            "optional_fields": ["issue_type", "labels"],
        },
        "servicenow": {
            "name": "ServiceNow",
            "description": "Sync incidents with ServiceNow ITSM",
            "category": "issue_tracking",
            "required_fields": ["instance_url", "username", "password"],
            "optional_fields": ["assignment_group", "category"],
        },
        "github": {
            "name": "GitHub",
            "description": "Create issues and link to repositories",
            "category": "issue_tracking",
            "required_fields": ["token", "owner", "repo"],
            "optional_fields": ["labels"],
        },
        "slack": {
            "name": "Slack",
            "description": "Send alerts and notifications to Slack channels",
            "category": "notification",
            "required_fields": ["webhook_url"],
            "optional_fields": ["channel", "username", "icon_emoji"],
        },
        "pagerduty": {
            "name": "PagerDuty",
            "description": "Trigger incidents and on-call notifications",
            "category": "notification",
            "required_fields": ["api_key", "service_id"],
            "optional_fields": ["escalation_policy_id"],
        },
        "teams": {
            "name": "Microsoft Teams",
            "description": "Send alerts to Microsoft Teams channels",
            "category": "notification",
            "required_fields": ["webhook_url"],
            "optional_fields": [],
        },
    }
