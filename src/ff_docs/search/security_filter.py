# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""
Global search with repository access filtering.

This module provides secure search functionality that respects repository
access permissions, ensuring users only see search results from repositories
they have access to view.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from ff_docs.auth.models import UserSession
from ff_docs.auth.repository_permissions import RepositoryPermissionManager

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Individual search result with repository context."""

    title: str
    url: str
    content: str
    repository: str
    section: str | None = None
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchQuery(BaseModel):
    """Search query with filtering options."""

    query: str
    repositories: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    limit: int = 50
    offset: int = 0


class SearchResponse(BaseModel):
    """Search response with filtered results."""

    query: str
    results: list[SearchResult]
    total_results: int
    filtered_results: int
    repositories_searched: list[str]
    execution_time_ms: float


class SecureSearchEngine:
    """
    Search engine with repository access filtering.

    This search engine integrates with the authentication system to ensure
    that search results are filtered based on the user's repository access
    permissions, providing secure cross-repository search.
    """

    def __init__(self) -> None:
        """Initialize the secure search engine."""
        self.permission_checker = RepositoryPermissionManager()

    async def search(
        self, query: SearchQuery, user_session: UserSession | None = None
    ) -> SearchResponse:
        """
        Perform secure search with repository access filtering.

        Args:
            query: Search query and parameters
            user_session: User session for permission checking

        Returns:
            Filtered search results
        """
        import time

        start_time = time.time()

        # Get accessible repositories for user
        accessible_repos = await self._get_accessible_repositories(
            user_session, query.repositories
        )

        if not accessible_repos:
            return SearchResponse(
                query=query.query,
                results=[],
                total_results=0,
                filtered_results=0,
                repositories_searched=[],
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Perform search across accessible repositories
        raw_results = await self._perform_search(query, accessible_repos)

        # Filter results by repository access
        filtered_results = await self._filter_results_by_access(
            raw_results, user_session, accessible_repos
        )

        # Apply pagination
        paginated_results = self._paginate_results(
            filtered_results, query.offset, query.limit
        )

        execution_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query.query,
            results=paginated_results,
            total_results=len(raw_results),
            filtered_results=len(filtered_results),
            repositories_searched=accessible_repos,
            execution_time_ms=execution_time,
        )

    async def _get_accessible_repositories(
        self, user_session: UserSession | None, requested_repos: list[str]
    ) -> list[str]:
        """
        Get list of repositories the user can access.

        Args:
            user_session: User session for permission checking
            requested_repos: Specific repositories requested

        Returns:
            List of accessible repository names
        """
        if not user_session:
            # Anonymous users have no repository access
            return []

        # Get all enrolled repositories
        from ff_docs.aggregator.enrollment import get_enrolled_repositories

        enrolled_repos = await get_enrolled_repositories()

        accessible_repos = []

        for repo in enrolled_repos:
            repo_name = repo["name"]

            # Skip if specific repos requested and this isn't one
            if requested_repos and repo_name not in requested_repos:
                continue

            # Check repository access
            try:
                has_access = (
                    await self.permission_checker.check_repository_access(
                        user_session.username,
                        repo_name,
                        user_session.access_token,
                        "read",
                    )
                )

                if has_access:
                    accessible_repos.append(repo_name)

            except Exception as e:
                logger.warning(
                    "Failed to check access for %s to %s: %s",
                    user_session.username,
                    repo_name,
                    e,
                )

        logger.debug(
            "User %s has access to %d repositories: %s",
            user_session.username,
            len(accessible_repos),
            accessible_repos,
        )

        return accessible_repos

    async def _perform_search(
        self, query: SearchQuery, accessible_repos: list[str]
    ) -> list[SearchResult]:
        """
        Perform search across accessible repositories.

        Args:
            query: Search query
            accessible_repos: List of accessible repositories

        Returns:
            Raw search results (before security filtering)
        """
        # TODO: Integrate with actual search backend
        # This is a placeholder implementation

        mock_results = []

        # Simulate search results from different repositories
        for i, repo in enumerate(accessible_repos[:3]):  # Limit for demo
            mock_results.extend(
                [
                    SearchResult(
                        title=f"Documentation for {query.query} in {repo}",
                        url=f"/projects/{repo}/docs/guide/",
                        content=f"This is documentation content related to {query.query} in repository {repo}",  # noqa: E501
                        repository=repo,
                        section="Guide",
                        score=0.9 - (i * 0.1),
                        metadata={
                            "type": "documentation",
                            "source": "markdown",
                        },
                    ),
                    SearchResult(
                        title=f"API Reference for {query.query}",
                        url=f"/projects/{repo}/docs/code/",
                        content=f"API documentation for {query.query} functions and classes",  # noqa: E501
                        repository=repo,
                        section="API",
                        score=0.8 - (i * 0.1),
                        metadata={"type": "api", "source": "pdoc"},
                    ),
                ]
            )

        # Sort by score
        mock_results.sort(key=lambda r: r.score, reverse=True)

        return mock_results

    async def _filter_results_by_access(
        self,
        results: list[SearchResult],
        user_session: UserSession | None,
        accessible_repos: list[str],
    ) -> list[SearchResult]:
        """
        Filter search results by repository access permissions.

        Args:
            results: Raw search results
            user_session: User session
            accessible_repos: Pre-filtered accessible repositories

        Returns:
            Filtered search results
        """
        if not user_session:
            return []

        filtered_results = []

        for result in results:
            # Check if result is from accessible repository
            if result.repository in accessible_repos:
                filtered_results.append(result)
            else:
                logger.debug(
                    "Filtered out result from %s for user %s",
                    result.repository,
                    user_session.username,
                )

        return filtered_results

    def _paginate_results(
        self, results: list[SearchResult], offset: int, limit: int
    ) -> list[SearchResult]:
        """
        Apply pagination to search results.

        Args:
            results: Filtered search results
            offset: Starting index
            limit: Maximum number of results

        Returns:
            Paginated results
        """
        start_idx = max(0, offset)
        end_idx = start_idx + limit

        return results[start_idx:end_idx]


# Global search engine instance
_search_engine: SecureSearchEngine | None = None


def get_search_engine() -> SecureSearchEngine:
    """Get the global search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = SecureSearchEngine()
    return _search_engine


async def search_with_security(
    query: SearchQuery, user_session: UserSession | None = None
) -> SearchResponse:
    """
    Perform secure search with repository access filtering.

    Args:
        query: Search query and parameters
        user_session: User session for permission checking

    Returns:
        Filtered search results
    """
    engine = get_search_engine()
    return await engine.search(query, user_session)
