# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001, S105
# mypy: disable-error-code="method-assign,assignment"

"""Unit tests for GitHub client module."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ff_docs.aggregator.github_client import (
    GitHubClient,
    RepositoryAggregator,
    RepositoryInfo,
)


class TestRepositoryInfo:
    """Test RepositoryInfo dataclass."""

    def test_repository_info_creation(self) -> None:
        """Test creating RepositoryInfo with all fields."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test repository",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
            has_docs=True,
            docs_path="docs/",
            mkdocs_config="mkdocs.yml",
        )

        assert repo_info.name == "test-repo"
        assert repo_info.full_name == "org/test-repo"
        assert repo_info.description == "Test repository"
        assert repo_info.clone_url == "https://github.com/org/test-repo.git"
        assert repo_info.ssh_url == "git@github.com:org/test-repo.git"
        assert repo_info.default_branch == "main"
        assert repo_info.private is False
        assert repo_info.has_docs is True
        assert repo_info.docs_path == "docs/"
        assert repo_info.mkdocs_config == "mkdocs.yml"

    def test_repository_info_defaults(self) -> None:
        """Test RepositoryInfo with default values."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description=None,
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=True,
        )

        assert repo_info.has_docs is False
        assert repo_info.docs_path is None
        assert repo_info.mkdocs_config is None


class TestGitHubClient:
    """Test GitHubClient class."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        """Create a GitHubClient instance."""
        return GitHubClient()

    @pytest.fixture
    def mock_repo_data(self) -> dict[str, Any]:
        """Create mock repository data from GitHub API."""
        return {
            "name": "test-repo",
            "full_name": "org/test-repo",
            "description": "Test repository",
            "clone_url": "https://github.com/org/test-repo.git",
            "ssh_url": "git@github.com:org/test-repo.git",
            "default_branch": "main",
            "private": False,
        }

    def test_client_initialization_with_token(
        self, client: GitHubClient
    ) -> None:
        """Test GitHubClient initialization with token."""
        with patch(
            "ff_docs.aggregator.github_client.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.token = "test-token"
            client = GitHubClient()

        assert client.base_url == "https://api.github.com"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test-token"

    def test_client_initialization_without_token(
        self, client: GitHubClient
    ) -> None:
        """Test GitHubClient initialization without token."""
        with patch(
            "ff_docs.aggregator.github_client.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.token = None
            client = GitHubClient()

        assert client.base_url == "https://api.github.com"
        assert "Authorization" not in client.headers

    def test_is_configured_with_token(self, client: GitHubClient) -> None:
        """Test is_configured when token is present."""
        client.settings.github.token = "test-token"
        assert client.is_configured() is True

    def test_is_configured_without_token(self, client: GitHubClient) -> None:
        """Test is_configured when token is missing."""
        client.settings.github.token = None
        assert client.is_configured() is False

    def test_require_token_success(self, client: GitHubClient) -> None:
        """Test require_token with token present."""
        client.settings.github.token = "test-token"
        # Should not raise
        client.require_token()

    def test_require_token_failure(self, client: GitHubClient) -> None:
        """Test require_token without token."""
        client.settings.github.token = None
        with pytest.raises(ValueError, match="GitHub token is required"):
            client.require_token()

    @pytest.mark.asyncio
    async def test_get_organization_repositories_success(
        self, client: GitHubClient, mock_repo_data: dict[str, Any]
    ) -> None:
        """Test getting organization repositories successfully."""
        client.settings.github.token = "test-token"

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()

            # First page response
            page1_response = MagicMock()
            page1_response.json.return_value = [
                mock_repo_data,
                {**mock_repo_data, "name": "test-repo-2"},
            ]
            page1_response.raise_for_status = MagicMock()

            # Second page response (empty)
            page2_response = MagicMock()
            page2_response.json.return_value = []
            page2_response.raise_for_status = MagicMock()

            mock_client.get.side_effect = [page1_response, page2_response]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            repos = await client.get_organization_repositories("test-org")

        assert len(repos) == 2
        assert repos[0].name == "test-repo"
        assert repos[1].name == "test-repo-2"
        assert repos[0].private is False

    @pytest.mark.asyncio
    async def test_get_organization_repositories_no_token(
        self, client: GitHubClient
    ) -> None:
        """Test getting repositories without token."""
        client.settings.github.token = None

        with pytest.raises(ValueError, match="GitHub token is required"):
            await client.get_organization_repositories("test-org")

    @pytest.mark.asyncio
    async def test_get_organization_repositories_http_error(
        self, client: GitHubClient
    ) -> None:
        """Test getting repositories with HTTP error."""
        client.settings.github.token = "test-token"

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await client.get_organization_repositories("test-org")

    @pytest.mark.asyncio
    async def test_get_organization_repositories_rate_limit(
        self, client: GitHubClient
    ) -> None:
        """Test getting repositories with rate limit error."""
        client.settings.github.token = "test-token"

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Rate limit exceeded",
                request=MagicMock(),
                response=MagicMock(status_code=403),
            )
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await client.get_organization_repositories("test-org")

    @pytest.mark.asyncio
    async def test_get_organization_repositories_request_error(
        self, client: GitHubClient
    ) -> None:
        """Test getting repositories with request error."""
        client.settings.github.token = "test-token"

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.RequestError):
                await client.get_organization_repositories("test-org")

    @pytest.mark.asyncio
    async def test_check_repository_documentation_found_docs_dir(
        self, client: GitHubClient
    ) -> None:
        """Test checking repository documentation with docs directory."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
        )

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()

            # docs/ directory found
            docs_response = MagicMock()
            docs_response.status_code = 200
            docs_response.json.return_value = [
                {"name": "index.md", "type": "file"},
                {"name": "guide.md", "type": "file"},
            ]

            # Function to simulate 404 responses
            async def mock_get_404(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                response = MagicMock()
                response.status_code = 404
                return response

            # Set up responses for each path check
            call_count = 0

            async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                nonlocal call_count
                url = args[0]
                if "docs/" in url and call_count == 0:
                    call_count += 1
                    return docs_response
                call_count += 1
                return await mock_get_404(*args, **kwargs)

            mock_client.get = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            updated_repo = await client.check_repository_documentation(
                repo_info
            )

        assert updated_repo.has_docs is True
        assert updated_repo.docs_path == "docs/"

    @pytest.mark.asyncio
    async def test_check_repository_documentation_found_mkdocs(
        self, client: GitHubClient
    ) -> None:
        """Test checking repository documentation with mkdocs.yml."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
        )

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()

            # mkdocs.yml found
            mkdocs_response = MagicMock()
            mkdocs_response.status_code = 200
            mkdocs_response.json.return_value = {
                "name": "mkdocs.yml",
                "type": "file",
                "content": "base64content",
            }

            # Function to simulate 404 responses
            async def mock_get_404(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                response = MagicMock()
                response.status_code = 404
                return response

            # Set up responses for each path check
            call_count = 0

            async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                nonlocal call_count
                url = args[0]
                if "mkdocs.yml" in url and call_count == 3:
                    call_count += 1
                    return mkdocs_response
                call_count += 1
                return await mock_get_404(*args, **kwargs)

            mock_client.get = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            updated_repo = await client.check_repository_documentation(
                repo_info
            )

        assert updated_repo.has_docs is True
        assert updated_repo.mkdocs_config == "mkdocs.yml"

    @pytest.mark.asyncio
    async def test_check_repository_documentation_http_error(
        self, client: GitHubClient
    ) -> None:
        """Test checking documentation with HTTP errors."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
        )

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()

            # Create a response that will raise HTTPStatusError
            async def mock_get_500(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                # Simulate non-404 HTTP error
                raise httpx.HTTPStatusError(
                    "Server Error",
                    request=MagicMock(),
                    response=MagicMock(status_code=500),
                )

            # Function to simulate 404 responses
            async def mock_get_404(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                response = MagicMock()
                response.status_code = 404
                return response

            # Set up responses: first error, then all 404s
            call_count = 0

            async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                nonlocal call_count
                if call_count == 0:
                    call_count += 1
                    return await mock_get_500(*args, **kwargs)
                call_count += 1
                return await mock_get_404(*args, **kwargs)

            mock_client.get = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            updated_repo = await client.check_repository_documentation(
                repo_info
            )

        # Should continue checking other paths
        assert updated_repo.has_docs is False

    @pytest.mark.asyncio
    async def test_check_repository_documentation_request_error(
        self, client: GitHubClient
    ) -> None:
        """Test checking documentation with request errors."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
        )

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()

            # Function to simulate network errors
            async def mock_get_error(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                raise httpx.RequestError("Network error")

            # Function to simulate 404 responses
            async def mock_get_404(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                response = MagicMock()
                response.status_code = 404
                return response

            # Mix of request errors and not found
            call_count = 0

            async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                nonlocal call_count
                if call_count in [0, 2]:  # First and third calls error
                    call_count += 1
                    return await mock_get_error(*args, **kwargs)
                call_count += 1
                return await mock_get_404(*args, **kwargs)

            mock_client.get = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            updated_repo = await client.check_repository_documentation(
                repo_info
            )

        # Should continue checking despite errors
        assert updated_repo.has_docs is False

    @pytest.mark.asyncio
    async def test_get_repository_content_success(
        self, client: GitHubClient
    ) -> None:
        """Test getting repository content successfully."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
        )

        expected_content = {
            "name": "README.md",
            "path": "README.md",
            "type": "file",
            "content": "base64encodedcontent",
        }

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = expected_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            content = await client.get_repository_content(
                repo_info, "README.md"
            )

        assert content == expected_content

    @pytest.mark.asyncio
    async def test_get_repository_content_not_found(
        self, client: GitHubClient
    ) -> None:
        """Test getting repository content when not found."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
        )

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            content = await client.get_repository_content(
                repo_info, "nonexistent.md"
            )

        assert content is None

    @pytest.mark.asyncio
    async def test_get_repository_content_http_error(
        self, client: GitHubClient
    ) -> None:
        """Test getting repository content with HTTP error."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
        )

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await client.get_repository_content(repo_info, "README.md")

    @pytest.mark.asyncio
    async def test_get_repository_content_request_error(
        self, client: GitHubClient
    ) -> None:
        """Test getting repository content with request error."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
        )

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.RequestError):
                await client.get_repository_content(repo_info, "README.md")

    def test_parse_repository_data(self, client: GitHubClient) -> None:
        """Test parsing repository data from GitHub API."""
        repo_data = {
            "name": "test-repo",
            "full_name": "org/test-repo",
            "description": "Test repository",
            "clone_url": "https://github.com/org/test-repo.git",
            "ssh_url": "git@github.com:org/test-repo.git",
            "default_branch": "main",
            "private": False,
        }

        repo_info = client._parse_repository_data(repo_data)

        assert repo_info.name == "test-repo"
        assert repo_info.full_name == "org/test-repo"
        assert repo_info.description == "Test repository"
        assert repo_info.clone_url == "https://github.com/org/test-repo.git"
        assert repo_info.ssh_url == "git@github.com:org/test-repo.git"
        assert repo_info.default_branch == "main"
        assert repo_info.private is False
        assert repo_info.has_docs is False  # Default value

    def test_parse_repository_data_no_description(
        self, client: GitHubClient
    ) -> None:
        """Test parsing repository data without description."""
        repo_data = {
            "name": "test-repo",
            "full_name": "org/test-repo",
            # No description field
            "clone_url": "https://github.com/org/test-repo.git",
            "ssh_url": "git@github.com:org/test-repo.git",
            "default_branch": "main",
            "private": True,
        }

        repo_info = client._parse_repository_data(repo_data)

        assert repo_info.description is None
        assert repo_info.private is True


class TestRepositoryAggregator:
    """Test RepositoryAggregator class."""

    @pytest.fixture
    def aggregator(self) -> RepositoryAggregator:
        """Create a RepositoryAggregator instance."""
        return RepositoryAggregator()

    @pytest.mark.asyncio
    async def test_discover_documentation_repositories_success(
        self, aggregator: RepositoryAggregator
    ) -> None:
        """Test discovering documentation repositories successfully."""
        # Mock repositories from GitHub
        mock_repos = [
            RepositoryInfo(
                name=f"repo-{i}",
                full_name=f"org/repo-{i}",
                description=f"Repository {i}",
                clone_url=f"https://github.com/org/repo-{i}.git",
                ssh_url=f"git@github.com:org/repo-{i}.git",
                default_branch="main",
                private=False,
            )
            for i in range(3)
        ]

        # Mock checking documentation (only first 2 have docs)
        async def mock_check_docs(repo: RepositoryInfo) -> RepositoryInfo:
            if repo.name in ["repo-0", "repo-1"]:
                repo.has_docs = True
                repo.docs_path = "docs/"
            return repo

        aggregator.github_client.get_organization_repositories = AsyncMock(
            return_value=mock_repos
        )
        aggregator.github_client.check_repository_documentation = AsyncMock(
            side_effect=mock_check_docs
        )

        doc_repos = await aggregator.discover_documentation_repositories()

        assert len(doc_repos) == 2
        assert doc_repos[0].name == "repo-0"
        assert doc_repos[1].name == "repo-1"
        assert all(repo.has_docs for repo in doc_repos)

    @pytest.mark.asyncio
    async def test_discover_documentation_repositories_no_org(
        self, aggregator: RepositoryAggregator
    ) -> None:
        """Test discovering repositories with no organization configured."""
        aggregator.settings.github.org = None

        with pytest.raises(
            ValueError, match="GitHub organization not configured"
        ):
            await aggregator.discover_documentation_repositories()

    @pytest.mark.asyncio
    async def test_discover_documentation_repositories_with_custom_org(
        self, aggregator: RepositoryAggregator
    ) -> None:
        """Test discovering repositories with custom organization."""
        mock_repos: list[dict[str, Any]] = []
        aggregator.github_client.get_organization_repositories = AsyncMock(
            return_value=mock_repos
        )

        doc_repos = await aggregator.discover_documentation_repositories(
            org="custom-org"
        )

        assert doc_repos == []
        aggregator.github_client.get_organization_repositories.assert_called_once_with(
            "custom-org",
        )

    @pytest.mark.asyncio
    async def test_discover_documentation_repositories_with_errors(
        self, aggregator: RepositoryAggregator
    ) -> None:
        """Test discovering repositories with some errors."""
        # Set up GitHub organization
        aggregator.settings.github.org = "test-org"

        # Create more than batch_size repos to test batching
        mock_repos = [
            RepositoryInfo(
                name=f"repo-{i}",
                full_name=f"org/repo-{i}",
                description=f"Repository {i}",
                clone_url=f"https://github.com/org/repo-{i}.git",
                ssh_url=f"git@github.com:org/repo-{i}.git",
                default_branch="main",
                private=False,
            )
            for i in range(15)  # More than batch_size (10)
        ]

        # Mock checking with some failures
        check_call_count = 0

        async def mock_check_docs(repo: RepositoryInfo) -> RepositoryInfo:
            nonlocal check_call_count
            check_call_count += 1
            # Make a copy to avoid modifying the original
            result = RepositoryInfo(
                name=repo.name,
                full_name=repo.full_name,
                description=repo.description,
                clone_url=repo.clone_url,
                ssh_url=repo.ssh_url,
                default_branch=repo.default_branch,
                private=repo.private,
                has_docs=False,
                docs_path=None,
                mkdocs_config=None,
            )
            if repo.name == "repo-5":
                raise RuntimeError("Check failed")
            if repo.name in ["repo-0", "repo-10"]:
                result.has_docs = True
                result.docs_path = "docs/"
            return result

        aggregator.github_client.get_organization_repositories = AsyncMock(
            return_value=mock_repos
        )
        aggregator.github_client.check_repository_documentation = AsyncMock(
            side_effect=mock_check_docs
        )

        # Mock sleep to avoid actual delay
        with patch("asyncio.sleep", new_callable=AsyncMock):
            doc_repos = await aggregator.discover_documentation_repositories()

        # Should have 2 repos with docs (repo-5 errored)
        assert len(doc_repos) == 2
        assert doc_repos[0].name == "repo-0"
        assert doc_repos[1].name == "repo-10"

    @pytest.mark.asyncio
    async def test_generate_mkdocs_config_success(
        self, aggregator: RepositoryAggregator
    ) -> None:
        """Test generating MkDocs configuration successfully."""
        repos = [
            RepositoryInfo(
                name="api-docs",
                full_name="org/api-docs",
                description="API Documentation",
                clone_url="https://github.com/org/api-docs.git",
                ssh_url="git@github.com:org/api-docs.git",
                default_branch="main",
                private=False,
                has_docs=True,
                docs_path="docs/",
            ),
            RepositoryInfo(
                name="user-guide",
                full_name="org/user-guide",
                description="User Guide",
                clone_url="https://github.com/org/user-guide.git",
                ssh_url="git@github.com:org/user-guide.git",
                default_branch="develop",
                private=True,
                has_docs=True,
                mkdocs_config="mkdocs.yml",
            ),
            RepositoryInfo(
                name="no-docs",
                full_name="org/no-docs",
                description="No documentation",
                clone_url="https://github.com/org/no-docs.git",
                ssh_url="git@github.com:org/no-docs.git",
                default_branch="main",
                private=False,
                has_docs=False,
            ),
        ]

        config = await aggregator.generate_mkdocs_config(repos)

        # Should only include repos with docs
        assert len(config["nav_entries"]) == 2

        # Check first entry
        assert "Api-Docs" in config["nav_entries"][0]
        assert config["nav_entries"][0]["Api-Docs"] == (
            "!import https://github.com/org/api-docs.git"
            "?branch=main&docs_dir=docs/*"
        )

        # Check second entry
        assert "User-Guide" in config["nav_entries"][1]
        assert config["nav_entries"][1]["User-Guide"] == (
            "!import https://github.com/org/user-guide.git?branch=develop"
        )

        # Check repositories list
        assert len(config["repositories"]) == 3  # All repos included
        assert config["repositories"][0]["name"] == "api-docs"
        assert config["repositories"][0]["has_docs"] is True
        assert config["repositories"][2]["has_docs"] is False

    @pytest.mark.asyncio
    async def test_generate_mkdocs_config_empty_repos(
        self, aggregator: RepositoryAggregator
    ) -> None:
        """Test generating MkDocs configuration with no repositories."""
        config = await aggregator.generate_mkdocs_config([])

        assert config["nav_entries"] == []
        assert config["repositories"] == []

    @pytest.mark.asyncio
    async def test_generate_mkdocs_config_no_docs_repos(
        self, aggregator: RepositoryAggregator
    ) -> None:
        """Test generating MkDocs configuration with no documented repos."""
        repos = [
            RepositoryInfo(
                name="no-docs-1",
                full_name="org/no-docs-1",
                description="No documentation",
                clone_url="https://github.com/org/no-docs-1.git",
                ssh_url="git@github.com:org/no-docs-1.git",
                default_branch="main",
                private=False,
                has_docs=False,
            ),
            RepositoryInfo(
                name="no-docs-2",
                full_name="org/no-docs-2",
                description="Also no documentation",
                clone_url="https://github.com/org/no-docs-2.git",
                ssh_url="git@github.com:org/no-docs-2.git",
                default_branch="main",
                private=True,
                has_docs=False,
            ),
        ]

        config = await aggregator.generate_mkdocs_config(repos)

        assert config["nav_entries"] == []  # No nav entries
        assert len(config["repositories"]) == 2  # But repos are listed
        assert all(not repo["has_docs"] for repo in config["repositories"])


class TestGitHubClientIntegration:
    """Integration tests for GitHub client functionality."""

    @pytest.mark.asyncio
    async def test_full_repository_discovery_flow(self) -> None:
        """Test complete repository discovery workflow."""
        aggregator = RepositoryAggregator()

        # Mock settings
        aggregator.settings.github.org = "test-org"
        aggregator.github_client.settings.github.token = "test-token"

        with patch(
            "ff_docs.aggregator.github_client.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()

            # Mock get repositories response
            repos_response = MagicMock()
            repos_response.json.return_value = [
                {
                    "name": "docs-repo",
                    "full_name": "test-org/docs-repo",
                    "description": "Documentation repository",
                    "clone_url": "https://github.com/test-org/docs-repo.git",
                    "ssh_url": "git@github.com:test-org/docs-repo.git",
                    "default_branch": "main",
                    "private": False,
                }
            ]
            repos_response.raise_for_status = MagicMock()

            # Mock empty second page
            empty_response = MagicMock()
            empty_response.json.return_value = []
            empty_response.raise_for_status = MagicMock()

            # Mock docs check - mkdocs.yml found
            mkdocs_response = MagicMock()
            mkdocs_response.status_code = 200
            mkdocs_response.json.return_value = {
                "name": "mkdocs.yml",
                "type": "file",
            }

            # Function to simulate 404 responses
            async def mock_get_404(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                response = MagicMock()
                response.status_code = 404
                return response

            # Setup async get responses
            call_count = 0

            async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:  # noqa: ANN401
                nonlocal call_count
                url = args[0]

                # First two calls are for getting repos
                if call_count == 0:
                    call_count += 1
                    return repos_response
                if call_count == 1:
                    call_count += 1
                    return empty_response
                # Next calls are for checking documentation
                if "mkdocs.yml" in url:
                    call_count += 1
                    return mkdocs_response
                call_count += 1
                return await mock_get_404(*args, **kwargs)

            mock_client.get = mock_get

            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Discover repositories
            doc_repos = await aggregator.discover_documentation_repositories()

            # Generate config
            config = await aggregator.generate_mkdocs_config(doc_repos)

        assert len(doc_repos) == 1
        assert doc_repos[0].name == "docs-repo"
        assert doc_repos[0].has_docs is True
        assert doc_repos[0].mkdocs_config == "mkdocs.yml"

        assert len(config["nav_entries"]) == 1
        assert "Docs-Repo" in config["nav_entries"][0]
