# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Repository-scoped authentication middleware."""

import logging
import re
from typing import Any

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from ff_docs.auth.oauth2_proxy import OAuth2ProxyHandler
from ff_docs.auth.repository_permissions import RepositoryPermissionManager

logger = logging.getLogger(__name__)


class RepositoryScopedAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for repository-specific access control."""

    def __init__(self, app: Any) -> None:  # noqa: ANN401
        """Initialize repository-scoped auth middleware."""
        super().__init__(app)
        self.permission_manager = RepositoryPermissionManager()
        self.oauth2_proxy = OAuth2ProxyHandler()

        # URL patterns that require repository-specific access
        self.repository_patterns = [
            # Documentation access patterns
            re.compile(r"^/docs/repo/(?P<repo_name>[^/]+)/?"),
            re.compile(r"^/api/repos/(?P<repo_name>[^/]+)/?"),
            # MkDocs site patterns (for served documentation)
            re.compile(r"^/site/(?P<repo_name>[^/]+)/?"),
            # Project-specific documentation patterns
            re.compile(r"^/projects/(?P<repo_name>[^/]+)/?"),
        ]

        # Patterns that are always public (no repository scoping)
        self.public_patterns = [
            re.compile(r"^/health/?"),
            re.compile(r"^/auth/?"),
            re.compile(r"^/docs/?$"),  # Main docs page
            re.compile(r"^/docs/overview/?"),
            re.compile(r"^/docs/getting-started/?"),
            re.compile(r"^/openapi\.json$"),
            re.compile(r"^/docs$"),  # API docs
            re.compile(r"^/redoc$"),  # ReDoc
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: Any,  # noqa: ANN401
    ) -> Response:
        """Process request with repository-specific access control."""
        try:
            # Check if this is a public endpoint
            if self._is_public_endpoint(request.url.path):
                logger.debug("Public endpoint accessed: %s", request.url.path)
                return await call_next(request)

            # Extract repository from URL
            repo_name = self._extract_repository_from_url(request.url.path)

            if repo_name:
                logger.debug(
                    "Repository-scoped request: %s -> %s",
                    request.url.path,
                    repo_name,
                )

                # Validate repository access
                has_access = await self._validate_repository_access(
                    request, repo_name
                )

                if not has_access:
                    logger.warning(
                        "Repository access denied: %s for repo %s",
                        self._get_username_from_request(request),
                        repo_name,
                    )
                    self._raise_repository_access_denied(repo_name)

                logger.debug("Repository access granted for: %s", repo_name)

            # Continue with the request
            return await call_next(request)

        except HTTPException:
            # Re-raise HTTP exceptions (like 403 Forbidden)
            raise
        except Exception:
            logger.exception("Error in repository-scoped auth middleware")
            # For middleware errors, allow the request to continue
            # This ensures the system doesn't break due to auth issues
            return await call_next(request)

    def _raise_repository_access_denied(self, repo_name: str) -> None:
        """Raise HTTP exception for repository access denied."""
        message = f"You do not have access to repository '{repo_name}'"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Repository access denied",
                "repository": repo_name,
                "message": message,
            },
        )

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if the endpoint is public and doesn't require repo access."""
        return any(pattern.match(path) for pattern in self.public_patterns)

    def _extract_repository_from_url(self, path: str) -> str | None:
        """Extract repository name from URL path."""
        for pattern in self.repository_patterns:
            match = pattern.match(path)
            if match:
                return match.group("repo_name")
        return None

    def _get_username_from_request(self, request: Request) -> str | None:
        """Extract username from request headers."""
        # Try OAuth2-Proxy headers first
        if self.oauth2_proxy.settings.auth.oauth2_proxy_enabled:
            username = request.headers.get(
                self.oauth2_proxy.settings.auth.oauth2_proxy_user_header
            )
            if username:
                return username

        # Try JWT token (if available)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # TODO: Extract username from JWT token
            # For now, return None to indicate JWT auth
            pass

        return None

    def _get_access_token_from_request(self, request: Request) -> str | None:
        """Extract GitHub access token from request headers."""
        # Try OAuth2-Proxy access token header
        access_token = request.headers.get("X-Auth-Request-Access-Token")
        if access_token:
            return access_token

        # Try Authorization header (for direct JWT/GitHub token auth)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        return None

    async def _validate_repository_access(
        self, request: Request, repo_name: str
    ) -> bool:
        """Validate that the user has access to the specified repository."""
        try:
            # Get username and access token from request
            username = self._get_username_from_request(request)
            access_token = self._get_access_token_from_request(request)

            if not username:
                logger.warning(
                    "No username found in request for repo access check"
                )
                return False

            if not access_token:
                logger.warning(
                    "No access token found in request for repo access check"
                )
                return False

            # Check repository access using GitHub API
            has_access = await self.permission_manager.check_repository_access(
                username=username,
                repo_name=repo_name,
                access_token=access_token,
                required_permission="read",  # Default to read access
            )

            logger.info(
                "Repository access validation: %s -> %s = %s",
                username,
                repo_name,
                has_access,
            )

        except Exception:
            logger.exception(
                "Error validating repository access for %s", repo_name
            )
            # Fail secure: deny access on error
            return False
        else:
            return has_access

    def get_required_permission_for_method(self, method: str) -> str:
        """Get required permission level based on HTTP method."""
        method_permissions = {
            "GET": "read",
            "HEAD": "read",
            "POST": "write",
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "admin",  # Deletions require admin access
        }
        return method_permissions.get(method.upper(), "read")

    async def validate_repository_operation(
        self, request: Request, repo_name: str, operation: str
    ) -> bool:
        """Validate user has permission for specific repository operation."""
        username = self._get_username_from_request(request)
        access_token = self._get_access_token_from_request(request)

        if not username or not access_token:
            return False

        # Map operations to required permissions
        operation_permissions = {
            "read": "read",
            "view": "read",
            "clone": "read",
            "edit": "write",
            "push": "write",
            "manage": "maintain",
            "admin": "admin",
            "delete": "admin",
        }

        required_permission = operation_permissions.get(operation, "read")

        return await self.permission_manager.check_repository_access(
            username=username,
            repo_name=repo_name,
            access_token=access_token,
            required_permission=required_permission,
        )


