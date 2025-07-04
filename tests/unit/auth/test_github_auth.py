# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001
# mypy: disable-error-code="method-assign,assignment"

"""Unit tests for GitHub authentication module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ff_docs.auth.github_auth import GitHubAuthenticator
from ff_docs.auth.models import GitHubTeam, User, UserSession


class TestGitHubAuthenticator:
    """Test GitHubAuthenticator class."""

    @pytest.fixture
    def authenticator(self) -> GitHubAuthenticator:
        """Create a GitHubAuthenticator instance."""
        return GitHubAuthenticator()

    @pytest.fixture
    def mock_github_user_response(self) -> dict:
        """Create mock GitHub user API response."""
        return {
            "login": "testuser",
            "id": 12345,
            "email": "test@example.com",
            "name": "Test User",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        }

    @pytest.fixture
    def mock_github_teams_response(self) -> list[dict]:
        """Create mock GitHub teams API response."""
        return [
            {"id": 1, "slug": "platform-team", "name": "Platform Team"},
            {"id": 2, "slug": "docs-team", "name": "Docs Team"},
            {"id": 3, "slug": "backend-team", "name": "Backend Team"},
        ]

    def test_authenticator_initialization(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test GitHubAuthenticator initialization."""
        assert authenticator.settings is not None
        assert authenticator.base_url == "https://api.github.com"

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self,
        authenticator: GitHubAuthenticator,
        mock_github_user_response: dict,  # noqa: ARG002
        mock_github_teams_response: list[dict],  # noqa: ARG002
    ) -> None:
        """Test successful user authentication."""
        # Mock _get_github_user
        mock_user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            github_id=12345,
            is_active=True,
            created_at=datetime.now(UTC),
            last_login=datetime.now(UTC),
        )
        authenticator._get_github_user = AsyncMock(return_value=mock_user)

        # Mock _get_user_teams
        mock_teams = [
            GitHubTeam(org="test-org", team="platform-team", role="member"),
            GitHubTeam(org="test-org", team="docs-team", role="maintainer"),
        ]
        authenticator._get_user_teams = AsyncMock(return_value=mock_teams)

        # Authenticate
        session = await authenticator.authenticate_user("test-token")

        assert session is not None
        assert session.user.username == "testuser"
        assert len(session.teams) == 2
        assert "docs:read" in session.permissions
        assert "docs:write" in session.permissions
        assert "repos:manage" in session.permissions

    @pytest.mark.asyncio
    async def test_authenticate_user_no_user(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test authentication when GitHub user fetch fails."""
        authenticator._get_github_user = AsyncMock(return_value=None)

        session = await authenticator.authenticate_user("invalid-token")

        assert session is None

    @pytest.mark.asyncio
    async def test_authenticate_user_exception(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test authentication with exception."""
        authenticator._get_github_user = AsyncMock(
            side_effect=Exception("API error")
        )

        session = await authenticator.authenticate_user("test-token")

        assert session is None

    @pytest.mark.asyncio
    async def test_get_github_user_success(
        self,
        authenticator: GitHubAuthenticator,
        mock_github_user_response: dict,
    ) -> None:
        """Test getting GitHub user information."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_github_user_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            user = await authenticator._get_github_user("test-token")

        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.github_id == 12345

    @pytest.mark.asyncio
    async def test_get_github_user_http_error(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test getting GitHub user with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized",
                request=MagicMock(),
                response=MagicMock(status_code=401),
            )
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            user = await authenticator._get_github_user("invalid-token")

        assert user is None

    @pytest.mark.asyncio
    async def test_get_github_user_general_error(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test getting GitHub user with general error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            user = await authenticator._get_github_user("test-token")

        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_teams_success(
        self,
        authenticator: GitHubAuthenticator,
        mock_github_teams_response: list[dict],
    ) -> None:
        """Test getting user teams successfully."""
        authenticator.settings.github.org = "test-org"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # Mock teams list response
            teams_response = MagicMock()
            teams_response.json.return_value = mock_github_teams_response
            teams_response.raise_for_status = MagicMock()

            # Mock membership responses
            membership_responses = []
            for i, _ in enumerate(mock_github_teams_response):
                membership_response = MagicMock()
                membership_response.status_code = httpx.codes.OK
                membership_response.json.return_value = {
                    "state": "active",
                    "role": "member" if i < 2 else "maintainer",
                }
                membership_responses.append(membership_response)

            # Fourth call is for non-member team
            non_member_response = MagicMock()
            non_member_response.status_code = httpx.codes.NOT_FOUND
            membership_responses.append(non_member_response)

            mock_client.get.side_effect = [
                teams_response,
                *membership_responses,
            ]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            teams = await authenticator._get_user_teams(
                "test-token", "testuser"
            )

        assert len(teams) == 3
        assert teams[0].org == "test-org"
        assert teams[0].team == "platform-team"
        assert teams[0].role == "member"
        assert teams[2].role == "maintainer"

    @pytest.mark.asyncio
    async def test_get_user_teams_no_org(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test getting user teams with no organization configured."""
        authenticator.settings.github.org = None

        teams = await authenticator._get_user_teams("test-token", "testuser")

        assert teams == []

    @pytest.mark.asyncio
    async def test_get_user_teams_org_not_found(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test getting user teams when org not found."""
        authenticator.settings.github.org = "test-org"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            teams = await authenticator._get_user_teams(
                "test-token", "testuser"
            )

        assert teams == []

    @pytest.mark.asyncio
    async def test_get_user_teams_http_error_non_404(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test getting user teams with non-404 HTTP error (line 155)."""
        authenticator.settings.github.org = "test-org"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            # Test a 500 server error (could also be 403, 429, etc.)
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Internal Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("ff_docs.auth.github_auth.logger") as mock_logger:
                teams = await authenticator._get_user_teams(
                    "test-token", "testuser"
                )

                # Should log the exception (line 155)
                mock_logger.exception.assert_called_with(
                    "GitHub API error getting teams"
                )

        assert teams == []

    @pytest.mark.asyncio
    async def test_get_user_teams_error(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test getting user teams with error."""
        authenticator.settings.github.org = "test-org"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("API error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            teams = await authenticator._get_user_teams(
                "test-token", "testuser"
            )

        assert teams == []

    def test_calculate_permissions_basic(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test calculating basic permissions."""
        teams: list[GitHubTeam] = []
        permissions = authenticator._calculate_permissions(teams)

        assert "docs:read" in permissions  # Base permission

    def test_calculate_permissions_admin_team(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test calculating permissions for admin team."""
        teams = [GitHubTeam(org="test-org", team="admin-team", role="member")]
        permissions = authenticator._calculate_permissions(teams)

        assert "docs:read" in permissions
        assert "docs:write" in permissions
        assert "docs:admin" in permissions
        assert "repos:manage" in permissions
        assert "users:manage" in permissions

    def test_calculate_permissions_multiple_teams(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test calculating permissions for multiple teams."""
        teams = [
            GitHubTeam(org="test-org", team="platform-team", role="member"),
            GitHubTeam(org="test-org", team="backend-team", role="member"),
        ]
        permissions = authenticator._calculate_permissions(teams)

        assert "docs:read" in permissions
        assert "docs:write" in permissions
        assert "repos:manage" in permissions
        assert "system:monitor" in permissions
        assert "backend:access" in permissions

    def test_calculate_permissions_unknown_team(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test calculating permissions for unknown team."""
        teams = [GitHubTeam(org="test-org", team="unknown-team", role="member")]
        permissions = authenticator._calculate_permissions(teams)

        # Should still have base permission
        assert "docs:read" in permissions

    @pytest.mark.asyncio
    async def test_validate_repository_access_success(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test validating repository access successfully."""
        authenticator.settings.github.org = "test-org"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = httpx.codes.NO_CONTENT
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            has_access = await authenticator.validate_repository_access(
                "test-token", "testuser", "test-repo"
            )

        assert has_access is True

    @pytest.mark.asyncio
    async def test_validate_repository_access_denied(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test validating repository access when denied."""
        authenticator.settings.github.org = "test-org"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = httpx.codes.NOT_FOUND
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            has_access = await authenticator.validate_repository_access(
                "test-token", "testuser", "test-repo"
            )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_validate_repository_access_error(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test validating repository access with error."""
        authenticator.settings.github.org = "test-org"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("API error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            has_access = await authenticator.validate_repository_access(
                "test-token", "testuser", "test-repo"
            )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_refresh_user_teams_success(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test refreshing user teams successfully."""
        # Create initial session
        user = User(
            username="testuser",
            email="test@example.com",
            github_id=12345,
        )
        initial_teams = [
            GitHubTeam(org="test-org", team="docs-team", role="member")
        ]
        session = UserSession(
            user=user,
            teams=initial_teams,
            permissions=["docs:read", "docs:write"],
            session_id="test-session",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        # Mock updated teams
        updated_teams = [
            GitHubTeam(org="test-org", team="platform-team", role="member"),
            GitHubTeam(org="test-org", team="admin-team", role="member"),
        ]
        authenticator._get_user_teams = AsyncMock(return_value=updated_teams)

        # Refresh teams
        updated_session = await authenticator.refresh_user_teams(
            "test-token", session
        )

        assert len(updated_session.teams) == 2
        assert updated_session.teams[0].team == "platform-team"
        assert "docs:admin" in updated_session.permissions
        assert "repos:manage" in updated_session.permissions

    @pytest.mark.asyncio
    async def test_refresh_user_teams_error(
        self, authenticator: GitHubAuthenticator
    ) -> None:
        """Test refreshing user teams with error."""
        user = User(username="testuser", email="test@example.com")
        session = UserSession(
            user=user,
            teams=[],
            permissions=["docs:read"],
            session_id="test-session",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        authenticator._get_user_teams = AsyncMock(
            side_effect=Exception("API error")
        )

        # Should return original session on error
        updated_session = await authenticator.refresh_user_teams(
            "test-token", session
        )

        assert updated_session == session


class TestGitHubAuthIntegration:
    """Integration tests for GitHub authentication."""

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self) -> None:
        """Test complete authentication flow."""
        authenticator = GitHubAuthenticator()
        authenticator.settings.github.org = "test-org"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # User API response
            user_response = MagicMock()
            user_response.json.return_value = {
                "login": "integrationuser",
                "id": 99999,
                "email": "integration@example.com",
                "name": "Integration User",
                "avatar_url": "https://avatars.example.com/u/99999",
            }
            user_response.raise_for_status = MagicMock()

            # Teams API response
            teams_response = MagicMock()
            teams_response.json.return_value = [
                {"id": 1, "slug": "platform-team", "name": "Platform Team"}
            ]
            teams_response.raise_for_status = MagicMock()

            # Membership API response
            membership_response = MagicMock()
            membership_response.status_code = httpx.codes.OK
            membership_response.json.return_value = {
                "state": "active",
                "role": "maintainer",
            }

            mock_client.get.side_effect = [
                user_response,
                teams_response,
                membership_response,
            ]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            session = await authenticator.authenticate_user("integration-token")

        assert session is not None
        assert session.user.username == "integrationuser"
        assert len(session.teams) == 1
        assert session.teams[0].team == "platform-team"
        assert "repos:manage" in session.permissions
