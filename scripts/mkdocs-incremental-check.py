#!/usr/bin/env python3
"""Incremental MkDocs validation - only checks changed files."""

# ruff: noqa: T201 S603 S607 TRY300

import subprocess
import sys


def get_changed_files() -> list[str]:
    """Get list of changed files in the current commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )
        return files
    except subprocess.CalledProcessError:
        return []


def should_run_mkdocs_validation(changed_files: list[str]) -> bool:
    """Determine if MkDocs validation is needed based on changed files."""
    # Patterns that require MkDocs validation
    validation_patterns = [
        "mkdocs.yml",
        "mkdocs-unified.yml",
        ".github/workflows/docs.yml",
        "docs/",  # Any documentation changes
        "pyproject.toml",  # Dependency changes might affect plugins
    ]

    for file in changed_files:
        for pattern in validation_patterns:
            if pattern in file:
                return True
    return False


def run_mkdocs_validation() -> bool:
    """Run MkDocs build with strict validation."""
    print("🔍 Running MkDocs validation...")
    try:
        subprocess.run(
            ["poetry", "run", "mkdocs", "build", "--strict", "--quiet"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ MkDocs validation failed: {e}")
        return False
    else:
        print("✅ MkDocs validation passed!")
        return True


def main() -> int:
    """Main function to run incremental validation."""
    changed_files = get_changed_files()

    if not changed_files:
        print("📋 No staged files to check")
        return 0

    if should_run_mkdocs_validation(changed_files):
        if run_mkdocs_validation():
            return 0
        return 1
    print("⏭️  Skipping MkDocs validation - no documentation changes detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
