# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001

"""Unit tests for pdoc integration module."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ff_docs.pipeline.pdoc_integration import (
    PdocConfig,
    PdocGenerator,
    generate_api_docs,
    get_pdoc_generator,
)


class TestPdocConfig:
    """Test PdocConfig model."""

    def test_pdoc_config_creation(self) -> None:
        """Test creating PdocConfig with all fields."""
        config = PdocConfig(
            enabled=True,
            packages=["src/mypackage", "lib/utils"],
            exclude_patterns=["*/tests/*", "*/__pycache__/*"],
            output_dir="docs/api",
            template_dir="templates/pdoc",
            show_source=True,
            include_undocumented=True,
        )

        assert config.enabled is True
        assert config.packages == ["src/mypackage", "lib/utils"]
        assert config.exclude_patterns == ["*/tests/*", "*/__pycache__/*"]
        assert config.output_dir == "docs/api"
        assert config.template_dir == "templates/pdoc"
        assert config.show_source is True
        assert config.include_undocumented is True

    def test_pdoc_config_defaults(self) -> None:
        """Test PdocConfig with default values."""
        config = PdocConfig()

        assert config.enabled is True
        assert config.packages == []
        assert "*/tests/*" in config.exclude_patterns
        assert "*/_internal/*" in config.exclude_patterns
        assert config.output_dir == "docs/code"
        assert config.template_dir is None
        assert config.show_source is True
        assert config.include_undocumented is False


class TestPdocGenerator:
    """Test PdocGenerator."""

    @pytest.fixture
    def generator(self) -> PdocGenerator:
        """Create PdocGenerator instance."""
        return PdocGenerator()

    @pytest.fixture
    def repo_dir(self, tmp_path: Path) -> Path:
        """Create test repository directory structure."""
        repo = tmp_path / "test-repo"
        repo.mkdir()

        # Create Python packages
        (repo / "src").mkdir()
        (repo / "src" / "mypackage").mkdir()
        (repo / "src" / "mypackage" / "__init__.py").write_text("")
        (repo / "src" / "mypackage" / "core.py").write_text("def hello(): pass")

        (repo / "tests").mkdir()
        (repo / "tests" / "__init__.py").write_text("")

        return repo

    @pytest.mark.asyncio
    async def test_generate_docs_for_repo_success(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test successful documentation generation."""
        config = PdocConfig(
            enabled=True,
            packages=["src/mypackage"],
        )

        # Mock subprocess execution
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            with patch.object(generator, "_post_process_html"):
                result = await generator.generate_docs_for_repo(
                    repo_dir, config
                )

        assert result["enabled"] is True
        assert result["packages_found"] == 1
        assert result["docs_generated"] == 1
        assert result["message"] == "Generated docs for 1/1 packages"

        # Verify subprocess call
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0]
        assert "python" in call_args
        assert "-m" in call_args
        assert "pdoc" in call_args
        assert "--docformat" in call_args
        assert "google" in call_args

    @pytest.mark.asyncio
    async def test_generate_docs_for_repo_disabled(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test generation when disabled."""
        config = PdocConfig(enabled=False)

        result = await generator.generate_docs_for_repo(repo_dir, config)

        assert result["enabled"] is False
        assert result["packages_found"] == 0
        assert result["docs_generated"] == 0
        assert result["message"] == "pdoc integration disabled"

    @pytest.mark.asyncio
    async def test_generate_docs_for_repo_no_packages(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test generation with no packages found."""
        config = PdocConfig(packages=["nonexistent"])

        result = await generator.generate_docs_for_repo(repo_dir, config)

        assert result["enabled"] is True
        assert result["packages_found"] == 0
        assert result["docs_generated"] == 0
        assert result["message"] == "No Python packages found"

    @pytest.mark.asyncio
    async def test_generate_docs_for_repo_with_errors(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test generation with some package errors."""
        config = PdocConfig(packages=["src/mypackage", "src/broken"])

        # Create broken package
        (repo_dir / "src" / "broken").mkdir()
        (repo_dir / "src" / "broken" / "__init__.py").write_text("")

        with patch.object(generator, "_generate_package_docs") as mock_generate:
            # First package succeeds, second fails with a caught exception type
            async def side_effect(
                repo_dir: Path, package: str, config: PdocConfig
            ) -> None:
                if package == "src/broken":
                    raise ImportError("Package import failed")
                # Success case - do nothing

            mock_generate.side_effect = side_effect

            result = await generator.generate_docs_for_repo(repo_dir, config)

        assert result["enabled"] is True
        assert result["packages_found"] == 2
        assert result["docs_generated"] == 1
        assert len(result["errors"]) == 1
        assert "Failed to generate docs for src/broken" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_detect_pdoc_config_from_file(
        self, generator: PdocGenerator, tmp_path: Path
    ) -> None:
        """Test auto-detecting config from .factfiber-docs.yml."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        config_file = repo_dir / ".factfiber-docs.yml"
        config_file.write_text("""
pdoc:
  enabled: true
  packages:
    - src/myapp
    - lib/utils
  output_dir: docs/api
  include_undocumented: true
""")

        with patch("aiofiles.open", create=True) as mock_open:
            mock_file = AsyncMock()
            mock_file.read.return_value = config_file.read_text()
            mock_open.return_value.__aenter__.return_value = mock_file

            config = await generator._detect_pdoc_config(repo_dir)

        assert config.enabled is True
        assert config.packages == ["src/myapp", "lib/utils"]
        assert config.output_dir == "docs/api"
        assert config.include_undocumented is True

    @pytest.mark.asyncio
    async def test_detect_pdoc_config_auto_discover(
        self, generator: PdocGenerator, tmp_path: Path
    ) -> None:
        """Test auto-discovering Python packages."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create package structure
        (repo_dir / "src").mkdir()
        (repo_dir / "src" / "myapp").mkdir()
        (repo_dir / "src" / "myapp" / "__init__.py").write_text("")

        (repo_dir / "lib").mkdir()
        (repo_dir / "lib" / "utils").mkdir()
        (repo_dir / "lib" / "utils" / "__init__.py").write_text("")

        # Create non-package directories
        (repo_dir / "tests").mkdir()
        (repo_dir / "tests" / "__init__.py").write_text("")
        (repo_dir / ".hidden").mkdir()
        (repo_dir / ".hidden" / "__init__.py").write_text("")

        config = await generator._detect_pdoc_config(repo_dir)

        assert config.enabled is True
        assert "src/myapp" in config.packages
        assert "lib/utils" in config.packages
        assert "tests" not in config.packages
        assert ".hidden" not in config.packages

    @pytest.mark.asyncio
    async def test_discover_packages(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test package discovery."""
        config = PdocConfig(packages=["src/mypackage", "nonexistent", "tests"])

        packages = await generator._discover_packages(repo_dir, config)

        # tests directory also exists and has __init__.py, so it gets found too
        # but it should be filtered out by exclude patterns
        assert len(packages) == 2  # src/mypackage and tests both found
        assert "src/mypackage" in packages
        assert "tests" in packages

    @pytest.mark.asyncio
    async def test_generate_package_docs(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test generating docs for a single package."""
        config = PdocConfig()

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(
                return_value=(b"Generated", b"")
            )
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            with (
                patch("aiofiles.os.makedirs") as mock_makedirs,
                patch.object(generator, "_post_process_html"),
            ):
                await generator._generate_package_docs(
                    repo_dir, "src/mypackage", config
                )

        # Verify output directory created
        mock_makedirs.assert_called_once()

        # Verify subprocess command
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0]
        assert "--output-dir" in call_args
        assert str(repo_dir / "docs/code") in call_args
        assert str(repo_dir / "src/mypackage") in call_args

    @pytest.mark.asyncio
    async def test_generate_package_docs_custom_config(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test generating docs with custom configuration."""
        config = PdocConfig(
            output_dir="api-docs",
            show_source=False,
            include_undocumented=False,
            template_dir="templates",
        )

        # Create template directory
        (repo_dir / "templates").mkdir()

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            with (
                patch("aiofiles.os.makedirs"),
                patch.object(generator, "_post_process_html"),
            ):
                await generator._generate_package_docs(
                    repo_dir, "src/mypackage", config
                )

        call_args = mock_subprocess.call_args[0]
        assert "--no-show-source" in call_args
        assert "--filter" in call_args
        assert "!__" in call_args
        assert "--template-dir" in call_args

    @pytest.mark.asyncio
    async def test_generate_package_docs_pdoc_not_found(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test handling pdoc not installed."""
        config = PdocConfig()

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError("pdoc not found")

            with (
                patch("aiofiles.os.makedirs"),
                pytest.raises(RuntimeError, match="pdoc not found"),
            ):
                await generator._generate_package_docs(
                    repo_dir, "src/mypackage", config
                )

    @pytest.mark.asyncio
    async def test_post_process_html(
        self, generator: PdocGenerator, tmp_path: Path
    ) -> None:
        """Test HTML post-processing."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create test HTML files
        (output_dir / "index.html").write_text("<html>Index</html>")
        (output_dir / "module.html").write_text("<html>Module</html>")
        subdir = output_dir / "subpackage"
        subdir.mkdir()
        (subdir / "class.html").write_text("<html>Class</html>")

        with patch("aiofiles.open", create=True) as mock_open:
            # Mock file operations
            read_count = 0
            files_content = [
                "<html>Index</html>",
                "<html>Module</html>",
                "<html>Class</html>",
            ]

            async def mock_read() -> str:
                nonlocal read_count
                content = files_content[read_count]
                read_count += 1
                return content

            mock_file = AsyncMock()
            mock_file.read = mock_read
            mock_file.write = AsyncMock()
            mock_open.return_value.__aenter__.return_value = mock_file

            with patch.object(
                generator, "_transform_html_content"
            ) as mock_transform:
                mock_transform.side_effect = lambda c, *_: c + " Transformed"

                await generator._post_process_html(output_dir, "mypackage")

        # Should process all HTML files
        assert mock_transform.call_count == 3
        assert mock_file.write.call_count == 3

    @pytest.mark.asyncio
    async def test_transform_html_content(
        self, generator: PdocGenerator
    ) -> None:
        """Test HTML content transformation."""
        content = "<html><body>Original content</body></html>"
        html_file = Path("/output/module.html")

        # Currently just returns content as-is
        result = await generator._transform_html_content(
            content, html_file, "mypackage"
        )
        assert result == content

    def test_cleanup(self, generator: PdocGenerator, tmp_path: Path) -> None:
        """Test cleanup of temporary directories."""
        # Create temp directories
        temp1 = tmp_path / "temp1"
        temp1.mkdir()
        temp2 = tmp_path / "temp2"
        temp2.mkdir()

        generator.temp_dirs = [temp1, temp2]

        with patch("shutil.rmtree") as mock_rmtree:
            generator.cleanup()

        assert mock_rmtree.call_count == 2
        assert len(generator.temp_dirs) == 0

    @pytest.mark.asyncio
    async def test_generate_docs_for_repo_with_none_config(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test generation when config is None (auto-detect path)."""
        with patch.object(generator, "_detect_pdoc_config") as mock_detect:
            mock_detect.return_value = PdocConfig(enabled=False)

            result = await generator.generate_docs_for_repo(repo_dir, None)

            assert result["enabled"] is False
            mock_detect.assert_called_once_with(repo_dir)

    @pytest.mark.asyncio
    async def test_detect_pdoc_config_parsing_error(
        self, generator: PdocGenerator, tmp_path: Path
    ) -> None:
        """Test config file parsing error handling."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        config_file = repo_dir / ".factfiber-docs.yml"
        config_file.write_text("invalid: yaml: content: [")  # Invalid YAML

        with patch("aiofiles.open", create=True) as mock_open:
            mock_file = AsyncMock()
            mock_file.read.return_value = "invalid: yaml: content: ["
            mock_open.return_value.__aenter__.return_value = mock_file

            with patch("yaml.safe_load") as mock_yaml:
                # Simulate yaml parsing error (line 147-148)
                mock_yaml.side_effect = ValueError("Invalid YAML")

                config = await generator._detect_pdoc_config(repo_dir)

                # Should fall back to auto-detection
                assert config.enabled is False  # No packages auto-detected

    @pytest.mark.asyncio
    async def test_discover_packages_warning_no_init_py(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test package discovery warning with no __init__.py."""
        # Create directory without __init__.py
        no_init_dir = repo_dir / "src" / "not_a_package"
        no_init_dir.mkdir(parents=True)

        config = PdocConfig(packages=["src/not_a_package"])

        with patch("ff_docs.pipeline.pdoc_integration.logger") as mock_logger:
            packages = await generator._discover_packages(repo_dir, config)

            assert len(packages) == 0
            mock_logger.warning.assert_called_with(
                "Package path exists but no __init__.py found: %s",
                "src/not_a_package",
            )

    @pytest.mark.asyncio
    async def test_generate_package_docs_subprocess_error(
        self, generator: PdocGenerator, repo_dir: Path
    ) -> None:
        """Test generate_package_docs with subprocess returning error code."""
        config = PdocConfig()

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(
                return_value=(b"", b"pdoc error")
            )
            mock_process.returncode = 1  # Error code
            mock_subprocess.return_value = mock_process

            with (
                patch("aiofiles.os.makedirs"),
                pytest.raises(RuntimeError, match="pdoc failed: pdoc error"),
            ):
                await generator._generate_package_docs(
                    repo_dir, "src/mypackage", config
                )

    @pytest.mark.asyncio
    async def test_post_process_html_file_error(
        self, generator: PdocGenerator, tmp_path: Path
    ) -> None:
        """Test HTML post-processing with file error."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create test HTML file
        (output_dir / "index.html").write_text("<html>Test</html>")

        with patch("aiofiles.open", create=True) as mock_open:
            # Mock file operations to raise an error
            mock_open.side_effect = OSError("File access error")

            with patch(
                "ff_docs.pipeline.pdoc_integration.logger"
            ) as mock_logger:
                await generator._post_process_html(output_dir, "mypackage")

                # Should log warning about failed post-processing
                mock_logger.warning.assert_called()


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_pdoc_generator(self) -> None:
        """Test getting global generator instance."""
        # Reset global instance
        import ff_docs.pipeline.pdoc_integration

        ff_docs.pipeline.pdoc_integration._pdoc_generator = None

        gen1 = get_pdoc_generator()
        assert isinstance(gen1, PdocGenerator)

        # Should return same instance
        gen2 = get_pdoc_generator()
        assert gen2 is gen1

    @pytest.mark.asyncio
    async def test_generate_api_docs(self) -> None:
        """Test generate_api_docs function."""
        repo_dir = Path("/test/repo")
        config = PdocConfig(enabled=True)

        with patch(
            "ff_docs.pipeline.pdoc_integration.get_pdoc_generator"
        ) as mock_get:
            mock_generator = Mock()
            mock_generator.generate_docs_for_repo = AsyncMock(
                return_value={"docs_generated": 3}
            )
            mock_get.return_value = mock_generator

            result = await generate_api_docs(repo_dir, config)

            assert result == {"docs_generated": 3}
            mock_generator.generate_docs_for_repo.assert_called_once_with(
                repo_dir, config
            )
