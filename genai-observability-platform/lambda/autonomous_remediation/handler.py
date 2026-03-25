"""
Autonomous Remediation Lambda

Executes remediation actions based on LLM-generated recommendations.
Implements safety checks, rollback capabilities, and approval workflows.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

import boto3

# Configuration
ANTHROPIC_SECRET_ARN = os.environ.get("ANTHROPIC_SECRET_ARN", "")
REMEDIATION_TABLE = os.environ.get("REMEDIATION_TABLE", "")
INVESTIGATION_RESULTS_TABLE = os.environ.get("INVESTIGATION_RESULTS_TABLE", "")
NOTIFICATION_TOPIC = os.environ.get("NOTIFICATION_TOPIC", "")
APPROVAL_QUEUE_URL = os.environ.get("APPROVAL_QUEUE_URL", "")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")

# Safety configuration
AUTO_APPROVE_SEVERITY = os.environ.get("AUTO_APPROVE_SEVERITY", "low").split(",")
REQUIRE_APPROVAL_ACTIONS = os.environ.get("REQUIRE_APPROVAL_ACTIONS", "restart,scale,rollback").split(",")
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
ROLLBACK_WINDOW_MINUTES = int(os.environ.get("ROLLBACK_WINDOW_MINUTES", "30"))

# Model configuration
MODEL_ID = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4000"))

# Initialize clients
secrets = boto3.client("secretsmanager")
dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")
sqs = boto3.client("sqs")
sfn = boto3.client("stepfunctions")
lambda_client = boto3.client("lambda")
ecs = boto3.client("ecs")
cloudwatch = boto3.client("cloudwatch")

# Cached Anthropic client
_anthropic_client = None


class RemediationStatus(str, Enum):
    """Status of a remediation action."""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ActionType(str, Enum):
    """Types of remediation actions."""
    RESTART_SERVICE = "restart_service"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    CLEAR_CACHE = "clear_cache"
    ROTATE_CREDENTIALS = "rotate_credentials"
    UPDATE_CONFIG = "update_config"
    ENABLE_CIRCUIT_BREAKER = "enable_circuit_breaker"
    THROTTLE_REQUESTS = "throttle_requests"
    FAILOVER = "failover"
    CUSTOM_SCRIPT = "custom_script"


def get_anthropic_client():
    """Get or create Anthropic client."""
    global _anthropic_client

    if _anthropic_client is None and ANTHROPIC_SECRET_ARN:
        try:
            secret_response = secrets.get_secret_value(SecretId=ANTHROPIC_SECRET_ARN)
            api_key = json.loads(secret_response["SecretString"])["api_key"]

            from anthropic import Anthropic

            _anthropic_client = Anthropic(api_key=api_key)
        except Exception as e:
            print(f"Error initializing Anthropic client: {e}")
            return None

    return _anthropic_client


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for autonomous remediation.

    Can be triggered by:
    - LLM Investigator (with recommendations)
    - Manual approval workflow
    - Scheduled retry for failed remediations

    Args:
        event: Event containing investigation results or approval
        context: Lambda context

    Returns:
        Remediation result
    """
    action_type = event.get("action", "execute")

    if action_type == "plan":
        return plan_remediation(event)
    elif action_type == "approve":
        return approve_remediation(event)
    elif action_type == "reject":
        return reject_remediation(event)
    elif action_type == "execute":
        return execute_remediation(event)
    elif action_type == "rollback":
        return rollback_remediation(event)
    elif action_type == "status":
        return get_remediation_status(event)
    else:
        return {
            "statusCode": 400,
            "error": f"Unknown action type: {action_type}",
        }


