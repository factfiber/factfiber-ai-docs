# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Authentication and authorization components."""

from ff_docs.auth.github_auth import GitHubAuthenticator
from ff_docs.auth.jwt_handler import JWTHandler
from ff_docs.auth.middleware import (
    AuthenticationMiddleware,
    get_current_user,
    get_optional_user,
    require_permission,
    require_team_membership,
)
from ff_docs.auth.models import (
    GitHubTeam,
    LoginRequest,
    LoginResponse,
    PermissionCheck,
    PermissionResult,
    TokenData,
    User,
    UserSession,
)
from ff_docs.auth.oauth2_proxy import OAuth2ProxyHandler

__all__ = [
    "AuthenticationMiddleware",
    "GitHubAuthenticator",
    "GitHubTeam",
    "JWTHandler",
    "LoginRequest",
    "LoginResponse",
    "OAuth2ProxyHandler",
    "PermissionCheck",
    "PermissionResult",
    "TokenData",
    "User",
    "UserSession",
    "get_current_user",
    "get_optional_user",
    "require_permission",
    "require_team_membership",
]
