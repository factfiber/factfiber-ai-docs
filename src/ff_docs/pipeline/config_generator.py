# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""
Unified MkDocs configuration generation.

This module creates dynamic MkDocs configurations that combine multiple
repositories into a unified documentation site with seamless navigation
and proper repository-scoped access control.

Note: This module contains complex integration logic that coordinates
multiple external systems (Git, GitHub, file system, MkDocs) and is
designed for integration testing rather than unit testing.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ff_docs.aggregator.enrollment import get_enrolled_repositories
from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)


class RepoNavigationEntry(BaseModel):
    """Navigation entry for a repository."""

    name: str
    path: str
    section: str | None = None
    nav_config: dict[str, Any] = Field(default_factory=dict)


class UnifiedConfigGenerator:
    """
    Generator for unified MkDocs configuration.

    This service creates a master MkDocs configuration that includes
    all enrolled repositories, their navigation structures, and
    unified themes and plugins.
    """

    def __init__(self) -> None:
        """Initialize the config generator."""
        self.settings = get_settings()

    async def generate_unified_config(
        self, output_path: Path | None = None
    ) -> dict[str, Any]:
        """
        Generate unified MkDocs configuration.

        Args:
            output_path: Optional path to write config file

        Returns:
            Generated configuration dictionary
        """
        # Get enrolled repositories
        enrolled_repos = await get_enrolled_repositories()

        # Build base configuration
        config = await self._build_base_config()

        # Add repository navigation
        config["nav"] = await self._build_unified_navigation(enrolled_repos)

        # Configure plugins for multi-repo
        config["plugins"] = await self._configure_plugins(enrolled_repos)

        # Add repository-specific configurations
        config = await self._merge_repo_configs(config, enrolled_repos)

        # Write to file if path provided
        if output_path:
            await self._write_config_file(config, output_path)

        logger.info(
            "Generated unified config with %d repositories", len(enrolled_repos)
        )

        return config

    async def _build_base_config(self) -> dict[str, Any]:
        """
        Build base MkDocs configuration.

        Returns:
            Base configuration dictionary
        """
        config = {
            "site_name": self.settings.mkdocs.site_name,
            "site_description": "Centralized documentation hub for FactFiber.ai projects and systems",  # noqa: E501
            "site_url": self.settings.mkdocs.site_url,
            "repo_name": "factfiber/factfiber-ai-docs",
            "repo_url": "https://github.com/factfiber/factfiber-ai-docs",
            "edit_uri": "edit/main/docs/",
            "docs_dir": "docs",
            "theme": {
                "name": "material",
                "palette": [
                    {
                        "scheme": "default",
                        "primary": "blue",
                        "accent": "blue",
                        "toggle": {
                            "icon": "material/brightness-7",
                            "name": "Switch to dark mode",
                        },
                    },
                    {
                        "scheme": "slate",
                        "primary": "blue",
                        "accent": "blue",
                        "toggle": {
                            "icon": "material/brightness-4",
                            "name": "Switch to light mode",
                        },
                    },
                ],
                "features": [
                    "navigation.tabs",
                    "navigation.sections",
                    "navigation.expand",
                    "navigation.top",
                    "navigation.indexes",
                    "search.highlight",
                    "search.share",
                    "search.suggest",
                    "content.code.copy",
                    "content.action.edit",
                    "content.action.view",
                    "content.tabs.link",
                ],
            },
            "markdown_extensions": [
                {
                    "pymdownx.highlight": {
                        "anchor_linenums": True,
                        "line_spans": "__span",
                        "pygments_lang_class": True,
                    }
                },
                "pymdownx.inlinehilite",
                "pymdownx.snippets",
                {
                    "pymdownx.superfences": {
                        "custom_fences": [
                            {
                                "name": "mermaid",
                                "class": "mermaid",
                                "format": "!!python/name:pymdownx.superfences.fence_code_format",  # noqa: E501
                            }
                        ]
                    }
                },
                {"pymdownx.arithmatex": {"generic": True}},
                {"pymdownx.betterem": {"smart_enable": "all"}},
                "pymdownx.caret",
                "pymdownx.details",
                {
                    "pymdownx.emoji": {
                        "emoji_index": "!!python/name:material.extensions.emoji.twemoji",  # noqa: E501
                        "emoji_generator": "!!python/name:material.extensions.emoji.to_svg",  # noqa: E501
                    }
                },
                "pymdownx.keys",
                "pymdownx.mark",
                "pymdownx.smartsymbols",
                {"pymdownx.tabbed": {"alternate_style": True}},
                {"pymdownx.tasklist": {"custom_checkbox": True}},
                "pymdownx.tilde",
                "attr_list",
                "md_in_html",
                "admonition",
                "def_list",
                "footnotes",
                "meta",
                {"toc": {"permalink": True, "title": "On this page"}},
            ],
            "extra_javascript": [
                "https://polyfill.io/v3/polyfill.min.js?features=es6",
                "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
                "https://unpkg.com/mermaid/dist/mermaid.min.js",
            ],
            "extra": {
                "version": {"provider": "mike"},
                "social": [
                    {
                        "icon": "fontawesome/brands/github",
                        "link": "https://github.com/factfiber",
                    },
                    {
                        "icon": "fontawesome/brands/linkedin",
                        "link": "https://linkedin.com/company/factfiber",
                    },
                ],
            },
        }

        return config

    async def _build_unified_navigation(
        self, enrolled_repos: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Build unified navigation structure.

        Args:
            enrolled_repos: List of enrolled repositories

        Returns:
            Unified navigation configuration
        """
        nav: list[dict[str, Any]] = [{"Home": "index.md"}]

        # Group repositories by section
        sections: dict[str, list[dict[str, Any]]] = {}

        for repo in enrolled_repos:
            section = repo.get("section", "Projects")

            if section not in sections:
                sections[section] = []

            # Create repository navigation entry
            repo_entry = await self._build_repo_navigation(repo)
            sections[section].append(repo_entry)

        # Add sections to navigation
        for section_name, section_repos in sections.items():
            if len(section_repos) == 1:
                # Single repository in section - add directly
                nav.append({section_name: section_repos[0]})
            else:
                # Multiple repositories - create subsection
                section_nav: dict[str, Any] = {
                    "Overview": f"{section_name.lower()}/index.md"
                }
                for repo_entry in section_repos:
                    section_nav.update(repo_entry)

                nav.append({section_name: section_nav})

        # Add global sections
        api_section: dict[str, Any] = {
            "API Reference": {"Overview": "api/index.md"}
        }
        dev_section: dict[str, Any] = {
            "Development": [
                {"Getting Started": "dev/getting-started.md"},
                {"Contributing": "dev/contributing.md"},
                {"Architecture": "dev/architecture.md"},
            ]
        }
        nav.extend([api_section, dev_section])

        return nav

    async def _build_repo_navigation(
        self, repo: dict[str, Any]
    ) -> dict[str, str]:
        """
        Build navigation entry for a single repository.

        Args:
            repo: Repository configuration

        Returns:
            Navigation entry for the repository
        """
        repo_name = repo["name"]

        # Extract short name (without org prefix)
        if "/" in repo_name:
            _, repo_short = repo_name.split("/", 1)
        else:
            repo_short = repo_name

        # Create multirepo import string
        import_url = repo["import_url"]

        return {repo_short.title(): f"!import {import_url}"}

    async def _configure_plugins(
        self, enrolled_repos: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Configure plugins for unified documentation.

        Args:
            enrolled_repos: List of enrolled repositories

        Returns:
            Plugin configuration list
        """
        plugins: list[dict[str, Any]] = [
            {
                "search": {
                    "separator": r'[\s\-,:!=\[\]()"`/]+|\.(?!\d)|&[lg]t;|(?!\b)(?=[A-Z][a-z])'  # noqa: E501
                }
            }
        ]

        # Add multirepo plugin if repositories are enrolled
        if enrolled_repos:
            multirepo_config: dict[str, Any] = {
                "multirepo": {"cleanup": True, "keep_docs_dir": True}
            }
            plugins.append(multirepo_config)

        # Add additional plugins
        plugins.extend([{"mermaid2": {"arguments": {"theme": "default"}}}])

        return plugins

    async def _merge_repo_configs(
        self, base_config: dict[str, Any], enrolled_repos: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Merge repository-specific configurations.

        Args:
            base_config: Base configuration
            enrolled_repos: List of enrolled repositories

        Returns:
            Configuration with repository-specific settings merged
        """
        config = base_config.copy()

        # Add watch paths for all repositories
        watch_paths = config.get("watch", [])
        watch_paths.extend(["src/", "docs/"])

        for repo in enrolled_repos:
            # Add repository-specific watch paths if available
            repo_config = repo.get("config", {})
            repo_watch = repo_config.get("watch", [])
            watch_paths.extend(repo_watch)

        config["watch"] = list(set(watch_paths))  # Remove duplicates

        return config

    async def _write_config_file(
        self, config: dict[str, Any], output_path: Path
    ) -> None:
        """
        Write configuration to YAML file.

        Args:
            config: Configuration dictionary
            output_path: Path to output file
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write YAML configuration
        with output_path.open("w", encoding="utf-8") as f:
            yaml.dump(
                config,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=80,
            )

        logger.info("Written unified config to %s", output_path)


# Global generator instance
_config_generator: UnifiedConfigGenerator | None = None


def get_config_generator() -> UnifiedConfigGenerator:
    """Get the global config generator instance."""
    global _config_generator  # noqa: PLW0603
    if _config_generator is None:
        _config_generator = UnifiedConfigGenerator()
    return _config_generator


async def generate_unified_config(
    output_path: Path | None = None,
) -> dict[str, Any]:
    """
    Generate unified MkDocs configuration.

    Args:
        output_path: Optional path to write config file

    Returns:
        Generated configuration
    """
    generator = get_config_generator()
    return await generator.generate_unified_config(output_path)
