# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Test authentication models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

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


class TestUser:
    """Test User model."""

    def test_user_creation_minimal(self) -> None:
        """Test user creation with minimal required fields."""
        user = User(username="testuser", email="test@example.com")
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name is None
        assert user.avatar_url is None
        assert user.github_id is None
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)
        assert user.last_login is None

    def test_user_creation_complete(self) -> None:
        """Test user creation with all fields."""
        created_time = datetime.now(UTC)
        login_time = datetime.now(UTC)

        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            avatar_url="https://github.com/avatar.png",
            github_id=12345,
            is_active=False,
            created_at=created_time,
            last_login=login_time,
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.avatar_url == "https://github.com/avatar.png"
        assert user.github_id == 12345
        assert user.is_active is False
        assert user.created_at == created_time
        assert user.last_login == login_time

    def test_user_validation_required_fields(self) -> None:
        """Test user validation for required fields."""
        with pytest.raises(ValidationError):
            User()  # Missing required fields

        with pytest.raises(ValidationError):
            User(username="testuser")  # Missing email

        with pytest.raises(ValidationError):
            User(email="test@example.com")  # Missing username


class TestGitHubTeam:
    """Test GitHubTeam model."""

    def test_github_team_creation(self) -> None:
        """Test GitHub team creation."""
        team = GitHubTeam(org="factfiber", team="developers")
        assert team.org == "factfiber"
        assert team.team == "developers"
        assert team.role is None

    def test_github_team_with_role(self) -> None:
        """Test GitHub team with role."""
        team = GitHubTeam(org="factfiber", team="developers", role="maintainer")
        assert team.org == "factfiber"
        assert team.team == "developers"
        assert team.role == "maintainer"

    def test_github_team_validation(self) -> None:
        """Test GitHub team validation."""
        with pytest.raises(ValidationError):
            GitHubTeam()  # Missing required fields

        with pytest.raises(ValidationError):
            GitHubTeam(org="factfiber")  # Missing team


class TestUserSession:
    """Test UserSession model."""

    def test_user_session_creation(self) -> None:
        """Test user session creation."""
        user = User(username="testuser", email="test@example.com")
        expires_at = datetime.now(UTC)

        session = UserSession(
            user=user, session_id="session-123", expires_at=expires_at
        )

        assert session.user == user
        assert session.teams == []
        assert session.permissions == []
        assert session.session_id == "session-123"
        assert session.expires_at == expires_at

    def test_user_session_with_teams_and_permissions(self) -> None:
        """Test user session with teams and permissions."""
        user = User(username="testuser", email="test@example.com")
        team = GitHubTeam(org="factfiber", team="developers")
        expires_at = datetime.now(UTC)

        session = UserSession(
            user=user,
            teams=[team],
            permissions=["docs:read", "docs:write"],
            session_id="session-123",
            expires_at=expires_at,
        )

        assert len(session.teams) == 1
        assert session.teams[0] == team
        assert session.permissions == ["docs:read", "docs:write"]

    def test_user_session_user_id_with_github_id(self) -> None:
        """Test user_id property when github_id is present."""
        user = User(
            username="testuser", email="test@example.com", github_id=12345
        )
        session = UserSession(
            user=user, session_id="session-123", expires_at=datetime.now(UTC)
        )

        # Should return stringified github_id when present (line 60)
        assert session.user_id == "12345"

    def test_user_session_user_id_without_github_id(self) -> None:
        """Test user_id property when github_id is None."""
        user = User(
            username="testuser", email="test@example.com", github_id=None
        )
        session = UserSession(
            user=user, session_id="session-123", expires_at=datetime.now(UTC)
        )

        # Should return username when github_id is None (line 60)
        assert session.user_id == "testuser"

    def test_user_session_email_property(self) -> None:
        """Test email property access."""
        user = User(username="testuser", email="user@domain.com")
        session = UserSession(
            user=user, session_id="session-123", expires_at=datetime.now(UTC)
        )

        # Should return user email (line 65)
        assert session.email == "user@domain.com"


class TestTokenData:
    """Test TokenData model."""

    def test_token_data_creation(self) -> None:
        """Test token data creation."""
        token = TokenData(
            username="testuser",
            sub="user-123",
            exp=1234567890,
            iat=1234567800,
            session_id="session-123",
        )

        assert token.username == "testuser"
        assert token.sub == "user-123"
        assert token.exp == 1234567890
        assert token.iat == 1234567800
        assert token.session_id == "session-123"

    def test_token_data_validation(self) -> None:
        """Test token data validation."""
        with pytest.raises(ValidationError):
            TokenData()  # Missing all required fields


class TestLoginRequest:
    """Test LoginRequest model."""

    def test_login_request_creation(self) -> None:
        """Test login request creation."""
        request = LoginRequest(github_token="github_token_123")  # noqa: S106
        assert request.github_token == "github_token_123"  # noqa: S105

    def test_login_request_validation(self) -> None:
        """Test login request validation."""
        with pytest.raises(ValidationError):
            LoginRequest()  # Missing required github_token


class TestLoginResponse:
    """Test LoginResponse model."""

    def test_login_response_creation(self) -> None:
        """Test login response creation."""
        user = User(username="testuser", email="test@example.com")

        response = LoginResponse(
            access_token="jwt_token_123",  # noqa: S106
            expires_in=3600,
            user=user,
        )

        assert response.access_token == "jwt_token_123"  # noqa: S105
        assert response.token_type == "bearer"  # Default value  # noqa: S105
        assert response.expires_in == 3600
        assert response.user == user

    def test_login_response_custom_token_type(self) -> None:
        """Test login response with custom token type."""
        user = User(username="testuser", email="test@example.com")

        response = LoginResponse(
            access_token="jwt_token_123",  # noqa: S106
            token_type="custom",  # noqa: S106
            expires_in=3600,
            user=user,
        )

        assert response.token_type == "custom"  # noqa: S105


class TestPermissionCheck:
    """Test PermissionCheck model."""

    def test_permission_check_creation(self) -> None:
        """Test permission check creation."""
        check = PermissionCheck(resource="docs", action="read")
        assert check.resource == "docs"
        assert check.action == "read"
        assert check.context == {}

    def test_permission_check_with_context(self) -> None:
        """Test permission check with context."""
        context = {"repository": "test-repo", "branch": "main"}
        check = PermissionCheck(resource="docs", action="read", context=context)
        assert check.context == context

    def test_permission_check_validation(self) -> None:
        """Test permission check validation."""
        with pytest.raises(ValidationError):
            PermissionCheck()  # Missing required fields


class TestPermissionResult:
    """Test PermissionResult model."""

    def test_permission_result_creation(self) -> None:
        """Test permission result creation."""
        result = PermissionResult(
            allowed=True, reason="User has required permissions"
        )

        assert result.allowed is True
        assert result.reason == "User has required permissions"
        assert result.required_permissions == []

    def test_permission_result_with_required_permissions(self) -> None:
        """Test permission result with required permissions."""
        result = PermissionResult(
            allowed=False,
            reason="Missing permissions",
            required_permissions=["docs:read", "docs:write"],
        )

        assert result.allowed is False
        assert result.required_permissions == ["docs:read", "docs:write"]

    def test_permission_result_validation(self) -> None:
        """Test permission result validation."""
        with pytest.raises(ValidationError):
            PermissionResult()  # Missing required fields
