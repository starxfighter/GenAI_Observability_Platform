"""
Integration Hub Lambda

Provides integrations with external services:
- Jira: Create issues, update tickets, link incidents
- ServiceNow: Create incidents, change requests, CMDB updates
- GitHub: Create issues, link PRs, update status checks

All integrations support bidirectional sync and webhook handling.
"""

import json
import os
import uuid
import hmac
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import logging
import urllib.request
import urllib.parse
import urllib.error
import base64

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
SECRETS_ARN = os.environ.get("SECRETS_ARN", "")
INTEGRATION_TABLE = os.environ.get("INTEGRATION_TABLE", "")
CALLBACK_URL = os.environ.get("CALLBACK_URL", "")

# Initialize AWS clients
secrets = boto3.client("secretsmanager")
dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

# Cached secrets
_secrets_cache: Dict[str, Any] = {}


class IntegrationType(str, Enum):
    """Supported integration types."""
    JIRA = "jira"
    SERVICENOW = "servicenow"
    GITHUB = "github"


class IntegrationAction(str, Enum):
    """Integration actions."""
    CREATE_ISSUE = "create_issue"
    UPDATE_ISSUE = "update_issue"
    LINK_INCIDENT = "link_incident"
    CREATE_CHANGE = "create_change"
    SYNC_STATUS = "sync_status"
    ADD_COMMENT = "add_comment"
    CLOSE_ISSUE = "close_issue"


def get_secrets(integration_type: str) -> Dict[str, Any]:
    """Get secrets for an integration type."""
    if integration_type in _secrets_cache:
        return _secrets_cache[integration_type]

    if not SECRETS_ARN:
        return {}

    try:
        response = secrets.get_secret_value(SecretId=SECRETS_ARN)
        all_secrets = json.loads(response["SecretString"])
        _secrets_cache[integration_type] = all_secrets.get(integration_type, {})
        return _secrets_cache[integration_type]
    except Exception as e:
        logger.error(f"Failed to get secrets: {e}")
        return {}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for integration hub.

    Supports:
    - Direct invocation for outbound integrations
    - API Gateway for webhook handling
    - SNS for async integration tasks

    Args:
        event: Input event
        context: Lambda context

    Returns:
        Integration result
    """
    # Determine invocation type
    if "httpMethod" in event:
        # API Gateway webhook
        return handle_webhook(event)
    elif "Records" in event:
        # SNS message
        return handle_sns_messages(event)
    else:
        # Direct invocation
        return handle_integration_request(event)


def handle_webhook(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming webhook from external service."""
    path = event.get("path", "")
    method = event.get("httpMethod", "POST")
    headers = event.get("headers", {})
    body = event.get("body", "")

    # Determine integration type from path
    if "/jira" in path:
        return handle_jira_webhook(headers, body)
    elif "/servicenow" in path:
        return handle_servicenow_webhook(headers, body)
    elif "/github" in path:
        return handle_github_webhook(headers, body)
    else:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Unknown integration path"}),
        }


