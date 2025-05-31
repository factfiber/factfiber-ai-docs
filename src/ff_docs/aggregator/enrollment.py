# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Repository enrollment and configuration management."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ff_docs.aggregator.github_client import (
    RepositoryAggregator,
    RepositoryInfo,
)
from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EnrollmentConfig:
    """Configuration for repository enrollment."""

    target_mkdocs_config: Path
    backup_config: bool = True
    auto_commit: bool = False
    validation_enabled: bool = True


class RepositoryEnrollment:
    """Manages enrollment of repositories into documentation system."""

    def __init__(self, config: EnrollmentConfig | None = None) -> None:
        """Initialize repository enrollment manager.

        Args:
            config: Enrollment configuration
        """
        self.config = config or EnrollmentConfig(
            target_mkdocs_config=Path("mkdocs.yml")
        )
        self.aggregator = RepositoryAggregator()
        self.settings = get_settings()

    async def enroll_repository(
        self,
        repository: str | RepositoryInfo,
        section: str | None = None,
    ) -> bool:
        """Enroll a single repository in the documentation system.

        Args:
            repository: Repository name or RepositoryInfo object
            section: Navigation section name (defaults to repository name)

        Returns:
            True if enrollment successful
        """
        if isinstance(repository, str):
            # Discover repository information
            repositories = (
                await self.aggregator.discover_documentation_repositories()
            )
            repo_info = next(
                (r for r in repositories if r.name == repository), None
            )
            if not repo_info:
                logger.error("Repository not found: %s", repository)
                return False
        else:
            repo_info = repository

        if not repo_info.has_docs:
            logger.warning(
                "Repository has no documentation: %s", repo_info.name
            )
            return False

        # Load current MkDocs configuration
        mkdocs_config = self._load_mkdocs_config()

        # Add repository to navigation
        section_name = section or repo_info.name.title()
        import_url = self._build_import_url(repo_info)

        nav_entry = {section_name: f"!import {import_url}"}

        # Find Projects section or create it
        nav = mkdocs_config.get("nav", [])
        projects_section = None

        for item in nav:
            if isinstance(item, dict) and "Projects" in item:
                projects_section = item["Projects"]
                break

        if projects_section is None:
            # Create Projects section
            projects_section = [{"Overview": "projects/index.md"}]
            nav.append({"Projects": projects_section})
            mkdocs_config["nav"] = nav

        # Add repository to Projects section
        projects_section.append(nav_entry)

        # Save updated configuration
        if self.config.backup_config:
            self._backup_config()

        self._save_mkdocs_config(mkdocs_config)

        logger.info("Successfully enrolled repository: %s", repo_info.name)
        return True

    async def enroll_all_repositories(
        self,
        org: str | None = None,
        exclude: list[str] | None = None,
    ) -> dict[str, bool]:
        """Enroll all repositories with documentation from organization.

        Args:
            org: Organization name (defaults to configured org)
            exclude: List of repository names to exclude

        Returns:
            Dictionary mapping repository names to enrollment success
        """
        exclude = exclude or []
        repositories = (
            await self.aggregator.discover_documentation_repositories(org)
        )

        # Filter out excluded repositories
        repositories = [
            repo for repo in repositories if repo.name not in exclude
        ]

        results = {}
        for repo in repositories:
            try:
                success = await self.enroll_repository(repo)
                results[repo.name] = success
            except Exception:
                logger.exception("Failed to enroll %s", repo.name)
                results[repo.name] = False

        successful = sum(1 for success in results.values() if success)
        logger.info(
            "Enrolled %d/%d repositories", successful, len(repositories)
        )

        return results

    def unenroll_repository(self, repository_name: str) -> bool:
        """Remove a repository from the documentation system.

        Args:
            repository_name: Name of repository to remove

        Returns:
            True if removal successful
        """
        mkdocs_config = self._load_mkdocs_config()
        nav = mkdocs_config.get("nav", [])

        # Find and remove repository from navigation
        removed = False
        for item in nav:
            if isinstance(item, dict) and "Projects" in item:
                projects = item["Projects"]
                if isinstance(projects, list):
                    original_length = len(projects)
                    # Remove entries that match repository name
                    projects[:] = [
                        entry
                        for entry in projects
                        if not (
                            isinstance(entry, dict)
                            and any(
                                repository_name.lower() in key.lower()
                                for key in entry
                            )
                        )
                    ]
                    removed = len(projects) < original_length
                break

        if removed:
            if self.config.backup_config:
                self._backup_config()

            self._save_mkdocs_config(mkdocs_config)
            logger.info(
                "Successfully unenrolled repository: %s", repository_name
            )
            return True

        logger.warning(
            "Repository not found in configuration: %s", repository_name
        )
        return False

    def list_enrolled_repositories(self) -> list[dict[str, str]]:
        """List all currently enrolled repositories.

        Returns:
            List of enrolled repository information
        """
        mkdocs_config = self._load_mkdocs_config()
        nav = mkdocs_config.get("nav", [])

        enrolled = []
        for item in nav:
            if isinstance(item, dict) and "Projects" in item:
                projects = item["Projects"]
                if isinstance(projects, list):
                    for entry in projects:
                        if isinstance(entry, dict):
                            for name, value in entry.items():
                                if isinstance(value, str) and value.startswith(
                                    "!import"
                                ):
                                    enrolled.append(
                                        {
                                            "name": name,
                                            "import_url": value.replace(
                                                "!import ", ""
                                            ),
                                        }
                                    )
                break

        return enrolled

    def _load_mkdocs_config(self) -> dict[str, Any]:
        """Load MkDocs configuration file.

        Returns:
            Configuration dictionary
        """
        config_path = self.config.target_mkdocs_config

        if not config_path.exists():
            logger.error("MkDocs config not found: %s", config_path)
            msg = f"MkDocs config not found: {config_path}"
            raise FileNotFoundError(msg)

        # Create a custom YAML loader that handles MkDocs-specific tags
        class MkDocsLoader(yaml.SafeLoader):
            pass

        def construct_python_name(
            loader: Any,  # noqa: ARG001, ANN401
            node: Any,  # noqa: ANN401
        ) -> str:
            """Handle !!python/name: tags by returning a placeholder."""
            return f"!!python/name:{node.value}"

        # Register constructors for specific MkDocs Python name tags
        MkDocsLoader.add_constructor(
            "tag:yaml.org,2002:python/name:material.extensions.emoji.twemoji",
            construct_python_name,
        )
        MkDocsLoader.add_constructor(
            "tag:yaml.org,2002:python/name:material.extensions.emoji.to_svg",
            construct_python_name,
        )
        MkDocsLoader.add_constructor(
            "tag:yaml.org,2002:python/name:pymdownx.superfences.fence_code_format",
            construct_python_name,
        )
        MkDocsLoader.add_constructor(
            "tag:yaml.org,2002:python/name:pymdownx.superfences.fence_div_format",
            construct_python_name,
        )

        # Add a fallback constructor for any remaining python tags
        MkDocsLoader.add_multi_constructor(  # type: ignore[no-untyped-call]
            "tag:yaml.org,2002:python/",
            lambda loader, suffix, node: f"!!python/{suffix}:{node.value}",  # noqa: ARG005
        )

        # Also register for the short form without tag prefix
        MkDocsLoader.add_multi_constructor(  # type: ignore[no-untyped-call]
            "!!python/", construct_python_name
        )

        with config_path.open(encoding="utf-8") as f:
            config = yaml.load(f, Loader=MkDocsLoader)  # noqa: S506

        return config or {}

    def _save_mkdocs_config(self, config: dict[str, Any]) -> None:
        """Save MkDocs configuration file.

        Args:
            config: Configuration dictionary to save
        """
        config_path = self.config.target_mkdocs_config

        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(
                config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
            )

    def _backup_config(self) -> None:
        """Create backup of current MkDocs configuration."""
        config_path = self.config.target_mkdocs_config
        backup_path = config_path.with_suffix(".yml.backup")

        if config_path.exists():
            import shutil

            shutil.copy2(config_path, backup_path)
            logger.debug("Created config backup: %s", backup_path)

    def _build_import_url(self, repo_info: RepositoryInfo) -> str:
        """Build import URL for repository.

        Args:
            repo_info: Repository information

        Returns:
            Formatted import URL
        """
        import_url = f"{repo_info.clone_url}?branch={repo_info.default_branch}"

        if repo_info.docs_path:
            import_url += f"&docs_dir={repo_info.docs_path}*"

        return import_url


