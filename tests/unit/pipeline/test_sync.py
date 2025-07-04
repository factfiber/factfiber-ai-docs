# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001

"""Unit tests for content synchronization service."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ff_docs.pipeline.sync import (
    ContentSyncService,
    SyncStatus,
    trigger_docs_sync,
)


class TestSyncStatus:
    """Test SyncStatus model."""

    def test_sync_status_creation(self) -> None:
        """Test creating SyncStatus with all fields."""
        status = SyncStatus(
            repository="org/test-repo",
            commit_sha="abc123",
            status="completed",
            message="Sync successful",
            docs_found=10,
            files_processed=8,
            error=None,
            started_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T00:05:00Z",
        )

        assert status.repository == "org/test-repo"
        assert status.commit_sha == "abc123"
        assert status.status == "completed"
        assert status.message == "Sync successful"
        assert status.docs_found == 10
        assert status.files_processed == 8
        assert status.error is None

    def test_sync_status_defaults(self) -> None:
        """Test SyncStatus with default values."""
        status = SyncStatus(
            repository="org/test-repo",
            status="started",
        )

        assert status.repository == "org/test-repo"
        assert status.commit_sha is None
        assert status.status == "started"
        assert status.message == ""
        assert status.docs_found == 0
        assert status.files_processed == 0
        assert status.error is None


class TestContentSyncService:
    """Test ContentSyncService."""

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings."""
        settings = Mock()
        settings.mkdocs.temp_dir = "/tmp/test"  # noqa: S108
        settings.github.token = "test-token"  # noqa: S105
        return settings

    @pytest.fixture
    def sync_service(self, mock_settings: Mock) -> ContentSyncService:
        """Create ContentSyncService instance."""
        with patch(
            "ff_docs.pipeline.sync.get_settings", return_value=mock_settings
        ):
            return ContentSyncService()

    @pytest.mark.asyncio
    async def test_sync_repository_success(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test successful repository synchronization."""
        # Mock dependencies
        with patch(
            "ff_docs.pipeline.sync.get_enrolled_repositories"
        ) as mock_get_enrolled:
            mock_get_enrolled.return_value = [
                {
                    "name": "org/test-repo",
                    "url": "https://github.com/org/test-repo",
                }
            ]

            with patch.object(
                sync_service, "_prepare_workspace"
            ) as mock_prepare:
                mock_prepare.return_value = Path("/tmp/test/repo-org-test-repo")  # noqa: S108

                with (
                    patch.object(
                        sync_service, "_clone_or_update_repo"
                    ) as mock_clone,
                    patch.object(
                        sync_service, "_process_documentation"
                    ) as mock_process,
                ):
                    mock_process.return_value = {
                        "docs_found": 5,
                        "files_processed": 3,
                    }

                    with patch.object(
                        sync_service, "_generate_api_documentation"
                    ) as mock_api:
                        mock_api.return_value = {
                            "enabled": True,
                            "docs_generated": 2,
                        }

                        # Execute sync
                        status = await sync_service.sync_repository(
                            "org/test-repo", "abc123"
                        )

                        # Verify results
                        assert status.repository == "org/test-repo"
                        assert status.commit_sha == "abc123"
                        assert status.status == "completed"
                        assert status.docs_found == 5
                        assert (
                            status.files_processed == 5
                        )  # 3 + 2 from API docs
                        assert status.error is None

                        # Verify method calls
                        mock_get_enrolled.assert_called_once()
                        mock_prepare.assert_called_once_with("org/test-repo")
                        mock_clone.assert_called_once()
                        mock_process.assert_called_once()
                        mock_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_repository_not_enrolled(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test sync fails for non-enrolled repository."""
        with patch(
            "ff_docs.pipeline.sync.get_enrolled_repositories"
        ) as mock_get_enrolled:
            mock_get_enrolled.return_value = []

            status = await sync_service.sync_repository("org/unknown-repo")

            assert status.status == "failed"
            assert status.error == "Repository 'org/unknown-repo' not enrolled"

    @pytest.mark.asyncio
    async def test_sync_repository_exception(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test sync handles exceptions gracefully."""
        with patch(
            "ff_docs.pipeline.sync.get_enrolled_repositories"
        ) as mock_get_enrolled:
            mock_get_enrolled.return_value = [
                {
                    "name": "org/test-repo",
                    "url": "https://github.com/org/test-repo",
                }
            ]

            with patch.object(
                sync_service, "_prepare_workspace"
            ) as mock_prepare:
                mock_prepare.side_effect = OSError("Permission denied")

                status = await sync_service.sync_repository("org/test-repo")

                assert status.status == "failed"
                assert status.error == "Permission denied"

    @pytest.mark.asyncio
    async def test_prepare_workspace(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test workspace preparation."""
        with (
            patch("aiofiles.os.makedirs") as mock_makedirs,
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            repo_dir = await sync_service._prepare_workspace("org/test-repo")

            assert str(repo_dir) == "/tmp/test/repo-org-test-repo"  # noqa: S108
            mock_makedirs.assert_called()
            mock_rmtree.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_workspace_new_dir(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test workspace preparation for new directory."""
        with (
            patch("aiofiles.os.makedirs") as mock_makedirs,
            patch("pathlib.Path.exists", return_value=False),
        ):
            repo_dir = await sync_service._prepare_workspace("org/test-repo")

            assert str(repo_dir) == "/tmp/test/repo-org-test-repo"  # noqa: S108
            # makedirs called twice - once for temp_dir, once for repo_dir
            assert mock_makedirs.call_count == 2

    @pytest.mark.asyncio
    async def test_clone_or_update_repo(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test repository cloning."""
        mock_repo = Mock()

        with patch("git.Repo.clone_from", return_value=mock_repo) as mock_clone:
            await sync_service._clone_or_update_repo(
                "org/test-repo",
                Path("/tmp/repo"),  # noqa: S108
                "abc123",
            )

            mock_clone.assert_called_once_with(
                "https://test-token@github.com/org/test-repo.git",
                Path("/tmp/repo"),  # noqa: S108
                depth=1,
            )
            mock_repo.git.fetch.assert_called_once_with("origin", "abc123")
            mock_repo.git.checkout.assert_called_once_with("abc123")

    @pytest.mark.asyncio
    async def test_clone_or_update_repo_no_commit(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test repository cloning without specific commit."""
        with patch("git.Repo.clone_from") as mock_clone:
            await sync_service._clone_or_update_repo(
                "org/test-repo",
                Path("/tmp/repo"),  # noqa: S108
                None,
            )

            mock_clone.assert_called_once()
            # Should not attempt to checkout specific commit
            mock_repo = mock_clone.return_value
            mock_repo.git.fetch.assert_not_called()
            mock_repo.git.checkout.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_documentation(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test documentation processing."""
        repo_dir = Path("/tmp/repo")  # noqa: S108

        # Mock file system

        with patch.object(Path, "glob") as mock_glob:
            # Set up glob to return mock Path objects
            mock_md_files: list[Mock] = [Mock(spec=Path), Mock(spec=Path)]
            mock_readme: Mock = Mock(spec=Path)
            mock_mkdocs: Mock = Mock(spec=Path)

            def glob_side_effect(pattern: str) -> list[Path]:
                if pattern == "docs/**/*":
                    return mock_md_files  # type: ignore[return-value]
                if pattern == "*.md":
                    return [mock_readme]
                if pattern == "mkdocs.yml":
                    return [mock_mkdocs]
                return []

            mock_glob.side_effect = glob_side_effect

            # Configure mock files
            for mock_file in mock_md_files:
                mock_file.is_file.return_value = True
                mock_file.suffix = ".md"
                mock_file.name = "guide.md"

            mock_readme.is_file.return_value = True
            mock_readme.suffix = ".md"
            mock_readme.name = "README.md"

            mock_mkdocs.is_file.return_value = True
            mock_mkdocs.suffix = ".yml"
            mock_mkdocs.name = "mkdocs.yml"

            with (
                patch.object(
                    sync_service, "_process_markdown_file"
                ) as mock_process_md,
                patch.object(
                    sync_service, "_process_mkdocs_config"
                ) as mock_process_config,
            ):
                result = await sync_service._process_documentation(
                    repo_dir, "org/test-repo"
                )

            assert result["docs_found"] == 4
            assert result["files_processed"] == 4
            assert mock_process_md.call_count == 3  # 3 markdown files
            mock_process_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_markdown_file(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test markdown file processing with link rewriting."""
        file_path = Path("/tmp/repo/docs/guide.md")  # noqa: S108
        content = "Check out the [API docs](../api/reference.md)"
        rewritten = (
            "Check out the [API docs](/projects/test-repo/api/reference/)"
        )

        with patch("aiofiles.open", create=True) as mock_open:
            # Mock file reading
            mock_file_read = AsyncMock()
            mock_file_read.read.return_value = content

            # Mock file writing
            mock_file_write = AsyncMock()
            mock_file_write.write = AsyncMock()

            # Configure context manager behavior
            mock_open.return_value.__aenter__ = AsyncMock(
                side_effect=[mock_file_read, mock_file_write]
            )
            mock_open.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch(
                "ff_docs.pipeline.sync.get_enrolled_repositories"
            ) as mock_get_enrolled:
                mock_get_enrolled.return_value = [{"name": "org/test-repo"}]

                with patch(
                    "ff_docs.pipeline.rewriter.create_link_rewriter_for_repos"
                ) as mock_create_rewriter:
                    mock_rewriter = Mock()
                    mock_rewriter.rewrite_file_content.return_value = rewritten
                    mock_create_rewriter.return_value = mock_rewriter

                    # Mock finding git root
                    with (
                        patch.object(Path, "exists", return_value=True),
                        patch.object(
                            Path,
                            "relative_to",
                            return_value=Path("docs/guide.md"),
                        ),
                    ):
                        await sync_service._process_markdown_file(
                            file_path, "org/test-repo"
                        )

                    mock_rewriter.rewrite_file_content.assert_called_once()
                    mock_file_write.write.assert_called_once_with(rewritten)

    @pytest.mark.asyncio
    async def test_process_markdown_file_no_changes(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test markdown file with no link changes."""
        file_path = Path("/tmp/repo/docs/guide.md")  # noqa: S108
        content = "This has no links"

        with patch("aiofiles.open", create=True) as mock_open:
            mock_file = AsyncMock()
            mock_file.read.return_value = content
            mock_open.return_value.__aenter__.return_value = mock_file

            with patch(
                "ff_docs.pipeline.sync.get_enrolled_repositories"
            ) as mock_get_enrolled:
                mock_get_enrolled.return_value = []

                with patch(
                    "ff_docs.pipeline.rewriter.create_link_rewriter_for_repos"
                ) as mock_create_rewriter:
                    mock_rewriter = Mock()
                    mock_rewriter.rewrite_file_content.return_value = (
                        content  # No changes
                    )
                    mock_create_rewriter.return_value = mock_rewriter

                    with (
                        patch.object(Path, "exists", return_value=True),
                        patch.object(
                            Path,
                            "relative_to",
                            return_value=Path("docs/guide.md"),
                        ),
                    ):
                        await sync_service._process_markdown_file(
                            file_path, "org/test-repo"
                        )

                    # Should read but not write since content unchanged
                    mock_open.assert_called_once()  # Only read, no write

    @pytest.mark.asyncio
    async def test_generate_api_documentation(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test API documentation generation."""
        repo_dir = Path("/tmp/repo")  # noqa: S108

        with patch(
            "ff_docs.pipeline.pdoc_integration.generate_api_docs"
        ) as mock_generate:
            mock_generate.return_value = {
                "enabled": True,
                "docs_generated": 3,
                "packages_found": 3,
            }

            result = await sync_service._generate_api_documentation(repo_dir)

            assert result["enabled"] is True
            assert result["docs_generated"] == 3
            mock_generate.assert_called_once_with(repo_dir)

    @pytest.mark.asyncio
    async def test_generate_api_documentation_error(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test API documentation generation error handling."""
        repo_dir = Path("/tmp/repo")  # noqa: S108

        with patch(
            "ff_docs.pipeline.pdoc_integration.generate_api_docs"
        ) as mock_generate:
            mock_generate.side_effect = ImportError("pdoc not installed")

            result = await sync_service._generate_api_documentation(repo_dir)

            assert result["enabled"] is False
            assert result["error"] == "pdoc not installed"
            assert result["docs_generated"] == 0

    def test_get_sync_status(self, sync_service: ContentSyncService) -> None:
        """Test getting sync status."""
        status = SyncStatus(repository="org/test-repo", status="completed")
        sync_service.sync_status["org/test-repo"] = status

        result = sync_service.get_sync_status("org/test-repo")
        assert result == status

        # Non-existent repo
        assert sync_service.get_sync_status("org/unknown") is None

    def test_get_all_sync_status(
        self, sync_service: ContentSyncService
    ) -> None:
        """Test getting all sync statuses."""
        status1 = SyncStatus(repository="org/repo1", status="completed")
        status2 = SyncStatus(repository="org/repo2", status="failed")

        sync_service.sync_status = {
            "org/repo1": status1,
            "org/repo2": status2,
        }

        result = sync_service.get_all_sync_status()
        assert len(result) == 2
        assert result["org/repo1"] == status1
        assert result["org/repo2"] == status2
        # Should return a copy
        assert result is not sync_service.sync_status


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_content_sync_service(self) -> None:
        """Test getting global sync service instance."""
        # Reset global instance
        import ff_docs.pipeline.sync
        from ff_docs.pipeline.sync import (
            get_content_sync_service,
        )

        ff_docs.pipeline.sync._content_sync_service = None

        service1 = get_content_sync_service()
        assert service1 is not None
        assert isinstance(service1, ContentSyncService)

        # Should return same instance
        service2 = get_content_sync_service()
        assert service2 is service1

    @pytest.mark.asyncio
    async def test_trigger_docs_sync(self) -> None:
        """Test trigger_docs_sync function."""
        mock_status = SyncStatus(repository="org/test-repo", status="completed")

        with patch(
            "ff_docs.pipeline.sync.get_content_sync_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.sync_repository = AsyncMock(return_value=mock_status)
            mock_get_service.return_value = mock_service

            result = await trigger_docs_sync("org/test-repo", "abc123")

            assert result == mock_status
            mock_service.sync_repository.assert_called_once_with(
                "org/test-repo", "abc123"
            )
