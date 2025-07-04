# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Test CLI commands using click.testing."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from ff_docs.cli import main


class TestCliCommands:
    """Test CLI command functionality."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI runner."""
        return CliRunner()

    def test_main_help(self, runner: CliRunner) -> None:
        """Test main command help."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "FactFiber.ai documentation system CLI" in result.output

    def test_main_version(self, runner: CliRunner) -> None:
        """Test version command."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0

    @patch("subprocess.run")
    def test_serve_command(
        self, mock_subprocess: MagicMock, runner: CliRunner
    ) -> None:
        """Test serve command."""
        result = runner.invoke(main, ["serve"])
        assert result.exit_code == 0
        assert "Starting MkDocs development server" in result.output
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_serve_command_with_options(
        self, mock_subprocess: MagicMock, runner: CliRunner
    ) -> None:
        """Test serve command with options."""
        result = runner.invoke(
            main,
            ["serve", "--host", "0.0.0.0", "--port", "9000", "--reload"],  # noqa: S104
        )
        assert result.exit_code == 0
        # Verify the command was called
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_serve_command_failure(
        self, mock_subprocess: MagicMock, runner: CliRunner
    ) -> None:
        """Test serve command failure handling."""
        import subprocess

        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "mkdocs")
        result = runner.invoke(main, ["serve"])
        assert result.exit_code == 1
        assert "MkDocs server failed to start" in result.output

    @patch("subprocess.run")
    def test_serve_command_keyboard_interrupt(
        self, mock_subprocess: MagicMock, runner: CliRunner
    ) -> None:
        """Test serve command keyboard interrupt handling."""
        mock_subprocess.side_effect = KeyboardInterrupt()
        result = runner.invoke(main, ["serve"])
        assert result.exit_code == 0
        assert "MkDocs server stopped" in result.output

    @patch("uvicorn.run")
    def test_serve_api_command(
        self, mock_uvicorn: MagicMock, runner: CliRunner
    ) -> None:
        """Test serve-api command."""
        result = runner.invoke(main, ["serve-api"])
        assert result.exit_code == 0
        assert "Starting FastAPI server" in result.output
        mock_uvicorn.assert_called_once()

    @patch("uvicorn.run")
    def test_serve_api_command_with_options(
        self, mock_uvicorn: MagicMock, runner: CliRunner
    ) -> None:
        """Test serve-api command with options."""
        result = runner.invoke(
            main,
            ["serve-api", "--host", "127.0.0.1", "--port", "9001", "--reload"],
        )
        assert result.exit_code == 0
        mock_uvicorn.assert_called_once()

    def test_repo_group_help(self, runner: CliRunner) -> None:
        """Test repo group help."""
        result = runner.invoke(main, ["repo", "--help"])
        assert result.exit_code == 0
        assert "Repository management commands" in result.output

    def test_legacy_enroll_command(self, runner: CliRunner) -> None:
        """Test legacy enroll command."""
        result = runner.invoke(main, ["enroll", "https://github.com/org/repo"])
        assert result.exit_code == 0
        assert "This command is deprecated" in result.output

    @patch("subprocess.run")
    def test_build_command_success(
        self, mock_subprocess: MagicMock, runner: CliRunner
    ) -> None:
        """Test build command success."""
        mock_result = MagicMock()
        mock_result.stdout = "Build completed"
        mock_subprocess.return_value = mock_result

        result = runner.invoke(main, ["build"])
        assert result.exit_code == 0
        assert "Building documentation" in result.output
        assert "Documentation build completed successfully" in result.output

    @patch("subprocess.run")
    def test_build_command_with_options(
        self, mock_subprocess: MagicMock, runner: CliRunner
    ) -> None:
        """Test build command with options."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        result = runner.invoke(main, ["build", "--clean", "--strict"])
        assert result.exit_code == 0
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_build_command_failure(
        self, mock_subprocess: MagicMock, runner: CliRunner
    ) -> None:
        """Test build command failure."""
        import subprocess

        mock_error = subprocess.CalledProcessError(1, "mkdocs")
        mock_error.stderr = "Build failed"
        mock_subprocess.side_effect = mock_error

        result = runner.invoke(main, ["build"])
        assert result.exit_code == 1
        assert "Documentation build failed" in result.output

    @patch("ff_docs.aggregator.github_client.RepositoryAggregator")
    def test_repo_discover_command(
        self, mock_aggregator: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo discover command."""
        # Mock the aggregator instance with async method
        mock_instance = MagicMock()
        mock_aggregator.return_value = mock_instance

        # Create mock repository objects that match expected interface
        mock_repo = MagicMock()
        mock_repo.name = "test-repo"
        mock_repo.private = False
        mock_repo.has_docs = True
        mock_repo.docs_path = "docs/"
        mock_repo.description = "Test repository"

        # Mock the async method with AsyncMock
        mock_instance.discover_documentation_repositories = AsyncMock(
            return_value=[mock_repo]
        )

        result = runner.invoke(main, ["repo", "discover"])
        assert result.exit_code == 0
        assert "Found 1 repositories" in result.output

    @patch("ff_docs.aggregator.github_client.RepositoryAggregator")
    def test_repo_discover_command_with_output(
        self, mock_aggregator: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo discover command with output file."""
        mock_instance = MagicMock()
        mock_aggregator.return_value = mock_instance
        mock_instance.discover_documentation_repositories = AsyncMock(
            return_value=[]
        )

        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["repo", "discover", "--output", "repos.json"]
            )
            assert result.exit_code == 0
            assert Path("repos.json").exists()

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_enroll_command(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo enroll command."""
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance
        mock_instance.enroll_repository = AsyncMock(return_value=True)

        result = runner.invoke(main, ["repo", "enroll", "org/test-repo"])
        assert result.exit_code == 0
        assert "Successfully enrolled" in result.output

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_enroll_command_with_section(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo enroll command with section."""
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance
        mock_instance.enroll_repository = AsyncMock(return_value=True)

        result = runner.invoke(
            main, ["repo", "enroll", "org/test-repo", "--section", "Core"]
        )
        assert result.exit_code == 0
        mock_instance.enroll_repository.assert_called_once()

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_enroll_all_command(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo enroll-all command."""
        # Create mock repository objects
        mock_repo1 = MagicMock()
        mock_repo1.name = "repo1"
        mock_repo1.has_docs = True
        mock_repo2 = MagicMock()
        mock_repo2.name = "repo2"
        mock_repo2.has_docs = True

        # Mock enrollment service
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance

        # Mock the aggregator that's accessible through enrollment.aggregator
        mock_aggregator = MagicMock()
        mock_instance.aggregator = mock_aggregator
        mock_aggregator.discover_documentation_repositories = AsyncMock(
            return_value=[mock_repo1, mock_repo2]
        )

        mock_instance.enroll_repository = AsyncMock(return_value=True)
        mock_instance.enroll_all_repositories = AsyncMock(
            return_value={"repo1": True, "repo2": True}
        )

        result = runner.invoke(main, ["repo", "enroll-all"])
        assert result.exit_code == 0
        assert "Successfully enrolled 2 repositories" in result.output

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_enroll_all_command_dry_run(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo enroll-all command with dry run."""
        mock_repo = MagicMock()
        mock_repo.name = "repo1"
        mock_repo.has_docs = True

        # Mock enrollment service
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance

        # Mock the aggregator that's accessible through enrollment.aggregator
        mock_aggregator = MagicMock()
        mock_instance.aggregator = mock_aggregator
        mock_aggregator.discover_documentation_repositories = AsyncMock(
            return_value=[mock_repo]
        )

        result = runner.invoke(main, ["repo", "enroll-all", "--dry-run"])
        assert result.exit_code == 0
        assert "Would enroll" in result.output

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_enroll_all_command_with_failures(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo enroll-all command with some failures."""
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance
        mock_instance.discover_documentation_repositories = AsyncMock(
            return_value=[
                {"name": "org/repo1", "description": "Test repo 1"},
                {"name": "org/repo2", "description": "Test repo 2"},
                {"name": "org/repo3", "description": "Test repo 3"},
            ]
        )
        # Some repositories fail enrollment
        mock_instance.enroll_all_repositories = AsyncMock(
            return_value={
                "org/repo1": True,
                "org/repo2": False,  # Failed
                "org/repo3": True,
            }
        )

        result = runner.invoke(main, ["repo", "enroll-all"])
        assert result.exit_code == 0
        # Should show failed repositories (lines 209-211)
        assert "Failed repositories:" in result.output
        assert "• org/repo2" in result.output
        assert "❌ Failed to enroll 1 repositories" in result.output

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_unenroll_command(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo unenroll command."""
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance
        mock_instance.unenroll_repository.return_value = (
            True  # Sync method returns bool
        )

        result = runner.invoke(main, ["repo", "unenroll", "org/test-repo"])
        assert result.exit_code == 0
        assert "Successfully removed" in result.output

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_list_command(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo list command."""
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance
        # Set return value with correct method name
        mock_instance.list_enrolled_repositories.return_value = [
            {"name": "org/repo1", "import_url": "https://github.com/org/repo1"},
            {"name": "org/repo2", "import_url": "https://github.com/org/repo2"},
        ]

        result = runner.invoke(main, ["repo", "list"])
        assert result.exit_code == 0
        assert "org/repo1" in result.output
        assert "org/repo2" in result.output

    def test_repo_list_command_empty(self, runner: CliRunner) -> None:
        """Test repo list command with no repositories."""
        with patch(
            "ff_docs.aggregator.enrollment.RepositoryEnrollment"
        ) as mock_enrollment:
            mock_instance = MagicMock()
            mock_enrollment.return_value = mock_instance
            # Set empty return value with correct method name
            mock_instance.list_enrolled_repositories.return_value = []

            result = runner.invoke(main, ["repo", "list"])
            assert result.exit_code == 0
            assert "No repositories" in result.output

    @patch("uvicorn.run")
    def test_serve_api_command_error_handling(
        self, mock_uvicorn: MagicMock, runner: CliRunner
    ) -> None:
        """Test serve-api command error handling."""
        mock_uvicorn.side_effect = Exception("Server failed")

        result = runner.invoke(main, ["serve-api"])
        assert result.exit_code == 1

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_enroll_command_error(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo enroll command error handling."""
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance
        mock_instance.enroll_repository = AsyncMock(
            return_value=False
        )  # Failed enrollment

        result = runner.invoke(main, ["repo", "enroll", "org/test-repo"])
        assert (
            result.exit_code == 0
        )  # CLI doesn't exit with error code, just prints failure
        assert "Failed to enroll" in result.output

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_unenroll_command_error(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo unenroll command error handling."""
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance
        mock_instance.unenroll_repository.return_value = (
            False  # Failed unenrollment (sync method)
        )

        result = runner.invoke(main, ["repo", "unenroll", "org/test-repo"])
        assert (
            result.exit_code == 0
        )  # CLI doesn't exit with error code, just prints failure
        assert "Failed to remove" in result.output

    @patch("ff_docs.aggregator.enrollment.RepositoryEnrollment")
    def test_repo_list_command_error(
        self, mock_enrollment: MagicMock, runner: CliRunner
    ) -> None:
        """Test repo list command error handling."""
        mock_instance = MagicMock()
        mock_enrollment.return_value = mock_instance
        mock_instance.list_enrolled_repositories.side_effect = Exception(
            "List failed"
        )  # Correct method name

        result = runner.invoke(main, ["repo", "list"])
        assert result.exit_code != 0  # Should fail with exception