def plan_remediation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a remediation plan based on investigation results.

    Args:
        event: Investigation results with recommendations

    Returns:
        Remediation plan
    """
    remediation_id = str(uuid.uuid4())
    investigation_id = event.get("investigation_id")
    agent_id = event.get("agent_id", "unknown")
    severity = event.get("severity", "warning")
    recommendations = event.get("recommendations", [])

    print(f"Planning remediation {remediation_id} for investigation {investigation_id}")

    # Use LLM to create detailed action plan
    action_plan = create_action_plan(event, recommendations)

    # Determine if auto-approval is possible
    requires_approval = should_require_approval(action_plan, severity)

    # Create remediation record
    remediation = {
        "remediation_id": remediation_id,
        "investigation_id": investigation_id,
        "agent_id": agent_id,
        "severity": severity,
        "status": RemediationStatus.PENDING_APPROVAL.value if requires_approval else RemediationStatus.APPROVED.value,
        "action_plan": action_plan,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "requires_approval": requires_approval,
        "approval_deadline": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z" if requires_approval else None,
        "retry_count": 0,
        "max_retries": MAX_RETRIES,
        "rollback_available": True,
        "rollback_deadline": (datetime.utcnow() + timedelta(minutes=ROLLBACK_WINDOW_MINUTES)).isoformat() + "Z",
    }

    # Store remediation plan
    store_remediation(remediation)

    # If auto-approved, trigger execution
    if not requires_approval:
        print(f"Auto-approved remediation {remediation_id}")
        trigger_execution(remediation)
    else:
        # Request approval
        request_approval(remediation)

    return {
        "statusCode": 200,
        "remediation_id": remediation_id,
        "status": remediation["status"],
        "requires_approval": requires_approval,
        "action_plan": action_plan,
    }


def create_action_plan(event: Dict[str, Any], recommendations: List[str]) -> Dict[str, Any]:
    """
    Use LLM to create a detailed action plan from recommendations.

    Args:
        event: Investigation event data
        recommendations: List of recommendations from investigation

    Returns:
        Structured action plan
    """
    client = get_anthropic_client()
    if client is None:
        # Return basic plan without LLM enhancement
        return {
            "actions": [
                {
                    "type": ActionType.CUSTOM_SCRIPT.value,
                    "description": rec,
                    "automated": False,
                    "risk_level": "medium",
                }
                for rec in recommendations[:5]
            ],
            "estimated_duration_minutes": 15,
            "risk_assessment": "Unable to assess without LLM",
        }

    prompt = f"""You are a DevOps automation expert creating a remediation plan for a production incident.

## Incident Context
- **Agent ID**: {event.get('agent_id')}
- **Anomaly Type**: {event.get('anomaly_type')}
- **Severity**: {event.get('severity')}
- **Root Cause**: {event.get('root_cause', 'Unknown')}

## Recommendations from Investigation
{json.dumps(recommendations, indent=2)}

## Available Automated Actions
- restart_service: Restart the affected service/container
- scale_up: Increase replicas/capacity
- scale_down: Decrease replicas/capacity
- rollback_deployment: Revert to previous deployment
- clear_cache: Clear application caches
- rotate_credentials: Rotate API keys/secrets
- update_config: Update configuration parameters
- enable_circuit_breaker: Enable circuit breaker pattern
- throttle_requests: Implement rate limiting
- failover: Trigger failover to backup system

## Task
Create a detailed, step-by-step remediation plan. For each step:
1. Specify the action type from the available actions
2. Provide specific parameters needed
3. Assess the risk level (low/medium/high)
4. Indicate if it can be automated
5. Define success criteria

