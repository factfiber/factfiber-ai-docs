# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""GitHub API client for repository discovery and content management."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from httpx import AsyncClient

from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RepositoryInfo:
    """Information about a GitHub repository."""

    name: str
    full_name: str
    description: str | None
    clone_url: str
    ssh_url: str
    default_branch: str
    private: bool
    has_docs: bool = False
    docs_path: str | None = None
    mkdocs_config: str | None = None


class GitHubClient:
    """GitHub API client for repository operations."""

    def __init__(self) -> None:
        """Initialize GitHub client with authentication."""
        self.settings = get_settings()
        self.base_url = "https://api.github.com"

        if not self.settings.github.token:
            raise ValueError(
                "GitHub token is required but not configured. "
                "Please set the GITHUB_TOKEN environment variable."
            )

        self.headers = {
            "Authorization": f"Bearer {self.settings.github.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_organization_repositories(
        self,
        org: str,
        type_filter: str = "all",
        per_page: int = 100,
    ) -> list[RepositoryInfo]:
        """Get all repositories for an organization.

        Args:
            org: Organization name
            type_filter: Repository type filter (all, public, private, etc.)
            per_page: Number of repositories per page

        Returns:
            List of repository information
        """
        repositories = []
        page = 1

        async with AsyncClient() as client:
            while True:
                url = f"{self.base_url}/orgs/{org}/repos"
                params = {
                    "type": type_filter,
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                }

                try:
                    response = await client.get(
                        url,
                        headers=self.headers,
                        params=params,
                        timeout=30.0,
                    )
                    response.raise_for_status()

                    repos_data = response.json()
                    if not repos_data:
                        break

                    for repo_data in repos_data:
                        repo_info = self._parse_repository_data(repo_data)
                        repositories.append(repo_info)

                    page += 1

                except httpx.HTTPStatusError as e:
                    logger.exception(
                        "GitHub API error: %d", e.response.status_code
                    )
                    if e.response.status_code == 403:  # noqa: PLR2004
                        logger.exception(
                            "Rate limit exceeded or insufficient permissions"
                        )
                    raise
                except httpx.RequestError:
                    logger.exception("Request error")
                    raise

        logger.info("Found %d repositories in %s", len(repositories), org)
        return repositories

    async def check_repository_documentation(
        self,
        repo_info: RepositoryInfo,
    ) -> RepositoryInfo:
        """Check if repository has documentation and detect configuration.

        Args:
            repo_info: Repository information to check

        Returns:
            Updated repository information with documentation details
        """
        docs_indicators = [
            "docs/",
            "documentation/",
            "doc/",
            "mkdocs.yml",
            "mkdocs.yaml",
            ".readthedocs.yml",
            ".readthedocs.yaml",
        ]

        async with AsyncClient() as client:
            for indicator in docs_indicators:
                try:
                    url = (
                        f"{self.base_url}/repos/{repo_info.full_name}"
                        f"/contents/{indicator}"
                    )

                    response = await client.get(
                        url,
                        headers=self.headers,
                        timeout=10.0,
                    )

                    if response.status_code == 200:  # noqa: PLR2004
                        content_data = response.json()

                        # Handle directory vs file
                        if isinstance(content_data, list):
                            # Directory found
                            if indicator.endswith("/"):
                                repo_info.has_docs = True
                                repo_info.docs_path = indicator
                                logger.info(
                                    "Found docs directory: %s/%s",
                                    repo_info.name,
                                    indicator,
                                )
                        # File found
                        elif "mkdocs.y" in indicator:
                            repo_info.has_docs = True
                            repo_info.mkdocs_config = indicator
                            logger.info(
                                "Found MkDocs config: %s/%s",
                                repo_info.name,
                                indicator,
                            )

                except httpx.HTTPStatusError:
                    # File/directory not found, continue checking
                    continue
                except httpx.RequestError as e:
                    logger.warning("Error checking %s: %s", indicator, e)
                    continue

        return repo_info

    async def get_repository_content(
        self,
        repo_info: RepositoryInfo,
        path: str,
    ) -> dict[str, Any] | None:
        """Get content from a repository path.

        Args:
            repo_info: Repository information
            path: Path within repository

        Returns:
            Content data or None if not found
        """
        url = f"{self.base_url}/repos/{repo_info.full_name}/contents/{path}"

        async with AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:  # noqa: PLR2004
                    logger.debug(
                        "Content not found: %s/%s", repo_info.name, path
                    )
                    return None
                logger.exception("Error getting content")
                raise
            except httpx.RequestError:
                logger.exception("Request error")
                raise

    def _parse_repository_data(
        self, repo_data: dict[str, Any]
    ) -> RepositoryInfo:
        """Parse GitHub API repository data.

        Args:
            repo_data: Raw repository data from GitHub API

        Returns:
            Parsed repository information
        """
        return RepositoryInfo(
            name=repo_data["name"],
            full_name=repo_data["full_name"],
            description=repo_data.get("description"),
            clone_url=repo_data["clone_url"],
            ssh_url=repo_data["ssh_url"],
            default_branch=repo_data["default_branch"],
            private=repo_data["private"],
        )


class RepositoryAggregator:
    """High-level repository aggregation coordinator."""

    def __init__(self) -> None:
        """Initialize repository aggregator."""
        self.github_client = GitHubClient()
        self.settings = get_settings()

    async def discover_documentation_repositories(
        self,
        org: str | None = None,
    ) -> list[RepositoryInfo]:
        """Discover all repositories with documentation in organization.

        Args:
            org: Organization name (defaults to configured org)

        Returns:
            List of repositories with documentation
        """
        org = org or self.settings.github.org
        if not org:
            raise ValueError("GitHub organization not configured")

        logger.info("Discovering documentation repositories in %s", org)

        # Get all repositories
        repositories = await self.github_client.get_organization_repositories(
            org
        )

        # Check each repository for documentation
        doc_repositories = []
        tasks = [
            self.github_client.check_repository_documentation(repo)
            for repo in repositories
        ]

        # Process in batches to avoid rate limiting
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            results = await asyncio.gather(*batch, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error("Error checking repository: %s", result)
                    continue

                # Type guard to ensure result is RepositoryInfo
                if isinstance(result, RepositoryInfo) and result.has_docs:
                    doc_repositories.append(result)

            # Brief pause between batches
            if i + batch_size < len(tasks):
                await asyncio.sleep(1)

        logger.info(
            "Found %d repositories with documentation", len(doc_repositories)
        )
        return doc_repositories

    async def generate_mkdocs_config(
        self,
        repositories: list[RepositoryInfo],
    ) -> dict[str, Any]:
        """Generate MkDocs configuration for discovered repositories.

        Args:
            repositories: List of repositories with documentation

        Returns:
            MkDocs configuration dictionary
        """
        nav_entries = []

        for repo in repositories:
            if not repo.has_docs:
                continue

            # Build import URL with branch specification
            import_url = f"{repo.clone_url}?branch={repo.default_branch}"

            if repo.docs_path:
                import_url += f"&docs_dir={repo.docs_path}*"

            nav_entry = {repo.name.title(): f"!import {import_url}"}
            nav_entries.append(nav_entry)

        return {
            "nav_entries": nav_entries,
            "repositories": [
                {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "private": repo.private,
                    "default_branch": repo.default_branch,
                    "has_docs": repo.has_docs,
                    "docs_path": repo.docs_path,
                }
                for repo in repositories
            ],
        }
