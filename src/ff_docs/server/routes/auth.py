# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Authentication endpoints."""

import logging
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ff_docs.auth.github_auth import GitHubAuthenticator
from ff_docs.auth.jwt_handler import JWTHandler
from ff_docs.auth.middleware import get_current_user, get_optional_user
from ff_docs.auth.models import LoginRequest, LoginResponse, UserSession
from ff_docs.auth.oauth2_proxy import OAuth2ProxyHandler

logger = logging.getLogger(__name__)
router = APIRouter()


def _raise_auth_error(message: str) -> NoReturn:
    """Raise authentication error."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
    )


@router.post("/login")  # type: ignore[misc]
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate user with GitHub token."""
    try:
        github_auth = GitHubAuthenticator()
        jwt_handler = JWTHandler()

        # Authenticate user with GitHub
        session = await github_auth.authenticate_user(request.github_token)
        if not session:
            _raise_auth_error("Invalid GitHub token or user not authorized")

        # Create JWT token
        access_token = jwt_handler.create_access_token(
            session.user, session.session_id
        )

        # Calculate token expiration
        token_expiry = jwt_handler.get_token_expiry(access_token)
        expires_in = (
            int((token_expiry - session.user.created_at).total_seconds())
            if token_expiry
            else 1800
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",  # noqa: S106
            expires_in=expires_in,
            user=session.user,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        ) from e


@router.post("/logout")  # type: ignore[misc]
async def logout(
    current_user: Annotated[UserSession, Depends(get_current_user)],
) -> dict[str, Any]:
    """Logout current user."""
    try:
        # TODO: Implement token blacklisting/session invalidation
        logger.info("User logged out: %s", current_user.user.username)

    except Exception as e:
        logger.exception("Logout failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        ) from e
    else:
        return {
            "message": "Successfully logged out",
            "username": current_user.user.username,
        }


@router.get("/me")  # type: ignore[misc]
async def get_current_user_info(
    current_user: Annotated[UserSession, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get current user information."""
    return {
        "user": current_user.user.model_dump(),
        "teams": [team.model_dump() for team in current_user.teams],
        "permissions": current_user.permissions,
        "session_id": current_user.session_id,
        "expires_at": current_user.expires_at.isoformat(),
    }


@router.get("/status")  # type: ignore[misc]
async def get_auth_status(
    request: Request,
    current_user: Annotated[UserSession | None, Depends(get_optional_user)],
) -> dict[str, Any]:
    """Get authentication status and available methods."""
    oauth2_proxy = OAuth2ProxyHandler()

    # Check OAuth2-Proxy headers
    oauth2_proxy_available = oauth2_proxy.validate_oauth2_proxy_headers(request)
    oauth2_proxy_info = (
        oauth2_proxy.get_user_info_from_headers(request)
        if oauth2_proxy_available
        else None
    )

    return {
        "authenticated": current_user is not None,
        "user": current_user.user.model_dump() if current_user else None,
        "auth_methods": {
            "jwt": True,
            "oauth2_proxy": oauth2_proxy_available,
        },
        "oauth2_proxy_info": oauth2_proxy_info,
        "requires_github_token": not oauth2_proxy_available,
    }


@router.post("/refresh")  # type: ignore[misc]
async def refresh_token(
    current_user: Annotated[UserSession, Depends(get_current_user)],
) -> LoginResponse:
    """Refresh JWT access token."""
    try:
        jwt_handler = JWTHandler()

        # Create new token with same session
        access_token = jwt_handler.create_access_token(
            current_user.user, current_user.session_id
        )

        # Calculate token expiration
        token_expiry = jwt_handler.get_token_expiry(access_token)
        expires_in = (
            int((token_expiry - current_user.user.created_at).total_seconds())
            if token_expiry
            else 1800
        )

        logger.info("Token refreshed for user: %s", current_user.user.username)

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",  # noqa: S106
            expires_in=expires_in,
            user=current_user.user,
        )

    except Exception as e:
        logger.exception("Token refresh failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        ) from e


@router.get("/permissions")  # type: ignore[misc]
async def get_user_permissions(
    current_user: Annotated[UserSession, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get current user's permissions and team memberships."""
    return {
        "username": current_user.user.username,
        "permissions": current_user.permissions,
        "teams": [
            {
                "org": team.org,
                "team": team.team,
                "role": team.role,
            }
            for team in current_user.teams
        ],
        "session_expires_at": current_user.expires_at.isoformat(),
    }


@router.post("/validate")  # type: ignore[misc]
async def validate_access(
    resource: str,
    current_user: Annotated[UserSession, Depends(get_current_user)],
    action: str = "read",
) -> dict[str, Any]:
    """Validate user access to a specific resource."""
    from ff_docs.auth.middleware import auth_middleware
    from ff_docs.auth.models import PermissionCheck

    try:
        check = PermissionCheck(
            resource=resource,
            action=action,
            context={"user": current_user.user.username},
        )

        result = auth_middleware.check_permission(current_user, check)

    except Exception as e:
        logger.exception("Access validation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Access validation failed",
        ) from e
    else:
        return {
            "allowed": result.allowed,
            "reason": result.reason,
            "required_permissions": result.required_permissions,
            "user_permissions": current_user.permissions,
        }