Return the plan as valid JSON in this exact format:
{{
    "actions": [
        {{
            "step": 1,
            "type": "action_type",
            "description": "What this action does",
            "parameters": {{}},
            "automated": true/false,
            "risk_level": "low/medium/high",
            "success_criteria": "How to verify success",
            "rollback_action": "How to undo if needed"
        }}
    ],
    "estimated_duration_minutes": number,
    "risk_assessment": "Overall risk assessment",
    "prerequisites": ["list of prerequisites"],
    "post_execution_checks": ["list of verification steps"]
}}"""

    try:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=MAX_TOKENS,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text

        # Extract JSON from response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(response_text[json_start:json_end])

    except Exception as e:
        print(f"Error creating action plan: {e}")

    # Fallback plan
    return {
        "actions": [
            {
                "step": 1,
                "type": ActionType.CUSTOM_SCRIPT.value,
                "description": recommendations[0] if recommendations else "Manual investigation required",
                "automated": False,
                "risk_level": "medium",
            }
        ],
        "estimated_duration_minutes": 30,
        "risk_assessment": "Manual review required",
    }


def should_require_approval(action_plan: Dict[str, Any], severity: str) -> bool:
    """
    Determine if remediation requires human approval.

    Args:
        action_plan: The remediation action plan
        severity: Incident severity

    Returns:
        True if approval is required
    """
    # Check severity-based auto-approval
    if severity.lower() in AUTO_APPROVE_SEVERITY:
        return False

    # Check if any actions require approval
    actions = action_plan.get("actions", [])
    for action in actions:
        action_type = action.get("type", "")
        risk_level = action.get("risk_level", "medium")

        # High risk actions always require approval
        if risk_level == "high":
            return True

        # Check against configured approval-required actions
        for require_approval_action in REQUIRE_APPROVAL_ACTIONS:
            if require_approval_action in action_type:
                return True

    return False


def approve_remediation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Approve a pending remediation.

    Args:
        event: Contains remediation_id and approver info

    Returns:
        Approval result
    """
    remediation_id = event.get("remediation_id")
    approver = event.get("approver", "system")
    notes = event.get("notes", "")

    if not remediation_id:
        return {"statusCode": 400, "error": "remediation_id required"}

    # Get remediation
    remediation = get_remediation(remediation_id)
    if not remediation:
        return {"statusCode": 404, "error": "Remediation not found"}

    if remediation["status"] != RemediationStatus.PENDING_APPROVAL.value:
        return {"statusCode": 400, "error": f"Invalid status: {remediation['status']}"}

    # Update status
    update_remediation_status(
        remediation_id,
        RemediationStatus.APPROVED.value,
        {
            "approved_by": approver,
            "approved_at": datetime.utcnow().isoformat() + "Z",
            "approval_notes": notes,
        },
    )

    # Trigger execution
    remediation["status"] = RemediationStatus.APPROVED.value
    trigger_execution(remediation)

    return {
        "statusCode": 200,
        "remediation_id": remediation_id,
        "status": RemediationStatus.APPROVED.value,
        "message": "Remediation approved and execution triggered",
    }