def handle_sns_messages(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle SNS messages for async integration tasks."""
    results = []

    for record in event.get("Records", []):
        try:
            message = json.loads(record["Sns"]["Message"])
            result = handle_integration_request(message)
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing SNS message: {e}")
            results.append({"error": str(e)})

    return {"results": results}


def handle_integration_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle an integration request.

    Args:
        event: Integration request with action and payload

    Returns:
        Integration result
    """
    integration_type = event.get("integration_type", "").lower()
    action = event.get("action", "")
    payload = event.get("payload", {})

    logger.info(f"Integration request: {integration_type}/{action}")

    try:
        if integration_type == IntegrationType.JIRA.value:
            return handle_jira_action(action, payload)
        elif integration_type == IntegrationType.SERVICENOW.value:
            return handle_servicenow_action(action, payload)
        elif integration_type == IntegrationType.GITHUB.value:
            return handle_github_action(action, payload)
        else:
            return {
                "statusCode": 400,
                "error": f"Unknown integration type: {integration_type}",
            }
    except Exception as e:
        logger.error(f"Integration error: {e}")
        return {
            "statusCode": 500,
            "error": str(e),
        }


# ============================================================================
# JIRA INTEGRATION
# ============================================================================

class JiraClient:
    """Jira Cloud API client."""

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get("base_url", "").rstrip("/")
        self.email = config.get("email", "")
        self.api_token = config.get("api_token", "")
        self.project_key = config.get("default_project", "")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Jira API."""
        url = f"{self.base_url}/rest/api/3/{endpoint}"

        # Basic auth
        credentials = base64.b64encode(
            f"{self.email}:{self.api_token}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        request_data = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.error(f"Jira API error: {e.code} - {error_body}")
            raise Exception(f"Jira API error: {e.code}")

    def create_issue(
        self,
        summary: str,
        description: str,
        issue_type: str = "Bug",
        priority: str = "Medium",
        labels: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a Jira issue."""
        fields = {
            "project": {"key": self.project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
        }

        if labels:
            fields["labels"] = labels

        if components:
            fields["components"] = [{"name": c} for c in components]

        if custom_fields:
            fields.update(custom_fields)

        result = self._make_request("POST", "issue", {"fields": fields})
        return {
            "key": result.get("key"),
            "id": result.get("id"),
            "url": f"{self.base_url}/browse/{result.get('key')}",
        }

    def update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a Jira issue."""
        self._make_request("PUT", f"issue/{issue_key}", {"fields": fields})
        return {"key": issue_key, "updated": True}

    def add_comment(
        self,
        issue_key: str,
        comment: str,
    ) -> Dict[str, Any]:
        """Add a comment to an issue."""
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }
        result = self._make_request("POST", f"issue/{issue_key}/comment", body)
        return {"comment_id": result.get("id")}

    def transition_issue(
        self,
        issue_key: str,
        transition_name: str,
    ) -> Dict[str, Any]:
        """Transition an issue to a new status."""
        # Get available transitions
        transitions = self._make_request("GET", f"issue/{issue_key}/transitions")

        transition_id = None
        for t in transitions.get("transitions", []):
            if t["name"].lower() == transition_name.lower():
                transition_id = t["id"]
                break

        if not transition_id:
            raise Exception(f"Transition '{transition_name}' not found")

        self._make_request(
            "POST",
            f"issue/{issue_key}/transitions",
            {"transition": {"id": transition_id}},
        )
        return {"key": issue_key, "transitioned_to": transition_name}

    def link_issues(
        self,
        inward_issue: str,
        outward_issue: str,
        link_type: str = "Relates",
    ) -> Dict[str, Any]:
        """Link two issues."""
        body = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_issue},
            "outwardIssue": {"key": outward_issue},
        }
        self._make_request("POST", "issueLink", body)
        return {"linked": True}


def handle_jira_action(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a Jira integration action."""
    config = get_secrets("jira")
    if not config:
        return {"statusCode": 500, "error": "Jira not configured"}

    client = JiraClient(config)

    if action == IntegrationAction.CREATE_ISSUE.value:
        # Create issue from incident
        incident = payload.get("incident", {})
        result = client.create_issue(
            summary=f"[{incident.get('severity', 'INFO').upper()}] {incident.get('anomaly_type', 'Incident')} - {incident.get('agent_id', 'Unknown')}",
            description=format_incident_description(incident),
            issue_type=payload.get("issue_type", "Bug"),
            priority=map_severity_to_priority(incident.get("severity", "warning")),
            labels=["genai-observability", incident.get("agent_id", "")],
        )

        # Store mapping
        store_integration_mapping(
            incident.get("investigation_id") or incident.get("agent_id"),
            "jira",
            result["key"],
        )

        return {"statusCode": 200, **result}

    elif action == IntegrationAction.UPDATE_ISSUE.value:
        result = client.update_issue(
            payload["issue_key"],
            payload.get("fields", {}),
        )
        return {"statusCode": 200, **result}

    elif action == IntegrationAction.ADD_COMMENT.value:
        result = client.add_comment(
            payload["issue_key"],
            payload["comment"],
        )
        return {"statusCode": 200, **result}

    elif action == IntegrationAction.CLOSE_ISSUE.value:
        result = client.transition_issue(
            payload["issue_key"],
            payload.get("transition", "Done"),
        )
        return {"statusCode": 200, **result}

    elif action == IntegrationAction.SYNC_STATUS.value:
        # Sync status from observability to Jira
        investigation_id = payload.get("investigation_id")
        mapping = get_integration_mapping(investigation_id, "jira")
        if mapping:
            status = payload.get("status", "")
            transition = map_status_to_transition(status)
            if transition:
                result = client.transition_issue(mapping["external_id"], transition)
                return {"statusCode": 200, **result}

        return {"statusCode": 404, "error": "No linked Jira issue found"}

    else:
        return {"statusCode": 400, "error": f"Unknown Jira action: {action}"}


def handle_jira_webhook(headers: Dict[str, str], body: str) -> Dict[str, Any]:
    """Handle incoming Jira webhook."""
    try:
        payload = json.loads(body)
        webhook_event = payload.get("webhookEvent", "")
        issue = payload.get("issue", {})

        logger.info(f"Jira webhook: {webhook_event}")

        if webhook_event == "jira:issue_updated":
            # Sync status back to observability
            issue_key = issue.get("key")
            status = issue.get("fields", {}).get("status", {}).get("name", "")

            mapping = get_integration_mapping_by_external("jira", issue_key)
            if mapping:
                # Update investigation status
                update_investigation_status(
                    mapping["internal_id"],
                    map_jira_status_to_internal(status),
                )

        return {"statusCode": 200, "body": json.dumps({"received": True})}

    except Exception as e:
        logger.error(f"Jira webhook error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# ============================================================================
# SERVICENOW INTEGRATION
# ============================================================================

class ServiceNowClient:
    """ServiceNow API client."""

    def __init__(self, config: Dict[str, Any]):
        self.instance = config.get("instance", "")  # e.g., "company.service-now.com"
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self._access_token = None

    def _get_auth_header(self) -> str:
        """Get authentication header."""
        if self.client_id and self.client_secret:
            # OAuth authentication
            if not self._access_token:
                self._access_token = self._get_oauth_token()
            return f"Bearer {self._access_token}"
        else:
            # Basic authentication
            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode()
            return f"Basic {credentials}"

    def _get_oauth_token(self) -> str:
        """Get OAuth access token."""
        url = f"https://{self.instance}/oauth_token.do"
        data = urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
        }).encode()

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            return result["access_token"]

    def _make_request(
        self,
        method: str,
        table: str,
        sys_id: Optional[str] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to ServiceNow API."""
        url = f"https://{self.instance}/api/now/table/{table}"
        if sys_id:
            url += f"/{sys_id}"

        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        request_data = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.error(f"ServiceNow API error: {e.code} - {error_body}")
            raise Exception(f"ServiceNow API error: {e.code}")

    def create_incident(
        self,
        short_description: str,
        description: str,
        urgency: int = 2,
        impact: int = 2,
        category: str = "Software",
        assignment_group: Optional[str] = None,
        caller_id: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a ServiceNow incident."""
        data = {
            "short_description": short_description,
            "description": description,
            "urgency": str(urgency),
            "impact": str(impact),
            "category": category,
        }

        if assignment_group:
            data["assignment_group"] = assignment_group
        if caller_id:
            data["caller_id"] = caller_id
        if custom_fields:
            data.update(custom_fields)

        result = self._make_request("POST", "incident", data=data)
        record = result.get("result", {})

        return {
            "sys_id": record.get("sys_id"),
            "number": record.get("number"),
            "url": f"https://{self.instance}/nav_to.do?uri=incident.do?sys_id={record.get('sys_id')}",
        }

    def update_incident(
        self,
        sys_id: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a ServiceNow incident."""
        result = self._make_request("PATCH", "incident", sys_id=sys_id, data=fields)
        return {"sys_id": sys_id, "updated": True}

    def add_work_note(
        self,
        sys_id: str,
        note: str,
    ) -> Dict[str, Any]:
        """Add a work note to an incident."""
        return self.update_incident(sys_id, {"work_notes": note})

    def resolve_incident(
        self,
        sys_id: str,
        resolution_code: str = "Solved",
        resolution_notes: str = "",
    ) -> Dict[str, Any]:
        """Resolve an incident."""
        data = {
            "state": "6",  # Resolved
            "close_code": resolution_code,
            "close_notes": resolution_notes,
        }
        return self.update_incident(sys_id, data)

    def create_change_request(
        self,
        short_description: str,
        description: str,
        type: str = "Normal",
        risk: int = 3,
        impact: int = 3,
        assignment_group: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a change request."""
        data = {
            "short_description": short_description,
            "description": description,
            "type": type,
            "risk": str(risk),
            "impact": str(impact),
        }

        if assignment_group:
            data["assignment_group"] = assignment_group

        result = self._make_request("POST", "change_request", data=data)
        record = result.get("result", {})

        return {
            "sys_id": record.get("sys_id"),
            "number": record.get("number"),
            "url": f"https://{self.instance}/nav_to.do?uri=change_request.do?sys_id={record.get('sys_id')}",
        }


def handle_servicenow_action(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a ServiceNow integration action."""
    config = get_secrets("servicenow")
    if not config:
        return {"statusCode": 500, "error": "ServiceNow not configured"}

    client = ServiceNowClient(config)

    if action == IntegrationAction.CREATE_ISSUE.value:
        # Create incident from observability incident
        incident = payload.get("incident", {})
        result = client.create_incident(
            short_description=f"[GenAI] {incident.get('anomaly_type', 'Incident')} - {incident.get('agent_id', 'Unknown')}",
            description=format_incident_description(incident),
            urgency=map_severity_to_urgency(incident.get("severity", "warning")),
            impact=map_severity_to_impact(incident.get("severity", "warning")),
            category=payload.get("category", "Software"),
        )

        store_integration_mapping(
            incident.get("investigation_id") or incident.get("agent_id"),
            "servicenow",
            result["sys_id"],
        )

        return {"statusCode": 200, **result}

    elif action == IntegrationAction.UPDATE_ISSUE.value:
        result = client.update_incident(
            payload["sys_id"],
            payload.get("fields", {}),
        )
        return {"statusCode": 200, **result}

    elif action == IntegrationAction.ADD_COMMENT.value:
        result = client.add_work_note(
            payload["sys_id"],
            payload["note"],
        )
        return {"statusCode": 200, **result}

    elif action == IntegrationAction.CLOSE_ISSUE.value:
        result = client.resolve_incident(
            payload["sys_id"],
            payload.get("resolution_code", "Solved"),
            payload.get("resolution_notes", ""),
        )
        return {"statusCode": 200, **result}

    elif action == IntegrationAction.CREATE_CHANGE.value:
        result = client.create_change_request(
            short_description=payload.get("summary", "Change request"),
            description=payload.get("description", ""),
            type=payload.get("type", "Normal"),
        )
        return {"statusCode": 200, **result}

    else:
        return {"statusCode": 400, "error": f"Unknown ServiceNow action: {action}"}


def handle_servicenow_webhook(headers: Dict[str, str], body: str) -> Dict[str, Any]:
    """Handle incoming ServiceNow webhook."""
    try:
        payload = json.loads(body)
        logger.info(f"ServiceNow webhook received")

        # Process based on payload type
        sys_id = payload.get("sys_id")
        state = payload.get("state")

        if sys_id:
            mapping = get_integration_mapping_by_external("servicenow", sys_id)
            if mapping:
                update_investigation_status(
                    mapping["internal_id"],
                    map_snow_state_to_internal(state),
                )

        return {"statusCode": 200, "body": json.dumps({"received": True})}

    except Exception as e:
        logger.error(f"ServiceNow webhook error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# ============================================================================
# GITHUB INTEGRATION
# ============================================================================

class GitHubClient:
    """GitHub API client."""

    def __init__(self, config: Dict[str, Any]):
        self.token = config.get("token", "")
        self.owner = config.get("owner", "")
        self.repo = config.get("repo", "")
        self.api_url = "https://api.github.com"

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to GitHub API."""
        url = f"{self.api_url}{endpoint}"

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

        request_data = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.error(f"GitHub API error: {e.code} - {error_body}")
            raise Exception(f"GitHub API error: {e.code}")

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a GitHub issue."""
        data = {
            "title": title,
            "body": body,
        }

        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        if milestone:
            data["milestone"] = milestone

        result = self._make_request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/issues",
            data,
        )

        return {
            "number": result.get("number"),
            "id": result.get("id"),
            "url": result.get("html_url"),
        }

    def update_issue(
        self,
        issue_number: int,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a GitHub issue."""
        self._make_request(
            "PATCH",
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}",
            fields,
        )
        return {"number": issue_number, "updated": True}

    def add_comment(
        self,
        issue_number: int,
        body: str,
    ) -> Dict[str, Any]:
        """Add a comment to an issue."""
        result = self._make_request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
            {"body": body},
        )
        return {"comment_id": result.get("id")}

    def close_issue(
        self,
        issue_number: int,
        reason: str = "completed",
    ) -> Dict[str, Any]:
        """Close a GitHub issue."""
        self._make_request(
            "PATCH",
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}",
            {"state": "closed", "state_reason": reason},
        )
        return {"number": issue_number, "closed": True}

    def create_check_run(
        self,
        name: str,
        head_sha: str,
        status: str = "completed",
        conclusion: str = "success",
        title: str = "",
        summary: str = "",
    ) -> Dict[str, Any]:
        """Create a check run for CI/CD integration."""
        data = {
            "name": name,
            "head_sha": head_sha,
            "status": status,
            "conclusion": conclusion,
            "output": {
                "title": title,
                "summary": summary,
            },
        }

        result = self._make_request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/check-runs",
            data,
        )

        return {
            "id": result.get("id"),
            "url": result.get("html_url"),
        }

    def create_deployment_status(
        self,
        deployment_id: int,
        state: str,
        description: str = "",
        environment_url: str = "",
    ) -> Dict[str, Any]:
        """Create a deployment status."""
        data = {
            "state": state,
            "description": description,
        }

        if environment_url:
            data["environment_url"] = environment_url

        result = self._make_request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/deployments/{deployment_id}/statuses",
            data,
        )

        return {"id": result.get("id")}


