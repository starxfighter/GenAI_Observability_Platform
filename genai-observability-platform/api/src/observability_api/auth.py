"""Authentication and authorization."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import get_settings
from .db import DynamoDBClient
from .models.auth import TokenData

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key."""
    return f"obs_{secrets.token_urlsafe(32)}"


def create_access_token(
    subject: str,
    scopes: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    settings = get_settings()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)

    to_encode = {
        "sub": subject,
        "exp": expire,
        "scopes": scopes or [],
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        subject: str = payload.get("sub", "")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        return TokenData(
            sub=subject,
            exp=datetime.fromtimestamp(payload.get("exp", 0)),
            scopes=payload.get("scopes", []),
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


async def verify_api_key(api_key: str) -> dict:
    """Verify an API key against the database."""
    db = DynamoDBClient()
    key_hash = hash_api_key(api_key)

    api_key_data = await db.get_api_key_by_hash(key_hash)

    if not api_key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if not api_key_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is disabled",
        )

    # Check expiration
    expires_at = api_key_data.get("expires_at")
    if expires_at:
        if datetime.fromisoformat(expires_at) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
            )

    # Update last used
    await db.update_api_key_last_used(api_key_data["key_id"])

    return api_key_data


async def get_current_user(
    api_key: Annotated[str | None, Security(api_key_header)] = None,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
) -> dict:
    """Get the current authenticated user from API key or JWT."""
    # Try API key first
    if api_key:
        return await verify_api_key(api_key)

    # Try JWT bearer token
    if bearer:
        token_data = verify_token(bearer.credentials)
        return {
            "user_id": token_data.sub,
            "scopes": token_data.scopes,
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    api_key: Annotated[str | None, Security(api_key_header)] = None,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
) -> dict | None:
    """Get the current user if authenticated, or None."""
    try:
        return await get_current_user(api_key, bearer)
    except HTTPException:
        return None


def require_scope(required_scope: str):
    """Dependency to require a specific scope."""

    async def check_scope(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        scopes = current_user.get("scopes", [])
        if required_scope not in scopes and "admin" not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}",
            )
        return current_user

    return check_scope