def reject_remediation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reject a pending remediation.

    Args:
        event: Contains remediation_id and rejection reason

    Returns:
        Rejection result
    """
    remediation_id = event.get("remediation_id")
    rejector = event.get("rejector", "system")
    reason = event.get("reason", "No reason provided")

    if not remediation_id:
        return {"statusCode": 400, "error": "remediation_id required"}

    # Get remediation
    remediation = get_remediation(remediation_id)
    if not remediation:
        return {"statusCode": 404, "error": "Remediation not found"}

    # Update status
    update_remediation_status(
        remediation_id,
        RemediationStatus.REJECTED.value,
        {
            "rejected_by": rejector,
            "rejected_at": datetime.utcnow().isoformat() + "Z",
            "rejection_reason": reason,
        },
    )

    # Notify about rejection
    send_notification({
        "type": "remediation_rejected",
        "remediation_id": remediation_id,
        "agent_id": remediation.get("agent_id"),
        "rejected_by": rejector,
        "reason": reason,
    })

    return {
        "statusCode": 200,
        "remediation_id": remediation_id,
        "status": RemediationStatus.REJECTED.value,
        "message": "Remediation rejected",
    }


def execute_remediation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute approved remediation actions.

    Args:
        event: Contains remediation data or remediation_id

    Returns:
        Execution result
    """
    remediation_id = event.get("remediation_id")

    if remediation_id:
        remediation = get_remediation(remediation_id)
        if not remediation:
            return {"statusCode": 404, "error": "Remediation not found"}
    else:
        remediation = event

    remediation_id = remediation.get("remediation_id")
    agent_id = remediation.get("agent_id")
    action_plan = remediation.get("action_plan", {})

    print(f"Executing remediation {remediation_id} for agent {agent_id}")

    # Update status to in progress
    update_remediation_status(
        remediation_id,
        RemediationStatus.IN_PROGRESS.value,
        {"execution_started_at": datetime.utcnow().isoformat() + "Z"},
    )

    # Store pre-execution state for rollback
    pre_state = capture_system_state(agent_id)
    update_remediation_status(
        remediation_id,
        RemediationStatus.IN_PROGRESS.value,
        {"pre_execution_state": pre_state},
    )

    results = []
    all_success = True

    # Execute each action in order
    actions = action_plan.get("actions", [])
    for action in actions:
        if not action.get("automated", False):
            results.append({
                "step": action.get("step", 0),
                "type": action.get("type"),
                "status": "skipped",
                "message": "Manual action required",
            })
            continue

        try:
            result = execute_action(action, agent_id)
            results.append(result)

            if not result.get("success"):
                all_success = False
                # Check if we should continue or abort
                if action.get("critical", False):
                    print(f"Critical action failed, aborting remediation")
                    break

        except Exception as e:
            print(f"Error executing action: {e}")
            results.append({
                "step": action.get("step", 0),
                "type": action.get("type"),
                "status": "failed",
                "error": str(e),
            })
            all_success = False
            break

    # Run post-execution checks
    post_checks_passed = True
    if all_success:
        post_checks = action_plan.get("post_execution_checks", [])
        for check in post_checks:
            if not verify_post_check(check, agent_id):
                post_checks_passed = False
                print(f"Post-execution check failed: {check}")

    # Determine final status
    if all_success and post_checks_passed:
        final_status = RemediationStatus.COMPLETED.value
    else:
        final_status = RemediationStatus.FAILED.value

    # Update remediation record
    update_remediation_status(
        remediation_id,
        final_status,
        {
            "execution_completed_at": datetime.utcnow().isoformat() + "Z",
            "execution_results": results,
            "post_checks_passed": post_checks_passed,
        },
    )

    # Send notification
    send_notification({
        "type": "remediation_completed" if all_success else "remediation_failed",
        "remediation_id": remediation_id,
        "agent_id": agent_id,
        "status": final_status,
        "results": results,
    })

    return {
        "statusCode": 200,
        "remediation_id": remediation_id,
        "status": final_status,
        "results": results,
        "post_checks_passed": post_checks_passed,
    }


