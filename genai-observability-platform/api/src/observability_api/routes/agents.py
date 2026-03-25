"""Agent endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.agents import Agent, AgentCreate, AgentMetrics, AgentUpdate
from ..models.common import PaginatedResponse
from ..services import AgentService

router = APIRouter()


def get_agent_service() -> AgentService:
    """Dependency for agent service."""
    return AgentService()


@router.get("", response_model=PaginatedResponse[Agent])
async def list_agents(
    service: Annotated[AgentService, Depends(get_agent_service)],
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[Agent]:
    """List registered agents."""
    return await service.list_agents(status, page, page_size)


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: str,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> Agent:
    """Get an agent by ID."""
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("", response_model=Agent, status_code=201)
async def create_agent(
    data: AgentCreate,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> Agent:
    """Register a new agent."""
    return await service.create_agent(data)


@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> Agent:
    """Update an agent."""
    agent = await service.update_agent(agent_id, data)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> None:
    """Delete an agent."""
    success = await service.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/{agent_id}/metrics", response_model=AgentMetrics)
async def get_agent_metrics(
    agent_id: str,
    service: Annotated[AgentService, Depends(get_agent_service)],
    period: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
) -> AgentMetrics:
    """Get metrics for an agent."""
    # Verify agent exists
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return await service.get_agent_metrics(agent_id, period)


@router.post("/{agent_id}/heartbeat", status_code=204)
async def agent_heartbeat(
    agent_id: str,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> None:
    """Update agent last seen timestamp."""
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await service.update_last_seen(agent_id)
