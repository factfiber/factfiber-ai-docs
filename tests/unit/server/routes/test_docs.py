# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Test documentation serving endpoints."""

import tempfile
from collections.abc import Callable
from datetime import UTC
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from ff_docs.auth.middleware import get_current_user
from ff_docs.auth.models import GitHubTeam, User, UserSession
from ff_docs.search.security_filter import SearchResponse
from ff_docs.server.main import app


class TestDocsRoutes:
    """Test documentation route endpoints."""

    def setup_method(self) -> None:
        """Set up test client and common test data."""
        self.client = TestClient(app)

        # Create test user data
        self.test_user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            github_id=12345,
        )

        self.test_team = GitHubTeam(
            org="testorg",
            team="developers",
            role="member",
        )

        from datetime import datetime

        self.test_session = UserSession(
            user=self.test_user,
            teams=[self.test_team],
            permissions=["docs:read", "docs:write"],
            session_id="test-session-123",
            expires_at=datetime.now(UTC),
        )

        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.docs_path = Path(self.temp_dir)

    def teardown_method(self) -> None:
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        app.dependency_overrides.clear()

    def _with_auth_user(
        self,
        test_func: Callable[[], None],
        user_session: UserSession | None = None,
    ) -> None:
        """Run test function with authenticated user dependency override."""
        session_to_use = user_session or self.test_session

        def mock_get_current_user() -> UserSession:
            return session_to_use

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            return test_func()
        finally:
            app.dependency_overrides.clear()

    def _with_optional_user(
        self,
        test_func: Callable[[], None],
        user_session: UserSession | None = None,
    ) -> None:
        """Run test function with optional user dependency override."""

        def mock_get_current_user() -> UserSession | None:
            return user_session

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            return test_func()
        finally:
            app.dependency_overrides.clear()

    def test_list_documentation(self) -> None:
        """Test list documentation endpoint."""

        def run_test() -> None:
            response = self.client.get("/docs/")
            assert response.status_code == 200
            data = response.json()
            assert "repositories" in data
            assert isinstance(data["repositories"], list)
            assert "example-repo" in data["repositories"]
            assert "another-repo" in data["repositories"]

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.docs.settings")
    @patch(
        "ff_docs.auth.repository_middleware.RepositoryScopedAuthMiddleware._validate_repository_access"
    )
    def test_serve_repository_docs_success(
        self, mock_validate_access: AsyncMock, mock_settings: Mock
    ) -> None:
        """Test serving repository documentation successfully."""
        # Setup mock settings
        mock_settings.output_dir = self.temp_dir

        # Mock repository access validation to return True
        mock_validate_access.return_value = True

        # Create test HTML file
        repo_path = self.docs_path / "test-repo"
        repo_path.mkdir()
        index_file = repo_path / "index.html"
        index_file.write_text("<html><body>Test Documentation</body></html>")

        response = self.client.get("/docs/repo/test-repo")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    @patch("ff_docs.server.routes.docs.settings")
    @patch(
        "ff_docs.auth.repository_middleware.RepositoryScopedAuthMiddleware._validate_repository_access"
    )
    def test_serve_repository_docs_not_found(
        self, mock_validate_access: AsyncMock, mock_settings: Mock
    ) -> None:
        """Test serving documentation for non-existent repository."""
        mock_settings.output_dir = self.temp_dir
        mock_validate_access.return_value = True

        response = self.client.get("/docs/repo/nonexistent-repo")
        assert response.status_code == 404
        assert "Documentation not found" in response.json()["detail"]

    @patch("ff_docs.server.routes.docs.settings")
    @patch(
        "ff_docs.auth.repository_middleware.RepositoryScopedAuthMiddleware._validate_repository_access"
    )
    def test_serve_repository_static_success(
        self, mock_validate_access: AsyncMock, mock_settings: Mock
    ) -> None:
        """Test serving static files successfully."""
        # Setup mock settings
        mock_settings.output_dir = self.temp_dir
        mock_validate_access.return_value = True

        # Create test static file
        repo_path = self.docs_path / "test-repo"
        repo_path.mkdir()
        static_file = repo_path / "style.css"
        static_file.write_text("body { color: blue; }")

        response = self.client.get("/docs/repo/test-repo/static/style.css")
        assert response.status_code == 200

    @patch("ff_docs.server.routes.docs.settings")
    @patch(
        "ff_docs.auth.repository_middleware.RepositoryScopedAuthMiddleware._validate_repository_access"
    )
    def test_serve_repository_static_not_found(
        self, mock_validate_access: AsyncMock, mock_settings: Mock
    ) -> None:
        """Test serving non-existent static file."""
        mock_settings.output_dir = self.temp_dir
        mock_validate_access.return_value = True

        response = self.client.get(
            "/docs/repo/test-repo/static/nonexistent.css"
        )
        assert response.status_code == 404
        assert "Static file not found" in response.json()["detail"]

    @patch("ff_docs.server.routes.docs.settings")
    @patch(
        "ff_docs.auth.repository_middleware.RepositoryScopedAuthMiddleware._validate_repository_access"
    )
    def test_serve_repository_static_path_traversal_security(
        self, mock_validate_access: AsyncMock, mock_settings: Mock
    ) -> None:
        """Test path traversal security check (line 65)."""
        mock_settings.output_dir = self.temp_dir
        mock_validate_access.return_value = True

        # Create files in repository directory
        repo_path = self.docs_path / "test-repo"
        repo_path.mkdir()

        # Create file outside repository
        outside_path = self.docs_path / "outside-repo"
        outside_path.mkdir()
        secret_file = outside_path / "secret.txt"
        secret_file.write_text("secret content")

        # Create a file in the repo directory that we'll mock to resolve outside
        malicious_file = repo_path / "malicious.txt"
        malicious_file.write_text("this file exists but resolves outside")

        # Mock Path constructor to return objects with custom resolve behavior
        class MockPath(Path):
            def resolve(self, *, strict: bool = False) -> Path:  # type: ignore[override]
                # If this is the static_file_path, return outside directory
                if str(self).endswith("malicious.txt"):
                    return secret_file  # Outside the allowed directory
                return super().resolve(strict=strict)

        with patch("ff_docs.server.routes.docs.Path", MockPath):
            response = self.client.get(
                "/docs/repo/test-repo/static/malicious.txt"
            )
            # Should return 403 Access denied (line 65)
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]

    def test_build_documentation(self) -> None:
        """Test triggering documentation build."""

        def run_test() -> None:
            response = self.client.get("/docs/build")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "Build started" in data["message"]

        self._with_auth_user(run_test)

    def test_build_repository_documentation(self) -> None:
        """Test triggering repository-specific documentation build."""

        def run_test() -> None:
            response = self.client.post("/docs/build/test-repo")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "test-repo" in data["message"]
            assert "Build started" in data["message"]

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.docs.search_with_security")
    def test_search_documentation_success(self, mock_search: AsyncMock) -> None:
        """Test documentation search with valid query."""

        def run_test() -> None:
            # Setup mock search response
            mock_response = SearchResponse(
                query="test query",
                results=[],
                total_results=0,
                filtered_results=0,
                repositories_searched=["repo1"],
                execution_time_ms=10.5,
            )
            mock_search.return_value = mock_response

            response = self.client.get(
                "/docs/search?q=test%20query&repos=repo1&limit=10"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "test query"
            assert data["total_results"] == 0
            assert data["filtered_results"] == 0

            # Verify search was called with correct parameters
            call_args = mock_search.call_args[0]
            search_query = call_args[0]
            assert search_query.query == "test query"
            assert search_query.repositories == ["repo1"]
            assert search_query.limit == 10

        self._with_auth_user(run_test)

    def test_search_documentation_empty_query(self) -> None:
        """Test search with empty query."""

        def run_test() -> None:
            response = self.client.get("/docs/search?q=")
            assert response.status_code == 400
            assert "cannot be empty" in response.json()["detail"]

        self._with_auth_user(run_test)

    def test_search_documentation_whitespace_query(self) -> None:
        """Test search with whitespace-only query."""

        def run_test() -> None:
            response = self.client.get(
                "/docs/search?q=%20%20%20"
            )  # URL encoded spaces
            assert response.status_code == 400
            assert "cannot be empty" in response.json()["detail"]

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.docs.search_with_security")
    def test_search_documentation_with_sections(
        self, mock_search: AsyncMock
    ) -> None:
        """Test search with repositories and sections filters."""

        def run_test() -> None:
            mock_response = SearchResponse(
                query="API",
                results=[],
                total_results=0,
                filtered_results=0,
                repositories_searched=["repo1", "repo2"],
                execution_time_ms=15.0,
            )
            mock_search.return_value = mock_response

            response = self.client.get(
                "/docs/search?q=API&repos=repo1,repo2&sections=api,guide&offset=10"
            )
            assert response.status_code == 200

            # Verify search parameters
            call_args = mock_search.call_args[0]
            search_query = call_args[0]
            assert search_query.query == "API"
            assert search_query.repositories == ["repo1", "repo2"]
            assert search_query.sections == ["api", "guide"]
            assert search_query.offset == 10

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.docs.search_with_security")
    def test_search_documentation_limit_capping(
        self, mock_search: AsyncMock
    ) -> None:
        """Test that search limits are properly capped."""

        def run_test() -> None:
            mock_response = SearchResponse(
                query="test",
                results=[],
                total_results=0,
                filtered_results=0,
                repositories_searched=[],
                execution_time_ms=5.0,
            )
            mock_search.return_value = mock_response

            # Request limit higher than max allowed (100)
            response = self.client.get("/docs/search?q=test&limit=200")
            assert response.status_code == 200

            # Verify limit was capped at 100
            call_args = mock_search.call_args[0]
            search_query = call_args[0]
            assert search_query.limit == 100

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.docs.search_with_security")
    def test_search_documentation_negative_offset(
        self, mock_search: AsyncMock
    ) -> None:
        """Test that negative offsets are handled correctly."""

        def run_test() -> None:
            mock_response = SearchResponse(
                query="test",
                results=[],
                total_results=0,
                filtered_results=0,
                execution_time_ms=10.0,
                repositories_searched=[],
            )
            mock_search.return_value = mock_response

            response = self.client.get("/docs/search?q=test&offset=-5")
            assert response.status_code == 200

            # Verify offset was set to 0
            call_args = mock_search.call_args[0]
            search_query = call_args[0]
            assert search_query.offset == 0

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.docs.search_with_security")
    def test_search_documentation_unauthenticated(
        self, mock_search: AsyncMock
    ) -> None:
        """Test search with unauthenticated user."""

        def run_test() -> None:
            mock_response = SearchResponse(
                query="public search",
                results=[],
                total_results=0,
                filtered_results=0,
                execution_time_ms=10.0,
                repositories_searched=[],
            )
            mock_search.return_value = mock_response

            response = self.client.get("/docs/search?q=public%20search")
            assert response.status_code == 200

            # Verify user was None
            call_args = mock_search.call_args[0]
            user_arg = call_args[1]
            assert user_arg is None

        self._with_optional_user(run_test, None)

    def test_get_search_suggestions_success(self) -> None:
        """Test search suggestions with valid query."""

        def run_test() -> None:
            response = self.client.get("/docs/search/suggestions?q=test")
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "test"
            assert "suggestions" in data
            assert len(data["suggestions"]) <= 5
            # Check that suggestions contain the query prefix
            for suggestion in data["suggestions"]:
                assert "test" in suggestion

        self._with_optional_user(run_test, self.test_session)

    def test_get_search_suggestions_short_query(self) -> None:
        """Test search suggestions with too short query."""

        def run_test() -> None:
            response = self.client.get("/docs/search/suggestions?q=t")
            assert response.status_code == 200
            data = response.json()
            assert data["suggestions"] == []

        self._with_optional_user(run_test, None)

    def test_get_search_suggestions_empty_query(self) -> None:
        """Test search suggestions with empty query."""

        def run_test() -> None:
            response = self.client.get("/docs/search/suggestions?q=")
            assert response.status_code == 200
            data = response.json()
            assert data["suggestions"] == []

        self._with_optional_user(run_test, None)

    def test_get_search_suggestions_unauthenticated(self) -> None:
        """Test search suggestions work for unauthenticated users."""

        def run_test() -> None:
            response = self.client.get("/docs/search/suggestions?q=api")
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "api"
            assert len(data["suggestions"]) > 0

        self._with_optional_user(run_test, None)

    @patch("ff_docs.server.routes.docs.search_with_security")
    def test_search_documentation_empty_repo_filter(
        self, mock_search: AsyncMock
    ) -> None:
        """Test search with empty repository filter."""

        def run_test() -> None:
            mock_response = SearchResponse(
                query="test",
                results=[],
                total_results=0,
                filtered_results=0,
                execution_time_ms=10.0,
                repositories_searched=[],
            )
            mock_search.return_value = mock_response

            # Empty repos parameter should result in empty list
            response = self.client.get("/docs/search?q=test&repos=,,,")
            assert response.status_code == 200

            call_args = mock_search.call_args[0]
            search_query = call_args[0]
            assert search_query.repositories == []

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.docs.search_with_security")
    def test_search_documentation_empty_section_filter(
        self, mock_search: AsyncMock
    ) -> None:
        """Test search with empty section filter."""

        def run_test() -> None:
            mock_response = SearchResponse(
                query="test",
                results=[],
                total_results=0,
                filtered_results=0,
                execution_time_ms=10.0,
                repositories_searched=[],
            )
            mock_search.return_value = mock_response

            # Empty sections parameter should result in empty list
            response = self.client.get("/docs/search?q=test&sections=,,,")
            assert response.status_code == 200

            call_args = mock_search.call_args[0]
            search_query = call_args[0]
            assert search_query.sections == []

        self._with_auth_user(run_test)
