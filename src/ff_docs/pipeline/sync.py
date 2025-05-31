# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""
Content synchronization service for repository documentation.

This module handles cloning, updating, and processing repository content
for the unified documentation system. It manages git operations, content
extraction, and validation of documentation changes.
"""

import logging
import shutil
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
import git
from pydantic import BaseModel

from ff_docs.aggregator.enrollment import get_enrolled_repositories
from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)


class SyncStatus(BaseModel):
    """Status information for a sync operation."""

    repository: str
    commit_sha: str | None = None
    status: str  # 'started', 'cloning', 'processing', 'completed', 'failed'
    message: str = ""
    docs_found: int = 0
    files_processed: int = 0
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class ContentSyncService:
    """
    Service for synchronizing repository documentation content.

    This service handles the process of cloning or updating repositories,
    extracting documentation content, and preparing it for the unified
    documentation build process.
    """

    def __init__(self) -> None:
        """Initialize the content sync service."""
        self.settings = get_settings()
        self.temp_dir = Path(self.settings.mkdocs.temp_dir)
        self.sync_status: dict[str, SyncStatus] = {}

    async def sync_repository(
        self, repo_full_name: str, commit_sha: str | None = None
    ) -> SyncStatus:
        """
        Synchronize a single repository's documentation content.

        Args:
            repo_full_name: Full repository name (org/repo)
            commit_sha: Specific commit to sync (optional)

        Returns:
            SyncStatus with operation details
        """
        import datetime

        status = SyncStatus(
            repository=repo_full_name,
            commit_sha=commit_sha,
            status="started",
            started_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        self.sync_status[repo_full_name] = status

        try:
            # Check if repository is enrolled
            enrolled_repos = await get_enrolled_repositories()
            if repo_full_name not in [r["name"] for r in enrolled_repos]:
                status.status = "failed"
                status.error = f"Repository '{repo_full_name}' not enrolled"
                return status

            # Create working directory
            repo_dir = await self._prepare_workspace(repo_full_name)

            # Clone or update repository
            status.status = "cloning"
            status.message = "Cloning repository content"
            await self._clone_or_update_repo(
                repo_full_name, repo_dir, commit_sha
            )

            # Process documentation content
            status.status = "processing"
            status.message = "Processing documentation files"
            docs_info = await self._process_documentation(
                repo_dir, repo_full_name
            )

            # Generate API documentation
            status.message = "Generating API documentation"
            api_docs_info = await self._generate_api_documentation(repo_dir)

            status.docs_found = docs_info["docs_found"]
            status.files_processed = docs_info[
                "files_processed"
            ] + api_docs_info.get("docs_generated", 0)

            # Complete sync
            status.status = "completed"
            status.message = "Documentation sync completed successfully"
            status.completed_at = datetime.datetime.now(
                datetime.UTC
            ).isoformat()

            logger.info(
                "Sync completed: repo=%s, docs=%d, files=%d",
                repo_full_name,
                status.docs_found,
                status.files_processed,
            )

        except (OSError, ValueError, RuntimeError) as e:
            status.status = "failed"
            status.error = str(e)
            status.completed_at = datetime.datetime.now(
                datetime.UTC
            ).isoformat()

            logger.exception("Sync failed for repository %s", repo_full_name)

        return status

    async def _prepare_workspace(self, repo_full_name: str) -> Path:
        """
        Prepare workspace directory for repository content.

        Args:
            repo_full_name: Full repository name

        Returns:
            Path to workspace directory
        """
        # Create base temp directory if it doesn't exist
        await aiofiles.os.makedirs(self.temp_dir, exist_ok=True)

        # Create repository-specific directory
        repo_slug = repo_full_name.replace("/", "-")
        repo_dir = self.temp_dir / f"repo-{repo_slug}"

        # Clean existing directory if present
        if repo_dir.exists():
            shutil.rmtree(repo_dir)

        await aiofiles.os.makedirs(repo_dir, exist_ok=True)

        return repo_dir

    async def _clone_or_update_repo(
        self, repo_full_name: str, repo_dir: Path, commit_sha: str | None = None
    ) -> None:
        """
        Clone or update repository content.

        Args:
            repo_full_name: Full repository name
            repo_dir: Directory for repository content
            commit_sha: Specific commit to checkout
        """
        repo_url = f"https://github.com/{repo_full_name}.git"

        # Add authentication if token available
        if self.settings.github.token:
            repo_url = f"https://{self.settings.github.token}@github.com/{repo_full_name}.git"

        # Clone repository
        repo = git.Repo.clone_from(repo_url, repo_dir, depth=1)

        # Checkout specific commit if provided
        if commit_sha:
            try:
                repo.git.fetch("origin", commit_sha)
                repo.git.checkout(commit_sha)
            except git.GitCommandError as e:
                logger.warning(
                    "Could not checkout commit %s for %s: %s",
                    commit_sha,
                    repo_full_name,
                    e,
                )

    async def _process_documentation(
        self, repo_dir: Path, repo_name: str | None = None
    ) -> dict[str, Any]:
        """
        Process documentation content from repository.

        Args:
            repo_dir: Repository directory path
            repo_name: Repository name for link rewriting

        Returns:
            Dictionary with processing statistics
        """
        docs_found = 0
        files_processed = 0

        # Common documentation directories and files
        doc_patterns = [
            "docs/**/*",
            "documentation/**/*",
            "*.md",
            "*.rst",
            "mkdocs.yml",
            "mkdocs.yaml",
            ".factfiber-docs.yml",
            ".factfiber-docs.yaml",
        ]

        for pattern in doc_patterns:
            for file_path in repo_dir.glob(pattern):
                if file_path.is_file():
                    docs_found += 1

                    # Process specific file types
                    if file_path.suffix.lower() in [".md", ".rst"]:
                        await self._process_markdown_file(file_path, repo_name)
                        files_processed += 1
                    elif file_path.name.startswith("mkdocs."):
                        await self._process_mkdocs_config(file_path)
                        files_processed += 1

        return {"docs_found": docs_found, "files_processed": files_processed}

    async def _process_markdown_file(
        self, file_path: Path, repo_name: str | None = None
    ) -> None:
        """
        Process individual markdown file for link rewriting.

        Args:
            file_path: Path to markdown file
            repo_name: Repository name for link rewriting context
        """
        if not repo_name:
            return

        try:
            # Read original content
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()

            # Apply link rewriting
            from ff_docs.pipeline.rewriter import create_link_rewriter_for_repos

            enrolled_repos = await get_enrolled_repositories()
            rewriter = create_link_rewriter_for_repos(enrolled_repos)

            # Get relative path within repository
            repo_root = file_path.parent
            while (
                repo_root.parent != repo_root
                and not (repo_root / ".git").exists()
            ):
                repo_root = repo_root.parent

            relative_path = file_path.relative_to(repo_root)

            # Rewrite content
            rewritten_content = rewriter.rewrite_file_content(
                content, repo_name, str(relative_path)
            )

            # Write rewritten content if changed
            if rewritten_content != content:
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(rewritten_content)

                logger.debug("Applied link rewriting to %s", file_path)

        except (OSError, ValueError) as e:
            logger.warning(
                "Failed to process markdown file %s: %s", file_path, e
            )

    async def _process_mkdocs_config(self, file_path: Path) -> None:  # noqa: ARG002
        """
        Process MkDocs configuration file.

        Args:
            file_path: Path to mkdocs config file
        """
        # TODO: Extract navigation structure for unified config
        # This will be part of the unified config generation
        return

    async def _generate_api_documentation(
        self, repo_dir: Path
    ) -> dict[str, Any]:
        """
        Generate API documentation for the repository.

        Args:
            repo_dir: Repository directory path

        Returns:
            API documentation generation results
        """
        try:
            from ff_docs.pipeline.pdoc_integration import generate_api_docs

            result = await generate_api_docs(repo_dir)

            if result.get("enabled") and result.get("docs_generated", 0) > 0:
                logger.info(
                    "Generated API docs: %d packages",
                    result.get("docs_generated", 0),
                )

        except (ImportError, OSError, ValueError) as e:
            logger.warning("Failed to generate API documentation: %s", e)
            return {"enabled": False, "error": str(e), "docs_generated": 0}
        else:
            return result

    def get_sync_status(self, repo_full_name: str) -> SyncStatus | None:
        """
        Get sync status for a repository.

        Args:
            repo_full_name: Full repository name

        Returns:
            SyncStatus if found, None otherwise
        """
        return self.sync_status.get(repo_full_name)

    def get_all_sync_status(self) -> dict[str, SyncStatus]:
        """
        Get sync status for all repositories.

        Returns:
            Dictionary of repository names to sync status
        """
        return self.sync_status.copy()


# Global service instance
_content_sync_service: ContentSyncService | None = None


def get_content_sync_service() -> ContentSyncService:
    """Get the global content sync service instance."""
    global _content_sync_service  # noqa: PLW0603
    if _content_sync_service is None:
        _content_sync_service = ContentSyncService()
    return _content_sync_service


async def trigger_docs_sync(
    repo_full_name: str, commit_sha: str | None = None
) -> SyncStatus:
    """
    Trigger documentation synchronization for a repository.

    Args:
        repo_full_name: Full repository name
        commit_sha: Specific commit to sync

    Returns:
        SyncStatus with operation details
    """
    service = get_content_sync_service()
    return await service.sync_repository(repo_full_name, commit_sha)
