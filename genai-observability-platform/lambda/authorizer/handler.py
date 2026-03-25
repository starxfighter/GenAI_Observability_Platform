"""
API Key Authorizer Lambda

Validates API keys and returns IAM policies for API Gateway authorization.
"""

import hashlib
import os
from typing import Any, Dict, Optional

import boto3

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb")
AGENT_METADATA_TABLE = os.environ.get("AGENT_METADATA_TABLE", "")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for API Gateway authorization.

    Args:
        event: API Gateway authorizer event
        context: Lambda context

    Returns:
        IAM policy document
    """
    # Extract token from Authorization header
    headers = event.get("headers", {})
    auth_header = headers.get("authorization", headers.get("Authorization", ""))

    if not auth_header.startswith("Bearer "):
        return generate_policy("anonymous", "Deny", event["routeArn"])

    api_key = auth_header[7:]  # Remove 'Bearer ' prefix

    # Hash the API key for comparison
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Get agent ID from header
    agent_id = headers.get("x-agent-id", headers.get("X-Agent-ID", ""))

    if not agent_id:
        return generate_policy("anonymous", "Deny", event["routeArn"])

    # Look up agent
    agent = get_agent(agent_id)

    if not agent:
        print(f"Agent not found: {agent_id}")
        return generate_policy("anonymous", "Deny", event["routeArn"])

    # Verify API key hash
    stored_hash = agent.get("api_key_hash", "")
    if stored_hash != api_key_hash:
        print(f"API key mismatch for agent: {agent_id}")
        return generate_policy("anonymous", "Deny", event["routeArn"])

    # Check if agent is active
    if not agent.get("active", True):
        print(f"Agent is inactive: {agent_id}")
        return generate_policy("anonymous", "Deny", event["routeArn"])

    # Return allow policy with agent context
    return generate_policy(
        agent_id,
        "Allow",
        event["routeArn"],
        context={
            "agent_id": agent_id,
            "team_name": agent.get("team_name", ""),
            "agent_type": agent.get("agent_type", ""),
            "environment": agent.get("environment", ""),
        },
    )


def get_agent(agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Get agent metadata from DynamoDB.

    Args:
        agent_id: Agent identifier

    Returns:
        Agent metadata or None if not found
    """
    if not AGENT_METADATA_TABLE:
        print("AGENT_METADATA_TABLE not configured")
        return None

    try:
        table = dynamodb.Table(AGENT_METADATA_TABLE)
        response = table.get_item(Key={"agent_id": agent_id})
        return response.get("Item")
    except Exception as e:
        print(f"Error fetching agent: {e}")
        return None


def generate_policy(
    principal_id: str,
    effect: str,
    resource: str,
    context: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Generate an IAM policy document.

    Args:
        principal_id: The principal (usually agent_id)
        effect: Allow or Deny
        resource: The API Gateway resource ARN
        context: Optional context to pass to the backend

    Returns:
        IAM policy document
    """
    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource,
                }
            ],
        },
    }

    if context:
        policy["context"] = context

    return policy
