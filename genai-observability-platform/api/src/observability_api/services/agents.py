"""Agent service for business logic."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from ..db import DynamoDBClient, TimestreamClient
from ..models.agents import Agent, AgentCreate, AgentMetrics, AgentUpdate
from ..models.common import PaginatedResponse


class AgentService:
    """Service for agent operations."""

    def __init__(self) -> None:
        """Initialize agent service."""
        self._dynamodb = DynamoDBClient()
        self._timestream = TimestreamClient()

    async def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        agent_data = await self._dynamodb.get_agent(agent_id)
        if not agent_data:
            return None
        return Agent(**agent_data)

    async def list_agents(
        self,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[Agent]:
        """List agents with optional status filter."""
        items, _ = await self._dynamodb.list_agents(
            status=status,
            limit=page_size,
        )

        agents = [Agent(**item) for item in items]
        total = len(items)  # Simplified - would need count query

        return PaginatedResponse.create(
            items=agents,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def create_agent(self, data: AgentCreate) -> Agent:
        """Register a new agent."""
        agent_id = data.agent_id or str(uuid4())
        now = datetime.utcnow()

        agent_data = {
            "agent_id": agent_id,
            "name": data.name,
            "framework": data.framework,
            "version": data.version,
            "status": "active",
            "created_at": now.isoformat(),
            "last_seen": now.isoformat(),
            "metadata": data.metadata,
        }

        await self._dynamodb.create_agent(agent_data)
        return Agent(**agent_data)

    async def update_agent(self, agent_id: str, data: AgentUpdate) -> Agent | None:
        """Update an agent."""
        updates: dict[str, Any] = {}

        if data.name is not None:
            updates["name"] = data.name
        if data.framework is not None:
            updates["framework"] = data.framework
        if data.version is not None:
            updates["version"] = data.version
        if data.status is not None:
            updates["status"] = data.status
        if data.metadata is not None:
            updates["metadata"] = data.metadata

        if not updates:
            return await self.get_agent(agent_id)

        updated = await self._dynamodb.update_agent(agent_id, updates)
        return Agent(**updated) if updated else None

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        return await self._dynamodb.delete_agent(agent_id)

    async def update_last_seen(self, agent_id: str) -> None:
        """Update agent's last seen timestamp."""
        await self._dynamodb.update_agent(agent_id, {
            "last_seen": datetime.utcnow().isoformat(),
        })

    async def get_agent_metrics(self, agent_id: str, period: str = "24h") -> AgentMetrics:
        """Get metrics for an agent."""
        metrics = await self._timestream.get_agent_metrics(agent_id, period)
        return AgentMetrics(**metrics)

    async def get_agent_count(self) -> tuple[int, int]:
        """Get total and active agent counts."""
        all_agents, _ = await self._dynamodb.list_agents(limit=1000)
        total = len(all_agents)
        active = sum(1 for a in all_agents if a.get("status") == "active")
        return total, active

    async def get_inactive_agents(self, threshold_hours: int = 24) -> list[Agent]:
        """Get agents that haven't been seen recently."""
        threshold = datetime.utcnow().timestamp() - (threshold_hours * 3600)
        all_agents, _ = await self._dynamodb.list_agents(limit=1000)

        inactive = []
        for agent_data in all_agents:
            last_seen = agent_data.get("last_seen")
            if last_seen:
                last_seen_ts = datetime.fromisoformat(last_seen).timestamp()
                if last_seen_ts < threshold:
                    inactive.append(Agent(**agent_data))

        return inactive
