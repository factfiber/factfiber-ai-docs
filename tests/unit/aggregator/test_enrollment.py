# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001
# mypy: disable-error-code="method-assign"

"""Unit tests for repository enrollment management."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ff_docs.aggregator.enrollment import (
    EnrollmentConfig,
    RepositoryEnrollment,
    ValidationManager,
    get_enrolled_repositories,
)
from ff_docs.aggregator.github_client import RepositoryInfo


class TestEnrollmentConfig:
    """Test EnrollmentConfig dataclass."""

    def test_enrollment_config_defaults(self) -> None:
        """Test EnrollmentConfig with default values."""
        config = EnrollmentConfig(target_mkdocs_config=Path("mkdocs.yml"))

        assert config.target_mkdocs_config == Path("mkdocs.yml")
        assert config.backup_config is True
        assert config.auto_commit is False
        assert config.validation_enabled is True

    def test_enrollment_config_custom(self) -> None:
        """Test EnrollmentConfig with custom values."""
        config = EnrollmentConfig(
            target_mkdocs_config=Path("custom/mkdocs.yml"),
            backup_config=False,
            auto_commit=True,
            validation_enabled=False,
        )

        assert config.target_mkdocs_config == Path("custom/mkdocs.yml")
        assert config.backup_config is False
        assert config.auto_commit is True
        assert config.validation_enabled is False


class TestRepositoryEnrollment:
    """Test RepositoryEnrollment class."""

    @pytest.fixture
    def enrollment(self) -> RepositoryEnrollment:
        """Create RepositoryEnrollment instance."""
        config = EnrollmentConfig(target_mkdocs_config=Path("test_mkdocs.yml"))
        return RepositoryEnrollment(config)

    @pytest.fixture
    def sample_mkdocs_config(self) -> dict[str, Any]:
        """Create sample MkDocs configuration."""
        return {
            "site_name": "Test Documentation",
            "nav": [
                {"Home": "index.md"},
                {"Projects": [{"Overview": "projects/index.md"}]},
            ],
            "plugins": ["search", "multirepo"],
        }

    @pytest.fixture
    def sample_repo_info(self) -> RepositoryInfo:
        """Create sample repository info."""
        return RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test repository",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
            has_docs=True,
            docs_path="docs/",
        )

    def test_enrollment_initialization_default(self) -> None:
        """Test RepositoryEnrollment initialization with defaults."""
        enrollment = RepositoryEnrollment()

        assert enrollment.config.target_mkdocs_config == Path("mkdocs.yml")
        assert enrollment.aggregator is not None
        assert enrollment.settings is not None

    def test_enrollment_initialization_custom(self) -> None:
        """Test RepositoryEnrollment initialization with custom config."""
        config = EnrollmentConfig(target_mkdocs_config=Path("custom.yml"))
        enrollment = RepositoryEnrollment(config)

        assert enrollment.config == config

    @pytest.mark.asyncio
    async def test_enroll_repository_success_with_string(
        self,
        enrollment: RepositoryEnrollment,
        sample_mkdocs_config: dict[str, Any],
        sample_repo_info: RepositoryInfo,
    ) -> None:
        """Test enrolling repository by name."""
        # Mock aggregator
        enrollment.aggregator.discover_documentation_repositories = AsyncMock(
            return_value=[sample_repo_info]
        )

        # Mock file operations
        enrollment._load_mkdocs_config = MagicMock(
            return_value=sample_mkdocs_config
        )
        enrollment._save_mkdocs_config = MagicMock()
        enrollment._backup_config = MagicMock()

        # Enroll repository
        result = await enrollment.enroll_repository("test-repo")

        assert result is True
        enrollment._save_mkdocs_config.assert_called_once()
        enrollment._backup_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_enroll_repository_success_with_info(
        self,
        enrollment: RepositoryEnrollment,
        sample_mkdocs_config: dict[str, Any],
        sample_repo_info: RepositoryInfo,
    ) -> None:
        """Test enrolling repository with RepositoryInfo."""
        # Mock file operations
        enrollment._load_mkdocs_config = MagicMock(
            return_value=sample_mkdocs_config
        )
        enrollment._save_mkdocs_config = MagicMock()
        enrollment._backup_config = MagicMock()

        # Enroll repository
        result = await enrollment.enroll_repository(sample_repo_info)

        assert result is True
        enrollment._save_mkdocs_config.assert_called_once()

        # Check that repository was added to config
        saved_config = enrollment._save_mkdocs_config.call_args[0][0]
        projects = saved_config["nav"][1]["Projects"]
        assert len(projects) == 2  # Overview + new repo
        assert "Test-Repo" in projects[1]

    @pytest.mark.asyncio
    async def test_enroll_repository_not_found(
        self, enrollment: RepositoryEnrollment
    ) -> None:
        """Test enrolling non-existent repository."""
        # Mock aggregator to return empty list
        enrollment.aggregator.discover_documentation_repositories = AsyncMock(
            return_value=[]
        )

        result = await enrollment.enroll_repository("non-existent")

        assert result is False

    @pytest.mark.asyncio
    async def test_enroll_repository_no_docs(
        self,
        enrollment: RepositoryEnrollment,
        sample_repo_info: RepositoryInfo,
    ) -> None:
        """Test enrolling repository without documentation."""
        sample_repo_info.has_docs = False

        result = await enrollment.enroll_repository(sample_repo_info)

        assert result is False

    @pytest.mark.asyncio
    async def test_enroll_repository_custom_section(
        self,
        enrollment: RepositoryEnrollment,
        sample_mkdocs_config: dict[str, Any],
        sample_repo_info: RepositoryInfo,
    ) -> None:
        """Test enrolling repository with custom section name."""
        # Mock file operations
        enrollment._load_mkdocs_config = MagicMock(
            return_value=sample_mkdocs_config
        )
        enrollment._save_mkdocs_config = MagicMock()
        enrollment._backup_config = MagicMock()

        # Enroll repository with custom section
        result = await enrollment.enroll_repository(
            sample_repo_info, section="Custom Section"
        )

        assert result is True

        # Check custom section name was used
        saved_config = enrollment._save_mkdocs_config.call_args[0][0]
        projects = saved_config["nav"][1]["Projects"]
        assert "Custom Section" in projects[1]

    @pytest.mark.asyncio
    async def test_enroll_repository_no_projects_section(
        self,
        enrollment: RepositoryEnrollment,
        sample_repo_info: RepositoryInfo,
    ) -> None:
        """Test enrolling when Projects section doesn't exist."""
        # Config without Projects section
        config = {
            "site_name": "Test",
            "nav": [{"Home": "index.md"}],
        }

        enrollment._load_mkdocs_config = MagicMock(return_value=config)
        enrollment._save_mkdocs_config = MagicMock()
        enrollment._backup_config = MagicMock()

        result = await enrollment.enroll_repository(sample_repo_info)

        assert result is True

        # Check Projects section was created
        saved_config = enrollment._save_mkdocs_config.call_args[0][0]
        assert len(saved_config["nav"]) == 2
        assert "Projects" in saved_config["nav"][1]

    @pytest.mark.asyncio
    async def test_enroll_repository_no_backup(
        self,
        enrollment: RepositoryEnrollment,
        sample_mkdocs_config: dict[str, Any],
        sample_repo_info: RepositoryInfo,
    ) -> None:
        """Test enrolling without creating backup."""
        enrollment.config.backup_config = False

        enrollment._load_mkdocs_config = MagicMock(
            return_value=sample_mkdocs_config
        )
        enrollment._save_mkdocs_config = MagicMock()
        enrollment._backup_config = MagicMock()

        result = await enrollment.enroll_repository(sample_repo_info)

        assert result is True
        enrollment._backup_config.assert_not_called()

    @pytest.mark.asyncio
    async def test_enroll_all_repositories_success(
        self, enrollment: RepositoryEnrollment
    ) -> None:
        """Test enrolling all repositories."""
        repos = [
            RepositoryInfo(
                name=f"repo-{i}",
                full_name=f"org/repo-{i}",
                description=f"Repository {i}",
                clone_url=f"https://github.com/org/repo-{i}.git",
                ssh_url=f"git@github.com:org/repo-{i}.git",
                default_branch="main",
                private=False,
                has_docs=True,
            )
            for i in range(3)
        ]

        enrollment.aggregator.discover_documentation_repositories = AsyncMock(
            return_value=repos
        )
        enrollment.enroll_repository = AsyncMock(return_value=True)

        results = await enrollment.enroll_all_repositories()

        assert len(results) == 3
        assert all(results.values())
        assert enrollment.enroll_repository.call_count == 3

    @pytest.mark.asyncio
    async def test_enroll_all_repositories_with_exclude(
        self, enrollment: RepositoryEnrollment
    ) -> None:
        """Test enrolling all repositories with exclusions."""
        repos = [
            RepositoryInfo(
                name="repo-1",
                full_name="org/repo-1",
                description="Repository 1",
                clone_url="https://github.com/org/repo-1.git",
                ssh_url="git@github.com:org/repo-1.git",
                default_branch="main",
                private=False,
                has_docs=True,
            ),
            RepositoryInfo(
                name="repo-2",
                full_name="org/repo-2",
                description="Repository 2",
                clone_url="https://github.com/org/repo-2.git",
                ssh_url="git@github.com:org/repo-2.git",
                default_branch="main",
                private=False,
                has_docs=True,
            ),
        ]

        enrollment.aggregator.discover_documentation_repositories = AsyncMock(
            return_value=repos
        )
        enrollment.enroll_repository = AsyncMock(return_value=True)

        results = await enrollment.enroll_all_repositories(exclude=["repo-2"])

        assert len(results) == 1
        assert "repo-1" in results
        assert "repo-2" not in results

    @pytest.mark.asyncio
    async def test_enroll_all_repositories_with_failures(
        self, enrollment: RepositoryEnrollment
    ) -> None:
        """Test enrolling all repositories with some failures."""
        repos = [
            RepositoryInfo(
                name=f"repo-{i}",
                full_name=f"org/repo-{i}",
                description=f"Repository {i}",
                clone_url=f"https://github.com/org/repo-{i}.git",
                ssh_url=f"git@github.com:org/repo-{i}.git",
                default_branch="main",
                private=False,
                has_docs=True,
            )
            for i in range(3)
        ]

        enrollment.aggregator.discover_documentation_repositories = AsyncMock(
            return_value=repos
        )

        # Mock enrollment to fail for second repo
        async def mock_enroll(repo: RepositoryInfo) -> bool:
            if repo.name == "repo-1":
                raise RuntimeError("Enrollment error")
            return True

        enrollment.enroll_repository = AsyncMock(side_effect=mock_enroll)

        results = await enrollment.enroll_all_repositories()

        assert results["repo-0"] is True
        assert results["repo-1"] is False
        assert results["repo-2"] is True

    def test_unenroll_repository_success(
        self,
        enrollment: RepositoryEnrollment,
        sample_mkdocs_config: dict[str, Any],
    ) -> None:
        """Test unenrolling repository successfully."""
        # Add a test repo to config
        sample_mkdocs_config["nav"][1]["Projects"].append(
            {"Test-Repo": "!import https://github.com/org/test-repo.git"}
        )

        enrollment._load_mkdocs_config = MagicMock(
            return_value=sample_mkdocs_config
        )
        enrollment._save_mkdocs_config = MagicMock()
        enrollment._backup_config = MagicMock()

        result = enrollment.unenroll_repository("test-repo")

        assert result is True
        enrollment._save_mkdocs_config.assert_called_once()

        # Check repo was removed
        saved_config = enrollment._save_mkdocs_config.call_args[0][0]
        projects = saved_config["nav"][1]["Projects"]
        assert len(projects) == 1  # Only Overview remains

    def test_unenroll_repository_not_found(
        self,
        enrollment: RepositoryEnrollment,
        sample_mkdocs_config: dict[str, Any],
    ) -> None:
        """Test unenrolling non-existent repository."""
        enrollment._load_mkdocs_config = MagicMock(
            return_value=sample_mkdocs_config
        )

        result = enrollment.unenroll_repository("non-existent")

        assert result is False

    def test_list_enrolled_repositories(
        self,
        enrollment: RepositoryEnrollment,
        sample_mkdocs_config: dict[str, Any],
    ) -> None:
        """Test listing enrolled repositories."""
        # Add test repos
        sample_mkdocs_config["nav"][1]["Projects"].extend(
            [
                {"Repo-1": "!import https://github.com/org/repo-1.git"},
                {"Repo-2": "!import https://github.com/org/repo-2.git"},
            ]
        )

        enrollment._load_mkdocs_config = MagicMock(
            return_value=sample_mkdocs_config
        )

        repos = enrollment.list_enrolled_repositories()

        assert len(repos) == 2
        assert repos[0]["name"] == "Repo-1"
        assert repos[0]["import_url"] == "https://github.com/org/repo-1.git"
        assert repos[1]["name"] == "Repo-2"

    def test_list_enrolled_repositories_no_projects(
        self, enrollment: RepositoryEnrollment
    ) -> None:
        """Test listing enrolled repositories with no Projects section."""
        config = {"site_name": "Test", "nav": [{"Home": "index.md"}]}

        enrollment._load_mkdocs_config = MagicMock(return_value=config)

        repos = enrollment.list_enrolled_repositories()

        assert repos == []

    def test_load_mkdocs_config_success(
        self, enrollment: RepositoryEnrollment, tmp_path: Path
    ) -> None:
        """Test loading MkDocs configuration successfully."""
        config_path = tmp_path / "mkdocs.yml"
        config_data = """
site_name: Test Site
nav:
  - Home: index.md
plugins:
  - search
"""
        config_path.write_text(config_data)

        enrollment.config.target_mkdocs_config = config_path

        config = enrollment._load_mkdocs_config()

        assert config["site_name"] == "Test Site"
        assert len(config["nav"]) == 1

    def test_load_mkdocs_config_not_found(
        self, enrollment: RepositoryEnrollment
    ) -> None:
        """Test loading non-existent MkDocs configuration."""
        enrollment.config.target_mkdocs_config = Path("/non/existent/path.yml")

        with pytest.raises(FileNotFoundError):
            enrollment._load_mkdocs_config()

    def test_load_mkdocs_config_with_python_tags(
        self, enrollment: RepositoryEnrollment, tmp_path: Path
    ) -> None:
        """Test loading MkDocs config with Python tags."""
        config_path = tmp_path / "mkdocs.yml"
        config_data = """
site_name: Test Site
markdown_extensions:
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
"""
        config_path.write_text(config_data)

        enrollment.config.target_mkdocs_config = config_path

        config = enrollment._load_mkdocs_config()

        assert config["site_name"] == "Test Site"
        assert "pymdownx.emoji" in str(config["markdown_extensions"])

    def test_save_mkdocs_config(
        self, enrollment: RepositoryEnrollment, tmp_path: Path
    ) -> None:
        """Test saving MkDocs configuration."""
        config_path = tmp_path / "mkdocs.yml"
        enrollment.config.target_mkdocs_config = config_path

        config = {
            "site_name": "Test Site",
            "nav": [{"Home": "index.md"}],
        }

        enrollment._save_mkdocs_config(config)

        assert config_path.exists()
        saved_content = config_path.read_text()
        assert "site_name: Test Site" in saved_content

    def test_backup_config(
        self, enrollment: RepositoryEnrollment, tmp_path: Path
    ) -> None:
        """Test backing up configuration."""
        config_path = tmp_path / "mkdocs.yml"
        config_path.write_text("original content")

        enrollment.config.target_mkdocs_config = config_path

        enrollment._backup_config()

        backup_path = tmp_path / "mkdocs.yml.backup"
        assert backup_path.exists()
        assert backup_path.read_text() == "original content"

    def test_backup_config_no_original(
        self, enrollment: RepositoryEnrollment, tmp_path: Path
    ) -> None:
        """Test backing up when no original config exists."""
        enrollment.config.target_mkdocs_config = tmp_path / "mkdocs.yml"

        # Should not raise
        enrollment._backup_config()

    def test_build_import_url_with_docs_path(
        self, enrollment: RepositoryEnrollment, sample_repo_info: RepositoryInfo
    ) -> None:
        """Test building import URL with docs path."""
        url = enrollment._build_import_url(sample_repo_info)

        assert (
            url
            == "https://github.com/org/test-repo.git?branch=main&docs_dir=docs/*"
        )

    def test_build_import_url_without_docs_path(
        self, enrollment: RepositoryEnrollment, sample_repo_info: RepositoryInfo
    ) -> None:
        """Test building import URL without docs path."""
        sample_repo_info.docs_path = None

        url = enrollment._build_import_url(sample_repo_info)

        assert url == "https://github.com/org/test-repo.git?branch=main"


