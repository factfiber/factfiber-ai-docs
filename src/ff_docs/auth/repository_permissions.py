# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Repository-specific permission management using GitHub API."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)

# GitHub repository role to permission mapping
GITHUB_ROLE_MAPPING = {
    "read": ["repo:read"],
    "triage": ["repo:read", "repo:triage"],
    "write": ["repo:read", "repo:write"],
    "maintain": ["repo:read", "repo:write", "repo:maintain"],
    "admin": ["repo:read", "repo:write", "repo:maintain", "repo:admin"],
}

# HTTP status codes
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_NO_CONTENT = 204


class RepositoryPermissionManager:
    """Manages repository-specific permissions using GitHub API."""

    def __init__(self) -> None:
        """Initialize repository permission manager."""
        self.settings = get_settings()
        self.base_url = "https://api.github.com"
        self._permission_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl_minutes = 10  # Cache permissions for 10 minutes

    def _get_cache_key(self, username: str, repo_name: str) -> str:
        """Generate cache key for user-repository permission."""
        return f"{username}:{repo_name}"

    def _is_cache_valid(self, cache_entry: dict[str, Any]) -> bool:
        """Check if cache entry is still valid."""
        cached_at = cache_entry.get("cached_at")
        if not cached_at:
            return False

        expiry_time = cached_at + timedelta(minutes=self._cache_ttl_minutes)
        return datetime.now(UTC) < expiry_time

    def _cache_permission(
        self, username: str, repo_name: str, permission_data: dict[str, Any]
    ) -> None:
        """Cache permission data for user-repository pair."""
        cache_key = self._get_cache_key(username, repo_name)
        self._permission_cache[cache_key] = {
            **permission_data,
            "cached_at": datetime.now(UTC),
        }

    def _get_cached_permission(
        self, username: str, repo_name: str
    ) -> dict[str, Any] | None:
        """Get cached permission data if valid."""
        cache_key = self._get_cache_key(username, repo_name)
        cache_entry = self._permission_cache.get(cache_key)

        if cache_entry and self._is_cache_valid(cache_entry):
            logger.debug(
                "Using cached permission for %s:%s", username, repo_name
            )
            return cache_entry

        # Remove expired cache entry
        if cache_entry:
            del self._permission_cache[cache_key]

        return None

    async def check_repository_access(
        self,
        username: str,
        repo_name: str,
        access_token: str,
        required_permission: str = "read",
    ) -> bool:
        """Check if user has specific permission for repository."""
        try:
            # Check cache first
            cached_data = self._get_cached_permission(username, repo_name)
            if cached_data:
                user_permissions = cached_data.get("permissions", [])
                has_permission = (
                    f"repo:{required_permission}" in user_permissions
                )
                logger.debug(
                    "Cached permission check for %s:%s:%s = %s",
                    username,
                    repo_name,
                    required_permission,
                    has_permission,
                )
                return has_permission

            # Get fresh permission data from GitHub
            permission_data = await self._get_repository_permission(
                username, repo_name, access_token
            )

            if permission_data:
                # Cache the result
                self._cache_permission(username, repo_name, permission_data)

                # Check if user has required permission
                user_permissions = permission_data.get("permissions", [])
                has_permission = (
                    f"repo:{required_permission}" in user_permissions
                )

                logger.info(
                    "Repository access check: %s -> %s (%s) = %s",
                    username,
                    repo_name,
                    required_permission,
                    has_permission,
                )
                return has_permission

        except Exception:
            logger.exception(
                "Error checking repository access for %s:%s",
                username,
                repo_name,
            )
            return False
        else:
            return False

    async def _get_repository_permission(
        self, username: str, repo_name: str, access_token: str
    ) -> dict[str, Any] | None:
        """Get user's permission level for a specific repository."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        org = self.settings.github.org
        if not org:
            logger.error("GitHub organization not configured")
            return None

        try:
            async with httpx.AsyncClient() as client:
                # Check user's permission level for the repository
                url = (
                    f"{self.base_url}/repos/{org}/{repo_name}/collaborators/"
                    f"{username}/permission"
                )
                response = await client.get(url, headers=headers)

                if response.status_code == HTTP_OK:
                    permission_info = response.json()
                    github_permission = permission_info.get(
                        "permission", "none"
                    )

                    # Map GitHub permission to our permission system
                    permissions = GITHUB_ROLE_MAPPING.get(github_permission, [])

                    return {
                        "username": username,
                        "repository": repo_name,
                        "github_permission": github_permission,
                        "permissions": permissions,
                        "role_name": permission_info.get("role_name"),
                        "has_access": github_permission != "none",
                    }

                if response.status_code == HTTP_NOT_FOUND:
                    # User doesn't have access to the repository
                    logger.debug(
                        "User %s does not have access to repository %s",
                        username,
                        repo_name,
                    )
                    return {
                        "username": username,
                        "repository": repo_name,
                        "github_permission": "none",
                        "permissions": [],
                        "role_name": None,
                        "has_access": False,
                    }

                logger.warning(
                    "Unexpected response from GitHub API: %s",
                    response.status_code,
                )
                return None

        except httpx.HTTPStatusError:
            logger.exception("GitHub API error getting repository permission")
            return None
        except Exception:
            logger.exception("Error getting repository permission")
            return None

    async def get_user_repository_permissions(
        self, username: str, access_token: str, org: str | None = None
    ) -> dict[str, list[str]]:
        """Get user's permissions for all repositories in organization."""
        if not org:
            org = self.settings.github.org

        if not org:
            logger.error("GitHub organization not configured")
            return {}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        repository_permissions = {}

        try:
            async with httpx.AsyncClient() as client:
                # Get all repositories in the organization
                url = f"{self.base_url}/orgs/{org}/repos"
                params = {"type": "all", "per_page": 100}

                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()

                repositories = response.json()

                # Check permissions for each repository
                for repo in repositories:
                    repo_name = repo["name"]

                    # Check user's permission for this repository
                    permission_data = await self._get_repository_permission(
                        username, repo_name, access_token
                    )

                    if permission_data and permission_data.get("has_access"):
                        repository_permissions[repo_name] = permission_data.get(
                            "permissions", []
                        )

                        # Cache the permission data
                        self._cache_permission(
                            username, repo_name, permission_data
                        )

                logger.info(
                    "Retrieved permissions for %d repositories for user %s",
                    len(repository_permissions),
                    username,
                )
                return repository_permissions

        except Exception:
            logger.exception(
                "Error getting user repository permissions for %s",
                username,
            )
            return {}

    async def get_accessible_repositories(
        self, username: str, access_token: str, org: str | None = None
    ) -> list[dict[str, Any]]:
        """Get list of repositories user has access to."""
        repository_permissions = await self.get_user_repository_permissions(
            username, access_token, org
        )

        accessible_repos = []
        for repo_name, permissions in repository_permissions.items():
            if permissions:  # User has some level of access
                accessible_repos.append(
                    {
                        "repository": repo_name,
                        "permissions": permissions,
                        "has_read": "repo:read" in permissions,
                        "has_write": "repo:write" in permissions,
                        "has_admin": "repo:admin" in permissions,
                    }
                )

        return accessible_repos

    async def validate_repository_list_access(
        self, username: str, access_token: str, repo_names: list[str]
    ) -> dict[str, bool]:
        """Validate user access to a list of repositories."""
        access_results = {}

        for repo_name in repo_names:
            has_access = await self.check_repository_access(
                username, repo_name, access_token, "read"
            )
            access_results[repo_name] = has_access

        return access_results

    def clear_user_cache(self, username: str) -> None:
        """Clear cached permissions for a specific user."""
        keys_to_remove = [
            key
            for key in self._permission_cache
            if key.startswith(f"{username}:")
        ]

        for key in keys_to_remove:
            del self._permission_cache[key]

        logger.info("Cleared permission cache for user: %s", username)

    def clear_repository_cache(self, repo_name: str) -> None:
        """Clear cached permissions for a specific repository."""
        keys_to_remove = [
            key
            for key in self._permission_cache
            if key.endswith(f":{repo_name}")
        ]

        for key in keys_to_remove:
            del self._permission_cache[key]

        logger.info("Cleared permission cache for repository: %s", repo_name)

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring."""
        total_entries = len(self._permission_cache)
        valid_entries = sum(
            1
            for entry in self._permission_cache.values()
            if self._is_cache_valid(entry)
        )

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": total_entries - valid_entries,
            "cache_hit_ratio": (
                valid_entries / total_entries if total_entries > 0 else 0
            ),
            "ttl_minutes": self._cache_ttl_minutes,
        }
