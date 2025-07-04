# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001
# mypy: disable-error-code="method-assign"

"""Unit tests for authentication middleware module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from ff_docs.auth.middleware import (
    AuthenticationMiddleware,
    get_current_user,
    get_optional_user,
    require_permission,
    require_team_membership,
)
from ff_docs.auth.models import (
    GitHubTeam,
    PermissionCheck,
    TokenData,
    User,
    UserSession,
)


class TestAuthenticationMiddleware:
    """Test AuthenticationMiddleware class."""

    @pytest.fixture
    def middleware(self) -> AuthenticationMiddleware:
        """Create an AuthenticationMiddleware instance."""
        return AuthenticationMiddleware()

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock request object."""
        request = MagicMock(spec=Request)
        request.headers = {}
        return request

    @pytest.fixture
    def user(self) -> User:
        """Create a test user."""
        return User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            github_id=12345,
        )

    @pytest.fixture
    def user_session(self, user: User) -> UserSession:
        """Create a test user session."""
        team = GitHubTeam(
            org="test-org",
            team="test-team",
            role="member",
        )

        return UserSession(
            user=user,
            teams=[team],
            permissions=["docs:read", "repos:manage"],
            session_id="test-session-123",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            access_token="github-token",  # noqa: S106
        )

    @pytest.fixture
    def token_data(self) -> TokenData:
        """Create test token data."""
        return TokenData(
            username="testuser",
            sub="testuser",
            exp=int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            iat=int(datetime.now(UTC).timestamp()),
            session_id="test-session-123",
        )

    @pytest.fixture
    def credentials(self) -> HTTPAuthorizationCredentials:
        """Create test HTTP authorization credentials."""
        return HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test.jwt.token",
        )

    def test_middleware_initialization(
        self, middleware: AuthenticationMiddleware
    ) -> None:
        """Test AuthenticationMiddleware initialization."""
        assert middleware.settings is not None
        assert middleware.jwt_handler is not None
        assert middleware.oauth2_proxy is not None
        assert middleware.github_auth is not None

    @pytest.mark.asyncio
    async def test_get_current_user_oauth2_proxy(
        self,
        middleware: AuthenticationMiddleware,
        mock_request: MagicMock,
        user_session: UserSession,
    ) -> None:
        """Test getting current user via OAuth2-Proxy."""
        # Enable OAuth2-Proxy
        middleware.settings.auth.oauth2_proxy_enabled = True

        # Mock OAuth2-Proxy extraction
        middleware.oauth2_proxy.extract_user_from_headers = MagicMock(
            return_value=user_session
        )

        result = await middleware.get_current_user(mock_request, None)

        assert result == user_session
        middleware.oauth2_proxy.extract_user_from_headers.assert_called_once_with(
            mock_request
        )

    @pytest.mark.asyncio
    async def test_get_current_user_jwt(
        self,
        middleware: AuthenticationMiddleware,
        mock_request: MagicMock,
        credentials: HTTPAuthorizationCredentials,
        token_data: TokenData,
        user_session: UserSession,
    ) -> None:
        """Test getting current user via JWT."""
        # Disable OAuth2-Proxy
        middleware.settings.auth.oauth2_proxy_enabled = False

        # Mock JWT verification
        middleware.jwt_handler.verify_token = MagicMock(return_value=token_data)

        # Mock session creation
        middleware._create_session_from_token = AsyncMock(
            return_value=user_session
        )

        result = await middleware.get_current_user(mock_request, credentials)

        assert result == user_session
        middleware.jwt_handler.verify_token.assert_called_once_with(
            credentials.credentials
        )

    @pytest.mark.asyncio
    async def test_get_current_user_no_auth(
        self,
        middleware: AuthenticationMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting current user with no authentication."""
        # Disable OAuth2-Proxy
        middleware.settings.auth.oauth2_proxy_enabled = False

        with pytest.raises(HTTPException) as exc_info:
            await middleware.get_current_user(mock_request, None)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Authentication required"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_jwt(
        self,
        middleware: AuthenticationMiddleware,
        mock_request: MagicMock,
        credentials: HTTPAuthorizationCredentials,
    ) -> None:
        """Test getting current user with invalid JWT."""
        # Disable OAuth2-Proxy
        middleware.settings.auth.oauth2_proxy_enabled = False

        # Mock JWT verification failure
        middleware.jwt_handler.verify_token = MagicMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await middleware.get_current_user(mock_request, credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_optional_user_authenticated(
        self,
        middleware: AuthenticationMiddleware,
        mock_request: MagicMock,
        user_session: UserSession,
    ) -> None:
        """Test getting optional user when authenticated."""
        # Mock get_current_user to return session
        middleware.get_current_user = AsyncMock(return_value=user_session)

        result = await middleware.get_optional_user(mock_request, None)

        assert result == user_session

    @pytest.mark.asyncio
    async def test_get_optional_user_not_authenticated(
        self,
        middleware: AuthenticationMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting optional user when not authenticated."""
        # Mock get_current_user to raise HTTPException
        middleware.get_current_user = AsyncMock(
            side_effect=HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        )

        result = await middleware.get_optional_user(mock_request, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_session_from_token(
        self,
        middleware: AuthenticationMiddleware,
        token_data: TokenData,
    ) -> None:
        """Test creating session from token data."""
        session = await middleware._create_session_from_token(token_data)

        assert session is not None
        assert session.user.username == token_data.username
        assert session.session_id == token_data.session_id
        assert session.permissions == ["docs:read"]

    @pytest.mark.asyncio
    async def test_create_session_from_token_exception(
        self,
        middleware: AuthenticationMiddleware,
    ) -> None:
        """Test creating session from token with exception."""
        # Create invalid token data that will cause exception
        invalid_token_data = MagicMock()
        invalid_token_data.username = None  # Will cause User creation to fail

        session = await middleware._create_session_from_token(
            invalid_token_data
        )

        assert session is None

    def test_check_permission_allowed(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test checking permissions when allowed."""
        check = PermissionCheck(
            resource="/repos/",
            action="read",
        )

        result = middleware.check_permission(user_session, check)

        assert result.allowed is True
        assert result.reason == "User has required permissions"
        assert result.required_permissions == ["docs:read"]

    def test_check_permission_denied(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test checking permissions when denied."""
        # Remove repos:manage permission
        user_session.permissions = ["docs:read"]

        check = PermissionCheck(
            resource="/repos/enroll",
            action="write",
        )

        result = middleware.check_permission(user_session, check)

        assert result.allowed is False
        assert "Missing required permissions" in result.reason
        assert result.required_permissions == ["repos:manage"]

    def test_check_permission_public_endpoint(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test checking permissions for public endpoint."""
        # Remove all permissions
        user_session.permissions = []

        check = PermissionCheck(
            resource="/health",
            action="read",
        )

        result = middleware.check_permission(user_session, check)

        assert result.allowed is True
        assert result.reason == "User has required permissions"
        assert result.required_permissions == []

    def test_check_permission_admin_path(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test checking permissions for admin path."""
        check = PermissionCheck(
            resource="/admin/users",
            action="read",
        )

        result = middleware.check_permission(user_session, check)

        assert result.allowed is False
        assert result.required_permissions == ["docs:admin"]

    def test_check_permission_exception(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test check_permission with exception."""
        # Mock exception in permission checking
        with patch(
            "ff_docs.auth.middleware.set", side_effect=Exception("Error")
        ):
            check = PermissionCheck(
                resource="/repos/",
                action="read",
            )

            result = middleware.check_permission(user_session, check)

            assert result.allowed is False
            assert result.reason == "Permission check failed"

    @pytest.mark.asyncio
    async def test_require_permission_allowed(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test require_permission when user has permissions."""
        permission_checker = middleware.require_permission(["docs:read"])

        # Mock get_current_user
        middleware.get_current_user = AsyncMock(return_value=user_session)

        result = await permission_checker(current_user=user_session)

        assert result == user_session

    @pytest.mark.asyncio
    async def test_require_permission_denied(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test require_permission when user lacks permissions."""
        # Remove required permission
        user_session.permissions = ["other:permission"]

        permission_checker = middleware.require_permission(["docs:read"])

        with pytest.raises(HTTPException) as exc_info:
            await permission_checker(current_user=user_session)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_permission_empty(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test require_permission with empty permissions list."""
        permission_checker = middleware.require_permission([])

        result = await permission_checker(current_user=user_session)

        assert result == user_session

    @pytest.mark.asyncio
    async def test_require_team_membership_allowed(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test require_team_membership when user is member."""
        team_checker = middleware.require_team_membership(["test-team"])

        result = await team_checker(current_user=user_session)

        assert result == user_session

    @pytest.mark.asyncio
    async def test_require_team_membership_denied(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test require_team_membership when user is not member."""
        team_checker = middleware.require_team_membership(["other-team"])

        with pytest.raises(HTTPException) as exc_info:
            await team_checker(current_user=user_session)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Team membership required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_team_membership_empty(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test require_team_membership with empty teams list."""
        team_checker = middleware.require_team_membership([])

        result = await team_checker(current_user=user_session)

        assert result == user_session

    @pytest.mark.asyncio
    async def test_require_repository_access_admin(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test repository access for admin user."""
        # Add admin permission
        user_session.permissions.append("docs:admin")

        has_access = await middleware.require_repository_access(
            "test-repo", user_session
        )

        assert has_access is True

    @pytest.mark.asyncio
    async def test_require_repository_access_manager(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test repository access for user with repos:manage."""
        # User already has repos:manage permission
        has_access = await middleware.require_repository_access(
            "test-repo", user_session
        )

        assert has_access is True

    @pytest.mark.asyncio
    async def test_require_repository_access_denied(
        self,
        middleware: AuthenticationMiddleware,
        user_session: UserSession,
    ) -> None:
        """Test repository access for regular user."""
        # Remove repos:manage permission
        user_session.permissions = ["docs:read"]

        has_access = await middleware.require_repository_access(
            "test-repo", user_session
        )

        assert has_access is False


class TestGlobalFunctions:
    """Test module-level global functions."""

    def test_global_instances(self) -> None:
        """Test that global instances are properly initialized."""
        assert get_current_user is not None
        assert get_optional_user is not None
        assert require_permission is not None
        assert require_team_membership is not None

    @pytest.mark.asyncio
    async def test_global_get_current_user(self) -> None:
        """Test global get_current_user function."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        # Mock the middleware instance
        from ff_docs.auth import middleware as auth_module

        auth_module.auth_middleware.get_current_user = AsyncMock(
            side_effect=HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Test auth required",
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, None)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthenticationIntegration:
    """Integration tests for authentication middleware."""

    @pytest.mark.asyncio
    async def test_full_auth_flow_oauth2_proxy(self) -> None:
        """Test complete authentication flow with OAuth2-Proxy."""
        middleware = AuthenticationMiddleware()
        mock_request = MagicMock(spec=Request)

        # Setup OAuth2-Proxy headers
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Forwarded-Email": "test@example.com",
            "X-Forwarded-Groups": "test-org:test-team",
        }

        # Enable OAuth2-Proxy
        middleware.settings.auth.oauth2_proxy_enabled = True

        # Create expected session
        user = User(
            username="testuser",
            email="test@example.com",
        )
        expected_session = UserSession(
            user=user,
            teams=[GitHubTeam(org="test-org", team="test-team")],
            permissions=["docs:read"],
            session_id="oauth2-proxy-session",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        # Mock OAuth2-Proxy extraction
        middleware.oauth2_proxy.extract_user_from_headers = MagicMock(
            return_value=expected_session
        )

        # Get current user
        session = await middleware.get_current_user(mock_request, None)

        assert session == expected_session

        # Check permissions
        check = PermissionCheck(resource="/repos/", action="read")
        result = middleware.check_permission(session, check)
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_full_auth_flow_jwt(self) -> None:
        """Test complete authentication flow with JWT."""
        middleware = AuthenticationMiddleware()
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        # Disable OAuth2-Proxy
        middleware.settings.auth.oauth2_proxy_enabled = False

        # Create JWT token
        user = User(username="jwtuser", email="jwt@example.com")
        token = middleware.jwt_handler.create_access_token(
            user, "jwt-session-123"
        )

        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        # Get current user
        session = await middleware.get_current_user(mock_request, credentials)

        assert session is not None
        assert session.user.username == "jwtuser"
        assert session.session_id == "jwt-session-123"

        # Test permission checking
        permission_checker = middleware.require_permission(["docs:read"])
        result = await permission_checker(current_user=session)
        assert result == session
