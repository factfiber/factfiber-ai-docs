# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""OAuth2-Proxy integration for enterprise authentication."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from ff_docs.auth.models import GitHubTeam, User, UserSession
from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)


class OAuth2ProxyHandler:
    """Handler for OAuth2-Proxy authentication headers."""

    def __init__(self) -> None:
        """Initialize OAuth2-Proxy handler."""
        self.settings = get_settings()

    def extract_user_from_headers(self, request: Request) -> UserSession | None:
        """Extract user information from OAuth2-Proxy headers."""
        if not self.settings.auth.oauth2_proxy_enabled:
            logger.debug("OAuth2-Proxy integration is disabled")
            return None

        try:
            # Extract user information from headers
            username = request.headers.get(
                self.settings.auth.oauth2_proxy_user_header
            )
            email = request.headers.get(
                self.settings.auth.oauth2_proxy_email_header
            )
            groups_header = request.headers.get(
                self.settings.auth.oauth2_proxy_groups_header
            )

            if not username:
                logger.warning("No username found in OAuth2-Proxy headers")
                return None

            # Parse GitHub teams from groups header
            teams = self._parse_github_teams(groups_header)

            # Create user object
            user = User(
                username=username,
                email=email or "",
                full_name=None,  # Not typically available from OAuth2-Proxy
                avatar_url=None,
                github_id=None,
                is_active=True,
                created_at=datetime.now(UTC),
                last_login=datetime.now(UTC),
            )

            # Create session
            session = UserSession(
                user=user,
                teams=teams,
                permissions=self._calculate_permissions(teams),
                session_id=f"oauth2-proxy-{username}",
                expires_at=datetime.now(UTC),  # Managed by OAuth2-Proxy
            )

        except Exception:
            logger.exception("Error extracting user from OAuth2-Proxy headers")
            return None
        else:
            logger.info(
                "Extracted user session from OAuth2-Proxy: %s", username
            )
            return session

    def _parse_github_teams(
        self, groups_header: str | None
    ) -> list[GitHubTeam]:
        """Parse GitHub teams from X-Forwarded-Groups header."""
        teams: list[GitHubTeam] = []

        if not groups_header:
            return teams

        try:
            # Format: org1:team1,org1:team2,org2:team1
            groups = groups_header.split(",")

            for group_item in groups:
                group = group_item.strip()
                if ":" in group:
                    org, team = group.split(":", 1)
                    teams.append(
                        GitHubTeam(
                            org=org.strip(),
                            team=team.strip(),
                            role="member",  # Role not available from header
                        )
                    )

        except Exception:
            logger.exception("Error parsing GitHub teams from header")
            return teams
        else:
            logger.debug("Parsed %d teams from groups header", len(teams))
            return teams

    def _calculate_permissions(self, teams: list[GitHubTeam]) -> list[str]:
        """Calculate user permissions based on team memberships."""
        permissions = set()

        # Base permissions for authenticated users
        permissions.add("docs:read")

        # Team-based permissions mapping
        team_permissions = {
            "admin-team": [
                "docs:read",
                "docs:write",
                "docs:admin",
                "repos:manage",
                "users:manage",
            ],
            "platform-team": [
                "docs:read",
                "docs:write",
                "repos:manage",
                "system:monitor",
            ],
            "docs-team": ["docs:read", "docs:write", "repos:view"],
            "backend-team": ["docs:read", "backend:access"],
            "frontend-team": ["docs:read", "frontend:access"],
            "mobile-team": ["docs:read", "mobile:access"],
        }

        for team in teams:
            team_perms = team_permissions.get(team.team, ["docs:read"])
            permissions.update(team_perms)

        logger.debug("Calculated %d permissions for user", len(permissions))
        return list(permissions)

    def validate_oauth2_proxy_headers(self, request: Request) -> bool:
        """Validate that required OAuth2-Proxy headers are present."""
        if not self.settings.auth.oauth2_proxy_enabled:
            return False

        required_headers = [
            self.settings.auth.oauth2_proxy_user_header,
            self.settings.auth.oauth2_proxy_email_header,
        ]

        for header in required_headers:
            if not request.headers.get(header):
                logger.warning(
                    "Missing required OAuth2-Proxy header: %s", header
                )
                return False

        return True

    def extract_access_token(self, request: Request) -> str | None:
        """Extract GitHub access token from OAuth2-Proxy headers."""
        # OAuth2-Proxy can pass through the original access token
        access_token_header = "X-Auth-Request-Access-Token"  # noqa: S105
        return request.headers.get(access_token_header)

    def get_user_info_from_headers(self, request: Request) -> dict[str, Any]:
        """Extract all available user information from headers."""
        return {
            "username": request.headers.get(
                self.settings.auth.oauth2_proxy_user_header
            ),
            "email": request.headers.get(
                self.settings.auth.oauth2_proxy_email_header
            ),
            "groups": request.headers.get(
                self.settings.auth.oauth2_proxy_groups_header
            ),
            "access_token": self.extract_access_token(request),
            "forwarded_for": request.headers.get("X-Forwarded-For"),
            "forwarded_proto": request.headers.get("X-Forwarded-Proto"),
            "forwarded_host": request.headers.get("X-Forwarded-Host"),
        }

    def is_user_in_required_org(self, teams: list[GitHubTeam]) -> bool:
        """Check if user is member of the required GitHub organization."""
        required_org = self.settings.github.org
        if not required_org:
            return True  # No org requirement

        return any(team.org == required_org for team in teams)

    def has_required_team_membership(
        self, teams: list[GitHubTeam], required_teams: list[str]
    ) -> bool:
        """Check if user has membership in any of the required teams."""
        if not required_teams:
            return True  # No team requirement

        user_teams = {team.team for team in teams}
        return any(team in user_teams for team in required_teams)