class TestValidationManager:
    """Test ValidationManager class."""

    def test_validate_repository_access_valid(self) -> None:
        """Test validating repository access with valid repo."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="https://github.com/org/test-repo.git",
            ssh_url="git@github.com:org/test-repo.git",
            default_branch="main",
            private=False,
        )

        result = ValidationManager.validate_repository_access(repo_info)

        assert result is True

    def test_validate_repository_access_no_clone_url(self) -> None:
        """Test validating repository access without clone URL."""
        repo_info = RepositoryInfo(
            name="test-repo",
            full_name="org/test-repo",
            description="Test",
            clone_url="",
            ssh_url="",
            default_branch="main",
            private=False,
        )

        result = ValidationManager.validate_repository_access(repo_info)

        assert result is False

    def test_validate_mkdocs_config_valid(self, tmp_path: Path) -> None:
        """Test validating valid MkDocs configuration."""
        config_path = tmp_path / "mkdocs.yml"
        config_data = """
site_name: Test Site
plugins:
  - search
  - multirepo
"""
        config_path.write_text(config_data)

        result = ValidationManager.validate_mkdocs_config(config_path)

        assert result is True

    def test_validate_mkdocs_config_missing_keys(self, tmp_path: Path) -> None:
        """Test validating MkDocs config with missing keys."""
        config_path = tmp_path / "mkdocs.yml"
        config_data = """
