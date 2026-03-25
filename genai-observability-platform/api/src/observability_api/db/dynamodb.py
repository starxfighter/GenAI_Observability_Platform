"""DynamoDB client for data access."""

from datetime import datetime
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key

from ..config import get_settings


class DynamoDBClient:
    """DynamoDB client wrapper."""

    def __init__(self) -> None:
        """Initialize DynamoDB client."""
        settings = get_settings()
        self._dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self._client = boto3.client("dynamodb", region_name=settings.aws_region)
        self._settings = settings

    def _get_table(self, table_name: str):
        """Get DynamoDB table resource."""
        return self._dynamodb.Table(table_name)

    # Traces
    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Get a trace by ID."""
        table = self._get_table(self._settings.traces_table)
        response = table.get_item(Key={"trace_id": trace_id})
        return response.get("Item")

    async def list_traces(
        self,
        agent_id: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        last_key: dict | None = None,
    ) -> tuple[list[dict[str, Any]], dict | None]:
        """List traces with optional filters."""
        table = self._get_table(self._settings.traces_table)

        # Build filter expression
        filter_expr = None
        expr_values = {}
        expr_names = {}

        if agent_id:
            filter_expr = Attr("agent_id").eq(agent_id)

        if status:
            status_filter = Attr("status").eq(status)
            filter_expr = filter_expr & status_filter if filter_expr else status_filter

        if start_time:
            time_filter = Attr("start_time").gte(start_time.isoformat())
            filter_expr = filter_expr & time_filter if filter_expr else time_filter

        if end_time:
            time_filter = Attr("start_time").lte(end_time.isoformat())
            filter_expr = filter_expr & time_filter if filter_expr else time_filter

        scan_kwargs: dict[str, Any] = {"Limit": limit}
        if filter_expr:
            scan_kwargs["FilterExpression"] = filter_expr
        if last_key:
            scan_kwargs["ExclusiveStartKey"] = last_key

        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        next_key = response.get("LastEvaluatedKey")

        return items, next_key

    async def create_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Create a new trace."""
        table = self._get_table(self._settings.traces_table)
        table.put_item(Item=trace)
        return trace

    async def update_trace(self, trace_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a trace."""
        table = self._get_table(self._settings.traces_table)

        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
        expr_names = {f"#{k}": k for k in updates.keys()}
        expr_values = {f":{k}": v for k, v in updates.items()}

        response = table.update_item(
            Key={"trace_id": trace_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    # Agents
    async def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        """Get an agent by ID."""
        table = self._get_table(self._settings.agents_table)
        response = table.get_item(Key={"agent_id": agent_id})
        return response.get("Item")

    async def list_agents(
        self,
        status: str | None = None,
        limit: int = 50,
        last_key: dict | None = None,
    ) -> tuple[list[dict[str, Any]], dict | None]:
        """List agents with optional filters."""
        table = self._get_table(self._settings.agents_table)

        scan_kwargs: dict[str, Any] = {"Limit": limit}
        if status:
            scan_kwargs["FilterExpression"] = Attr("status").eq(status)
        if last_key:
            scan_kwargs["ExclusiveStartKey"] = last_key

        response = table.scan(**scan_kwargs)
        return response.get("Items", []), response.get("LastEvaluatedKey")

    async def create_agent(self, agent: dict[str, Any]) -> dict[str, Any]:
        """Create a new agent."""
        table = self._get_table(self._settings.agents_table)
        table.put_item(Item=agent)
        return agent

    async def update_agent(self, agent_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update an agent."""
        table = self._get_table(self._settings.agents_table)

        updates["updated_at"] = datetime.utcnow().isoformat()
        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
        expr_names = {f"#{k}": k for k in updates.keys()}
        expr_values = {f":{k}": v for k, v in updates.items()}

        response = table.update_item(
            Key={"agent_id": agent_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        table = self._get_table(self._settings.agents_table)
        table.delete_item(Key={"agent_id": agent_id})
        return True

    # Alerts
    async def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        """Get an alert by ID."""
        table = self._get_table(self._settings.alerts_table)
        response = table.get_item(Key={"alert_id": alert_id})
        return response.get("Item")

    async def list_alerts(
        self,
        agent_id: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        last_key: dict | None = None,
    ) -> tuple[list[dict[str, Any]], dict | None]:
        """List alerts with optional filters."""
        table = self._get_table(self._settings.alerts_table)

        filter_expr = None

        if agent_id:
            filter_expr = Attr("agent_id").eq(agent_id)

        if status:
            status_filter = Attr("status").eq(status)
            filter_expr = filter_expr & status_filter if filter_expr else status_filter

        if severity:
            severity_filter = Attr("severity").eq(severity)
            filter_expr = filter_expr & severity_filter if filter_expr else severity_filter

        if start_time:
            time_filter = Attr("timestamp").gte(start_time.isoformat())
            filter_expr = filter_expr & time_filter if filter_expr else time_filter

        if end_time:
            time_filter = Attr("timestamp").lte(end_time.isoformat())
            filter_expr = filter_expr & time_filter if filter_expr else time_filter

        scan_kwargs: dict[str, Any] = {"Limit": limit}
        if filter_expr:
            scan_kwargs["FilterExpression"] = filter_expr
        if last_key:
            scan_kwargs["ExclusiveStartKey"] = last_key

        response = table.scan(**scan_kwargs)
        return response.get("Items", []), response.get("LastEvaluatedKey")

    async def create_alert(self, alert: dict[str, Any]) -> dict[str, Any]:
        """Create a new alert."""
        table = self._get_table(self._settings.alerts_table)
        table.put_item(Item=alert)
        return alert

    async def update_alert(self, alert_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update an alert."""
        table = self._get_table(self._settings.alerts_table)

        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
        expr_names = {f"#{k}": k for k in updates.keys()}
        expr_values = {f":{k}": v for k, v in updates.items()}

        response = table.update_item(
            Key={"alert_id": alert_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    # Investigations
    async def get_investigation(self, alert_id: str) -> dict[str, Any] | None:
        """Get investigation for an alert."""
        table = self._get_table(self._settings.investigations_table)
        response = table.query(
            IndexName="alert_id-index",
            KeyConditionExpression=Key("alert_id").eq(alert_id),
            Limit=1,
        )
        items = response.get("Items", [])
        return items[0] if items else None

    # API Keys
    async def get_api_key(self, key_id: str) -> dict[str, Any] | None:
        """Get an API key by ID."""
        table = self._get_table(self._settings.api_keys_table)
        response = table.get_item(Key={"key_id": key_id})
        return response.get("Item")

    async def get_api_key_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        """Get an API key by its hash."""
        table = self._get_table(self._settings.api_keys_table)
        response = table.query(
            IndexName="key_hash-index",
            KeyConditionExpression=Key("key_hash").eq(key_hash),
            Limit=1,
        )
        items = response.get("Items", [])
        return items[0] if items else None

    async def create_api_key(self, api_key: dict[str, Any]) -> dict[str, Any]:
        """Create a new API key."""
        table = self._get_table(self._settings.api_keys_table)
        table.put_item(Item=api_key)
        return api_key

    async def update_api_key_last_used(self, key_id: str) -> None:
        """Update API key last used timestamp."""
        table = self._get_table(self._settings.api_keys_table)
        table.update_item(
            Key={"key_id": key_id},
            UpdateExpression="SET last_used = :ts",
            ExpressionAttributeValues={":ts": datetime.utcnow().isoformat()},
        )
