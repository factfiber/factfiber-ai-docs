# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001

"""Unit tests for markdown link rewriter."""

from pathlib import Path

import pytest

from ff_docs.pipeline.rewriter import (
    LinkRewriteRule,
    MarkdownLinkRewriter,
    create_link_rewriter_for_repos,
)


class TestLinkRewriteRule:
    """Test LinkRewriteRule model."""

    def test_link_rewrite_rule_creation(self) -> None:
        """Test creating LinkRewriteRule with all fields."""
        rule = LinkRewriteRule(
            repo_name="org/test-repo",
            base_path="/projects/test-repo/",
            docs_dir="docs",
            preserve_anchors=True,
            preserve_query_params=True,
        )

        assert rule.repo_name == "org/test-repo"
        assert rule.base_path == "/projects/test-repo/"
        assert rule.docs_dir == "docs"
        assert rule.preserve_anchors is True
        assert rule.preserve_query_params is True

    def test_link_rewrite_rule_defaults(self) -> None:
        """Test LinkRewriteRule with default values."""
        rule = LinkRewriteRule(
            repo_name="org/test-repo",
            base_path="/projects/test-repo/",
        )

        assert rule.docs_dir == "docs"
        assert rule.preserve_anchors is True
        assert rule.preserve_query_params is True