class ValidationManager:
    """Validates repository enrollment and configuration."""

    @staticmethod
    def validate_repository_access(repo_info: RepositoryInfo) -> bool:
        """Validate that repository is accessible.

        Args:
            repo_info: Repository information to validate

        Returns:
            True if repository is accessible
        """
        # This would typically test git access or API access
        # For now, assume accessible if we have the info
        return bool(repo_info.clone_url)

    @staticmethod
    def validate_mkdocs_config(config_path: Path) -> bool:
        """Validate MkDocs configuration file.

        Args:
            config_path: Path to MkDocs configuration

        Returns:
            True if configuration is valid
        """
        try:
            with config_path.open(encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # Basic validation - ensure required keys exist
            required_keys = ["site_name", "plugins"]
            for key in required_keys:
                if key not in config:
                    logger.error(
                        "Missing required key in MkDocs config: %s", key
                    )
                    return False
            # All required keys present
            return True  # noqa: TRY300

        except yaml.YAMLError:
            logger.exception("Invalid YAML in MkDocs config")
            return False
        except OSError:
            logger.exception("Error reading MkDocs config file")
            return False


# Helper functions for global access
async def get_enrolled_repositories() -> list[dict[str, Any]]:
    """
    Get list of enrolled repositories.

    Returns:
        List of enrolled repository configurations
    """
    enrollment = RepositoryEnrollment()
    repos = enrollment.list_enrolled_repositories()

    # Convert to expected format with import_url and other metadata
    return [
        {
            "name": repo["name"],
            "section": repo.get("section", "Projects"),
            "import_url": repo["import_url"],
            "config": {},
        }
        for repo in repos
    ]