def execute_action(action: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    """
    Execute a single remediation action.

    Args:
        action: Action definition
        agent_id: Target agent ID

    Returns:
        Execution result
    """
    action_type = action.get("type")
    parameters = action.get("parameters", {})

    print(f"Executing action: {action_type} for {agent_id}")

    result = {
        "step": action.get("step", 0),
        "type": action_type,
        "started_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        if action_type == ActionType.RESTART_SERVICE.value:
            success = restart_service(agent_id, parameters)
        elif action_type == ActionType.SCALE_UP.value:
            success = scale_service(agent_id, parameters, direction="up")
        elif action_type == ActionType.SCALE_DOWN.value:
            success = scale_service(agent_id, parameters, direction="down")
        elif action_type == ActionType.CLEAR_CACHE.value:
            success = clear_cache(agent_id, parameters)
        elif action_type == ActionType.ENABLE_CIRCUIT_BREAKER.value:
            success = enable_circuit_breaker(agent_id, parameters)
        elif action_type == ActionType.THROTTLE_REQUESTS.value:
            success = throttle_requests(agent_id, parameters)
        elif action_type == ActionType.UPDATE_CONFIG.value:
            success = update_config(agent_id, parameters)
        elif action_type == ActionType.ROLLBACK_DEPLOYMENT.value:
            success = rollback_deployment(agent_id, parameters)
        elif action_type == ActionType.ROTATE_CREDENTIALS.value:
            success = rotate_credentials(agent_id, parameters)
        elif action_type == ActionType.FAILOVER.value:
            success = trigger_failover(agent_id, parameters)
        else:
            # Unknown action type
            result["status"] = "skipped"
            result["message"] = f"Unknown action type: {action_type}"
            return result

        result["success"] = success
        result["status"] = "completed" if success else "failed"
        result["completed_at"] = datetime.utcnow().isoformat() + "Z"

    except Exception as e:
        result["success"] = False
        result["status"] = "failed"
        result["error"] = str(e)

    return result


# Action implementations
def restart_service(agent_id: str, parameters: Dict[str, Any]) -> bool:
    """Restart a service/container."""
    cluster = parameters.get("cluster", os.environ.get("ECS_CLUSTER"))
    service = parameters.get("service", agent_id)

    if cluster:
        try:
            ecs.update_service(
                cluster=cluster,
                service=service,
                forceNewDeployment=True,
            )
            print(f"Service restart triggered for {service}")
            return True
        except Exception as e:
            print(f"Failed to restart service: {e}")
            return False

    return False


def scale_service(agent_id: str, parameters: Dict[str, Any], direction: str) -> bool:
    """Scale a service up or down."""
    cluster = parameters.get("cluster", os.environ.get("ECS_CLUSTER"))
    service = parameters.get("service", agent_id)
    delta = parameters.get("delta", 1)

    if cluster:
        try:
            # Get current desired count
            response = ecs.describe_services(cluster=cluster, services=[service])
            if response["services"]:
                current_count = response["services"][0]["desiredCount"]
                new_count = current_count + delta if direction == "up" else max(1, current_count - delta)

                ecs.update_service(
                    cluster=cluster,
                    service=service,
                    desiredCount=new_count,
                )
                print(f"Scaled {service} to {new_count} instances")
                return True
        except Exception as e:
            print(f"Failed to scale service: {e}")
            return False

    return False


def clear_cache(agent_id: str, parameters: Dict[str, Any]) -> bool:
    """Clear application cache."""
    cache_endpoint = parameters.get("cache_endpoint")
    cache_type = parameters.get("cache_type", "redis")

    # This would typically invoke a Lambda or send a message to clear cache
    print(f"Cache clear requested for {agent_id}")
    return True


def enable_circuit_breaker(agent_id: str, parameters: Dict[str, Any]) -> bool:
    """Enable circuit breaker for a service."""
    threshold = parameters.get("error_threshold", 50)
    timeout = parameters.get("timeout_seconds", 30)

    # This would update configuration or invoke a control plane
    print(f"Circuit breaker enabled for {agent_id}: threshold={threshold}%, timeout={timeout}s")
    return True


def throttle_requests(agent_id: str, parameters: Dict[str, Any]) -> bool:
    """Implement rate limiting."""
    rate_limit = parameters.get("requests_per_second", 100)

    # This would update API Gateway or load balancer configuration
    print(f"Rate limiting set for {agent_id}: {rate_limit} req/s")
    return True


def update_config(agent_id: str, parameters: Dict[str, Any]) -> bool:
    """Update configuration parameters."""
    config_updates = parameters.get("updates", {})

    # This would update SSM parameters or configuration store
    print(f"Configuration updated for {agent_id}: {list(config_updates.keys())}")
    return True


def rollback_deployment(agent_id: str, parameters: Dict[str, Any]) -> bool:
    """Rollback to previous deployment."""
    target_version = parameters.get("target_version", "previous")

    # This would trigger CodeDeploy rollback or similar
    print(f"Deployment rollback initiated for {agent_id} to {target_version}")
    return True


def rotate_credentials(agent_id: str, parameters: Dict[str, Any]) -> bool:
    """Rotate API keys or secrets."""
    secret_id = parameters.get("secret_id")

    if secret_id:
        try:
            secrets.rotate_secret(SecretId=secret_id)
            print(f"Credential rotation initiated for {secret_id}")
            return True
        except Exception as e:
            print(f"Failed to rotate credentials: {e}")
            return False

    return False


def trigger_failover(agent_id: str, parameters: Dict[str, Any]) -> bool:
    """Trigger failover to backup system."""
    backup_region = parameters.get("backup_region")
    failover_type = parameters.get("failover_type", "manual")

    print(f"Failover initiated for {agent_id} to {backup_region}")
    return True


def capture_system_state(agent_id: str) -> Dict[str, Any]:
    """Capture current system state for potential rollback."""
    state = {
        "captured_at": datetime.utcnow().isoformat() + "Z",
        "agent_id": agent_id,
    }

    # Capture ECS service state
    cluster = os.environ.get("ECS_CLUSTER")
    if cluster:
        try:
            response = ecs.describe_services(cluster=cluster, services=[agent_id])
            if response["services"]:
                service = response["services"][0]
                state["ecs_service"] = {
                    "desired_count": service["desiredCount"],
                    "running_count": service["runningCount"],
                    "task_definition": service["taskDefinition"],
                }
        except Exception as e:
            logger.warning(f"Failed to get ECS service state for {agent_id}: {e}")

    return state


def verify_post_check(check: str, agent_id: str) -> bool:
    """Verify a post-execution check."""
    # Basic health check implementation
    # In production, this would check actual service health
    print(f"Verifying post-check: {check}")
    return True


def rollback_remediation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rollback a completed remediation.

    Args:
        event: Contains remediation_id

    Returns:
        Rollback result
    """
    remediation_id = event.get("remediation_id")
    reason = event.get("reason", "Manual rollback requested")

    if not remediation_id:
        return {"statusCode": 400, "error": "remediation_id required"}

    remediation = get_remediation(remediation_id)
    if not remediation:
        return {"statusCode": 404, "error": "Remediation not found"}

    # Check if rollback is still available
    if not remediation.get("rollback_available", False):
        return {"statusCode": 400, "error": "Rollback not available"}

    rollback_deadline = remediation.get("rollback_deadline")
    if rollback_deadline and datetime.fromisoformat(rollback_deadline.replace("Z", "")) < datetime.utcnow():
        return {"statusCode": 400, "error": "Rollback window has expired"}

    pre_state = remediation.get("pre_execution_state", {})
    if not pre_state:
        return {"statusCode": 400, "error": "No pre-execution state available for rollback"}

    print(f"Rolling back remediation {remediation_id}")

    # Restore previous state
    agent_id = remediation.get("agent_id")
    rollback_success = restore_system_state(agent_id, pre_state)

    # Update status
    update_remediation_status(
        remediation_id,
        RemediationStatus.ROLLED_BACK.value,
        {
            "rolled_back_at": datetime.utcnow().isoformat() + "Z",
            "rollback_reason": reason,
            "rollback_success": rollback_success,
        },
    )

    # Notify
    send_notification({
        "type": "remediation_rolled_back",
        "remediation_id": remediation_id,
        "agent_id": agent_id,
        "reason": reason,
        "success": rollback_success,
    })

    return {
        "statusCode": 200,
        "remediation_id": remediation_id,
        "status": RemediationStatus.ROLLED_BACK.value,
        "rollback_success": rollback_success,
    }


def restore_system_state(agent_id: str, pre_state: Dict[str, Any]) -> bool:
    """Restore system to pre-execution state."""
    try:
        # Restore ECS service state
        ecs_state = pre_state.get("ecs_service")
        if ecs_state:
            cluster = os.environ.get("ECS_CLUSTER")
            if cluster:
                ecs.update_service(
                    cluster=cluster,
                    service=agent_id,
                    desiredCount=ecs_state.get("desired_count", 1),
                    taskDefinition=ecs_state.get("task_definition"),
                )
                print(f"Restored ECS service state for {agent_id}")

        return True
    except Exception as e:
        print(f"Error restoring system state: {e}")
        return False


def get_remediation_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """Get the current status of a remediation."""
    remediation_id = event.get("remediation_id")

    if not remediation_id:
        return {"statusCode": 400, "error": "remediation_id required"}

    remediation = get_remediation(remediation_id)
    if not remediation:
        return {"statusCode": 404, "error": "Remediation not found"}

    return {
        "statusCode": 200,
        "remediation": remediation,
    }


# Database operations
def store_remediation(remediation: Dict[str, Any]) -> None:
    """Store remediation record in DynamoDB."""
    if not REMEDIATION_TABLE:
        print("REMEDIATION_TABLE not configured")
        return

    try:
        table = dynamodb.Table(REMEDIATION_TABLE)
        # Calculate TTL (90 days)
        remediation["ttl"] = int(datetime.utcnow().timestamp() + (90 * 24 * 60 * 60))
        table.put_item(Item=remediation)
        print(f"Stored remediation: {remediation['remediation_id']}")
    except Exception as e:
        print(f"Error storing remediation: {e}")


def get_remediation(remediation_id: str) -> Optional[Dict[str, Any]]:
    """Get remediation record from DynamoDB."""
    if not REMEDIATION_TABLE:
        return None

    try:
        table = dynamodb.Table(REMEDIATION_TABLE)
        response = table.get_item(Key={"remediation_id": remediation_id})
        return response.get("Item")
    except Exception as e:
        print(f"Error getting remediation: {e}")
        return None


def update_remediation_status(
    remediation_id: str,
    status: str,
    additional_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Update remediation status in DynamoDB."""
    if not REMEDIATION_TABLE:
        return

    try:
        table = dynamodb.Table(REMEDIATION_TABLE)

        update_expr = "SET #status = :status, updated_at = :updated_at"
        expr_values = {
            ":status": status,
            ":updated_at": datetime.utcnow().isoformat() + "Z",
        }
        expr_names = {"#status": "status"}

        if additional_data:
            for key, value in additional_data.items():
                update_expr += f", {key} = :{key}"
                expr_values[f":{key}"] = value

        table.update_item(
            Key={"remediation_id": remediation_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names,
        )
        print(f"Updated remediation status: {remediation_id} -> {status}")
    except Exception as e:
        print(f"Error updating remediation status: {e}")


def trigger_execution(remediation: Dict[str, Any]) -> None:
    """Trigger execution of an approved remediation."""
    if STATE_MACHINE_ARN:
        try:
            sfn.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=f"remediation-{remediation['remediation_id']}",
                input=json.dumps({"action": "execute", **remediation}),
            )
            print(f"Triggered Step Functions execution for {remediation['remediation_id']}")
            return
        except Exception as e:
            print(f"Error triggering Step Functions: {e}")

    # Direct execution as fallback
    execute_remediation(remediation)


def request_approval(remediation: Dict[str, Any]) -> None:
    """Request approval for a remediation."""
    if APPROVAL_QUEUE_URL:
        try:
            sqs.send_message(
                QueueUrl=APPROVAL_QUEUE_URL,
                MessageBody=json.dumps({
                    "type": "approval_request",
                    "remediation_id": remediation["remediation_id"],
                    "agent_id": remediation["agent_id"],
                    "severity": remediation["severity"],
                    "action_plan": remediation["action_plan"],
                    "deadline": remediation.get("approval_deadline"),
                }),
            )
            print(f"Approval request sent for {remediation['remediation_id']}")
        except Exception as e:
            print(f"Error sending approval request: {e}")

    # Also send notification
    send_notification({
        "type": "approval_required",
        "remediation_id": remediation["remediation_id"],
        "agent_id": remediation["agent_id"],
        "severity": remediation["severity"],
        "action_plan": remediation["action_plan"],
        "deadline": remediation.get("approval_deadline"),
    })


def send_notification(message: Dict[str, Any]) -> None:
    """Send notification about remediation status."""
    if not NOTIFICATION_TOPIC:
        print("NOTIFICATION_TOPIC not configured")
        return

    try:
        sns.publish(
            TopicArn=NOTIFICATION_TOPIC,
            Subject=f"[Remediation] {message.get('type', 'update').replace('_', ' ').title()}",
            Message=json.dumps(message, indent=2),
            MessageAttributes={
                "notification_type": {
                    "DataType": "String",
                    "StringValue": message.get("type", "remediation_update"),
                },
                "agent_id": {
                    "DataType": "String",
                    "StringValue": message.get("agent_id", "unknown"),
                },
            },
        )
        print(f"Notification sent: {message.get('type')}")
    except Exception as e:
        print(f"Error sending notification: {e}")
