# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001
# mypy: disable-error-code="method-assign"

"""Unit tests for repository-scoped authentication middleware."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request, Response, status

from ff_docs.auth.repository_middleware import (
    RepositoryAccessValidator,
    RepositoryScopedAuthMiddleware,
)


class TestRepositoryScopedAuthMiddleware:
    """Test RepositoryScopedAuthMiddleware class."""

    @pytest.fixture
    def app(self) -> MagicMock:
        """Create a mock app."""
        return MagicMock()

    @pytest.fixture
    def middleware(self, app: MagicMock) -> RepositoryScopedAuthMiddleware:
        """Create middleware instance."""
        return RepositoryScopedAuthMiddleware(app)

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.headers = {}
        return request

    @pytest.fixture
    def call_next(self) -> AsyncMock:
        """Create a mock call_next function."""

        async def mock_call_next(request: Request) -> Response:
            return MagicMock(spec=Response)

        return AsyncMock(side_effect=mock_call_next)

    def test_middleware_initialization(
        self, middleware: RepositoryScopedAuthMiddleware
    ) -> None:
        """Test middleware initialization."""
        assert middleware.permission_manager is not None
        assert middleware.oauth2_proxy is not None
        assert len(middleware.repository_patterns) > 0
        assert len(middleware.public_patterns) > 0

    @pytest.mark.asyncio
    async def test_dispatch_public_endpoint(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
        call_next: AsyncMock,
    ) -> None:
        """Test dispatch with public endpoint."""
        mock_request.url.path = "/health/"

        response = await middleware.dispatch(mock_request, call_next)

        assert response is not None
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_non_repository_endpoint(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
        call_next: AsyncMock,
    ) -> None:
        """Test dispatch with non-repository endpoint."""
        mock_request.url.path = "/some/other/path"

        response = await middleware.dispatch(mock_request, call_next)

        assert response is not None
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_repository_endpoint_with_access(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
        call_next: AsyncMock,
    ) -> None:
        """Test dispatch with repository endpoint and access granted."""
        mock_request.url.path = "/docs/repo/test-repo/"
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Auth-Request-Access-Token": "test-token",
        }

        # Mock access validation
        middleware._validate_repository_access = AsyncMock(return_value=True)

        response = await middleware.dispatch(mock_request, call_next)

        assert response is not None
        middleware._validate_repository_access.assert_called_once_with(
            mock_request, "test-repo"
        )
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_repository_endpoint_no_access(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
        call_next: AsyncMock,
    ) -> None:
        """Test dispatch with repository endpoint and access denied."""
        mock_request.url.path = "/docs/repo/test-repo/"
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Auth-Request-Access-Token": "test-token",
        }

        # Mock access validation
        middleware._validate_repository_access = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, call_next)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "test-repo" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_dispatch_http_exception_reraised(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
        call_next: AsyncMock,
    ) -> None:
        """Test that HTTP exceptions are re-raised."""
        mock_request.url.path = "/docs/repo/test-repo/"

        # Mock validation to raise HTTPException
        middleware._validate_repository_access = AsyncMock(
            side_effect=HTTPException(status_code=403, detail="Forbidden")
        )

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, call_next)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_dispatch_general_exception_handled(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
        call_next: AsyncMock,
    ) -> None:
        """Test that general exceptions are handled gracefully."""
        mock_request.url.path = "/docs/repo/test-repo/"

        # Mock extract to raise exception
        middleware._extract_repository_from_url = MagicMock(
            side_effect=Exception("Unexpected error")
        )

        # Should not raise, but continue with request
        response = await middleware.dispatch(mock_request, call_next)

        assert response is not None
        call_next.assert_called_once_with(mock_request)

    def test_is_public_endpoint_true(
        self, middleware: RepositoryScopedAuthMiddleware
    ) -> None:
        """Test checking public endpoints."""
        public_paths = [
            "/health",
            "/health/",
            "/auth/",
            "/docs/",
            "/docs/overview/",
            "/openapi.json",
            "/docs",
            "/redoc",
        ]

        for path in public_paths:
            assert middleware._is_public_endpoint(path) is True

    def test_is_public_endpoint_false(
        self, middleware: RepositoryScopedAuthMiddleware
    ) -> None:
        """Test checking non-public endpoints."""
        non_public_paths = [
            "/docs/repo/test",
            "/api/repos/test",
            "/projects/test",
            "/some/other/path",
        ]

        for path in non_public_paths:
            assert middleware._is_public_endpoint(path) is False

    def test_extract_repository_from_url_docs(
        self, middleware: RepositoryScopedAuthMiddleware
    ) -> None:
        """Test extracting repository from docs URL."""
        paths = [
            ("/docs/repo/test-repo/", "test-repo"),
            ("/docs/repo/my-project", "my-project"),
            ("/docs/repo/org-repo-name/guide", "org-repo-name"),
        ]

        for path, expected in paths:
            assert middleware._extract_repository_from_url(path) == expected

    def test_extract_repository_from_url_api(
        self, middleware: RepositoryScopedAuthMiddleware
    ) -> None:
        """Test extracting repository from API URL."""
        paths = [
            ("/api/repos/test-repo/", "test-repo"),
            ("/api/repos/my-project", "my-project"),
        ]

        for path, expected in paths:
            assert middleware._extract_repository_from_url(path) == expected

    def test_extract_repository_from_url_site(
        self, middleware: RepositoryScopedAuthMiddleware
    ) -> None:
        """Test extracting repository from site URL."""
        assert (
            middleware._extract_repository_from_url("/site/test-repo/")
            == "test-repo"
        )

    def test_extract_repository_from_url_projects(
        self, middleware: RepositoryScopedAuthMiddleware
    ) -> None:
        """Test extracting repository from projects URL."""
        assert (
            middleware._extract_repository_from_url("/projects/test-repo/")
            == "test-repo"
        )

    def test_extract_repository_from_url_none(
        self, middleware: RepositoryScopedAuthMiddleware
    ) -> None:
        """Test extracting repository from non-matching URL."""
        paths = [
            "/health",
            "/auth/login",
            "/docs",
            "/some/other/path",
        ]

        for path in paths:
            assert middleware._extract_repository_from_url(path) is None

    def test_get_username_from_request_oauth2_proxy(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting username from OAuth2-Proxy headers."""
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        mock_request.headers = {"X-Forwarded-User": "testuser"}

        username = middleware._get_username_from_request(mock_request)
        assert username == "testuser"

    def test_get_username_from_request_no_oauth2_proxy(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting username when OAuth2-Proxy is disabled."""
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = False
        mock_request.headers = {"X-Forwarded-User": "testuser"}

        username = middleware._get_username_from_request(mock_request)
        assert username is None

    def test_get_username_from_request_jwt(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting username from JWT (currently returns None)."""
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = False
        mock_request.headers = {"Authorization": "Bearer jwt-token"}

        username = middleware._get_username_from_request(mock_request)
        assert username is None  # JWT extraction not implemented yet

    def test_get_access_token_from_request_oauth2_proxy(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting access token from OAuth2-Proxy header."""
        mock_request.headers = {"X-Auth-Request-Access-Token": "test-token"}

        token = middleware._get_access_token_from_request(mock_request)
        assert token == "test-token"  # noqa: S105

    def test_get_access_token_from_request_authorization(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting access token from Authorization header."""
        mock_request.headers = {"Authorization": "Bearer test-token"}

        token = middleware._get_access_token_from_request(mock_request)
        assert token == "test-token"  # noqa: S105

    def test_get_access_token_from_request_alternative_headers(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting access token from alternative headers."""
        headers_to_test = [
            "X-Forwarded-Access-Token",
            "X-Auth-Access-Token",
            "X-Access-Token",
        ]

        for header in headers_to_test:
            mock_request.headers = {header: "test-token"}
            token = middleware._get_access_token_from_request(mock_request)
            assert token == "test-token"  # noqa: S105

    def test_get_access_token_from_request_none(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting access token when none present."""
        mock_request.headers = {}

        token = middleware._get_access_token_from_request(mock_request)
        assert token is None

    def test_get_access_token_from_request_empty(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test getting access token with empty value."""
        mock_request.headers = {"X-Auth-Request-Access-Token": "  "}

        token = middleware._get_access_token_from_request(mock_request)
        assert token is None

    @pytest.mark.asyncio
    async def test_validate_repository_access_success(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test successful repository access validation."""
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Auth-Request-Access-Token": "test-token",
        }

        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        # Mock permission manager
        middleware.permission_manager.check_repository_access = AsyncMock(
            return_value=True
        )

        has_access = await middleware._validate_repository_access(
            mock_request, "test-repo"
        )

        assert has_access is True
        middleware.permission_manager.check_repository_access.assert_called_once_with(
            username="testuser",
            repo_name="test-repo",
            access_token="test-token",  # noqa: S106
            required_permission="read",
        )

    @pytest.mark.asyncio
    async def test_validate_repository_access_no_username(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test repository access validation with no username."""
        mock_request.headers = {"X-Auth-Request-Access-Token": "test-token"}

        has_access = await middleware._validate_repository_access(
            mock_request, "test-repo"
        )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_validate_repository_access_no_token(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test repository access validation with no token."""
        mock_request.headers = {"X-Forwarded-User": "testuser"}

        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        has_access = await middleware._validate_repository_access(
            mock_request, "test-repo"
        )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_validate_repository_access_denied(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test repository access validation when access denied."""
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Auth-Request-Access-Token": "test-token",
        }

        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        # Mock permission manager to deny access
        middleware.permission_manager.check_repository_access = AsyncMock(
            return_value=False
        )

        has_access = await middleware._validate_repository_access(
            mock_request, "test-repo"
        )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_validate_repository_access_exception(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test repository access validation with exception."""
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Auth-Request-Access-Token": "test-token",
        }

        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        # Mock permission manager to raise exception
        middleware.permission_manager.check_repository_access = AsyncMock(
            side_effect=Exception("API error")
        )

        has_access = await middleware._validate_repository_access(
            mock_request, "test-repo"
        )

        # Should fail secure
        assert has_access is False

    def test_get_required_permission_for_method(
        self, middleware: RepositoryScopedAuthMiddleware
    ) -> None:
        """Test getting required permission for HTTP methods."""
        method_tests = [
            ("GET", "read"),
            ("get", "read"),
            ("HEAD", "read"),
            ("POST", "write"),
            ("PUT", "write"),
            ("PATCH", "write"),
            ("DELETE", "admin"),
            ("OPTIONS", "read"),  # Default
            ("UNKNOWN", "read"),  # Default
        ]

        for method, expected in method_tests:
            assert (
                middleware.get_required_permission_for_method(method)
                == expected
            )

    @pytest.mark.asyncio
    async def test_validate_repository_operation_success(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test validating repository operation successfully."""
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Auth-Request-Access-Token": "test-token",
        }

        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        # Mock permission manager
        middleware.permission_manager.check_repository_access = AsyncMock(
            return_value=True
        )

        has_access = await middleware.validate_repository_operation(
            mock_request, "test-repo", "edit"
        )

        assert has_access is True
        middleware.permission_manager.check_repository_access.assert_called_once_with(
            username="testuser",
            repo_name="test-repo",
            access_token="test-token",  # noqa: S106
            required_permission="write",
        )

    @pytest.mark.asyncio
    async def test_validate_repository_operation_no_credentials(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test validating repository operation without credentials."""
        mock_request.headers = {}

        has_access = await middleware.validate_repository_operation(
            mock_request, "test-repo", "read"
        )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_validate_repository_operation_mappings(
        self,
        middleware: RepositoryScopedAuthMiddleware,
        mock_request: MagicMock,
    ) -> None:
        """Test operation to permission mappings."""
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Auth-Request-Access-Token": "test-token",
        }

        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        # Mock permission manager to track calls
        calls = []

        async def track_calls(**kwargs: Any) -> bool:  # noqa: ANN401
            calls.append(kwargs)
            return True

        middleware.permission_manager.check_repository_access = AsyncMock(
            side_effect=track_calls
        )

        # Test different operations
        operations = [
            ("read", "read"),
            ("view", "read"),
            ("clone", "read"),
            ("edit", "write"),
            ("push", "write"),
            ("manage", "maintain"),
            ("admin", "admin"),
            ("delete", "admin"),
            ("unknown", "read"),  # Default
        ]

        for operation, expected_perm in operations:
            calls.clear()
            await middleware.validate_repository_operation(
                mock_request, "test-repo", operation
            )
            assert calls[0]["required_permission"] == expected_perm


class TestRepositoryAccessValidator:
    """Test RepositoryAccessValidator class."""

    @pytest.fixture
    def validator(self) -> RepositoryAccessValidator:
        """Create validator instance."""
        return RepositoryAccessValidator()

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.headers = {}
        return request

    def test_validator_initialization(
        self, validator: RepositoryAccessValidator
    ) -> None:
        """Test validator initialization."""
        assert validator.permission_manager is not None
        assert validator.oauth2_proxy is not None

    @pytest.mark.asyncio
    async def test_require_repository_access_success(
        self, validator: RepositoryAccessValidator, mock_request: MagicMock
    ) -> None:
        """Test requiring repository access successfully."""
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Auth-Request-Access-Token": "test-token",
        }

        validator.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        validator.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        # Mock permission manager
        validator.permission_manager.check_repository_access = AsyncMock(
            return_value=True
        )

        result = await validator.require_repository_access(
            mock_request, "test-repo", "write"
        )

        assert result is True
        validator.permission_manager.check_repository_access.assert_called_once_with(
            username="testuser",
            repo_name="test-repo",
            access_token="test-token",  # noqa: S106
            required_permission="write",
        )

    @pytest.mark.asyncio
    async def test_require_repository_access_no_credentials(
        self, validator: RepositoryAccessValidator, mock_request: MagicMock
    ) -> None:
        """Test requiring repository access without credentials."""
        mock_request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await validator.require_repository_access(mock_request, "test-repo")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_repository_access_denied(
        self, validator: RepositoryAccessValidator, mock_request: MagicMock
    ) -> None:
        """Test requiring repository access when denied."""
        mock_request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Auth-Request-Access-Token": "test-token",
        }

        validator.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        validator.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        # Mock permission manager to deny access
        validator.permission_manager.check_repository_access = AsyncMock(
            return_value=False
        )

        with pytest.raises(HTTPException) as exc_info:
            await validator.require_repository_access(
                mock_request, "test-repo", "admin"
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "test-repo" in str(exc_info.value.detail)
        assert "admin" in str(exc_info.value.detail)

    def test_get_username_from_request_oauth2_proxy(
        self, validator: RepositoryAccessValidator, mock_request: MagicMock
    ) -> None:
        """Test getting username from OAuth2-Proxy headers."""
        validator.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        validator.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        mock_request.headers = {"X-Forwarded-User": "testuser"}

        username = validator._get_username_from_request(mock_request)
        assert username == "testuser"

    def test_get_username_from_request_disabled(
        self, validator: RepositoryAccessValidator, mock_request: MagicMock
    ) -> None:
        """Test getting username when OAuth2-Proxy disabled."""
        validator.oauth2_proxy.settings.auth.oauth2_proxy_enabled = False
        mock_request.headers = {"X-Forwarded-User": "testuser"}

        username = validator._get_username_from_request(mock_request)
        assert username is None

    def test_get_access_token_from_request(
        self, validator: RepositoryAccessValidator, mock_request: MagicMock
    ) -> None:
        """Test getting access token from request."""
        mock_request.headers = {"X-Auth-Request-Access-Token": "test-token"}

        token = validator._get_access_token_from_request(mock_request)
        assert token == "test-token"  # noqa: S105

    def test_get_access_token_from_request_none(
        self, validator: RepositoryAccessValidator, mock_request: MagicMock
    ) -> None:
        """Test getting access token when not present."""
        mock_request.headers = {}

        token = validator._get_access_token_from_request(mock_request)
        assert token is None


class TestRepositoryMiddlewareIntegration:
    """Integration tests for repository middleware functionality."""

    @pytest.mark.asyncio
    async def test_full_request_flow_with_access(self) -> None:
        """Test complete request flow with repository access."""
        app = MagicMock()
        middleware = RepositoryScopedAuthMiddleware(app)

        # Create request
        request = MagicMock(spec=Request)
        request.url.path = "/docs/repo/my-project/guide"
        request.headers = {
            "X-Forwarded-User": "alice",
            "X-Auth-Request-Access-Token": "github-token",
        }

        # Mock settings
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        # Mock permission check
        middleware.permission_manager.check_repository_access = AsyncMock(
            return_value=True
        )

        # Mock response
        expected_response = MagicMock(spec=Response)
        call_next = AsyncMock(return_value=expected_response)

        # Execute
        response = await middleware.dispatch(request, call_next)

        # Verify
        assert response == expected_response
        middleware.permission_manager.check_repository_access.assert_called_once_with(
            username="alice",
            repo_name="my-project",
            access_token="github-token",  # noqa: S106
            required_permission="read",
        )

    @pytest.mark.asyncio
    async def test_full_request_flow_access_denied(self) -> None:
        """Test complete request flow with access denied."""
        app = MagicMock()
        middleware = RepositoryScopedAuthMiddleware(app)

        # Create request
        request = MagicMock(spec=Request)
        request.url.path = "/api/repos/private-repo/settings"
        request.headers = {
            "X-Forwarded-User": "bob",
            "X-Auth-Request-Access-Token": "github-token",
        }

        # Mock settings
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_enabled = True
        middleware.oauth2_proxy.settings.auth.oauth2_proxy_user_header = (
            "X-Forwarded-User"
        )

        # Mock permission check to deny
        middleware.permission_manager.check_repository_access = AsyncMock(
            return_value=False
        )

        # Mock call_next
        call_next = AsyncMock()

        # Execute and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "private-repo" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_multiple_repository_patterns(self) -> None:
        """Test that all repository patterns work correctly."""
        app = MagicMock()
        middleware = RepositoryScopedAuthMiddleware(app)

        # Test URLs
        test_urls = [
            ("/docs/repo/test-repo/", "test-repo"),
            ("/api/repos/my-api/", "my-api"),
            ("/site/docs-site/", "docs-site"),
            ("/projects/cool-project/", "cool-project"),
        ]

        for url, expected_repo in test_urls:
            repo_name = middleware._extract_repository_from_url(url)
            assert repo_name == expected_repo
