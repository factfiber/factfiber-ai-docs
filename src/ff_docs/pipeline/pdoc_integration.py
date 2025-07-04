# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""
pdoc integration for automatic API documentation generation.

This module handles automatic generation of API documentation from Python
source code using pdoc, converting it to MkDocs-compatible format for
integration with the unified documentation system.

Note: This module contains complex integration logic with external
processes and file systems, designed for integration testing.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PdocConfig(BaseModel):
    """Configuration for pdoc integration."""

    enabled: bool = True
    packages: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "*/tests/*",
            "*/_internal/*",
            "*/test_*",
            "*/__pycache__/*",
        ]
    )
    output_dir: str = "docs/code"
    template_dir: str | None = None
    show_source: bool = True
    include_undocumented: bool = False


class PdocGenerator:
    """
    Service for generating API documentation using pdoc.

    This service scans Python packages in repositories, generates
    HTML documentation with pdoc, and converts it to MkDocs-compatible
    format for integration with the unified documentation system.
    """

    def __init__(self) -> None:
        """Initialize the pdoc generator."""
        self.temp_dirs: list[Path] = []

    async def generate_docs_for_repo(
        self, repo_dir: Path, config: PdocConfig | None = None
    ) -> dict[str, Any]:
        """
        Generate API documentation for a repository.

        Args:
            repo_dir: Repository directory path
            config: pdoc configuration (auto-detected if None)

        Returns:
            Generation status and statistics
        """
        if config is None:
            config = await self._detect_pdoc_config(repo_dir)

        if not config.enabled:
            return {
                "enabled": False,
                "packages_found": 0,
                "docs_generated": 0,
                "message": "pdoc integration disabled",
            }

        packages_found = await self._discover_packages(repo_dir, config)

        if not packages_found:
            return {
                "enabled": True,
                "packages_found": 0,
                "docs_generated": 0,
                "message": "No Python packages found",
            }

        docs_generated = 0
        errors = []

        for package in packages_found:
            try:
                await self._generate_package_docs(repo_dir, package, config)
                docs_generated += 1
                logger.info("Generated docs for package: %s", package)
            except (ImportError, OSError, ValueError) as e:
                error_msg = f"Failed to generate docs for {package}: {e}"
                errors.append(error_msg)
                logger.exception(
                    "Failed to generate docs for package %s", package
                )

        return {
            "enabled": True,
            "packages_found": len(packages_found),
            "docs_generated": docs_generated,
            "errors": errors,
            "message": f"Generated docs for {docs_generated}/{len(packages_found)} packages",  # noqa: E501
        }

    async def _detect_pdoc_config(self, repo_dir: Path) -> PdocConfig:
        """
        Auto-detect pdoc configuration from repository.

        Args:
            repo_dir: Repository directory

        Returns:
            Detected or default pdoc configuration
        """
        # Look for .factfiber-docs.yml config
        config_files = [
            repo_dir / ".factfiber-docs.yml",
            repo_dir / ".factfiber-docs.yaml",
            repo_dir / "pyproject.toml",  # Could extract from tool.pdoc section
        ]

        for config_file in config_files:
            if config_file.exists() and config_file.name.endswith(
                (".yml", ".yaml")
            ):
                try:
                    async with aiofiles.open(config_file) as f:
                        content = await f.read()

                    config_data = yaml.safe_load(content)
                    pdoc_config = config_data.get("pdoc", {})

                    if pdoc_config:
                        return PdocConfig(**pdoc_config)

                except (OSError, ValueError, TypeError) as e:
                    logger.warning(
                        "Failed to parse config file %s: %s", config_file, e
                    )

        # Auto-detect Python packages
        python_packages = []

        # Common Python package locations
        src_dirs = [
            repo_dir / "src",
            repo_dir / "lib",
            repo_dir,
        ]

        for src_dir in src_dirs:
            if src_dir.exists():
                for item in src_dir.iterdir():
                    if (
                        item.is_dir()
                        and (item / "__init__.py").exists()
                        and not item.name.startswith(".")
                        and item.name not in ["tests", "test", "__pycache__"]
                    ):
                        # Calculate relative path from repo root
                        rel_path = item.relative_to(repo_dir)
                        python_packages.append(str(rel_path))

        return PdocConfig(
            enabled=bool(python_packages), packages=python_packages
        )

    async def _discover_packages(
        self, repo_dir: Path, config: PdocConfig
    ) -> list[str]:
        """
        Discover Python packages to document.

        Args:
            repo_dir: Repository directory
            config: pdoc configuration

        Returns:
            List of package paths to document
        """
        packages = []

        for package_path in config.packages:
            full_path = repo_dir / package_path

            if full_path.exists() and full_path.is_dir():
                # Check if it's a valid Python package
                if (full_path / "__init__.py").exists():
                    packages.append(package_path)
                else:
                    logger.warning(
                        "Package path exists but no __init__.py found: %s",
                        package_path,
                    )
            else:
                logger.warning("Package path not found: %s", package_path)

        return packages

    async def _generate_package_docs(
        self, repo_dir: Path, package_path: str, config: PdocConfig
    ) -> None:
        """
        Generate documentation for a single package.

        Args:
            repo_dir: Repository directory
            package_path: Relative path to package
            config: pdoc configuration
        """
        output_dir = repo_dir / config.output_dir
        await aiofiles.os.makedirs(output_dir, exist_ok=True)

        # Prepare pdoc command
        cmd = [
            "python",
            "-m",
            "pdoc",
            "--docformat",
            "google",
            "--html",
            "--math",
            "--mermaid",
            "--include-undocumented",
            "--output-dir",
            str(output_dir),
            "--force",
        ]

        # Add configuration options
        if not config.show_source:
            cmd.append("--no-show-source")

        if not config.include_undocumented:
            cmd.extend(["--filter", "!__"])

        if config.template_dir:
            template_path = repo_dir / config.template_dir
            if template_path.exists():
                cmd.extend(["--template-dir", str(template_path)])

        # Add package path
        package_full_path = repo_dir / package_path
        cmd.append(str(package_full_path))

        # Run pdoc
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(repo_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                error_msg = f"pdoc failed: {stderr.decode()}"
                raise RuntimeError(error_msg)

            logger.debug(
                "pdoc output for %s: %s", package_path, stdout.decode()
            )

            # Post-process generated HTML
            await self._post_process_html(output_dir, package_path)

        except FileNotFoundError as e:
            raise RuntimeError(
                "pdoc not found. Install with 'pip install pdoc3' or 'pip install pdoc'"  # noqa: E501
            ) from e

    async def _post_process_html(
        self, output_dir: Path, package_path: str
    ) -> None:
        """
        Post-process generated HTML for MkDocs integration.

        Args:
            output_dir: Directory containing generated HTML
            package_path: Package path that was documented
        """
        # Find generated HTML files
        html_files = list(output_dir.rglob("*.html"))

        for html_file in html_files:
            try:
                # Read HTML content
                async with aiofiles.open(html_file, encoding="utf-8") as f:
                    content = await f.read()

                # Apply post-processing transformations
                processed_content = await self._transform_html_content(
                    content, html_file, package_path
                )

                # Write back if changed
                if processed_content != content:
                    async with aiofiles.open(
                        html_file, "w", encoding="utf-8"
                    ) as f:
                        await f.write(processed_content)

            except (OSError, ValueError) as e:
                logger.warning(
                    "Failed to post-process HTML file %s: %s", html_file, e
                )

    async def _transform_html_content(
        self,
        content: str,
        html_file: Path,  # noqa: ARG002
        package_path: str,  # noqa: ARG002
    ) -> str:
        """
        Transform HTML content for better MkDocs integration.

        Args:
            content: Original HTML content
            html_file: Path to HTML file
            package_path: Package path being documented

        Returns:
            Transformed HTML content
        """
        # TODO: Add specific transformations for MkDocs compatibility
        # - Update CSS classes to match Material theme
        # - Fix navigation links
        # - Add MkDocs-compatible metadata

        return content

    def cleanup(self) -> None:
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                import shutil

                shutil.rmtree(temp_dir)
        self.temp_dirs.clear()


# Global generator instance
_pdoc_generator: PdocGenerator | None = None


def get_pdoc_generator() -> PdocGenerator:
    """Get the global pdoc generator instance."""
    global _pdoc_generator  # noqa: PLW0603
    if _pdoc_generator is None:
        _pdoc_generator = PdocGenerator()
    return _pdoc_generator


async def generate_api_docs(
    repo_dir: Path, config: PdocConfig | None = None
) -> dict[str, Any]:
    """
    Generate API documentation for a repository.

    Args:
        repo_dir: Repository directory path
        config: Optional pdoc configuration

    Returns:
        Generation results
    """
    generator = get_pdoc_generator()
    return await generator.generate_docs_for_repo(repo_dir, config)
