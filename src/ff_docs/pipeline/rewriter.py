# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""
Markdown link rewriting system for unified navigation.

This module handles transparent rewriting of relative links in markdown files
to create seamless navigation across repositories in the unified documentation
system. It preserves the original authoring experience while enabling
cross-repository linking.
"""

import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LinkRewriteRule(BaseModel):
    """Configuration for link rewriting behavior."""

    repo_name: str
    base_path: str  # e.g., "/docs/timbuktu/"
    docs_dir: str = "docs"  # relative path within repo
    preserve_anchors: bool = True
    preserve_query_params: bool = True


class MarkdownLinkRewriter:
    """
    Service for rewriting markdown links to unified navigation format.

    This rewriter transforms relative links in repository documentation
    to work within the unified documentation site structure without
    requiring changes to the original markdown files.
    """

    # Regex patterns for different types of links
    MARKDOWN_LINK_PATTERN = re.compile(
        r"\[([^\]]*)\]\(([^)]+)\)",  # [text](url)
        re.MULTILINE,
    )

    MARKDOWN_REF_LINK_PATTERN = re.compile(
        r"\[([^\]]*)\]:\s*([^\s]+)",  # [ref]: url
        re.MULTILINE,
    )

    RELATIVE_LINK_PATTERN = re.compile(
        r"^(?!https?://|mailto:|#)([^/].*)",  # Not absolute URL, mailto, or fragment
        re.IGNORECASE,
    )

    def __init__(self, rewrite_rules: dict[str, LinkRewriteRule]) -> None:
        """
        Initialize the link rewriter with repository-specific rules.

        Args:
            rewrite_rules: Dictionary mapping repo names to rewrite rules
        """
        self.rewrite_rules = rewrite_rules

    def rewrite_file_content(
        self, content: str, source_repo: str, source_file_path: str
    ) -> str:
        """
        Rewrite all links in markdown content for unified navigation.

        Args:
            content: Original markdown content
            source_repo: Name of source repository
            source_file_path: Path of file within repository

        Returns:
            Modified content with rewritten links
        """
        if source_repo not in self.rewrite_rules:
            logger.warning(
                "No rewrite rules found for repository: %s", source_repo
            )
            return content

        rule = self.rewrite_rules[source_repo]

        # Rewrite inline links [text](url)
        content = self._rewrite_inline_links(content, rule, source_file_path)

        # Rewrite reference links [ref]: url
        content = self._rewrite_reference_links(content, rule, source_file_path)

        return content

    def _rewrite_inline_links(
        self, content: str, rule: LinkRewriteRule, source_file_path: str
    ) -> str:
        """
        Rewrite inline markdown links [text](url).

        Args:
            content: Markdown content
            rule: Rewrite rule for the repository
            source_file_path: Path of source file

        Returns:
            Content with rewritten inline links
        """

        def replace_link(match: re.Match[str]) -> str:
            text = match.group(1)
            url = match.group(2)

            # Skip non-relative links
            if not self.RELATIVE_LINK_PATTERN.match(url):
                return match.group(0)

            # Rewrite the URL
            new_url = self._rewrite_url(url, rule, source_file_path)
            return f"[{text}]({new_url})"

        return self.MARKDOWN_LINK_PATTERN.sub(replace_link, content)

    def _rewrite_reference_links(
        self, content: str, rule: LinkRewriteRule, source_file_path: str
    ) -> str:
        """
        Rewrite reference markdown links [ref]: url.

        Args:
            content: Markdown content
            rule: Rewrite rule for the repository
            source_file_path: Path of source file

        Returns:
            Content with rewritten reference links
        """

        def replace_ref_link(match: re.Match[str]) -> str:
            ref = match.group(1)
            url = match.group(2)

            # Skip non-relative links
            if not self.RELATIVE_LINK_PATTERN.match(url):
                return match.group(0)

            # Rewrite the URL
            new_url = self._rewrite_url(url, rule, source_file_path)
            return f"[{ref}]: {new_url}"

        return self.MARKDOWN_REF_LINK_PATTERN.sub(replace_ref_link, content)

    def _rewrite_url(
        self, original_url: str, rule: LinkRewriteRule, source_file_path: str
    ) -> str:
        """
        Rewrite a single URL to unified format.

        Args:
            original_url: Original relative URL
            rule: Rewrite rule for the repository
            source_file_path: Path of source file within repository

        Returns:
            Rewritten URL for unified navigation
        """
        # Parse URL components
        url_parts = original_url.split("#", 1)
        base_url = url_parts[0]
        anchor = f"#{url_parts[1]}" if len(url_parts) > 1 else ""

        # Handle query parameters
        query_parts = base_url.split("?", 1)
        path_part = query_parts[0]
        query = f"?{query_parts[1]}" if len(query_parts) > 1 else ""

        # Resolve relative path
        source_dir = Path(source_file_path).parent
        resolved_path = self._resolve_relative_path(source_dir, path_part)

        # Convert to unified format
        unified_path = self._convert_to_unified_path(resolved_path, rule)

        # Reconstruct URL
        result = unified_path
        if query and rule.preserve_query_params:
            result += query
        if anchor and rule.preserve_anchors:
            result += anchor

        logger.debug(
            "Rewritten link: %s -> %s (repo: %s, source: %s)",
            original_url,
            result,
            rule.repo_name,
            source_file_path,
        )

        return result

    def _resolve_relative_path(
        self, source_dir: Path, relative_path: str
    ) -> Path:
        """
        Resolve relative path from source directory.

        Args:
            source_dir: Directory containing the source file
            relative_path: Relative path to resolve

        Returns:
            Resolved path
        """
        # Handle current directory and parent directory references
        relative_path = relative_path.removeprefix("./")

        # Resolve path relative to source directory
        resolved = source_dir / relative_path

        # Normalize path (resolve .. references)
        try:
            resolved = resolved.resolve()
        except (OSError, ValueError):
            # If resolution fails, use simple normalization
            resolved = Path(*[p for p in resolved.parts if p != "."])

        return resolved

    def _convert_to_unified_path(
        self, resolved_path: Path, rule: LinkRewriteRule
    ) -> str:
        """
        Convert resolved path to unified documentation format.

        Args:
            resolved_path: Resolved file path
            rule: Rewrite rule for the repository

        Returns:
            Unified path for the documentation site
        """
        # Convert path to string and normalize separators
        path_str = str(resolved_path).replace("\\", "/")

        # Remove docs/ prefix if present
        if path_str.startswith(f"{rule.docs_dir}/"):
            path_str = path_str[len(rule.docs_dir) + 1 :]
        elif path_str.startswith(rule.docs_dir):
            path_str = path_str[len(rule.docs_dir) :]

        # Handle markdown file extensions
        if path_str.endswith(".md"):
            path_str = path_str[:-3] + "/"
        elif path_str.endswith(".rst"):
            path_str = path_str[:-4] + "/"

        # Ensure path starts with /
        if not path_str.startswith("/"):
            path_str = "/" + path_str

        # Construct unified path
        unified_path = urljoin(rule.base_path, path_str.lstrip("/"))

        # Ensure trailing slash for directories
        if (
            not unified_path.endswith("/")
            and "." not in Path(unified_path).name
        ):
            unified_path += "/"

        return unified_path


def create_link_rewriter_for_repos(
    enrolled_repos: list[dict[str, Any]],
) -> MarkdownLinkRewriter:
    """
    Create a link rewriter configured for enrolled repositories.

    Args:
        enrolled_repos: List of enrolled repository configurations

    Returns:
        Configured MarkdownLinkRewriter instance
    """
    rewrite_rules = {}

    for repo in enrolled_repos:
        repo_name = repo["name"]

        # Extract organization and repository name
        if "/" in repo_name:
            org, repo_short = repo_name.split("/", 1)
        else:
            org = "unknown"
            repo_short = repo_name

        # Create rewrite rule
        rule = LinkRewriteRule(
            repo_name=repo_name,
            base_path=f"/projects/{repo_short}/docs/",
            docs_dir="docs",
            preserve_anchors=True,
            preserve_query_params=True,
        )

        rewrite_rules[repo_name] = rule

    return MarkdownLinkRewriter(rewrite_rules)
