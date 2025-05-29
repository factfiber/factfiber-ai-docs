# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""GitHub authentication and user management."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

import httpx

from ff_docs.auth.models import GitHubTeam, User, UserSession
from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)


class GitHubAuthenticator:
    """GitHub authentication handler."""

    def __init__(self) -> None:
        """Initialize GitHub authenticator."""
        self.settings = get_settings()
        self.base_url = "https://api.github.com"

    async def authenticate_user(self, github_token: str) -> UserSession | None:
        """Authenticate user with GitHub token and create session."""
        try:
            # Get user information from GitHub
            user = await self._get_github_user(github_token)
            if not user:
                return None

            # Get user's team memberships
            teams = await self._get_user_teams(github_token, user.username)

            # Generate session
            session_id = str(uuid.uuid4())
            expires_at = datetime.now(UTC) + timedelta(
                minutes=self.settings.auth.access_token_expire_minutes
            )

            # Create user session
            session = UserSession(
                user=user,
                teams=teams,
                permissions=self._calculate_permissions(teams),
                session_id=session_id,
                expires_at=expires_at,
            )

        except Exception:
            logger.exception("GitHub authentication failed")
            return None
        else:
            logger.info("Successfully authenticated user: %s", user.username)
            return session

    async def _get_github_user(self, token: str) -> User | None:
        """Get user information from GitHub API."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user", headers=headers
                )
                response.raise_for_status()

                user_data = response.json()

                # Update last login
                now = datetime.now(UTC)

                return User(
                    username=user_data["login"],
                    email=user_data.get("email", ""),
                    full_name=user_data.get("name"),
                    avatar_url=user_data.get("avatar_url"),
                    github_id=user_data.get("id"),
                    is_active=True,
                    created_at=now,
                    last_login=now,
                )

        except httpx.HTTPStatusError:
            logger.exception("GitHub API error getting user")
            return None
        except Exception:
            logger.exception("Error getting GitHub user")
            return None

    async def _get_user_teams(
        self, token: str, username: str
    ) -> list[GitHubTeam]:
        """Get user's team memberships from GitHub."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        teams: list[GitHubTeam] = []
        org_name = self.settings.github.org

        if not org_name:
            logger.warning("No GitHub organization configured")
            return teams

        try:
            async with httpx.AsyncClient() as client:
                # Get user's teams in the organization
                response = await client.get(
                    f"{self.base_url}/orgs/{org_name}/teams", headers=headers
                )
                response.raise_for_status()

                org_teams = response.json()

                # Check membership for each team
                for team in org_teams:
                    team_slug = team["slug"]
                    member_response = await client.get(
                        f"{self.base_url}/orgs/{org_name}/teams/{team_slug}/memberships/{username}",
                        headers=headers,
                    )

                    if member_response.status_code == httpx.codes.OK:
                        membership = member_response.json()
                        if membership.get("state") == "active":
                            teams.append(
                                GitHubTeam(
                                    org=org_name,
                                    team=team_slug,
                                    role=membership.get("role", "member"),
                                )
                            )

                logger.info(
                    "Found %d team memberships for user: %s",
                    len(teams),
                    username,
                )
                return teams

        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.NOT_FOUND:
                logger.info(
                    "User %s not found in organization %s", username, org_name
                )
            else:
                logger.exception("GitHub API error getting teams")
            return teams
        except Exception:
            logger.exception("Error getting user teams")
            return teams

    def _calculate_permissions(self, teams: list[GitHubTeam]) -> list[str]:
        """Calculate user permissions based on team memberships."""
        permissions = set()

        # Base permissions for authenticated users
        permissions.add("docs:read")

        # Team-based permissions
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

        return list(permissions)

    async def validate_repository_access(
        self, token: str, username: str, repo_name: str
    ) -> bool:
        """Validate if user has access to a specific repository."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            async with httpx.AsyncClient() as client:
                # Check repository collaborator status
                response = await client.get(
                    f"{self.base_url}/repos/{self.settings.github.org}/{repo_name}/collaborators/{username}",
                    headers=headers,
                )

                if response.status_code == httpx.codes.NO_CONTENT:
                    logger.debug(
                        "User %s has access to repository %s",
                        username,
                        repo_name,
                    )
                    return True
                logger.debug(
                    "User %s does not have access to repository %s",
                    username,
                    repo_name,
                )
                return False

        except Exception:
            logger.exception("Error checking repository access")
            return False

    async def refresh_user_teams(
        self, token: str, session: UserSession
    ) -> UserSession:
        """Refresh user's team memberships and permissions."""
        try:
            # Get updated team memberships
            updated_teams = await self._get_user_teams(
                token, session.user.username
            )

            # Update session with new teams and permissions
            session.teams = updated_teams
            session.permissions = self._calculate_permissions(updated_teams)

        except Exception:
            logger.exception("Error refreshing user teams")
            return session
        else:
            logger.info("Refreshed teams for user: %s", session.user.username)
            return session
