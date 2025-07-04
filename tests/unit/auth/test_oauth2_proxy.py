# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001
# mypy: disable-error-code="assignment"

"""Unit tests for OAuth2-Proxy integration module."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request

from ff_docs.auth.models import GitHubTeam
from ff_docs.auth.oauth2_proxy import OAuth2ProxyHandler


class TestOAuth2ProxyHandler:
    """Test OAuth2ProxyHandler class."""

    @pytest.fixture
    def handler(self) -> OAuth2ProxyHandler:
        """Create an OAuth2ProxyHandler instance."""
        return OAuth2ProxyHandler()

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock request with OAuth2-Proxy headers."""
        request = MagicMock(spec=Request)
        request.headers = {
            "X-Forwarded-User": "testuser",
            "X-Forwarded-Email": "test@example.com",
            "X-Forwarded-Groups": "test-org:platform-team,test-org:docs-team",
            "X-Forwarded-Access-Token": "github-token-123",
            "X-Forwarded-For": "192.168.1.1",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "docs.example.com",
        }
        return request

    def test_handler_initialization(self, handler: OAuth2ProxyHandler) -> None:
        """Test OAuth2ProxyHandler initialization."""
        assert handler.settings is not None

    def test_extract_user_from_headers_success(
        self, handler: OAuth2ProxyHandler, mock_request: MagicMock
    ) -> None:
        """Test successful user extraction from headers."""
        handler.settings.auth.oauth2_proxy_enabled = True
        handler.settings.auth.oauth2_proxy_user_header = "X-Forwarded-User"
        handler.settings.auth.oauth2_proxy_email_header = "X-Forwarded-Email"
        handler.settings.auth.oauth2_proxy_groups_header = "X-Forwarded-Groups"

        session = handler.extract_user_from_headers(mock_request)

        assert session is not None
        assert session.user.username == "testuser"
        assert session.user.email == "test@example.com"
        assert len(session.teams) == 2
        assert session.teams[0].org == "test-org"
        assert session.teams[0].team == "platform-team"
        assert "docs:read" in session.permissions
        assert "docs:write" in session.permissions
        assert "repos:manage" in session.permissions

    def test_extract_user_from_headers_disabled(
        self, handler: OAuth2ProxyHandler, mock_request: MagicMock
    ) -> None:
        """Test user extraction when OAuth2-Proxy is disabled."""
        handler.settings.auth.oauth2_proxy_enabled = False

        session = handler.extract_user_from_headers(mock_request)

        assert session is None

    def test_extract_user_from_headers_no_username(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test user extraction with missing username."""
        handler.settings.auth.oauth2_proxy_enabled = True
        handler.settings.auth.oauth2_proxy_user_header = "X-Forwarded-User"

        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-Email": "test@example.com"}

        session = handler.extract_user_from_headers(request)

        assert session is None

    def test_extract_user_from_headers_no_email(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test user extraction with missing email."""
        handler.settings.auth.oauth2_proxy_enabled = True
        handler.settings.auth.oauth2_proxy_user_header = "X-Forwarded-User"
        handler.settings.auth.oauth2_proxy_email_header = "X-Forwarded-Email"

        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-User": "testuser"}

        session = handler.extract_user_from_headers(request)

        assert session is not None
        assert session.user.email == ""  # Default empty string

    def test_extract_user_from_headers_exception(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test user extraction with exception."""
        handler.settings.auth.oauth2_proxy_enabled = True

        request = MagicMock(spec=Request)
        # Mock headers.get to raise exception
        request.headers.get.side_effect = Exception("Header error")

        session = handler.extract_user_from_headers(request)

        assert session is None

    def test_parse_github_teams_success(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test parsing GitHub teams from header."""
        teams_header = "org1:team1,org1:team2,org2:team3"

        teams = handler._parse_github_teams(teams_header)

        assert len(teams) == 3
        assert teams[0].org == "org1"
        assert teams[0].team == "team1"
        assert teams[1].team == "team2"
        assert teams[2].org == "org2"

    def test_parse_github_teams_with_spaces(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test parsing teams with extra spaces."""
        teams_header = " org1:team1 , org2:team2 "

        teams = handler._parse_github_teams(teams_header)

        assert len(teams) == 2
        assert teams[0].org == "org1"
        assert teams[0].team == "team1"

    def test_parse_github_teams_empty(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test parsing empty teams header."""
        teams = handler._parse_github_teams(None)
        assert teams == []

        teams = handler._parse_github_teams("")
        assert teams == []

    def test_parse_github_teams_invalid_format(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test parsing teams with invalid format."""
        teams_header = "invalid_team,org:team,another_invalid"

        teams = handler._parse_github_teams(teams_header)

        # Should only parse the valid one
        assert len(teams) == 1
        assert teams[0].org == "org"
        assert teams[0].team == "team"

    def test_parse_github_teams_exception(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test parsing teams with exception."""
        # Mock the split method on the teams_header string
        teams_header = MagicMock()
        teams_header.split.side_effect = Exception("Split error")

        teams = handler._parse_github_teams(teams_header)

        assert teams == []

    def test_calculate_permissions_basic(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test calculating basic permissions."""
        teams: list[GitHubTeam] = []
        permissions = handler._calculate_permissions(teams)

        assert "docs:read" in permissions  # Base permission

    def test_calculate_permissions_admin_team(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test calculating permissions for admin team."""
        teams = [GitHubTeam(org="test-org", team="admin-team", role="member")]
        permissions = handler._calculate_permissions(teams)

        assert "docs:admin" in permissions
        assert "users:manage" in permissions

    def test_calculate_permissions_multiple_teams(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test calculating permissions for multiple teams."""
        teams = [
            GitHubTeam(org="test-org", team="platform-team", role="member"),
            GitHubTeam(org="test-org", team="backend-team", role="member"),
        ]
        permissions = handler._calculate_permissions(teams)

        assert "system:monitor" in permissions
        assert "backend:access" in permissions

    def test_validate_oauth2_proxy_headers_valid(
        self, handler: OAuth2ProxyHandler, mock_request: MagicMock
    ) -> None:
        """Test validating OAuth2-Proxy headers when valid."""
        handler.settings.auth.oauth2_proxy_enabled = True
        handler.settings.auth.oauth2_proxy_user_header = "X-Forwarded-User"
        handler.settings.auth.oauth2_proxy_email_header = "X-Forwarded-Email"

        is_valid = handler.validate_oauth2_proxy_headers(mock_request)

        assert is_valid is True

    def test_validate_oauth2_proxy_headers_disabled(
        self, handler: OAuth2ProxyHandler, mock_request: MagicMock
    ) -> None:
        """Test validating headers when OAuth2-Proxy is disabled."""
        handler.settings.auth.oauth2_proxy_enabled = False

        is_valid = handler.validate_oauth2_proxy_headers(mock_request)

        assert is_valid is False

    def test_validate_oauth2_proxy_headers_missing(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test validating headers with missing required headers."""
        handler.settings.auth.oauth2_proxy_enabled = True
        handler.settings.auth.oauth2_proxy_user_header = "X-Forwarded-User"
        handler.settings.auth.oauth2_proxy_email_header = "X-Forwarded-Email"

        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-User": "testuser"}  # Missing email

        is_valid = handler.validate_oauth2_proxy_headers(request)

        assert is_valid is False

    def test_extract_access_token_success(
        self, handler: OAuth2ProxyHandler, mock_request: MagicMock
    ) -> None:
        """Test extracting access token from headers."""
        handler.settings.auth.oauth2_proxy_access_token_header = (
            "X-Forwarded-Access-Token"  # noqa: S105
        )

        token = handler.extract_access_token(mock_request)

        assert token == "github-token-123"  # noqa: S105

    def test_extract_access_token_missing(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test extracting access token when missing."""
        handler.settings.auth.oauth2_proxy_access_token_header = (
            "X-Forwarded-Access-Token"  # noqa: S105
        )

        request = MagicMock(spec=Request)
        request.headers = {}

        token = handler.extract_access_token(request)

        assert token is None

    def test_extract_access_token_empty(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test extracting access token when empty."""
        handler.settings.auth.oauth2_proxy_access_token_header = (
            "X-Forwarded-Access-Token"  # noqa: S105
        )

        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-Access-Token": "  "}  # Whitespace only

        token = handler.extract_access_token(request)

        assert token is None

    def test_get_user_info_from_headers(
        self, handler: OAuth2ProxyHandler, mock_request: MagicMock
    ) -> None:
        """Test extracting all user info from headers."""
        handler.settings.auth.oauth2_proxy_user_header = "X-Forwarded-User"
        handler.settings.auth.oauth2_proxy_email_header = "X-Forwarded-Email"
        handler.settings.auth.oauth2_proxy_groups_header = "X-Forwarded-Groups"
        handler.settings.auth.oauth2_proxy_access_token_header = (
            "X-Forwarded-Access-Token"  # noqa: S105
        )

        info = handler.get_user_info_from_headers(mock_request)

        assert info["username"] == "testuser"
        assert info["email"] == "test@example.com"
        assert "platform-team" in info["groups"]
        assert info["access_token"] == "github-token-123"  # noqa: S105
        assert info["forwarded_for"] == "192.168.1.1"
        assert info["forwarded_proto"] == "https"
        assert info["forwarded_host"] == "docs.example.com"

    def test_is_user_in_required_org_yes(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test checking user org membership when in org."""
        handler.settings.github.org = "test-org"

        teams = [
            GitHubTeam(org="test-org", team="team1"),
            GitHubTeam(org="other-org", team="team2"),
        ]

        is_member = handler.is_user_in_required_org(teams)

        assert is_member is True

    def test_is_user_in_required_org_no(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test checking user org membership when not in org."""
        handler.settings.github.org = "required-org"

        teams = [
            GitHubTeam(org="test-org", team="team1"),
            GitHubTeam(org="other-org", team="team2"),
        ]

        is_member = handler.is_user_in_required_org(teams)

        assert is_member is False

    def test_is_user_in_required_org_no_requirement(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test checking org membership with no requirement."""
        handler.settings.github.org = None

        teams: list[GitHubTeam] = []
        is_member = handler.is_user_in_required_org(teams)

        assert is_member is True

    def test_has_required_team_membership_yes(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test checking team membership when has required team."""
        teams = [
            GitHubTeam(org="test-org", team="platform-team"),
            GitHubTeam(org="test-org", team="docs-team"),
        ]
        required_teams = ["platform-team", "admin-team"]

        has_membership = handler.has_required_team_membership(
            teams, required_teams
        )

        assert has_membership is True

    def test_has_required_team_membership_no(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test checking team membership when lacks required teams."""
        teams = [
            GitHubTeam(org="test-org", team="frontend-team"),
            GitHubTeam(org="test-org", team="mobile-team"),
        ]
        required_teams = ["platform-team", "admin-team"]

        has_membership = handler.has_required_team_membership(
            teams, required_teams
        )

        assert has_membership is False

    def test_has_required_team_membership_no_requirement(
        self, handler: OAuth2ProxyHandler
    ) -> None:
        """Test checking team membership with no requirement."""
        teams: list[GitHubTeam] = []
        required_teams: list[str] = []

        has_membership = handler.has_required_team_membership(
            teams, required_teams
        )

        assert has_membership is True


class TestOAuth2ProxyIntegration:
    """Integration tests for OAuth2-Proxy functionality."""

    def test_full_oauth2_proxy_flow(self) -> None:
        """Test complete OAuth2-Proxy authentication flow."""
        handler = OAuth2ProxyHandler()
        handler.settings.auth.oauth2_proxy_enabled = True
        handler.settings.auth.oauth2_proxy_user_header = "X-Forwarded-User"
        handler.settings.auth.oauth2_proxy_email_header = "X-Forwarded-Email"
        handler.settings.auth.oauth2_proxy_groups_header = "X-Forwarded-Groups"
        handler.settings.github.org = "test-org"

        # Create request with full headers
        request = MagicMock(spec=Request)
        request.headers = {
            "X-Forwarded-User": "integrationuser",
            "X-Forwarded-Email": "integration@example.com",
            "X-Forwarded-Groups": "test-org:admin-team,test-org:platform-team",
        }

        # Validate headers
        assert handler.validate_oauth2_proxy_headers(request) is True

        # Extract user session
        session = handler.extract_user_from_headers(request)
        assert session is not None
        assert session.user.username == "integrationuser"

        # Check org membership
        assert handler.is_user_in_required_org(session.teams) is True

        # Check team membership
        required_teams = ["admin-team", "backend-team"]
        assert (
            handler.has_required_team_membership(session.teams, required_teams)
            is True
        )

        # Check permissions
        assert "docs:admin" in session.permissions
        assert "users:manage" in session.permissions
