# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Authentication middleware for FastAPI."""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ff_docs.auth.github_auth import GitHubAuthenticator
from ff_docs.auth.jwt_handler import JWTHandler
from ff_docs.auth.models import (
    PermissionCheck,
    PermissionResult,
    TokenData,
    UserSession,
)
from ff_docs.auth.oauth2_proxy import OAuth2ProxyHandler
from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


class AuthenticationMiddleware:
    """Authentication middleware for handling multiple auth methods."""

    def __init__(self) -> None:
        """Initialize authentication middleware."""
        self.settings = get_settings()
        self.jwt_handler = JWTHandler()
        self.oauth2_proxy = OAuth2ProxyHandler()
        self.github_auth = GitHubAuthenticator()

    async def get_current_user(
        self,
        request: Request,
        credentials: (HTTPAuthorizationCredentials | None) = Depends(  # noqa: B008
            security
        ),
    ) -> UserSession:
        """Get current authenticated user from various auth methods."""
        # Try OAuth2-Proxy first (for production deployments)
        if self.settings.auth.oauth2_proxy_enabled:
            session = self.oauth2_proxy.extract_user_from_headers(request)
            if session:
                logger.debug(
                    "Authenticated via OAuth2-Proxy: %s", session.user.username
                )
                return session

        # Try JWT authentication
        if credentials:
            token = credentials.credentials
            token_data = self.jwt_handler.verify_token(token)
            if token_data:
                # TODO: Load full user session from storage/cache
                # For now, create minimal session from token
                session = await self._create_session_from_token(token_data)
                if session:
                    logger.debug(
                        "Authenticated via JWT: %s", session.user.username
                    )
                    return session

        # No valid authentication found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def get_optional_user(
        self,
        request: Request,
        credentials: (HTTPAuthorizationCredentials | None) = Depends(  # noqa: B008
            security
        ),
    ) -> UserSession | None:
        """Get current user if authenticated, otherwise None."""
        try:
            return await self.get_current_user(request, credentials)
        except HTTPException:
            return None

    async def _create_session_from_token(
        self, token_data: TokenData
    ) -> UserSession | None:
        """Create user session from JWT token data."""
        # TODO: Implement session storage/retrieval
        # This is a simplified implementation
        try:
            from ff_docs.auth.models import User

            user = User(
                username=token_data.username,
                email="",  # Would be loaded from storage
                is_active=True,
            )

            session = UserSession(
                user=user,
                teams=[],  # Would be loaded from storage
                permissions=["docs:read"],  # Would be calculated from teams
                session_id=token_data.session_id,
                expires_at=token_data.exp,
            )

        except Exception:
            logger.exception("Error creating session from token")
            return None
        else:
            return session

    def check_permission(
        self, session: UserSession, check: PermissionCheck
    ) -> PermissionResult:
        """Check if user has required permissions for a resource."""
        try:
            # Define permission patterns
            permission_patterns = {
                "/health": [],  # Public endpoint
                "/repos/config": [],  # Public endpoint
                "/repos/": ["docs:read"],
                "/repos/discover": ["docs:read"],
                "/repos/enroll": ["repos:manage"],
                "/repos/unenroll": ["repos:manage"],
                "/repos/enroll-all": ["repos:manage"],
            }

            # Check for admin paths
            if check.resource.startswith("/admin"):
                required_permissions = ["docs:admin"]
            else:
                # Get required permissions for resource
                required_permissions = permission_patterns.get(
                    check.resource, ["docs:read"]
                )

            # Check if user has any of the required permissions
            user_permissions = set(session.permissions)
            required_perms_set = set(required_permissions)

            if not required_permissions or required_perms_set.intersection(
                user_permissions
            ):
                return PermissionResult(
                    allowed=True,
                    reason="User has required permissions",
                    required_permissions=required_permissions,
                )
            return PermissionResult(
                allowed=False,
                reason=f"Missing required permissions: {required_permissions}",
                required_permissions=required_permissions,
            )

        except Exception:
            logger.exception("Error checking permissions")
            return PermissionResult(
                allowed=False,
                reason="Permission check failed",
                required_permissions=[],
            )

    def require_permission(
        self, required_permissions: list[str]
    ) -> Callable[..., Any]:
        """Dependency that requires specific permissions."""

        async def permission_checker(
            current_user: UserSession = Depends(  # noqa: B008
                self.get_current_user
            ),
        ) -> UserSession:
            """Check if current user has required permissions."""
            if not required_permissions:
                return current_user

            user_permissions = set(current_user.permissions)
            required_perms_set = set(required_permissions)

            if not required_perms_set.intersection(user_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Insufficient permissions. Required: "
                        f"{required_permissions}"
                    ),
                )

            return current_user

        return permission_checker

    def require_team_membership(
        self, required_teams: list[str]
    ) -> Callable[..., Any]:
        """Dependency that requires specific team membership."""

        async def team_checker(
            current_user: UserSession = Depends(  # noqa: B008
                self.get_current_user
            ),
        ) -> UserSession:
            """Check if current user is member of required teams."""
            if not required_teams:
                return current_user

            user_teams = {team.team for team in current_user.teams}
            required_teams_set = set(required_teams)

            if not required_teams_set.intersection(user_teams):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Team membership required. Required teams: "
                        f"{required_teams}"
                    ),
                )

            return current_user

        return team_checker

    async def require_repository_access(
        self, repo_name: str, current_user: UserSession
    ) -> bool:
        """Check if user has access to a specific repository."""
        # Check if user has admin permissions
        if "docs:admin" in current_user.permissions:
            return True

        # Check if user has general repository management permissions
        if "repos:manage" in current_user.permissions:
            return True

        # TODO: Implement repository-specific access control
        # This would check GitHub API for repository collaborator status
        logger.warning(
            "Repository-specific access control not fully implemented "
            "for repo: %s",
            repo_name,
        )
        return False


# Global authentication middleware instance
auth_middleware = AuthenticationMiddleware()

# Convenience dependencies
get_current_user = auth_middleware.get_current_user
get_optional_user = auth_middleware.get_optional_user
require_permission = auth_middleware.require_permission
require_team_membership = auth_middleware.require_team_membership
