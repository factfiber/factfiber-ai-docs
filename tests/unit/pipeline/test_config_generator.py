# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001

"""Unit tests for unified MkDocs configuration generator."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

from ff_docs.pipeline.config_generator import (
    RepoNavigationEntry,
    UnifiedConfigGenerator,
    generate_unified_config,
    get_config_generator,
)


class TestRepoNavigationEntry:
    """Test RepoNavigationEntry model."""

    def test_repo_navigation_entry_creation(self) -> None:
        """Test creating RepoNavigationEntry with all fields."""
        entry = RepoNavigationEntry(
            name="test-repo",
            path="/projects/test-repo/",
            section="Core Projects",
            nav_config={"order": 1, "icon": "material/book"},
        )

        assert entry.name == "test-repo"
        assert entry.path == "/projects/test-repo/"
        assert entry.section == "Core Projects"
        assert entry.nav_config == {"order": 1, "icon": "material/book"}

    def test_repo_navigation_entry_defaults(self) -> None:
        """Test RepoNavigationEntry with default values."""
        entry = RepoNavigationEntry(
            name="test-repo",
            path="/projects/test-repo/",
        )

        assert entry.section is None
        assert entry.nav_config == {}


class TestUnifiedConfigGenerator:
    """Test UnifiedConfigGenerator."""

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings."""
        settings = Mock()
        settings.mkdocs.site_name = "FactFiber Documentation"
        settings.mkdocs.site_url = "https://docs.factfiber.ai"
        return settings

    @pytest.fixture
    def generator(self, mock_settings: Mock) -> UnifiedConfigGenerator:
        """Create UnifiedConfigGenerator instance."""
        with patch(
            "ff_docs.pipeline.config_generator.get_settings",
            return_value=mock_settings,
        ):
            return UnifiedConfigGenerator()

    @pytest.fixture
    def enrolled_repos(self) -> list[dict]:
        """Create test enrolled repositories."""
        return [
            {
                "name": "org/core-lib",
                "import_url": "https://github.com/org/core-lib.git#docs?branch=main",
                "section": "Core Libraries",
            },
            {
                "name": "org/utils",
                "import_url": "https://github.com/org/utils.git#docs?branch=main",
                "section": "Core Libraries",
            },
            {
                "name": "org/app",
                "import_url": "https://github.com/org/app.git#docs?branch=main",
                "section": "Applications",
            },
        ]

    @pytest.mark.asyncio
    async def test_generate_unified_config(
        self, generator: UnifiedConfigGenerator, enrolled_repos: list[dict]
    ) -> None:
        """Test generating unified configuration."""
        with patch(
            "ff_docs.pipeline.config_generator.get_enrolled_repositories"
        ) as mock_get:
            mock_get.return_value = enrolled_repos

            config = await generator.generate_unified_config()

        # Verify basic structure
        assert config["site_name"] == "FactFiber Documentation"
        assert config["site_url"] == "https://docs.factfiber.ai"
        assert "theme" in config
        assert "nav" in config
        assert "plugins" in config
        assert "markdown_extensions" in config

    @pytest.mark.asyncio
    async def test_generate_unified_config_with_output(
        self,
        generator: UnifiedConfigGenerator,
        enrolled_repos: list[dict],
        tmp_path: Path,
    ) -> None:
        """Test generating config with file output."""
        output_path = tmp_path / "mkdocs.yml"

        with patch(
            "ff_docs.pipeline.config_generator.get_enrolled_repositories"
        ) as mock_get:
            mock_get.return_value = enrolled_repos

            with patch.object(generator, "_write_config_file") as mock_write:
                config = await generator.generate_unified_config(output_path)

        mock_write.assert_called_once_with(config, output_path)

    @pytest.mark.asyncio
    async def test_build_base_config(
        self, generator: UnifiedConfigGenerator
    ) -> None:
        """Test building base configuration."""
        config = await generator._build_base_config()

        # Verify site configuration
        assert config["site_name"] == "FactFiber Documentation"
        expected_desc = (
            "Centralized documentation hub for FactFiber.ai projects and "
            "systems"
        )
        assert config["site_description"] == expected_desc
        assert config["site_url"] == "https://docs.factfiber.ai"

        # Verify theme
        assert config["theme"]["name"] == "material"
        assert "palette" in config["theme"]
        assert "features" in config["theme"]

        # Verify markdown extensions
        assert "pymdownx.highlight" in [
            ext if isinstance(ext, str) else next(iter(ext.keys()))
            for ext in config["markdown_extensions"]
        ]

        # Verify extra JavaScript
        assert any("mathjax" in js for js in config["extra_javascript"])
        assert any("mermaid" in js for js in config["extra_javascript"])

    @pytest.mark.asyncio
    async def test_build_unified_navigation(
        self, generator: UnifiedConfigGenerator, enrolled_repos: list[dict]
    ) -> None:
        """Test building unified navigation structure."""
        with patch.object(
            generator, "_build_repo_navigation"
        ) as mock_build_repo:
            # Mock repo navigation entries
            mock_build_repo.side_effect = [
                {
                    "Core-Lib": "!import https://github.com/org/core-lib.git#docs?branch=main"
                },
                {
                    "Utils": "!import https://github.com/org/utils.git#docs?branch=main"
                },
                {
                    "App": "!import https://github.com/org/app.git#docs?branch=main"
                },
            ]

            nav = await generator._build_unified_navigation(enrolled_repos)

        # Should have Home, sectioned repos, API Reference, and Development
        assert len(nav) >= 4
        assert nav[0] == {"Home": "index.md"}

        # Find sections
        sections = {
            k: v for item in nav for k, v in item.items() if isinstance(v, dict)
        }
        assert "Core Libraries" in sections
        assert "Applications" in sections

    @pytest.mark.asyncio
    async def test_build_unified_navigation_single_repo_section(
        self, generator: UnifiedConfigGenerator
    ) -> None:
        """Test navigation with single repository in section."""
        repos = [
            {
                "name": "org/solo-app",
                "import_url": "https://github.com/org/solo-app.git",
                "section": "Standalone",
            }
        ]

        with patch.object(generator, "_build_repo_navigation") as mock_build:
            mock_build.return_value = {
                "Solo-App": "!import https://github.com/org/solo-app.git"
            }

            nav = await generator._build_unified_navigation(repos)

        # Single repo section should be added directly
        standalone_section = next(
            (item for item in nav if "Standalone" in item), None
        )
        assert standalone_section is not None
        assert standalone_section["Standalone"] == {
            "Solo-App": "!import https://github.com/org/solo-app.git"
        }

    @pytest.mark.asyncio
    async def test_build_repo_navigation(
        self, generator: UnifiedConfigGenerator
    ) -> None:
        """Test building navigation for single repository."""
        repo = {
            "name": "org/test-repo",
            "import_url": "https://github.com/org/test-repo.git#docs?branch=main",
        }

        result = await generator._build_repo_navigation(repo)

        assert result == {
            "Test-Repo": "!import https://github.com/org/test-repo.git#docs?branch=main"
        }

    @pytest.mark.asyncio
    async def test_build_repo_navigation_no_org(
        self, generator: UnifiedConfigGenerator
    ) -> None:
        """Test building navigation for repository without org prefix."""
        repo = {
            "name": "standalone-repo",
            "import_url": "https://github.com/standalone-repo.git",
        }

        result = await generator._build_repo_navigation(repo)

        assert result == {
            "Standalone-Repo": "!import https://github.com/standalone-repo.git"
        }

    @pytest.mark.asyncio
    async def test_configure_plugins(
        self, generator: UnifiedConfigGenerator, enrolled_repos: list[dict]
    ) -> None:
        """Test plugin configuration."""
        plugins = await generator._configure_plugins(enrolled_repos)

        # Should have search plugin
        search_plugin = next((p for p in plugins if "search" in p), None)
        assert search_plugin is not None

        # Should have multirepo plugin when repos enrolled
        multirepo_plugin = next((p for p in plugins if "multirepo" in p), None)
        assert multirepo_plugin is not None
        assert multirepo_plugin["multirepo"]["cleanup"] is True
        assert multirepo_plugin["multirepo"]["keep_docs_dir"] is True

        # Should have mermaid plugin
        mermaid_plugin = next((p for p in plugins if "mermaid2" in p), None)
        assert mermaid_plugin is not None

    @pytest.mark.asyncio
    async def test_configure_plugins_no_repos(
        self, generator: UnifiedConfigGenerator
    ) -> None:
        """Test plugin configuration with no repositories."""
        plugins = await generator._configure_plugins([])

        # Should not have multirepo plugin
        multirepo_plugin = next((p for p in plugins if "multirepo" in p), None)
        assert multirepo_plugin is None

    @pytest.mark.asyncio
    async def test_merge_repo_configs(
        self, generator: UnifiedConfigGenerator, enrolled_repos: list[dict]
    ) -> None:
        """Test merging repository-specific configurations."""
        base_config = {
            "site_name": "Test Docs",
            "watch": ["README.md"],
        }

        # Add custom config to repos
        repos_with_config = [
            {
                **enrolled_repos[0],
                "config": {"watch": ["custom1/", "shared/"]},
            },
            {
                **enrolled_repos[1],
                "config": {"watch": ["custom2/", "shared/"]},
            },
        ]

        result = await generator._merge_repo_configs(
            base_config, repos_with_config
        )

        # Should merge watch paths
        assert "watch" in result
        assert "README.md" in result["watch"]
        assert "src/" in result["watch"]
        assert "docs/" in result["watch"]
        assert "custom1/" in result["watch"]
        assert "custom2/" in result["watch"]
        # Should deduplicate
        assert result["watch"].count("shared/") == 1

    @pytest.mark.asyncio
    async def test_write_config_file(
        self, generator: UnifiedConfigGenerator, tmp_path: Path
    ) -> None:
        """Test writing configuration to YAML file."""
        config = {
            "site_name": "Test Documentation",
            "theme": {
                "name": "material",
                "palette": [
                    {"scheme": "default", "primary": "blue"},
                ],
            },
            "nav": [
                {"Home": "index.md"},
                {"Guide": "guide/index.md"},
            ],
        }

        output_path = tmp_path / "subdir" / "mkdocs.yml"

        await generator._write_config_file(config, output_path)

        # Verify file created
        assert output_path.exists()
        assert output_path.parent.exists()

        # Verify content
        loaded = yaml.safe_load(output_path.read_text())

        assert loaded["site_name"] == "Test Documentation"
        assert loaded["theme"]["name"] == "material"
        assert len(loaded["nav"]) == 2

    @pytest.mark.asyncio
    async def test_full_config_generation_flow(
        self, generator: UnifiedConfigGenerator, enrolled_repos: list[dict]
    ) -> None:
        """Test complete configuration generation flow."""
        with patch(
            "ff_docs.pipeline.config_generator.get_enrolled_repositories"
        ) as mock_get:
            mock_get.return_value = enrolled_repos

            config = await generator.generate_unified_config()

        # Verify complete structure
        assert config["site_name"] == "FactFiber Documentation"
        assert config["docs_dir"] == "docs"
        assert config["edit_uri"] == "edit/main/docs/"

        # Verify theme features
        theme_features = config["theme"]["features"]
        assert "navigation.tabs" in theme_features
        assert "search.highlight" in theme_features
        assert "content.code.copy" in theme_features

        # Verify markdown extensions are properly configured
        extensions = config["markdown_extensions"]
        assert any(
            isinstance(ext, dict) and "pymdownx.superfences" in ext
            for ext in extensions
        )

        # Verify extra configuration
        assert "version" in config["extra"]
        assert "social" in config["extra"]


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_config_generator(self) -> None:
        """Test getting global generator instance."""
        # Reset global instance
        import ff_docs.pipeline.config_generator

        ff_docs.pipeline.config_generator._config_generator = None

        gen1 = get_config_generator()
        assert isinstance(gen1, UnifiedConfigGenerator)

        # Should return same instance
        gen2 = get_config_generator()
        assert gen2 is gen1

    @pytest.mark.asyncio
    async def test_generate_unified_config_function(self) -> None:
        """Test generate_unified_config module function."""
        output_path = Path("/tmp/mkdocs.yml")  # noqa: S108

        with patch(
            "ff_docs.pipeline.config_generator.get_config_generator"
        ) as mock_get:
            mock_generator = Mock()
            mock_generator.generate_unified_config = AsyncMock(
                return_value={"site_name": "Test"}
            )
            mock_get.return_value = mock_generator

            result = await generate_unified_config(output_path)

            assert result == {"site_name": "Test"}
            mock_generator.generate_unified_config.assert_called_once_with(
                output_path
            )
