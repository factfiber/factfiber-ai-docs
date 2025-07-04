# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Test authentication routes."""

from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from ff_docs.auth.middleware import get_current_user, get_optional_user
from ff_docs.auth.models import (
    GitHubTeam,
    PermissionResult,
    User,
    UserSession,
)
from ff_docs.server.main import app


class TestAuthRoutes:
    """Test authentication route endpoints."""

    def setup_method(self) -> None:
        """Set up test client and common test data."""
        self.client = TestClient(app)

        # Create test user data
        self.test_user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            github_id=12345,
            created_at=datetime.now(UTC),
        )

        self.test_team = GitHubTeam(
            org="testorg",
            team="developers",
            role="member",
        )

        self.test_session = UserSession(
            user=self.test_user,
            teams=[self.test_team],
            permissions=["docs:read", "docs:write"],
            session_id="test-session-123",
            expires_at=datetime.now(UTC),
        )

    def _with_auth_user(
        self,
        test_func: Callable[[], None],
        user_session: UserSession | None = None,
    ) -> None:
        """Run test function with authenticated user dependency override."""
        session_to_use = user_session or self.test_session

        def mock_get_current_user() -> UserSession:
            return session_to_use

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            return test_func()
        finally:
            app.dependency_overrides.clear()

    def _with_optional_user(
        self,
        test_func: Callable[[], None],
        user_session: UserSession | None = None,
    ) -> None:
        """Run test function with optional user dependency override."""

        def mock_get_optional_user() -> UserSession | None:
            return user_session

        app.dependency_overrides[get_optional_user] = mock_get_optional_user

        try:
            return test_func()
        finally:
            app.dependency_overrides.clear()

    def test_raise_auth_error(self) -> None:
        """Test the _raise_auth_error helper function."""
        from ff_docs.server.routes.auth import _raise_auth_error

        with pytest.raises(HTTPException) as exc_info:
            _raise_auth_error("Test error message")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Test error message"

    @patch("ff_docs.server.routes.auth.GitHubAuthenticator")
    @patch("ff_docs.server.routes.auth.JWTHandler")
    def test_login_success(
        self, mock_jwt_handler_class: Mock, mock_github_auth_class: Mock
    ) -> None:
        """Test successful login."""
        # Setup mocks
        mock_github_auth = AsyncMock()
        mock_github_auth_class.return_value = mock_github_auth
        mock_github_auth.authenticate_user.return_value = self.test_session

        mock_jwt_handler = Mock()
        mock_jwt_handler_class.return_value = mock_jwt_handler
        mock_jwt_handler.create_access_token.return_value = "test.jwt.token"
        mock_jwt_handler.get_token_expiry.return_value = datetime.now(UTC)

        # Make request
        login_request = {"github_token": "valid_token"}
        response = self.client.post("/auth/login", json=login_request)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test.jwt.token"  # noqa: S105
        assert data["token_type"] == "bearer"  # noqa: S105
        assert "expires_in" in data
        assert data["user"]["username"] == "testuser"

        # Verify method calls
        mock_github_auth.authenticate_user.assert_called_once_with(
            "valid_token"
        )
        mock_jwt_handler.create_access_token.assert_called_once_with(
            self.test_user, "test-session-123"
        )

    @patch("ff_docs.server.routes.auth.GitHubAuthenticator")
    def test_login_invalid_token(self, mock_github_auth_class: Mock) -> None:
        """Test login with invalid GitHub token."""
        # Setup mock to return None (authentication failed)
        mock_github_auth = AsyncMock()
        mock_github_auth_class.return_value = mock_github_auth
        mock_github_auth.authenticate_user.return_value = None

        # Make request
        login_request = {"github_token": "invalid_token"}
        response = self.client.post("/auth/login", json=login_request)

        # Verify response
        assert response.status_code == 401
        assert "Invalid GitHub token" in response.json()["detail"]

    @patch("ff_docs.server.routes.auth.GitHubAuthenticator")
    def test_login_server_error(self, mock_github_auth_class: Mock) -> None:
        """Test login with server error."""
        # Setup mock to raise exception
        mock_github_auth = AsyncMock()
        mock_github_auth_class.return_value = mock_github_auth
        mock_github_auth.authenticate_user.side_effect = Exception(
            "Server error"
        )

        # Make request
        login_request = {"github_token": "valid_token"}
        response = self.client.post("/auth/login", json=login_request)

        # Verify response
        assert response.status_code == 500
        assert "Authentication failed" in response.json()["detail"]

    def test_logout_success(self) -> None:
        """Test successful logout."""

        def run_test() -> None:
            response = self.client.post("/auth/logout")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Successfully logged out"
            assert data["username"] == "testuser"

        self._with_auth_user(run_test)

    def test_logout_error(self) -> None:
        """Test logout with error."""

        def run_test() -> None:
            with patch("ff_docs.server.routes.auth.logger") as mock_logger:
                mock_logger.info.side_effect = Exception("Logout error")
                response = self.client.post("/auth/logout")
                assert response.status_code == 500
                assert "Logout failed" in response.json()["detail"]

        self._with_auth_user(run_test)

    def test_get_current_user_info(self) -> None:
        """Test get current user info endpoint."""

        def run_test() -> None:
            response = self.client.get("/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["username"] == "testuser"
            assert data["teams"][0]["org"] == "testorg"
            assert "docs:read" in data["permissions"]
            assert data["session_id"] == "test-session-123"
            assert "expires_at" in data

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.auth.OAuth2ProxyHandler")
    def test_get_auth_status_authenticated(
        self, mock_oauth2_proxy_class: Mock
    ) -> None:
        """Test auth status with authenticated user."""

        def run_test() -> None:
            mock_oauth2_proxy = Mock()
            mock_oauth2_proxy_class.return_value = mock_oauth2_proxy
            mock_oauth2_proxy.validate_oauth2_proxy_headers.return_value = True
            mock_oauth2_proxy.get_user_info_from_headers.return_value = {
                "user": "proxy_user",
                "email": "proxy@example.com",
            }

            response = self.client.get("/auth/status")
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["user"]["username"] == "testuser"
            assert data["auth_methods"]["jwt"] is True
            assert data["auth_methods"]["oauth2_proxy"] is True
            assert data["requires_github_token"] is False

        self._with_optional_user(run_test, self.test_session)

    @patch("ff_docs.server.routes.auth.OAuth2ProxyHandler")
    def test_get_auth_status_unauthenticated(
        self, mock_oauth2_proxy_class: Mock
    ) -> None:
        """Test auth status with unauthenticated user."""

        def run_test() -> None:
            mock_oauth2_proxy = Mock()
            mock_oauth2_proxy_class.return_value = mock_oauth2_proxy
            mock_oauth2_proxy.validate_oauth2_proxy_headers.return_value = False

            response = self.client.get("/auth/status")
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is False
            assert data["user"] is None
            assert data["auth_methods"]["jwt"] is True
            assert data["auth_methods"]["oauth2_proxy"] is False
            assert data["requires_github_token"] is True

        self._with_optional_user(run_test, None)

    @patch("ff_docs.server.routes.auth.JWTHandler")
    def test_refresh_token_success(self, mock_jwt_handler_class: Mock) -> None:
        """Test successful token refresh."""

        def run_test() -> None:
            mock_jwt_handler = Mock()
            mock_jwt_handler_class.return_value = mock_jwt_handler
            mock_jwt_handler.create_access_token.return_value = "new.jwt.token"
            mock_jwt_handler.get_token_expiry.return_value = datetime.now(UTC)

            response = self.client.post("/auth/refresh")
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new.jwt.token"  # noqa: S105
            assert data["token_type"] == "bearer"  # noqa: S105
            assert "expires_in" in data
            assert data["user"]["username"] == "testuser"

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.auth.JWTHandler")
    def test_refresh_token_error(self, mock_jwt_handler_class: Mock) -> None:
        """Test token refresh with error."""

        def run_test() -> None:
            mock_jwt_handler = Mock()
            mock_jwt_handler_class.return_value = mock_jwt_handler
            mock_jwt_handler.create_access_token.side_effect = Exception(
                "JWT error"
            )

            response = self.client.post("/auth/refresh")
            assert response.status_code == 500
            assert "Token refresh failed" in response.json()["detail"]

        self._with_auth_user(run_test)

    def test_get_user_permissions(self) -> None:
        """Test get user permissions endpoint."""

        def run_test() -> None:
            response = self.client.get("/auth/permissions")
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert "docs:read" in data["permissions"]
            assert len(data["teams"]) == 1
            assert data["teams"][0]["org"] == "testorg"
            assert data["teams"][0]["team"] == "developers"
            assert "session_expires_at" in data

        self._with_auth_user(run_test)

    @patch("ff_docs.auth.middleware.auth_middleware")
    def test_validate_access_allowed(self, mock_auth_middleware: Mock) -> None:
        """Test access validation when access is allowed."""

        def run_test() -> None:
            permission_result = PermissionResult(
                allowed=True,
                reason="User has required permissions",
                required_permissions=["docs:read"],
            )
            mock_auth_middleware.check_permission.return_value = (
                permission_result
            )

            response = self.client.post(
                "/auth/validate?resource=docs/example&action=read"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] is True
            assert data["reason"] == "User has required permissions"
            assert "docs:read" in data["required_permissions"]
            assert "docs:read" in data["user_permissions"]

        self._with_auth_user(run_test)

    @patch("ff_docs.auth.middleware.auth_middleware")
    def test_validate_access_denied(self, mock_auth_middleware: Mock) -> None:
        """Test access validation when access is denied."""

        def run_test() -> None:
            permission_result = PermissionResult(
                allowed=False,
                reason="Insufficient permissions",
                required_permissions=["admin:write"],
            )
            mock_auth_middleware.check_permission.return_value = (
                permission_result
            )

            response = self.client.post(
                "/auth/validate?resource=admin/config&action=write"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] is False
            assert data["reason"] == "Insufficient permissions"
            assert "admin:write" in data["required_permissions"]

        self._with_auth_user(run_test)

    @patch("ff_docs.auth.middleware.auth_middleware")
    def test_validate_access_error(self, mock_auth_middleware: Mock) -> None:
        """Test access validation with server error."""

        def run_test() -> None:
            mock_auth_middleware.check_permission.side_effect = Exception(
                "Permission check failed"
            )

            response = self.client.post(
                "/auth/validate?resource=docs/example&action=read"
            )
            assert response.status_code == 500
            assert "Access validation failed" in response.json()["detail"]

        self._with_auth_user(run_test)

    def test_login_request_validation(self) -> None:
        """Test login request validation."""
        # Test missing github_token
        response = self.client.post("/auth/login", json={})
        assert response.status_code == 422

        # Test invalid JSON
        response = self.client.post(
            "/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @patch("ff_docs.auth.middleware.auth_middleware")
    def test_validate_access_default_action(self, mock_auth: Mock) -> None:
        """Test validate access with default action parameter."""

        def run_test() -> None:
            permission_result = PermissionResult(
                allowed=True,
                reason="Access granted",
                required_permissions=["docs:read"],
            )
            mock_auth.check_permission.return_value = permission_result

            # Make request without action parameter (should default to "read")
            response = self.client.post("/auth/validate?resource=docs/example")
            assert response.status_code == 200

            # Verify that check_permission was called with action="read"
            call_args = mock_auth.check_permission.call_args[0]
            permission_check = call_args[1]
            assert permission_check.action == "read"

        self._with_auth_user(run_test)