def handle_github_action(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a GitHub integration action."""
    config = get_secrets("github")
    if not config:
        return {"statusCode": 500, "error": "GitHub not configured"}

    client = GitHubClient(config)

    if action == IntegrationAction.CREATE_ISSUE.value:
        incident = payload.get("incident", {})
        result = client.create_issue(
            title=f"[{incident.get('severity', 'INFO').upper()}] {incident.get('anomaly_type', 'Incident')} - {incident.get('agent_id', 'Unknown')}",
            body=format_incident_markdown(incident),
            labels=["genai-observability", incident.get("severity", "warning")],
        )

        store_integration_mapping(
            incident.get("investigation_id") or incident.get("agent_id"),
            "github",
            str(result["number"]),
        )

        return {"statusCode": 200, **result}

    elif action == IntegrationAction.UPDATE_ISSUE.value:
        result = client.update_issue(
            payload["issue_number"],
            payload.get("fields", {}),
        )
        return {"statusCode": 200, **result}

    elif action == IntegrationAction.ADD_COMMENT.value:
        result = client.add_comment(
            payload["issue_number"],
            payload["body"],
        )
        return {"statusCode": 200, **result}

    elif action == IntegrationAction.CLOSE_ISSUE.value:
        result = client.close_issue(
            payload["issue_number"],
            payload.get("reason", "completed"),
        )
        return {"statusCode": 200, **result}

    else:
        return {"statusCode": 400, "error": f"Unknown GitHub action: {action}"}


def handle_github_webhook(headers: Dict[str, str], body: str) -> Dict[str, Any]:
    """Handle incoming GitHub webhook."""
    try:
        # Verify signature
        signature = headers.get("X-Hub-Signature-256", "")
        config = get_secrets("github")
        webhook_secret = config.get("webhook_secret", "")

        if webhook_secret and not verify_github_signature(body, signature, webhook_secret):
            return {"statusCode": 401, "body": json.dumps({"error": "Invalid signature"})}

        payload = json.loads(body)
        event_type = headers.get("X-GitHub-Event", "")

        logger.info(f"GitHub webhook: {event_type}")

        if event_type == "issues":
            action = payload.get("action")
            issue = payload.get("issue", {})
            issue_number = issue.get("number")

            mapping = get_integration_mapping_by_external("github", str(issue_number))
            if mapping:
                if action == "closed":
                    update_investigation_status(mapping["internal_id"], "resolved")
                elif action == "reopened":
                    update_investigation_status(mapping["internal_id"], "open")

        return {"statusCode": 200, "body": json.dumps({"received": True})}

    except Exception as e:
        logger.error(f"GitHub webhook error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def verify_github_signature(body: str, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    expected = "sha256=" + hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_incident_description(incident: Dict[str, Any]) -> str:
    """Format incident for plain text description."""
    return f"""
Agent ID: {incident.get('agent_id', 'Unknown')}
Anomaly Type: {incident.get('anomaly_type', 'Unknown')}
Severity: {incident.get('severity', 'Unknown')}
Timestamp: {incident.get('timestamp', 'Unknown')}

Root Cause:
{incident.get('root_cause', 'Investigation in progress...')}

Metrics:
{json.dumps(incident.get('metrics', {}), indent=2)}

Investigation ID: {incident.get('investigation_id', 'N/A')}
"""


def format_incident_markdown(incident: Dict[str, Any]) -> str:
    """Format incident for GitHub markdown."""
    return f"""
## Incident Details

| Field | Value |
|-------|-------|
| Agent ID | `{incident.get('agent_id', 'Unknown')}` |
| Anomaly Type | {incident.get('anomaly_type', 'Unknown')} |
| Severity | **{incident.get('severity', 'Unknown').upper()}** |
| Timestamp | {incident.get('timestamp', 'Unknown')} |

### Root Cause
{incident.get('root_cause', '_Investigation in progress..._')}

### Metrics
```json
{json.dumps(incident.get('metrics', {}), indent=2)}
```

---
_Automatically created by GenAI Observability Platform_
Investigation ID: `{incident.get('investigation_id', 'N/A')}`
"""


def map_severity_to_priority(severity: str) -> str:
    """Map severity to Jira priority."""
    mapping = {
        "critical": "Highest",
        "error": "High",
        "warning": "Medium",
        "info": "Low",
    }
    return mapping.get(severity.lower(), "Medium")


def map_severity_to_urgency(severity: str) -> int:
    """Map severity to ServiceNow urgency."""
    mapping = {
        "critical": 1,
        "error": 2,
        "warning": 2,
        "info": 3,
    }
    return mapping.get(severity.lower(), 2)


def map_severity_to_impact(severity: str) -> int:
    """Map severity to ServiceNow impact."""
    mapping = {
        "critical": 1,
        "error": 2,
        "warning": 2,
        "info": 3,
    }
    return mapping.get(severity.lower(), 2)


def map_status_to_transition(status: str) -> Optional[str]:
    """Map internal status to Jira transition."""
    mapping = {
        "resolved": "Done",
        "in_progress": "In Progress",
        "open": "To Do",
    }
    return mapping.get(status.lower())


def map_jira_status_to_internal(status: str) -> str:
    """Map Jira status to internal status."""
    status_lower = status.lower()
    if status_lower in ["done", "closed", "resolved"]:
        return "resolved"
    elif status_lower in ["in progress", "in review"]:
        return "in_progress"
    return "open"


def map_snow_state_to_internal(state: str) -> str:
    """Map ServiceNow state to internal status."""
    state_mapping = {
        "1": "open",      # New
        "2": "in_progress",  # In Progress
        "3": "in_progress",  # On Hold
        "6": "resolved",  # Resolved
        "7": "resolved",  # Closed
    }
    return state_mapping.get(state, "open")


def store_integration_mapping(
    internal_id: str,
    integration_type: str,
    external_id: str,
) -> None:
    """Store mapping between internal and external IDs."""
    if not INTEGRATION_TABLE:
        return

    try:
        table = dynamodb.Table(INTEGRATION_TABLE)
        table.put_item(Item={
            "internal_id": internal_id,
            "integration_type": integration_type,
            "external_id": external_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "ttl": int(datetime.utcnow().timestamp() + (365 * 24 * 60 * 60)),
        })
    except Exception as e:
        logger.error(f"Failed to store integration mapping: {e}")


def get_integration_mapping(internal_id: str, integration_type: str) -> Optional[Dict]:
    """Get integration mapping by internal ID."""
    if not INTEGRATION_TABLE:
        return None

    try:
        table = dynamodb.Table(INTEGRATION_TABLE)
        response = table.get_item(Key={
            "internal_id": internal_id,
            "integration_type": integration_type,
        })
        return response.get("Item")
    except Exception as e:
        logger.error(f"Failed to get integration mapping: {e}")
        return None


def get_integration_mapping_by_external(
    integration_type: str,
    external_id: str,
) -> Optional[Dict]:
    """Get integration mapping by external ID."""
    if not INTEGRATION_TABLE:
        return None

    try:
        table = dynamodb.Table(INTEGRATION_TABLE)
        response = table.query(
            IndexName="external-id-index",
            KeyConditionExpression="integration_type = :type AND external_id = :ext_id",
            ExpressionAttributeValues={
                ":type": integration_type,
                ":ext_id": external_id,
            },
        )
        items = response.get("Items", [])
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Failed to get integration mapping: {e}")
        return None


def update_investigation_status(investigation_id: str, status: str) -> None:
    """Update investigation status in DynamoDB."""
    logger.info(f"Updating investigation {investigation_id} to status: {status}")

    table_name = os.environ.get("INVESTIGATIONS_TABLE", "genai-obs-investigations")

    try:
        dynamodb.update_item(
            TableName=table_name,
            Key={"investigation_id": {"S": investigation_id}},
            UpdateExpression="SET #status = :status, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": {"S": status},
                ":updated_at": {"S": datetime.utcnow().isoformat() + "Z"},
            },
        )
        logger.info(f"Successfully updated investigation {investigation_id} to {status}")
    except Exception as e:
        logger.error(f"Failed to update investigation status: {e}")
        raise
