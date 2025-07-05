# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001

"""Unit tests for search security filter module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from ff_docs.auth.models import GitHubTeam, User, UserSession
from ff_docs.search.security_filter import (
    SearchQuery,
    SearchResponse,
    SearchResult,
    SecureSearchEngine,
    get_search_engine,
    search_with_security,
)


class TestSearchModels:
    """Test search-related Pydantic models."""

    def test_search_result_model(self) -> None:
        """Test SearchResult model creation and validation."""
        result = SearchResult(
            title="Test Result",
            url="/test/url",
            content="Test content",
            repository="test-repo",
            section="Guide",
            score=0.95,
            metadata={"type": "doc"},
        )

        assert result.title == "Test Result"
        assert result.url == "/test/url"
        assert result.content == "Test content"
        assert result.repository == "test-repo"
        assert result.section == "Guide"
        assert result.score == 0.95
        assert result.metadata == {"type": "doc"}

    def test_search_result_defaults(self) -> None:
        """Test SearchResult model with default values."""
        result = SearchResult(
            title="Test",
            url="/test",
            content="Content",
            repository="repo",
        )

        assert result.section is None
        assert result.score == 0.0
        assert result.metadata == {}

    def test_search_query_model(self) -> None:
        """Test SearchQuery model creation and validation."""
        query = SearchQuery(
            query="test query",
            repositories=["repo1", "repo2"],
            sections=["Guide", "API"],
            limit=25,
            offset=10,
        )

        assert query.query == "test query"
        assert query.repositories == ["repo1", "repo2"]
        assert query.sections == ["Guide", "API"]
        assert query.limit == 25
        assert query.offset == 10

    def test_search_query_defaults(self) -> None:
        """Test SearchQuery model with default values."""
        query = SearchQuery(query="test")

        assert query.query == "test"
        assert query.repositories == []
        assert query.sections == []
        assert query.limit == 50
        assert query.offset == 0

    def test_search_response_model(self) -> None:
        """Test SearchResponse model creation and validation."""
        result = SearchResult(
            title="Test",
            url="/test",
            content="Content",
            repository="repo",
        )

        response = SearchResponse(
            query="test query",
            results=[result],
            total_results=10,
            filtered_results=5,
            repositories_searched=["repo1", "repo2"],
            execution_time_ms=12.5,
        )

        assert response.query == "test query"
        assert len(response.results) == 1
        assert response.results[0] == result
        assert response.total_results == 10
        assert response.filtered_results == 5
        assert response.repositories_searched == ["repo1", "repo2"]
        assert response.execution_time_ms == 12.5


class TestSecureSearchEngine:
    """Test SecureSearchEngine class."""

    @pytest.fixture
    def engine(self) -> SecureSearchEngine:
        """Create a SecureSearchEngine instance."""
        return SecureSearchEngine()

    @pytest.fixture
    def user_session(self) -> UserSession:
        """Create a test user session."""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            github_id=123456,
        )

        team = GitHubTeam(
            org="test-org",
            team="test-team",
            role="member",
        )

        return UserSession(
            user=user,
            teams=[team],
            permissions=["docs:read"],
            session_id="test-session-id",
            expires_at=datetime.now(UTC),
            access_token="test-token",  # noqa: S106
        )

    @pytest.fixture
    def search_query(self) -> SearchQuery:
        """Create a test search query."""
        return SearchQuery(query="test search")

    def test_engine_initialization(self, engine: SecureSearchEngine) -> None:
        """Test SecureSearchEngine initialization."""
        assert engine.permission_checker is not None

    @pytest.mark.asyncio
    async def test_search_anonymous_user(
        self, engine: SecureSearchEngine, search_query: SearchQuery
    ) -> None:
        """Test search with anonymous user returns no results."""
        response = await engine.search(search_query, user_session=None)

        assert response.query == "test search"
        assert response.results == []
        assert response.total_results == 0
        assert response.filtered_results == 0
        assert response.repositories_searched == []
        assert response.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_search_with_user_no_repos(
        self,
        engine: SecureSearchEngine,
        search_query: SearchQuery,
        user_session: UserSession,
    ) -> None:
        """Test search when user has no accessible repositories."""
        with patch(
            "ff_docs.aggregator.enrollment.get_enrolled_repositories",
            return_value=[],
        ):
            response = await engine.search(search_query, user_session)

        assert response.results == []
        assert response.total_results == 0
        assert response.filtered_results == 0
        assert response.repositories_searched == []

    @pytest.mark.asyncio
    async def test_search_with_accessible_repos(
        self,
        engine: SecureSearchEngine,
        search_query: SearchQuery,
        user_session: UserSession,
    ) -> None:
        """Test search with accessible repositories."""
        mock_repos = [
            {"name": "repo1", "url": "https://github.com/org/repo1"},
            {"name": "repo2", "url": "https://github.com/org/repo2"},
        ]

        with (
            patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories",
                return_value=mock_repos,
            ),
            patch.object(
                engine.permission_checker,
                "check_repository_access",
                AsyncMock(return_value=True),
            ),
        ):
            response = await engine.search(search_query, user_session)

            assert response.query == "test search"
            assert len(response.results) > 0
            assert response.total_results > 0
            assert response.filtered_results > 0
            assert response.repositories_searched == ["repo1", "repo2"]
            assert response.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_search_with_specific_repos(
        self,
        engine: SecureSearchEngine,
        user_session: UserSession,
    ) -> None:
        """Test search with specific repository filter."""
        query = SearchQuery(query="test", repositories=["repo1", "repo3"])
        mock_repos = [
            {"name": "repo1", "url": "https://github.com/org/repo1"},
            {"name": "repo2", "url": "https://github.com/org/repo2"},
            {"name": "repo3", "url": "https://github.com/org/repo3"},
        ]

        with (
            patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories",
                return_value=mock_repos,
            ),
            patch.object(
                engine.permission_checker,
                "check_repository_access",
                AsyncMock(return_value=True),
            ),
        ):
            response = await engine.search(query, user_session)

            # Should only search requested repos
            assert set(response.repositories_searched) == {"repo1", "repo3"}

    @pytest.mark.asyncio
    async def test_search_with_permission_denied(
        self,
        engine: SecureSearchEngine,
        search_query: SearchQuery,
        user_session: UserSession,
    ) -> None:
        """Test search when user lacks permissions for some repos."""
        mock_repos = [
            {"name": "repo1", "url": "https://github.com/org/repo1"},
            {"name": "repo2", "url": "https://github.com/org/repo2"},
        ]

        with patch(
            "ff_docs.aggregator.enrollment.get_enrolled_repositories",
            return_value=mock_repos,
        ):
            # Mock permission checker to deny access to repo2
            async def mock_check_access(
                username: str, repo: str, token: str, action: str
            ) -> bool:
                return repo == "repo1"

            with patch.object(
                engine.permission_checker,
                "check_repository_access",
                AsyncMock(side_effect=mock_check_access),
            ):
                response = await engine.search(search_query, user_session)

                # Should only include accessible repo
                assert response.repositories_searched == ["repo1"]

    @pytest.mark.asyncio
    async def test_search_with_permission_check_error(
        self,
        engine: SecureSearchEngine,
        search_query: SearchQuery,
        user_session: UserSession,
    ) -> None:
        """Test search handles permission check errors gracefully."""
        mock_repos = [
            {"name": "repo1", "url": "https://github.com/org/repo1"},
            {"name": "repo2", "url": "https://github.com/org/repo2"},
        ]

        with patch(
            "ff_docs.aggregator.enrollment.get_enrolled_repositories",
            return_value=mock_repos,
        ):
            # Mock permission checker to raise error for repo2
            async def mock_check_access(
                username: str, repo: str, token: str, action: str
            ) -> bool:
                if repo == "repo2":
                    msg = "Permission check failed"
                    raise ValueError(msg)
                return True

            with patch.object(
                engine.permission_checker,
                "check_repository_access",
                AsyncMock(side_effect=mock_check_access),
            ):
                response = await engine.search(search_query, user_session)

                # Should only include repo1 (repo2 failed)
                assert response.repositories_searched == ["repo1"]

    @pytest.mark.asyncio
    async def test_get_accessible_repositories_anonymous(
        self, engine: SecureSearchEngine
    ) -> None:
        """Test _get_accessible_repositories with anonymous user."""
        repos = await engine._get_accessible_repositories(None, [])
        assert repos == []

    @pytest.mark.asyncio
    async def test_get_accessible_repositories_with_filter(
        self, engine: SecureSearchEngine, user_session: UserSession
    ) -> None:
        """Test _get_accessible_repositories with repository filter."""
        mock_repos = [
            {"name": "repo1", "url": "https://github.com/org/repo1"},
            {"name": "repo2", "url": "https://github.com/org/repo2"},
            {"name": "repo3", "url": "https://github.com/org/repo3"},
        ]

        with (
            patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories",
                return_value=mock_repos,
            ),
            patch.object(
                engine.permission_checker,
                "check_repository_access",
                AsyncMock(return_value=True),
            ),
        ):
            repos = await engine._get_accessible_repositories(
                user_session, ["repo1", "repo3"]
            )

            # Should only check requested repos
            assert set(repos) == {"repo1", "repo3"}

    @pytest.mark.asyncio
    async def test_perform_search(self, engine: SecureSearchEngine) -> None:
        """Test _perform_search generates mock results."""
        query = SearchQuery(query="test")
        accessible_repos = ["repo1", "repo2", "repo3", "repo4"]

        results = await engine._perform_search(query, accessible_repos)

        # Should generate results for first 3 repos
        assert len(results) == 6  # 2 results per repo, 3 repos
        assert all(isinstance(r, SearchResult) for r in results)

        # Check results are sorted by score
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # Check repository distribution
        repo_counts: dict[str, int] = {}
        for result in results:
            repo_counts[result.repository] = (
                repo_counts.get(result.repository, 0) + 1
            )
        assert repo_counts == {"repo1": 2, "repo2": 2, "repo3": 2}

    @pytest.mark.asyncio
    async def test_filter_results_by_access_anonymous(
        self, engine: SecureSearchEngine
    ) -> None:
        """Test _filter_results_by_access with anonymous user."""
        results = [
            SearchResult(
                title="Test",
                url="/test",
                content="Content",
                repository="repo1",
            )
        ]

        filtered = await engine._filter_results_by_access(
            results, None, ["repo1"]
        )
        assert filtered == []

    @pytest.mark.asyncio
    async def test_filter_results_by_access_with_user(
        self, engine: SecureSearchEngine, user_session: UserSession
    ) -> None:
        """Test _filter_results_by_access filters correctly."""
        results = [
            SearchResult(
                title="Result 1",
                url="/test1",
                content="Content 1",
                repository="repo1",
            ),
            SearchResult(
                title="Result 2",
                url="/test2",
                content="Content 2",
                repository="repo2",
            ),
            SearchResult(
                title="Result 3",
                url="/test3",
                content="Content 3",
                repository="repo3",
            ),
        ]

        accessible_repos = ["repo1", "repo3"]

        filtered = await engine._filter_results_by_access(
            results, user_session, accessible_repos
        )

        assert len(filtered) == 2
        assert filtered[0].repository == "repo1"
        assert filtered[1].repository == "repo3"

    def test_paginate_results(self, engine: SecureSearchEngine) -> None:
        """Test _paginate_results applies pagination correctly."""
        results = [
            SearchResult(
                title=f"Result {i}",
                url=f"/test{i}",
                content=f"Content {i}",
                repository="repo",
            )
            for i in range(10)
        ]

        # Test basic pagination
        paginated = engine._paginate_results(results, 0, 5)
        assert len(paginated) == 5
        assert paginated[0].title == "Result 0"
        assert paginated[4].title == "Result 4"

        # Test offset
        paginated = engine._paginate_results(results, 3, 5)
        assert len(paginated) == 5
        assert paginated[0].title == "Result 3"
        assert paginated[4].title == "Result 7"

        # Test edge cases
        paginated = engine._paginate_results(results, 8, 5)
        assert len(paginated) == 2  # Only 2 results left

        # Test negative offset
        paginated = engine._paginate_results(results, -5, 5)
        assert len(paginated) == 5
        assert paginated[0].title == "Result 0"  # Clamps to 0

        # Test beyond end
        paginated = engine._paginate_results(results, 20, 5)
        assert len(paginated) == 0


class TestGlobalFunctions:
    """Test module-level global functions."""

    def test_get_search_engine_singleton(self) -> None:
        """Test get_search_engine returns singleton instance."""
        # Clear any existing instance
        import ff_docs.search.security_filter

        ff_docs.search.security_filter._search_engine = None

        engine1 = get_search_engine()
        engine2 = get_search_engine()

        assert engine1 is engine2
        assert isinstance(engine1, SecureSearchEngine)

    @pytest.mark.asyncio
    async def test_search_with_security(self) -> None:
        """Test search_with_security convenience function."""
        query = SearchQuery(query="test")
        user = User(
            username="testuser",
            email="test@example.com",
            github_id=123,
        )

        user_session = UserSession(
            user=user,
            teams=[],
            permissions=[],
            session_id="test-session",
            expires_at=datetime.now(UTC),
            access_token="token",  # noqa: S106
        )

        mock_response = SearchResponse(
            query="test",
            results=[],
            total_results=0,
            filtered_results=0,
            repositories_searched=[],
            execution_time_ms=1.0,
        )

        with patch(
            "ff_docs.search.security_filter.SecureSearchEngine.search",
            return_value=mock_response,
        ) as mock_search:
            response = await search_with_security(query, user_session)

        assert response == mock_response
        mock_search.assert_called_once_with(query, user_session)

    @pytest.mark.asyncio
    async def test_search_with_security_anonymous(self) -> None:
        """Test search_with_security with anonymous user."""
        query = SearchQuery(query="test")

        with patch(
            "ff_docs.search.security_filter.SecureSearchEngine.search"
        ) as mock_search:
            mock_search.return_value = SearchResponse(
                query="test",
                results=[],
                total_results=0,
                filtered_results=0,
                repositories_searched=[],
                execution_time_ms=1.0,
            )

            await search_with_security(query, None)

        mock_search.assert_called_once_with(query, None)


class TestSearchIntegration:
    """Integration tests for search functionality."""

    @pytest.mark.asyncio
    async def test_full_search_flow(self) -> None:
        """Test complete search flow with mocked dependencies."""
        engine = SecureSearchEngine()
        user = User(
            username="testuser",
            email="test@example.com",
            github_id=12345,
        )

        team = GitHubTeam(
            org="test-org",
            team="test-team",
            role="member",
        )

        user_session = UserSession(
            user=user,
            teams=[team],
            permissions=["docs:read"],
            session_id="test-session-flow",
            expires_at=datetime.now(UTC),
            access_token="test-token",  # noqa: S106
        )

        query = SearchQuery(
            query="kubernetes",
            repositories=["infra", "backend"],
            limit=10,
            offset=0,
        )

        mock_repos = [
            {"name": "infra", "url": "https://github.com/org/infra"},
            {"name": "backend", "url": "https://github.com/org/backend"},
            {"name": "frontend", "url": "https://github.com/org/frontend"},
        ]

        with patch(
            "ff_docs.aggregator.enrollment.get_enrolled_repositories",
            return_value=mock_repos,
        ):
            # User has access to infra but not backend
            async def mock_check_access(
                username: str, repo: str, token: str, action: str
            ) -> bool:
                return repo == "infra"

            with patch.object(
                engine.permission_checker,
                "check_repository_access",
                AsyncMock(side_effect=mock_check_access),
            ):
                response = await engine.search(query, user_session)

                # Verify response structure
                assert response.query == "kubernetes"
                assert response.repositories_searched == ["infra"]
                assert len(response.results) == 2  # 2 results from infra
                assert all(r.repository == "infra" for r in response.results)
                assert response.total_results == 2
                assert response.filtered_results == 2
                assert response.execution_time_ms > 0

        # Verify result content
        for result in response.results:
            assert "kubernetes" in result.title.lower()
            assert "kubernetes" in result.content.lower()
            assert result.url.startswith("/projects/infra/")

    @pytest.mark.asyncio
    async def test_search_pagination_integration(self) -> None:
        """Test search with pagination across multiple pages."""
        engine = SecureSearchEngine()
        user = User(
            username="testuser",
            email="test@example.com",
            github_id=12345,
        )

        team = GitHubTeam(
            org="test-org",
            team="test-team",
            role="member",
        )

        user_session = UserSession(
            user=user,
            teams=[team],
            permissions=["docs:read"],
            session_id="test-session-page",
            expires_at=datetime.now(UTC),
            access_token="test-token",  # noqa: S106
        )

        # Create search query for first page
        query_page1 = SearchQuery(query="api", limit=2, offset=0)

        mock_repos = [
            {"name": f"repo{i}", "url": f"https://github.com/org/repo{i}"}
            for i in range(1, 4)
        ]

        with (
            patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories",
                return_value=mock_repos,
            ),
            patch.object(
                engine.permission_checker,
                "check_repository_access",
                AsyncMock(return_value=True),
            ),
        ):
            # Get first page
            response1 = await engine.search(query_page1, user_session)

            # Get second page
            query_page2 = SearchQuery(query="api", limit=2, offset=2)
            response2 = await engine.search(query_page2, user_session)

            # Verify pagination
            assert len(response1.results) == 2
            assert len(response2.results) == 2

        # Verify no overlap
        results1_ids = {(r.title, r.repository) for r in response1.results}
        results2_ids = {(r.title, r.repository) for r in response2.results}
        assert len(results1_ids & results2_ids) == 0  # No intersection
