# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Test repository management endpoints."""

from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from ff_docs.auth.middleware import get_current_user, require_permission
from ff_docs.auth.models import GitHubTeam, User, UserSession
from ff_docs.server.main import app


class TestReposRoutes:
    """Test repository management route endpoints."""

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

        self.test_session = UserSession(
            user=self.test_user,
            teams=[self.test_team],
            permissions=["docs:read", "docs:write", "repos:manage"],
            session_id="test-session-123",
            expires_at=datetime.now(UTC),
        )

    def teardown_method(self) -> None:
        """Clean up dependency overrides."""
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

        def mock_require_permission(
            permissions: list[str],
        ) -> Callable[[], UserSession]:
            def dependency() -> UserSession:
                return session_to_use

            return dependency

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[require_permission] = mock_require_permission

        try:
            return test_func()
        finally:
            app.dependency_overrides.clear()

    @patch("ff_docs.aggregator.github_client.GitHubClient")
    def test_get_configuration(self, mock_github_client_class: Mock) -> None:
        """Test get configuration endpoint."""
        # Setup mock GitHub client
        mock_github_client = Mock()
        mock_github_client_class.return_value = mock_github_client
        mock_github_client.is_configured.return_value = True
        mock_github_client.settings.github.org = "test-org"

        response = self.client.get("/repos/config")
        assert response.status_code == 200
        data = response.json()
        assert data["github_configured"] is True
        assert data["github_org"] == "test-org"
        assert data["service"] == "ff-docs-repository-api"

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_list_repositories_success(
        self, mock_enrollment_class: Mock
    ) -> None:
        """Test listing repositories successfully."""
        # Setup mock enrollment
        mock_enrollment = Mock()
        mock_enrollment_class.return_value = mock_enrollment
        mock_enrollment.list_enrolled_repositories.return_value = [
            {"name": "repo1", "import_url": "https://github.com/org/repo1"},
            {"name": "repo2", "import_url": "https://github.com/org/repo2"},
        ]

        response = self.client.get("/repos/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["repositories"]) == 2
        assert data["repositories"][0]["name"] == "repo1"
        assert (
            data["repositories"][0]["import_url"]
            == "https://github.com/org/repo1"
        )

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_list_repositories_error(self, mock_enrollment_class: Mock) -> None:
        """Test listing repositories with error."""
        # Setup mock to raise exception
        mock_enrollment_class.side_effect = Exception("Database error")

        response = self.client.get("/repos/")
        assert response.status_code == 500
        assert "Failed to list repositories" in response.json()["detail"]

    @patch("ff_docs.server.routes.repos.RepositoryAggregator")
    def test_discover_repositories_success(
        self, mock_aggregator_class: AsyncMock
    ) -> None:
        """Test discovering repositories successfully."""

        def run_test() -> None:
            # Create mock repository objects
            mock_repo1 = Mock()
            mock_repo1.name = "repo1"
            mock_repo1.full_name = "org/repo1"
            mock_repo1.description = "Test repository 1"
            mock_repo1.private = False
            mock_repo1.has_docs = True
            mock_repo1.docs_path = "docs/"
            mock_repo1.clone_url = "https://github.com/org/repo1.git"

            mock_repo2 = Mock()
            mock_repo2.name = "repo2"
            mock_repo2.full_name = "org/repo2"
            mock_repo2.description = None
            mock_repo2.private = True
            mock_repo2.has_docs = False
            mock_repo2.docs_path = None
            mock_repo2.clone_url = "https://github.com/org/repo2.git"

            # Setup mock aggregator
            mock_aggregator = AsyncMock()
            mock_aggregator_class.return_value = mock_aggregator
            mock_aggregator.discover_documentation_repositories.return_value = [
                mock_repo1,
                mock_repo2,
            ]

            response = self.client.get("/repos/discover?org=test-org")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2
            assert data["organization"] == "test-org"
            assert len(data["repositories"]) == 2

            # Check first repository
            repo1_data = data["repositories"][0]
            assert repo1_data["name"] == "repo1"
            assert repo1_data["full_name"] == "org/repo1"
            assert repo1_data["description"] == "Test repository 1"
            assert repo1_data["private"] is False
            assert repo1_data["has_docs"] is True

            # Check second repository
            repo2_data = data["repositories"][1]
            assert repo2_data["name"] == "repo2"
            assert repo2_data["description"] is None
            assert repo2_data["private"] is True
            assert repo2_data["has_docs"] is False

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryAggregator")
    def test_discover_repositories_value_error(
        self, mock_aggregator_class: AsyncMock
    ) -> None:
        """Test discovering repositories with GitHub token not configured."""

        def run_test() -> None:
            # Setup mock to raise ValueError (GitHub token not configured)
            mock_aggregator = AsyncMock()
            mock_aggregator_class.return_value = mock_aggregator
            mock_aggregator.discover_documentation_repositories.side_effect = (
                ValueError("GitHub token not configured")
            )

            response = self.client.get("/repos/discover")
            assert response.status_code == 400
            assert "GitHub token not configured" in response.json()["detail"]

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryAggregator")
    def test_discover_repositories_server_error(
        self, mock_aggregator_class: AsyncMock
    ) -> None:
        """Test discovering repositories with server error."""

        def run_test() -> None:
            # Setup mock to raise general exception
            mock_aggregator = AsyncMock()
            mock_aggregator_class.return_value = mock_aggregator
            mock_aggregator.discover_documentation_repositories.side_effect = (
                Exception("API error")
            )

            response = self.client.get("/repos/discover")
            assert response.status_code == 500
            assert (
                "Failed to discover repositories" in response.json()["detail"]
            )

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_enroll_repository_success(
        self, mock_enrollment_class: AsyncMock
    ) -> None:
        """Test enrolling repository successfully."""

        def run_test() -> None:
            # Setup mock enrollment
            mock_enrollment = AsyncMock()
            mock_enrollment_class.return_value = mock_enrollment
            mock_enrollment.enroll_repository.return_value = True

            request_data = {
                "repository": "org/test-repo",
                "section": "projects",
            }

            response = self.client.post("/repos/enroll", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Successfully enrolled" in data["message"]
            assert data["repository"] == "org/test-repo"

            # Verify enrollment was called correctly
            mock_enrollment.enroll_repository.assert_called_once_with(
                repository="org/test-repo", section="projects"
            )

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_enroll_repository_failure(
        self, mock_enrollment_class: AsyncMock
    ) -> None:
        """Test enrolling repository with failure."""

        def run_test() -> None:
            # Setup mock enrollment to return False
            mock_enrollment = AsyncMock()
            mock_enrollment_class.return_value = mock_enrollment
            mock_enrollment.enroll_repository.return_value = False

            request_data = {"repository": "org/test-repo", "section": None}

            response = self.client.post("/repos/enroll", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Failed to enroll" in data["message"]
            assert data["repository"] == "org/test-repo"

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_enroll_repository_error(
        self, mock_enrollment_class: AsyncMock
    ) -> None:
        """Test enrolling repository with error."""

        def run_test() -> None:
            # Setup mock to raise exception
            mock_enrollment_class.side_effect = Exception(
                "Database connection failed"
            )

            request_data = {"repository": "org/test-repo"}

            response = self.client.post("/repos/enroll", json=request_data)
            assert response.status_code == 500
            assert "Failed to enroll repository" in response.json()["detail"]

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_unenroll_repository_success(
        self, mock_enrollment_class: Mock
    ) -> None:
        """Test unenrolling repository successfully."""

        def run_test() -> None:
            # Setup mock enrollment
            mock_enrollment = Mock()
            mock_enrollment_class.return_value = mock_enrollment
            mock_enrollment.unenroll_repository.return_value = True

            request_data = {"repository_name": "org/test-repo"}

            response = self.client.request(
                "DELETE", "/repos/unenroll", json=request_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Successfully unenrolled" in data["message"]
            assert data["repository"] == "org/test-repo"

            # Verify unenrollment was called correctly
            mock_enrollment.unenroll_repository.assert_called_once_with(
                "org/test-repo"
            )

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_unenroll_repository_not_found(
        self, mock_enrollment_class: Mock
    ) -> None:
        """Test unenrolling repository that doesn't exist."""

        def run_test() -> None:
            # Setup mock enrollment to return False (not found)
            mock_enrollment = Mock()
            mock_enrollment_class.return_value = mock_enrollment
            mock_enrollment.unenroll_repository.return_value = False

            request_data = {"repository_name": "org/nonexistent-repo"}

            response = self.client.request(
                "DELETE", "/repos/unenroll", json=request_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Repository not found" in data["message"]
            assert data["repository"] == "org/nonexistent-repo"

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_unenroll_repository_error(
        self, mock_enrollment_class: Mock
    ) -> None:
        """Test unenrolling repository with error."""

        def run_test() -> None:
            # Setup mock to raise exception
            mock_enrollment_class.side_effect = Exception("Database error")

            request_data = {"repository_name": "org/test-repo"}

            response = self.client.request(
                "DELETE", "/repos/unenroll", json=request_data
            )
            assert response.status_code == 500
            assert "Failed to unenroll repository" in response.json()["detail"]

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_enroll_all_repositories_success(
        self, mock_enrollment_class: AsyncMock
    ) -> None:
        """Test enrolling all repositories successfully."""

        def run_test() -> None:
            # Setup mock enrollment
            mock_enrollment = AsyncMock()
            mock_enrollment_class.return_value = mock_enrollment
            mock_enrollment.enroll_all_repositories.return_value = {
                "repo1": True,
                "repo2": True,
                "repo3": False,
            }

            response = self.client.post("/repos/enroll-all?org=test-org")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total"] == 3
            assert len(data["successful"]) == 2
            assert len(data["failed"]) == 1
            assert "repo1" in data["successful"]
            assert "repo2" in data["successful"]
            assert "repo3" in data["failed"]
            assert "2/3 repositories" in data["message"]

            # Verify enrollment was called correctly
            mock_enrollment.enroll_all_repositories.assert_called_once_with(
                "test-org", []
            )

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_enroll_all_repositories_with_exclude(
        self, mock_enrollment_class: AsyncMock
    ) -> None:
        """Test enrolling all repositories with exclusions."""

        def run_test() -> None:
            # Setup mock enrollment
            mock_enrollment = AsyncMock()
            mock_enrollment_class.return_value = mock_enrollment
            mock_enrollment.enroll_all_repositories.return_value = {
                "repo1": True,
                "repo2": True,
            }

            response = self.client.post(
                "/repos/enroll-all?org=test-org&exclude=excluded-repo&exclude=another-excluded"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total"] == 2

            # Verify enrollment was called with exclusions
            mock_enrollment.enroll_all_repositories.assert_called_once_with(
                "test-org", ["excluded-repo", "another-excluded"]
            )

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_enroll_all_repositories_value_error(
        self, mock_enrollment_class: AsyncMock
    ) -> None:
        """Test enrolling all repositories with GitHub token not configured."""

        def run_test() -> None:
            # Setup mock to raise ValueError
            mock_enrollment = AsyncMock()
            mock_enrollment_class.return_value = mock_enrollment
            mock_enrollment.enroll_all_repositories.side_effect = ValueError(
                "GitHub token not configured"
            )

            response = self.client.post("/repos/enroll-all")
            assert response.status_code == 400
            assert "GitHub token not configured" in response.json()["detail"]

        self._with_auth_user(run_test)

    @patch("ff_docs.server.routes.repos.RepositoryEnrollment")
    def test_enroll_all_repositories_server_error(
        self, mock_enrollment_class: AsyncMock
    ) -> None:
        """Test enrolling all repositories with server error."""

        def run_test() -> None:
            # Setup mock to raise general exception
            mock_enrollment = AsyncMock()
            mock_enrollment_class.return_value = mock_enrollment
            mock_enrollment.enroll_all_repositories.side_effect = Exception(
                "API error"
            )

            response = self.client.post("/repos/enroll-all")
            assert response.status_code == 500
            assert (
                "Failed to enroll all repositories" in response.json()["detail"]
            )

        self._with_auth_user(run_test)

    def test_enroll_repository_validation_error(self) -> None:
        """Test enrolling repository with invalid request data."""

        def run_test() -> None:
            # Missing required repository field
            request_data = {"section": "projects"}

            response = self.client.post("/repos/enroll", json=request_data)
            assert response.status_code == 422  # Validation error

        self._with_auth_user(run_test)

    def test_unenroll_repository_validation_error(self) -> None:
        """Test unenrolling repository with invalid request data."""

        def run_test() -> None:
            # Missing required repository_name field
            request_data: dict[str, str] = {}

            response = self.client.request(
                "DELETE", "/repos/unenroll", json=request_data
            )
            assert response.status_code == 422  # Validation error

        self._with_auth_user(run_test)

    def test_discover_repositories_authentication_required(self) -> None:
        """Test that discover repositories requires authentication."""
        response = self.client.get("/repos/discover")
        assert response.status_code == 401  # Unauthorized

    def test_enroll_repository_permission_required(self) -> None:
        """Test that enroll repository requires repos:manage permission."""
        request_data = {"repository": "org/test-repo"}
        response = self.client.post("/repos/enroll", json=request_data)
        assert response.status_code == 401  # Unauthorized

    def test_unenroll_repository_permission_required(self) -> None:
        """Test that unenroll repository requires repos:manage permission."""
        request_data = {"repository_name": "org/test-repo"}
        response = self.client.request(
            "DELETE", "/repos/unenroll", json=request_data
        )
        assert response.status_code == 401  # Unauthorized

    def test_enroll_all_repositories_permission_required(self) -> None:
        """Test that enroll all repos requires repos:manage permission."""
        response = self.client.post("/repos/enroll-all")
        assert response.status_code == 401  # Unauthorized
