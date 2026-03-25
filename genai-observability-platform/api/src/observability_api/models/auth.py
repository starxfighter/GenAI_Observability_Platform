"""Authentication models and schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Data embedded in JWT token."""

    sub: str  # User ID or API key ID
    exp: datetime
    scopes: list[str] = Field(default_factory=list)


class User(BaseModel):
    """User model."""

    user_id: str
    email: str
    name: str
    role: str = "user"
    is_active: bool = True
    created_at: datetime
    last_login: datetime | None = None


class UserCreate(BaseModel):
    """Schema for creating a user."""

    email: str
    name: str
    password: str
    role: str = "user"


class UserLogin(BaseModel):
    """Schema for user login."""

    email: str
    password: str


class ApiKey(BaseModel):
    """API key model."""

    key_id: str
    name: str
    key_hash: str
    owner_id: str
    scopes: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime
    last_used: datetime | None = None
    expires_at: datetime | None = None


class ApiKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: str
    scopes: list[str] = Field(default_factory=lambda: ["read", "write"])
    expires_in_days: int | None = None


class ApiKeyResponse(BaseModel):
    """API key creation response (includes plain key only once)."""

    key_id: str
    name: str
    api_key: str  # Plain text key, shown only at creation
    scopes: list[str]
    expires_at: datetime | None = None
