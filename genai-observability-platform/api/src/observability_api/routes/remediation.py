"""
Autonomous Remediation API Routes

Provides endpoints for managing AI-powered remediation actions including:
- Listing and retrieving remediation plans
- Approval workflow (approve/reject)
- Execution and rollback
- Creating new remediation plans from investigations
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Pydantic Models
# ============================================

class RemediationAction(BaseModel):
    """Single action in a remediation plan."""
    step: int
    type: str
    description: str
    parameters: Optional[dict] = None
    automated: bool = True
    risk_level: str = "low"  # low, medium, high
    success_criteria: Optional[str] = None
    rollback_action: Optional[str] = None


class ActionPlan(BaseModel):
    """Complete remediation action plan."""
    actions: List[RemediationAction]
    estimated_duration_minutes: int
    risk_assessment: str
    prerequisites: Optional[List[str]] = None
    post_execution_checks: Optional[List[str]] = None


class ExecutionResult(BaseModel):
    """Result of executing a remediation step."""
    step: int
    type: str
    status: str  # success, failed, skipped
    error: Optional[str] = None
    executed_at: Optional[str] = None


class Remediation(BaseModel):
    """Complete remediation record."""
    remediation_id: str
    investigation_id: str
    agent_id: str
    severity: str
    status: str  # pending_approval, approved, rejected, in_progress, completed, failed, rolled_back
    action_plan: ActionPlan
    created_at: str
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    executed_at: Optional[str] = None
    completed_at: Optional[str] = None
    execution_results: Optional[List[ExecutionResult]] = None
    rollback_available: bool = True
    rollback_deadline: Optional[str] = None


class CreateRemediationRequest(BaseModel):
    """Request to create a new remediation plan."""
    investigation_id: str


class ApproveRequest(BaseModel):
    """Request to approve a remediation."""
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    """Request to reject a remediation."""
    reason: str


class RollbackRequest(BaseModel):
    """Request to rollback a remediation."""
    reason: str


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[Remediation]
    total: int
    page: int
    page_size: int
    has_more: bool


# ============================================
# In-memory storage (replace with DynamoDB in production)
# ============================================

_remediations: dict[str, Remediation] = {}


def _init_demo_data():
    """Initialize demo remediation data."""
    if _remediations:
        return

    demo_remediations = [
        Remediation(
            remediation_id="rem_001",
            investigation_id="inv_123",
            agent_id="agent_billing_processor",
            severity="high",
            status="pending_approval",
            action_plan=ActionPlan(
                actions=[
                    RemediationAction(
                        step=1,
                        type="scale_up",
                        description="Increase billing processor replicas from 3 to 6",
                        automated=True,
                        risk_level="low",
                        success_criteria="All new replicas healthy and accepting requests",
                        rollback_action="Scale back down to 3 replicas",
                    ),
                    RemediationAction(
                        step=2,
                        type="configuration_change",
                        description="Increase connection pool size from 10 to 25",
                        automated=True,
                        risk_level="medium",
                        success_criteria="Connection pool metrics stable",
                        rollback_action="Revert connection pool to 10",
                    ),
                ],
                estimated_duration_minutes=15,
                risk_assessment="Medium risk - scaling operations are reversible.",
                prerequisites=["Verify billing queue backlog is manageable"],
                post_execution_checks=["Monitor error rate for 15 minutes"],
            ),
            created_at=datetime.utcnow().isoformat(),
            rollback_available=True,
        ),
        Remediation(
            remediation_id="rem_002",
            investigation_id="inv_124",
            agent_id="agent_recommendation_engine",
            severity="medium",
            status="in_progress",
            action_plan=ActionPlan(
                actions=[
                    RemediationAction(
                        step=1,
                        type="restart_service",
                        description="Rolling restart of recommendation service pods",
                        automated=True,
                        risk_level="low",
                    ),
                ],
                estimated_duration_minutes=10,
                risk_assessment="Low risk - rolling restart has zero downtime.",
            ),
            created_at=datetime.utcnow().isoformat(),
            approved_at=datetime.utcnow().isoformat(),
            approved_by="admin@example.com",
            executed_at=datetime.utcnow().isoformat(),
            execution_results=[
                ExecutionResult(step=1, type="restart_service", status="success")
            ],
            rollback_available=True,
        ),
    ]

    for rem in demo_remediations:
        _remediations[rem.remediation_id] = rem


# ============================================
# API Endpoints
# ============================================

@router.get("", response_model=PaginatedResponse)
async def list_remediations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
):
    """
    List all remediation actions with optional filtering.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        status: Filter by status
        agent_id: Filter by agent ID
        severity: Filter by severity
    """
    _init_demo_data()

    items = list(_remediations.values())

    # Apply filters
    if status:
        items = [r for r in items if r.status == status]
    if agent_id:
        items = [r for r in items if r.agent_id == agent_id]
    if severity:
        items = [r for r in items if r.severity == severity]

    # Sort by created_at descending
    items.sort(key=lambda x: x.created_at, reverse=True)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    return PaginatedResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


@router.get("/{remediation_id}", response_model=Remediation)
async def get_remediation(remediation_id: str):
    """Get a specific remediation by ID."""
    _init_demo_data()

    if remediation_id not in _remediations:
        raise HTTPException(status_code=404, detail="Remediation not found")

    return _remediations[remediation_id]


@router.post("/plan", response_model=Remediation)
async def create_remediation_plan(request: CreateRemediationRequest):
    """
    Create a new remediation plan from an investigation.

    This endpoint triggers the AI-powered remediation planning process
    which analyzes the investigation and generates an action plan.
    """
    remediation_id = f"rem_{uuid4().hex[:8]}"

    # In production, this would:
    # 1. Fetch the investigation details
    # 2. Call the autonomous remediation Lambda
    # 3. Store the generated plan

    remediation = Remediation(
        remediation_id=remediation_id,
        investigation_id=request.investigation_id,
        agent_id="agent_unknown",
        severity="medium",
        status="pending_approval",
        action_plan=ActionPlan(
            actions=[
                RemediationAction(
                    step=1,
                    type="diagnostic",
                    description="Run diagnostic checks on affected service",
                    automated=True,
                    risk_level="low",
                ),
            ],
            estimated_duration_minutes=5,
            risk_assessment="Low risk - diagnostic only.",
        ),
        created_at=datetime.utcnow().isoformat(),
        rollback_available=True,
    )

    _remediations[remediation_id] = remediation
    logger.info(f"Created remediation plan {remediation_id} for investigation {request.investigation_id}")

    return remediation


@router.post("/{remediation_id}/approve", response_model=Remediation)
async def approve_remediation(remediation_id: str, request: ApproveRequest):
    """
    Approve a remediation plan for execution.

    Only remediations in 'pending_approval' status can be approved.
    """
    _init_demo_data()

    if remediation_id not in _remediations:
        raise HTTPException(status_code=404, detail="Remediation not found")

    remediation = _remediations[remediation_id]

    if remediation.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve remediation in '{remediation.status}' status"
        )

    remediation.status = "approved"
    remediation.approved_at = datetime.utcnow().isoformat()
    remediation.approved_by = "current_user@example.com"  # Would come from auth

    logger.info(f"Approved remediation {remediation_id}")
    return remediation


@router.post("/{remediation_id}/reject", response_model=Remediation)
async def reject_remediation(remediation_id: str, request: RejectRequest):
    """
    Reject a remediation plan.

    Only remediations in 'pending_approval' status can be rejected.
    """
    _init_demo_data()

    if remediation_id not in _remediations:
        raise HTTPException(status_code=404, detail="Remediation not found")

    remediation = _remediations[remediation_id]

    if remediation.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject remediation in '{remediation.status}' status"
        )

    remediation.status = "rejected"
    logger.info(f"Rejected remediation {remediation_id}: {request.reason}")

    return remediation


@router.post("/{remediation_id}/execute", response_model=Remediation)
async def execute_remediation(remediation_id: str):
    """
    Execute an approved remediation plan.

    Only remediations in 'approved' status can be executed.
    This triggers the autonomous remediation Lambda to execute each step.
    """
    _init_demo_data()

    if remediation_id not in _remediations:
        raise HTTPException(status_code=404, detail="Remediation not found")

    remediation = _remediations[remediation_id]

    if remediation.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute remediation in '{remediation.status}' status"
        )

    remediation.status = "in_progress"
    remediation.executed_at = datetime.utcnow().isoformat()
    remediation.execution_results = []

    # In production, this would trigger the Lambda function
    # For demo, simulate immediate completion of first step
    if remediation.action_plan.actions:
        first_action = remediation.action_plan.actions[0]
        remediation.execution_results.append(
            ExecutionResult(
                step=first_action.step,
                type=first_action.type,
                status="success",
                executed_at=datetime.utcnow().isoformat(),
            )
        )

    logger.info(f"Started execution of remediation {remediation_id}")
    return remediation


@router.post("/{remediation_id}/rollback", response_model=Remediation)
async def rollback_remediation(remediation_id: str, request: RollbackRequest):
    """
    Rollback a completed or failed remediation.

    Only remediations with rollback_available=True can be rolled back.
    """
    _init_demo_data()

    if remediation_id not in _remediations:
        raise HTTPException(status_code=404, detail="Remediation not found")

    remediation = _remediations[remediation_id]

    if not remediation.rollback_available:
        raise HTTPException(
            status_code=400,
            detail="Rollback is not available for this remediation"
        )

    if remediation.status not in ["completed", "failed", "in_progress"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot rollback remediation in '{remediation.status}' status"
        )

    remediation.status = "rolled_back"
    remediation.rollback_available = False

    logger.info(f"Rolled back remediation {remediation_id}: {request.reason}")
    return remediation


@router.get("/{remediation_id}/status")
async def get_remediation_status(remediation_id: str):
    """Get current execution status of a remediation."""
    _init_demo_data()

    if remediation_id not in _remediations:
        raise HTTPException(status_code=404, detail="Remediation not found")

    remediation = _remediations[remediation_id]

    total_steps = len(remediation.action_plan.actions)
    completed_steps = len(remediation.execution_results or [])
    failed_steps = len([r for r in (remediation.execution_results or []) if r.status == "failed"])

    return {
        "remediation_id": remediation_id,
        "status": remediation.status,
        "total_steps": total_steps,
        "completed_steps": completed_steps,
        "failed_steps": failed_steps,
        "progress_percent": (completed_steps / total_steps * 100) if total_steps > 0 else 0,
        "current_step": completed_steps + 1 if completed_steps < total_steps else None,
        "execution_results": remediation.execution_results,
    }