class RepositoryAccessValidator:
    """Helper class for validating repository access in route handlers."""

    def __init__(self) -> None:
        """Initialize repository access validator."""
        self.permission_manager = RepositoryPermissionManager()
        self.oauth2_proxy = OAuth2ProxyHandler()

    async def require_repository_access(
        self, request: Request, repo_name: str, permission: str = "read"
    ) -> bool:
        """Require user to have specific permission for repository."""
        username = self._get_username_from_request(request)
        access_token = self._get_access_token_from_request(request)

        if not username or not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for repository access",
            )

        has_access = await self.permission_manager.check_repository_access(
            username=username,
            repo_name=repo_name,
            access_token=access_token,
            required_permission=permission,
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Repository access denied",
                    "repository": repo_name,
                    "required_permission": permission,
                    "message": (
                        f"You need '{permission}' access to repository "
                        f"'{repo_name}'"
                    ),
                },
            )

        return True

    def _get_username_from_request(self, request: Request) -> str | None:
        """Extract username from request headers."""
        if self.oauth2_proxy.settings.auth.oauth2_proxy_enabled:
            return request.headers.get(
                self.oauth2_proxy.settings.auth.oauth2_proxy_user_header
            )
        return None

    def _get_access_token_from_request(self, request: Request) -> str | None:
        """Extract access token from request headers."""
        return request.headers.get("X-Auth-Request-Access-Token")


# Global repository access validator instance
repository_access_validator = RepositoryAccessValidator()