class TestMarkdownLinkRewriter:
    """Test MarkdownLinkRewriter."""

    @pytest.fixture
    def rewrite_rules(self) -> dict[str, LinkRewriteRule]:
        """Create test rewrite rules."""
        return {
            "org/test-repo": LinkRewriteRule(
                repo_name="org/test-repo",
                base_path="/projects/test-repo/",
                docs_dir="docs",
            ),
            "org/another-repo": LinkRewriteRule(
                repo_name="org/another-repo",
                base_path="/projects/another-repo/",
                docs_dir="documentation",
            ),
        }

    @pytest.fixture
    def rewriter(
        self, rewrite_rules: dict[str, LinkRewriteRule]
    ) -> MarkdownLinkRewriter:
        """Create MarkdownLinkRewriter instance."""
        return MarkdownLinkRewriter(rewrite_rules)

    def test_rewrite_file_content_simple_link(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting simple relative link."""
        content = "Check out the [guide](guide/setup.md) for more info."
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/index.md"
        )

        expected = (
            "Check out the [guide](/projects/test-repo/guide/setup/) for "
            "more info."
        )
        assert result == expected

    def test_rewrite_file_content_parent_directory(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting link with parent directory reference."""
        content = "See the [API docs](../api/reference.md) for details."
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/guide/setup.md"
        )

        expected = (
            "See the [API docs](/projects/test-repo/api/reference/) for "
            "details."
        )
        assert result == expected

    def test_rewrite_file_content_with_anchor(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting link with anchor."""
        content = "Jump to [installation](guide/setup.md#installation)"
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/index.md"
        )

        expected = (
            "Jump to [installation]"
            "(/projects/test-repo/guide/setup/#installation)"
        )
        assert result == expected

    def test_rewrite_file_content_with_query_params(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting link with query parameters."""
        content = "View [search results](search.md?q=test&type=docs)"
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/index.md"
        )

        expected = (
            "View [search results]"
            "(/projects/test-repo/search/?q=test&type=docs)"
        )
        assert result == expected

    def test_rewrite_file_content_absolute_url(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test that absolute URLs are not rewritten."""
        content = "Visit [GitHub](https://github.com/org/repo)"
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/index.md"
        )

        assert result == content  # Should not change

    def test_rewrite_file_content_mailto_link(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test that mailto links are not rewritten."""
        content = "Contact [support](mailto:support@example.com)"
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/index.md"
        )

        assert result == content  # Should not change

    def test_rewrite_file_content_anchor_only(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test that anchor-only links are not rewritten."""
        content = "Jump to [section](#section-name)"
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/index.md"
        )

        assert result == content  # Should not change

    def test_rewrite_file_content_reference_links(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting reference-style links."""
        content = """
See the guide[1] for more info.

[1]: guide/setup.md
[2]: https://example.com
"""
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/index.md"
        )

        expected = """
See the guide[1] for more info.

[1]: /projects/test-repo/guide/setup/
[2]: https://example.com
"""
        assert result == expected

    def test_rewrite_file_content_multiple_links(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting multiple links in content."""
        content = """
# Documentation

- [Getting Started](guide/quickstart.md)
- [API Reference](api/index.md)
- [Examples](../examples/basic.md)
- [GitHub](https://github.com/org/repo)
"""
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/overview/index.md"
        )

        expected = """
# Documentation

- [Getting Started](/projects/test-repo/guide/quickstart/)
- [API Reference](/projects/test-repo/api/index/)
- [Examples](/projects/test-repo/examples/basic/)
- [GitHub](https://github.com/org/repo)
"""
        assert result == expected

    def test_rewrite_file_content_unknown_repo(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting with unknown repository."""
        content = "Check out the [guide](guide/setup.md)"
        result = rewriter.rewrite_file_content(
            content, "org/unknown-repo", "docs/index.md"
        )

        assert result == content  # Should not change

    def test_rewrite_file_content_rst_extension(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting .rst file extensions."""
        content = "See [documentation](guide/setup.rst)"
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/index.md"
        )

        assert result == "See [documentation](/projects/test-repo/guide/setup/)"

    def test_rewrite_file_content_complex_path(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting complex relative paths."""
        content = "See [config](../../config/settings.md)"
        result = rewriter.rewrite_file_content(
            content, "org/test-repo", "docs/guide/advanced/usage.md"
        )

        assert result == "See [config](/projects/test-repo/config/settings/)"

    def test_rewrite_file_content_different_docs_dir(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test rewriting with non-standard docs directory."""
        content = "Check the [API](api/client.md)"
        result = rewriter.rewrite_file_content(
            content, "org/another-repo", "documentation/index.md"
        )

        assert result == "Check the [API](/projects/another-repo/api/client/)"

    def test_resolve_relative_path(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test _resolve_relative_path method."""
        source_dir = Path("docs/guide")

        # Simple relative path (resolved relative to docs root)
        result = rewriter._resolve_relative_path(source_dir, "setup.md")
        assert result == Path("docs/setup.md")

        # Parent directory reference (resolved relative to current dir)
        result = rewriter._resolve_relative_path(
            source_dir, "../api/reference.md"
        )
        assert result == Path("docs/api/reference.md")

        # Current directory reference (resolved relative to docs root)
        result = rewriter._resolve_relative_path(source_dir, "./advanced.md")
        assert result == Path("docs/advanced.md")

    def test_convert_to_unified_path(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test _convert_to_unified_path method."""
        rule = LinkRewriteRule(
            repo_name="org/test-repo",
            base_path="/projects/test-repo/",
            docs_dir="docs",
        )

        # Markdown file
        result = rewriter._convert_to_unified_path(
            Path("docs/guide/setup.md"), rule
        )
        assert result == "/projects/test-repo/guide/setup/"

        # RST file
        result = rewriter._convert_to_unified_path(
            Path("docs/api/reference.rst"), rule
        )
        assert result == "/projects/test-repo/api/reference/"

        # Directory
        result = rewriter._convert_to_unified_path(Path("docs/examples"), rule)
        assert result == "/projects/test-repo/examples/"

        # File without docs prefix
        result = rewriter._convert_to_unified_path(Path("guide/setup.md"), rule)
        assert result == "/projects/test-repo/guide/setup/"

    def test_convert_to_unified_path_docs_dir_edge_case(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test docs_dir edge case without trailing slash (line 270)."""
        rule = LinkRewriteRule(
            repo_name="org/test-repo",
            base_path="/projects/test-repo/",
            docs_dir="docs",
        )

        # Path that starts exactly with docs_dir but no trailing slash
        # This triggers line 270: path_str = path_str[len(rule.docs_dir):]
        result = rewriter._convert_to_unified_path(Path("docsfile.md"), rule)
        assert result == "/projects/test-repo/file/"

    def test_rewrite_url(self, rewriter: MarkdownLinkRewriter) -> None:
        """Test _rewrite_url method."""
        rule = LinkRewriteRule(
            repo_name="org/test-repo",
            base_path="/projects/test-repo/",
            docs_dir="docs",
        )

        # Simple URL
        result = rewriter._rewrite_url("guide/setup.md", rule, "docs/index.md")
        assert result == "/projects/test-repo/guide/setup/"

        # URL with anchor
        result = rewriter._rewrite_url(
            "guide/setup.md#install", rule, "docs/index.md"
        )
        assert result == "/projects/test-repo/guide/setup/#install"

        # URL with query params
        result = rewriter._rewrite_url(
            "search.md?q=test", rule, "docs/index.md"
        )
        assert result == "/projects/test-repo/search/?q=test"

        # URL with both
        result = rewriter._rewrite_url(
            "api.md?version=2#methods", rule, "docs/index.md"
        )
        assert result == "/projects/test-repo/api/?version=2#methods"

    def test_rewrite_url_no_preserve(
        self, rewriter: MarkdownLinkRewriter
    ) -> None:
        """Test URL rewriting without preserving anchors/params."""
        rule = LinkRewriteRule(
            repo_name="org/test-repo",
            base_path="/projects/test-repo/",
            preserve_anchors=False,
            preserve_query_params=False,
        )

        result = rewriter._rewrite_url(
            "api.md?version=2#methods", rule, "docs/index.md"
        )
        assert result == "/projects/test-repo/api/"


class TestModuleFunctions:
    """Test module-level functions."""

    def test_create_link_rewriter_for_repos(self) -> None:
        """Test creating rewriter from enrolled repositories."""
        enrolled_repos = [
            {
                "name": "org/test-repo",
                "url": "https://github.com/org/test-repo",
            },
            {
                "name": "org/another-repo",
                "url": "https://github.com/org/another-repo",
            },
            {"name": "single-repo", "url": "https://github.com/single-repo"},
        ]

        rewriter = create_link_rewriter_for_repos(enrolled_repos)

        assert isinstance(rewriter, MarkdownLinkRewriter)
        assert len(rewriter.rewrite_rules) == 3

        # Check first repo rule
        rule1 = rewriter.rewrite_rules["org/test-repo"]
        assert rule1.repo_name == "org/test-repo"
        assert rule1.base_path == "/projects/test-repo/docs/"

        # Check second repo rule
        rule2 = rewriter.rewrite_rules["org/another-repo"]
        assert rule2.repo_name == "org/another-repo"
        assert rule2.base_path == "/projects/another-repo/docs/"

        # Check single repo (no org prefix)
        rule3 = rewriter.rewrite_rules["single-repo"]
        assert rule3.repo_name == "single-repo"
        assert rule3.base_path == "/projects/single-repo/docs/"

    def test_create_link_rewriter_empty_repos(self) -> None:
        """Test creating rewriter with no repositories."""
        rewriter = create_link_rewriter_for_repos([])

        assert isinstance(rewriter, MarkdownLinkRewriter)
        assert len(rewriter.rewrite_rules) == 0
