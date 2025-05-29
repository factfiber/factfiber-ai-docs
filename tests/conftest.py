# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Pytest configuration and shared fixtures."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ff_docs.server.main import create_app


@pytest.fixture  # type: ignore[misc]
def app() -> FastAPI:
    """Create test FastAPI application."""
    return create_app()


@pytest.fixture  # type: ignore[misc]
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture  # type: ignore[misc]
def sample_repo_config() -> dict[str, object]:
    """Sample repository configuration for testing."""
    return {
        "name": "test-repo",
        "url": "https://github.com/factfiber/test-repo",
        "branch": "main",
        "docs_path": "docs/",
        "enabled": True,
    }