site_name: Test Site
# Missing plugins key
"""
        config_path.write_text(config_data)

        result = ValidationManager.validate_mkdocs_config(config_path)

        assert result is False

    def test_validate_mkdocs_config_invalid_yaml(self, tmp_path: Path) -> None:
        """Test validating MkDocs config with invalid YAML."""
        config_path = tmp_path / "mkdocs.yml"
        config_data = """
site_name: Test Site
  invalid: yaml indentation
plugins
"""
        config_path.write_text(config_data)

        result = ValidationManager.validate_mkdocs_config(config_path)

        assert result is False

    def test_validate_mkdocs_config_file_error(self) -> None:
        """Test validating non-existent MkDocs config."""
        result = ValidationManager.validate_mkdocs_config(
            Path("/non/existent/file.yml")
        )

        assert result is False


class TestHelperFunctions:
    """Test module-level helper functions."""

    @pytest.mark.asyncio
    async def test_get_enrolled_repositories(self) -> None:
        """Test get_enrolled_repositories helper."""
        with patch(
            "ff_docs.aggregator.enrollment.RepositoryEnrollment"
        ) as mock_enrollment_class:
            mock_enrollment = MagicMock()
            mock_enrollment.list_enrolled_repositories.return_value = [
                {
                    "name": "Test-Repo",
                    "import_url": "https://github.com/org/test-repo.git",
                },
                {
                    "name": "Another-Repo",
                    "import_url": "https://github.com/org/another-repo.git",
                },
            ]
            mock_enrollment_class.return_value = mock_enrollment

            repos = await get_enrolled_repositories()

        assert len(repos) == 2
        assert repos[0]["name"] == "Test-Repo"
        assert repos[0]["section"] == "Projects"
        assert repos[0]["import_url"] == "https://github.com/org/test-repo.git"
        assert repos[0]["config"] == {}
