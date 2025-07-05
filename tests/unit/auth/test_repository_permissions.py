# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001

"""Unit tests for repository permissions management."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ff_docs.auth.repository_permissions import (
    GITHUB_ROLE_MAPPING,
    RepositoryPermissionManager,
)


class TestRepositoryPermissionManager:
    """Test RepositoryPermissionManager class."""

    @pytest.fixture
    def manager(self) -> RepositoryPermissionManager:
        """Create a RepositoryPermissionManager instance."""
        return RepositoryPermissionManager()

    def test_manager_initialization(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test manager initialization."""
        assert manager.settings is not None
        assert manager.base_url == "https://api.github.com"
        assert manager._permission_cache == {}
        assert manager._cache_ttl_minutes == 10

    def test_get_cache_key(self, manager: RepositoryPermissionManager) -> None:
        """Test cache key generation."""
        key = manager._get_cache_key("testuser", "test-repo")
        assert key == "testuser:test-repo"

    def test_is_cache_valid_fresh_entry(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test cache validity for fresh entry."""
        cache_entry = {"cached_at": datetime.now(UTC)}
        assert manager._is_cache_valid(cache_entry) is True

    def test_is_cache_valid_expired_entry(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test cache validity for expired entry."""
        cache_entry = {"cached_at": datetime.now(UTC) - timedelta(minutes=15)}
        assert manager._is_cache_valid(cache_entry) is False

    def test_is_cache_valid_no_timestamp(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test cache validity without timestamp."""
        cache_entry: dict[str, Any] = {}
        assert manager._is_cache_valid(cache_entry) is False

    def test_cache_permission(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test caching permission data."""
        permission_data = {
            "username": "testuser",
            "repository": "test-repo",
            "permissions": ["repo:read", "repo:write"],
        }

        manager._cache_permission("testuser", "test-repo", permission_data)

        cache_key = "testuser:test-repo"
        assert cache_key in manager._permission_cache
        cached = manager._permission_cache[cache_key]
        assert cached["username"] == "testuser"
        assert "cached_at" in cached

    def test_get_cached_permission_valid(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting valid cached permission."""
        permission_data = {
            "username": "testuser",
            "repository": "test-repo",
            "permissions": ["repo:read"],
        }
        manager._cache_permission("testuser", "test-repo", permission_data)

        cached = manager._get_cached_permission("testuser", "test-repo")
        assert cached is not None
        assert cached["username"] == "testuser"

    def test_get_cached_permission_expired(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting expired cached permission."""
        # Add expired entry directly
        cache_key = "testuser:test-repo"
        manager._permission_cache[cache_key] = {
            "username": "testuser",
            "cached_at": datetime.now(UTC) - timedelta(minutes=15),
        }

        cached = manager._get_cached_permission("testuser", "test-repo")
        assert cached is None
        # Expired entry should be removed
        assert cache_key not in manager._permission_cache

    def test_get_cached_permission_not_found(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting non-existent cached permission."""
        cached = manager._get_cached_permission("testuser", "test-repo")
        assert cached is None

    @pytest.mark.asyncio
    async def test_check_repository_access_cached(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test checking repository access with cached data."""
        # Cache permission data
        permission_data = {
            "username": "testuser",
            "repository": "test-repo",
            "permissions": ["repo:read", "repo:write"],
        }
        manager._cache_permission("testuser", "test-repo", permission_data)

        # Check access
        has_access = await manager.check_repository_access(
            "testuser", "test-repo", "token", "write"
        )

        assert has_access is True

    @pytest.mark.asyncio
    async def test_check_repository_access_cached_no_permission(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test checking repository access with cached data - no permission."""
        # Cache permission data
        permission_data = {
            "username": "testuser",
            "repository": "test-repo",
            "permissions": ["repo:read"],
        }
        manager._cache_permission("testuser", "test-repo", permission_data)

        # Check access for permission not in cache
        has_access = await manager.check_repository_access(
            "testuser", "test-repo", "token", "admin"
        )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_check_repository_access_fresh_fetch(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test checking repository access with fresh fetch."""
        manager.settings.github.org = "test-org"

        # Mock _get_repository_permission
        permission_data = {
            "username": "testuser",
            "repository": "test-repo",
            "permissions": ["repo:read", "repo:write"],
            "github_permission": "write",
            "has_access": True,
        }
        # Mock the method using patch.object
        with patch.object(
            manager,
            "_get_repository_permission",
            AsyncMock(return_value=permission_data),
        ):
            # Check access
            has_access = await manager.check_repository_access(
                "testuser", "test-repo", "token", "write"
            )

            assert has_access is True
        # Should be cached now
        assert "testuser:test-repo" in manager._permission_cache

    @pytest.mark.asyncio
    async def test_check_repository_access_no_permission(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test checking repository access with no permission."""
        manager.settings.github.org = "test-org"

        # Mock _get_repository_permission to return no access
        permission_data = {
            "username": "testuser",
            "repository": "test-repo",
            "permissions": [],
            "github_permission": "none",
            "has_access": False,
        }
        # Mock the method using patch.object
        with patch.object(
            manager,
            "_get_repository_permission",
            AsyncMock(return_value=permission_data),
        ):
            # Check access
            has_access = await manager.check_repository_access(
                "testuser", "test-repo", "token", "read"
            )

            assert has_access is False

    @pytest.mark.asyncio
    async def test_check_repository_access_api_failure(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test checking repository access with API failure."""
        manager.settings.github.org = "test-org"

        # Mock _get_repository_permission to return None
        with patch.object(
            manager, "_get_repository_permission", AsyncMock(return_value=None)
        ):
            # Check access
            has_access = await manager.check_repository_access(
                "testuser", "test-repo", "token", "read"
            )

            assert has_access is False

    @pytest.mark.asyncio
    async def test_check_repository_access_exception(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test checking repository access with exception."""
        # Mock _get_cached_permission to raise exception
        with patch.object(
            manager,
            "_get_cached_permission",
            MagicMock(side_effect=Exception("Cache error")),
        ):
            # Check access
            has_access = await manager.check_repository_access(
                "testuser", "test-repo", "token", "read"
            )

            assert has_access is False

    @pytest.mark.asyncio
    async def test_get_repository_permission_success(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting repository permission successfully."""
        manager.settings.github.org = "test-org"

        with patch(
            "ff_docs.auth.repository_permissions.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "permission": "write",
                "role_name": "write",
                "user": {"login": "testuser"},
            }
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await manager._get_repository_permission(
                "testuser", "test-repo", "token"
            )

        assert result is not None
        assert result["username"] == "testuser"
        assert result["repository"] == "test-repo"
        assert result["github_permission"] == "write"
        assert "repo:read" in result["permissions"]
        assert "repo:write" in result["permissions"]
        assert result["has_access"] is True

    @pytest.mark.asyncio
    async def test_get_repository_permission_no_access(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting repository permission with no access."""
        manager.settings.github.org = "test-org"

        with patch(
            "ff_docs.auth.repository_permissions.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await manager._get_repository_permission(
                "testuser", "test-repo", "token"
            )

        assert result is not None
        assert result["username"] == "testuser"
        assert result["repository"] == "test-repo"
        assert result["github_permission"] == "none"
        assert result["permissions"] == []
        assert result["has_access"] is False

    @pytest.mark.asyncio
    async def test_get_repository_permission_no_org(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting repository permission with no organization."""
        manager.settings.github.org = None  # type: ignore[assignment]

        result = await manager._get_repository_permission(
            "testuser", "test-repo", "token"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_repository_permission_unexpected_status(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting repository permission with unexpected status code."""
        manager.settings.github.org = "test-org"

        with patch(
            "ff_docs.auth.repository_permissions.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await manager._get_repository_permission(
                "testuser", "test-repo", "token"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_repository_permission_http_error(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting repository permission with HTTP error."""
        manager.settings.github.org = "test-org"

        with patch(
            "ff_docs.auth.repository_permissions.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await manager._get_repository_permission(
                "testuser", "test-repo", "token"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_repository_permission_general_error(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting repository permission with general error."""
        manager.settings.github.org = "test-org"

        with patch(
            "ff_docs.auth.repository_permissions.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await manager._get_repository_permission(
                "testuser", "test-repo", "token"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_repository_permissions_success(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting user repository permissions successfully."""
        manager.settings.github.org = "test-org"

        with patch(
            "ff_docs.auth.repository_permissions.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()

            # Mock repository list response
            repos_response = MagicMock()
            repos_response.status_code = 200
            repos_response.json.return_value = [
                {"name": "repo1", "full_name": "test-org/repo1"},
                {"name": "repo2", "full_name": "test-org/repo2"},
            ]
            repos_response.raise_for_status = MagicMock()
            mock_client.get.return_value = repos_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock _get_repository_permission
            async def mock_get_perm(
                username: str, repo: str, token: str
            ) -> dict[str, Any] | None:
                if repo == "repo1":
                    return {
                        "username": username,
                        "repository": repo,
                        "permissions": ["repo:read", "repo:write"],
                        "has_access": True,
                    }
                return {
                    "username": username,
                    "repository": repo,
                    "permissions": [],
                    "has_access": False,
                }

            # Mock the method using patch.object
            with patch.object(
                manager,
                "_get_repository_permission",
                AsyncMock(side_effect=mock_get_perm),
            ):
                result = await manager.get_user_repository_permissions(
                    "testuser", "token"
                )

                assert "repo1" in result
                assert result["repo1"] == ["repo:read", "repo:write"]
                assert "repo2" not in result  # No access

    @pytest.mark.asyncio
    async def test_get_user_repository_permissions_no_org(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting user repository permissions with no org."""
        manager.settings.github.org = None  # type: ignore[assignment]

        result = await manager.get_user_repository_permissions(
            "testuser", "token"
        )

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_user_repository_permissions_custom_org(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting user repository permissions with custom org."""
        with patch(
            "ff_docs.auth.repository_permissions.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()

            # Mock repository list response
            repos_response = MagicMock()
            repos_response.status_code = 200
            repos_response.json.return_value = []
            repos_response.raise_for_status = MagicMock()
            mock_client.get.return_value = repos_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await manager.get_user_repository_permissions(
                "testuser", "token", "custom-org"
            )

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_user_repository_permissions_exception(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting user repository permissions with exception."""
        manager.settings.github.org = "test-org"

        with patch(
            "ff_docs.auth.repository_permissions.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("API error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await manager.get_user_repository_permissions(
                "testuser", "token"
            )

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_accessible_repositories(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting accessible repositories."""
        # Mock get_user_repository_permissions
        mock_permissions = {
            "repo1": ["repo:read", "repo:write"],
            "repo2": ["repo:read"],
            "repo3": ["repo:read", "repo:write", "repo:admin"],
        }
        with patch.object(
            manager,
            "get_user_repository_permissions",
            AsyncMock(return_value=mock_permissions),
        ):
            result = await manager.get_accessible_repositories(
                "testuser", "token"
            )

            assert len(result) == 3

            # Check repo1
            repo1 = next(r for r in result if r["repository"] == "repo1")
            assert repo1["has_read"] is True
            assert repo1["has_write"] is True
            assert repo1["has_admin"] is False

            # Check repo3
            repo3 = next(r for r in result if r["repository"] == "repo3")
            assert repo3["has_admin"] is True

    @pytest.mark.asyncio
    async def test_get_accessible_repositories_none(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting accessible repositories with no access."""
        # Mock get_user_repository_permissions to return empty
        with patch.object(
            manager,
            "get_user_repository_permissions",
            AsyncMock(return_value={}),
        ):
            result = await manager.get_accessible_repositories(
                "testuser", "token"
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_validate_repository_list_access(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test validating access to repository list."""

        # Mock check_repository_access
        async def mock_check(
            username: str, repo: str, token: str, perm: str
        ) -> bool:
            return repo in ["repo1", "repo3"]

        with patch.object(
            manager,
            "check_repository_access",
            AsyncMock(side_effect=mock_check),
        ):
            result = await manager.validate_repository_list_access(
                "testuser", "token", ["repo1", "repo2", "repo3"]
            )

            assert result == {
                "repo1": True,
                "repo2": False,
                "repo3": True,
            }

    def test_clear_user_cache(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test clearing user cache."""
        # Add some cache entries
        manager._permission_cache = {
            "user1:repo1": {"data": "test1"},
            "user1:repo2": {"data": "test2"},
            "user2:repo1": {"data": "test3"},
        }

        manager.clear_user_cache("user1")

        assert "user1:repo1" not in manager._permission_cache
        assert "user1:repo2" not in manager._permission_cache
        assert "user2:repo1" in manager._permission_cache

    def test_clear_repository_cache(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test clearing repository cache."""
        # Add some cache entries
        manager._permission_cache = {
            "user1:repo1": {"data": "test1"},
            "user2:repo1": {"data": "test2"},
            "user1:repo2": {"data": "test3"},
        }

        manager.clear_repository_cache("repo1")

        assert "user1:repo1" not in manager._permission_cache
        assert "user2:repo1" not in manager._permission_cache
        assert "user1:repo2" in manager._permission_cache

    def test_get_cache_stats(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting cache statistics."""
        # Add cache entries with different timestamps
        now = datetime.now(UTC)
        manager._permission_cache = {
            "user1:repo1": {"cached_at": now},  # Valid
            "user1:repo2": {"cached_at": now - timedelta(minutes=5)},  # Valid
            "user2:repo1": {
                "cached_at": now - timedelta(minutes=15)
            },  # Expired
        }

        stats = manager.get_cache_stats()

        assert stats["total_entries"] == 3
        assert stats["valid_entries"] == 2
        assert stats["expired_entries"] == 1
        assert stats["cache_hit_ratio"] == 2 / 3
        assert stats["ttl_minutes"] == 10

    def test_get_cache_stats_empty(
        self, manager: RepositoryPermissionManager
    ) -> None:
        """Test getting cache statistics with empty cache."""
        stats = manager.get_cache_stats()

        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["cache_hit_ratio"] == 0
        assert stats["ttl_minutes"] == 10


class TestGitHubRoleMapping:
    """Test GitHub role mapping constants."""

    def test_github_role_mapping(self) -> None:
        """Test GitHub role mapping definitions."""
        assert "read" in GITHUB_ROLE_MAPPING
        assert "repo:read" in GITHUB_ROLE_MAPPING["read"]

        assert "write" in GITHUB_ROLE_MAPPING
        assert "repo:read" in GITHUB_ROLE_MAPPING["write"]
        assert "repo:write" in GITHUB_ROLE_MAPPING["write"]

        assert "admin" in GITHUB_ROLE_MAPPING
        assert "repo:admin" in GITHUB_ROLE_MAPPING["admin"]


class TestRepositoryPermissionIntegration:
    """Integration tests for repository permission functionality."""

    @pytest.mark.asyncio
    async def test_full_permission_check_flow(self) -> None:
        """Test complete permission check flow."""
        manager = RepositoryPermissionManager()
        manager.settings.github.org = "test-org"

        with patch(
            "ff_docs.auth.repository_permissions.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()

            # First call - permission check
            perm_response = MagicMock()
            perm_response.status_code = 200
            perm_response.json.return_value = {
                "permission": "maintain",
                "role_name": "maintain",
            }
            mock_client.get.return_value = perm_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Check write access
            has_access = await manager.check_repository_access(
                "alice", "important-repo", "github-token", "write"
            )

        assert has_access is True

        # Check cache was populated
        assert "alice:important-repo" in manager._permission_cache

        # Second check should use cache (no API call)
        has_access2 = await manager.check_repository_access(
            "alice", "important-repo", "github-token", "read"
        )
        assert has_access2 is True

    @pytest.mark.asyncio
    async def test_permission_escalation_check(self) -> None:
        """Test that users cannot access higher permissions than granted."""
        manager = RepositoryPermissionManager()
        manager.settings.github.org = "test-org"

        # Cache read-only permission
        manager._cache_permission(
            "bob",
            "secure-repo",
            {
                "username": "bob",
                "repository": "secure-repo",
                "permissions": ["repo:read"],
                "github_permission": "read",
                "has_access": True,
            },
        )

        # Try to check for write access
        has_write = await manager.check_repository_access(
            "bob", "secure-repo", "token", "write"
        )
        assert has_write is False

        # Try to check for admin access
        has_admin = await manager.check_repository_access(
            "bob", "secure-repo", "token", "admin"
        )
        assert has_admin is False

        # Check read access should work
        has_read = await manager.check_repository_access(
            "bob", "secure-repo", "token", "read"
        )
        assert has_read is True
