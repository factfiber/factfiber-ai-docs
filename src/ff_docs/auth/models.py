# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Authentication models and data structures."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model for authentication."""

    username: str = Field(..., description="GitHub username")
    email: str = Field(..., description="User email address")
    full_name: str | None = Field(None, description="User's full name")
    avatar_url: str | None = Field(None, description="User's avatar URL")
    github_id: int | None = Field(None, description="GitHub user ID")
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="User creation timestamp"
    )
    last_login: datetime | None = Field(
        None, description="Last login timestamp"
    )


class GitHubTeam(BaseModel):
    """GitHub team information."""

    org: str = Field(..., description="GitHub organization name")
    team: str = Field(..., description="GitHub team name")
    role: str | None = Field(None, description="User's role in the team")


class UserSession(BaseModel):
    """User session information."""

    user: User = Field(..., description="Authenticated user")
    teams: list[GitHubTeam] = Field(
        default_factory=list, description="User's GitHub teams"
    )
    permissions: list[str] = Field(
        default_factory=list, description="User's permissions"
    )
    session_id: str = Field(..., description="Unique session identifier")
    expires_at: datetime = Field(..., description="Session expiration time")


class TokenData(BaseModel):
    """JWT token payload data."""

    username: str = Field(..., description="Username")
    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    session_id: str = Field(..., description="Session identifier")


class LoginRequest(BaseModel):
    """Login request model."""

    github_token: str = Field(..., description="GitHub access token")


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: User = Field(..., description="Authenticated user information")


class PermissionCheck(BaseModel):
    """Permission check request."""

    resource: str = Field(..., description="Resource being accessed")
    action: str = Field(..., description="Action being performed")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )


class PermissionResult(BaseModel):
    """Permission check result."""

    allowed: bool = Field(..., description="Whether access is allowed")
    reason: str = Field(..., description="Reason for the decision")
    required_permissions: list[str] = Field(
        default_factory=list, description="Required permissions for access"
    )
