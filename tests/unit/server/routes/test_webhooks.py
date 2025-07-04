# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Unit tests for webhooks routes module."""

import hashlib
import hmac
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ff_docs.server.routes.webhooks import (
    GitHubWebhookPayload,
    WebhookResponse,
    contains_docs_changes,
    verify_github_signature,
)


class TestWebhookModels:
    """Test webhook-related Pydantic models."""

    def test_github_webhook_payload_minimal(self) -> None:
        """Test GitHubWebhookPayload with minimal data."""
        payload = GitHubWebhookPayload()

        assert payload.action is None
        assert payload.repository == {}
        assert payload.commits == []
        assert payload.head_commit is None
        assert payload.ref == ""
        assert payload.before == ""
        assert payload.after == ""
        assert payload.pusher == {}

    def test_github_webhook_payload_full(self) -> None:
        """Test GitHubWebhookPayload with full data."""
        payload_data = {
            "action": "push",
            "repository": {"name": "test-repo", "full_name": "org/test-repo"},
            "commits": [{"id": "abc123", "message": "Update docs"}],
            "head_commit": {"id": "abc123", "message": "Update docs"},
            "ref": "refs/heads/main",
            "before": "def456",
            "after": "abc123",
            "pusher": {"name": "testuser", "email": "test@example.com"},
        }

        payload = GitHubWebhookPayload(**payload_data)

        assert payload.action == "push"
        assert payload.repository["name"] == "test-repo"
        assert len(payload.commits) == 1
        assert payload.head_commit is not None
        assert payload.ref == "refs/heads/main"
        assert payload.before == "def456"
        assert payload.after == "abc123"
        assert payload.pusher["name"] == "testuser"

    def test_webhook_response_model(self) -> None:
        """Test WebhookResponse model."""
        response = WebhookResponse(
            status="processed",
            message="Documentation sync triggered",
            repository="org/test-repo",
            commit_sha="abc123",
            docs_updated=True,
        )

        assert response.status == "processed"
        assert response.message == "Documentation sync triggered"
        assert response.repository == "org/test-repo"
        assert response.commit_sha == "abc123"
        assert response.docs_updated is True


class TestWebhookUtilities:
    """Test webhook utility functions."""

    def test_verify_github_signature_valid(self) -> None:
        """Test verifying valid GitHub webhook signature."""
        secret = "test-secret"  # noqa: S105
        payload = b'{"test": "data"}'

        # Generate valid signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        signature = f"sha256={expected_signature}"

        assert verify_github_signature(payload, signature, secret) is True

    def test_verify_github_signature_invalid(self) -> None:
        """Test verifying invalid GitHub webhook signature."""
        secret = "test-secret"  # noqa: S105
        payload = b'{"test": "data"}'
        invalid_signature = "sha256=invalid_signature"

        assert (
            verify_github_signature(payload, invalid_signature, secret) is False
        )

    def test_verify_github_signature_no_prefix(self) -> None:
        """Test verifying signature without sha256= prefix."""
        secret = "test-secret"  # noqa: S105
        payload = b'{"test": "data"}'
        signature = "invalid_format_signature"

        assert verify_github_signature(payload, signature, secret) is False

    def test_verify_github_signature_wrong_secret(self) -> None:
        """Test verifying signature with wrong secret."""
        payload = b'{"test": "data"}'

        # Generate signature with one secret
        signature_secret = "secret1"  # noqa: S105
        expected_signature = hmac.new(
            signature_secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        signature = f"sha256={expected_signature}"

        # Verify with different secret
        verify_secret = "secret2"  # noqa: S105
        assert (
            verify_github_signature(payload, signature, verify_secret) is False
        )

    def test_contains_docs_changes_true(self) -> None:
        """Test detecting documentation changes."""
        commits = [
            {
                "id": "abc123",
                "added": ["docs/guide.md", "src/main.py"],
                "modified": [],
                "removed": [],
            },
            {
                "id": "def456",
                "added": [],
                "modified": ["README.md"],
                "removed": [],
            },
        ]

        assert contains_docs_changes(commits) is True

    def test_contains_docs_changes_mkdocs_config(self) -> None:
        """Test detecting mkdocs.yml changes."""
        commits = [
            {
                "id": "abc123",
                "added": [],
                "modified": ["mkdocs.yml"],
                "removed": [],
            }
        ]

        assert contains_docs_changes(commits) is True

    def test_contains_docs_changes_factfiber_config(self) -> None:
        """Test detecting .factfiber-docs.yml changes."""
        commits = [
            {
                "id": "abc123",
                "added": [],
                "modified": ["src/main.py"],
                "removed": [".factfiber-docs.yaml"],
            }
        ]

        assert contains_docs_changes(commits) is True

    def test_contains_docs_changes_false(self) -> None:
        """Test no documentation changes detected."""
        commits = [
            {
                "id": "abc123",
                "added": ["src/main.py", "tests/test_main.py"],
                "modified": ["requirements.txt"],
                "removed": [".gitignore"],
            }
        ]

        assert contains_docs_changes(commits) is False

    def test_contains_docs_changes_empty_commits(self) -> None:
        """Test with empty commits list."""
        assert contains_docs_changes([]) is False

    def test_contains_docs_changes_missing_file_lists(self) -> None:
        """Test with commits missing file lists."""
        commits = [
            {
                "id": "abc123",
                # Missing added, modified, removed
            }
        ]

        assert contains_docs_changes(commits) is False


class TestWebhookRoutes:
    """Test webhook route handlers."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        from ff_docs.server.main import app

        return TestClient(app)

    @pytest.fixture
    def webhook_payload(self) -> dict[str, Any]:
        """Create test webhook payload."""
        return {
            "action": "push",
            "repository": {
                "name": "test-repo",
                "full_name": "org/test-repo",
                "url": "https://github.com/org/test-repo",
            },
            "commits": [
                {
                    "id": "abc123",
                    "message": "Update documentation",
                    "added": ["docs/guide.md"],
                    "modified": [],
                    "removed": [],
                }
            ],
            "head_commit": {
                "id": "abc123",
                "message": "Update documentation",
            },
            "ref": "refs/heads/main",
            "before": "def456",
            "after": "abc123",
            "pusher": {"name": "testuser", "email": "test@example.com"},
        }

    def generate_webhook_signature(self, payload: bytes, secret: str) -> str:
        """Generate GitHub webhook signature."""
        signature = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    @pytest.mark.asyncio
    async def test_handle_github_webhook_success(
        self, client: TestClient, webhook_payload: dict[str, Any]
    ) -> None:
        """Test successful webhook processing."""
        # Mock settings with webhook secret
        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.webhook_secret = "test-secret"  # noqa: S105

            # Mock enrollment check
            with patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories"
            ) as mock_get_enrolled:

                async def async_mock() -> list[dict[str, str]]:
                    return [
                        {
                            "name": "org/test-repo",
                            "url": "https://github.com/org/test-repo",
                        }
                    ]

                mock_get_enrolled.side_effect = async_mock

                # Mock sync trigger
                with patch(
                    "ff_docs.pipeline.sync.trigger_docs_sync"
                ) as mock_trigger:
                    mock_sync_status = MagicMock()
                    mock_sync_status.status = "pending"

                    async def async_trigger(
                        *args: Any,  # noqa: ANN401
                        **kwargs: Any,  # noqa: ANN401
                    ) -> MagicMock:
                        return mock_sync_status

                    mock_trigger.side_effect = async_trigger

                    # Prepare request
                    payload_bytes = json.dumps(webhook_payload).encode()
                    signature = self.generate_webhook_signature(
                        payload_bytes, "test-secret"
                    )

                    response = client.post(
                        "/webhooks/github",
                        content=payload_bytes,
                        headers={
                            "X-Hub-Signature-256": signature,
                            "X-GitHub-Event": "push",
                            "X-GitHub-Delivery": "test-delivery-123",
                            "Content-Type": "application/json",
                        },
                    )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processed"
        assert data["repository"] == "org/test-repo"
        assert data["docs_updated"] is True

    @pytest.mark.asyncio
    async def test_handle_github_webhook_invalid_signature(
        self, client: TestClient, webhook_payload: dict[str, Any]
    ) -> None:
        """Test webhook with invalid signature."""
        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.webhook_secret = "test-secret"  # noqa: S105

            payload_bytes = json.dumps(webhook_payload).encode()
            invalid_signature = "sha256=invalid_signature"

            response = client.post(
                "/webhooks/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": invalid_signature,
                    "X-GitHub-Event": "push",
                    "X-GitHub-Delivery": "test-delivery-123",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid webhook signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_handle_github_webhook_no_signature_verification(
        self, client: TestClient, webhook_payload: dict[str, Any]
    ) -> None:
        """Test webhook without signature verification (no secret)."""
        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            # No webhook secret configured
            mock_settings.return_value.github.webhook_secret = None

            with patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories"
            ) as mock_get_enrolled:
                mock_get_enrolled.return_value = [{"name": "org/test-repo"}]

                with patch(
                    "ff_docs.pipeline.sync.trigger_docs_sync",
                    AsyncMock(return_value=MagicMock(status="pending")),
                ):
                    response = client.post(
                        "/webhooks/github",
                        json=webhook_payload,
                        headers={
                            "X-GitHub-Event": "push",
                            "X-GitHub-Delivery": "test-delivery-123",
                        },
                    )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_handle_github_webhook_invalid_payload(
        self, client: TestClient
    ) -> None:
        """Test webhook with invalid payload."""
        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.webhook_secret = None

            response = client.post(
                "/webhooks/github",
                content=b"invalid json",
                headers={
                    "X-GitHub-Event": "push",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid webhook payload" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_handle_github_webhook_non_push_event(
        self, client: TestClient, webhook_payload: dict[str, Any]
    ) -> None:
        """Test webhook with non-push event."""
        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.webhook_secret = None

            response = client.post(
                "/webhooks/github",
                json=webhook_payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-delivery-123",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ignored"
        assert "pull_request" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_github_webhook_missing_repo_name(
        self, client: TestClient
    ) -> None:
        """Test webhook with missing repository name."""
        payload = {
            "repository": {},  # Missing name
            "commits": [],
            "ref": "refs/heads/main",
        }

        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.webhook_secret = None

            response = client.post(
                "/webhooks/github",
                json=payload,
                headers={
                    "X-GitHub-Event": "push",
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Repository name not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_handle_github_webhook_not_enrolled(
        self, client: TestClient, webhook_payload: dict[str, Any]
    ) -> None:
        """Test webhook for non-enrolled repository."""
        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.webhook_secret = None

            with patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories"
            ) as mock_get_enrolled:
                mock_get_enrolled.return_value = []  # No enrolled repos

                response = client.post(
                    "/webhooks/github",
                    json=webhook_payload,
                    headers={
                        "X-GitHub-Event": "push",
                    },
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ignored"
        assert "not enrolled" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_github_webhook_enrollment_check_error(
        self, client: TestClient, webhook_payload: dict[str, Any]
    ) -> None:
        """Test webhook when enrollment check fails."""
        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.webhook_secret = None

            with patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories"
            ) as mock_get_enrolled:
                mock_get_enrolled.side_effect = ValueError("Enrollment error")

                with patch(
                    "ff_docs.pipeline.sync.trigger_docs_sync",
                    AsyncMock(return_value=MagicMock(status="pending")),
                ):
                    response = client.post(
                        "/webhooks/github",
                        json=webhook_payload,
                        headers={
                            "X-GitHub-Event": "push",
                        },
                    )

        # Should continue processing despite enrollment error
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_handle_github_webhook_no_docs_changes(
        self, client: TestClient
    ) -> None:
        """Test webhook with no documentation changes."""
        payload = {
            "repository": {
                "name": "test-repo",
                "full_name": "org/test-repo",
            },
            "commits": [
                {
                    "id": "abc123",
                    "added": ["src/main.py"],
                    "modified": ["tests/test_main.py"],
                    "removed": [],
                }
            ],
            "ref": "refs/heads/main",
            "after": "abc123",
        }

        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.webhook_secret = None

            with patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories"
            ) as mock_get_enrolled:
                mock_get_enrolled.return_value = [{"name": "org/test-repo"}]

                response = client.post(
                    "/webhooks/github",
                    json=payload,
                    headers={
                        "X-GitHub-Event": "push",
                    },
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ignored"
        assert "No documentation changes" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_github_webhook_sync_trigger_error(
        self, client: TestClient, webhook_payload: dict[str, Any]
    ) -> None:
        """Test webhook when sync trigger fails."""
        with patch(
            "ff_docs.server.routes.webhooks.get_settings"
        ) as mock_settings:
            mock_settings.return_value.github.webhook_secret = None

            with patch(
                "ff_docs.aggregator.enrollment.get_enrolled_repositories"
            ) as mock_get_enrolled:
                mock_get_enrolled.return_value = [{"name": "org/test-repo"}]

                with patch(
                    "ff_docs.pipeline.sync.trigger_docs_sync"
                ) as mock_trigger:
                    mock_trigger.side_effect = Exception("Sync error")

                    response = client.post(
                        "/webhooks/github",
                        json=webhook_payload,
                        headers={
                            "X-GitHub-Event": "push",
                        },
                    )

        # Should still return success as webhook was processed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processed"

    def test_test_webhook_endpoint(self, client: TestClient) -> None:
        """Test the webhook test endpoint."""
        response = client.get("/webhooks/github/test")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert "operational" in data["message"]
        assert data["endpoint"] == "/webhooks/github"

    @pytest.mark.asyncio
    async def test_get_sync_status_found(self, client: TestClient) -> None:
        """Test getting sync status for a repository."""
        with patch(
            "ff_docs.pipeline.sync.get_content_sync_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_status = MagicMock()
            mock_status.model_dump.return_value = {
                "repository": "org/test-repo",
                "status": "completed",
                "last_sync": "2024-01-01T00:00:00Z",
            }
            mock_service.get_sync_status.return_value = mock_status
            mock_get_service.return_value = mock_service

            response = client.get("/webhooks/sync/status/org/test-repo")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["repository"] == "org/test-repo"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_sync_status_not_found(self, client: TestClient) -> None:
        """Test getting sync status for unknown repository."""
        with patch(
            "ff_docs.pipeline.sync.get_content_sync_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_sync_status.return_value = None
            mock_get_service.return_value = mock_service

            response = client.get("/webhooks/sync/status/unknown/repo")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No sync status found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_all_sync_status(self, client: TestClient) -> None:
        """Test getting sync status for all repositories."""
        with patch(
            "ff_docs.pipeline.sync.get_content_sync_service"
        ) as mock_get_service:
            mock_service = MagicMock()

            mock_status1 = MagicMock()
            mock_status1.model_dump.return_value = {
                "repository": "org/repo1",
                "status": "completed",
            }

            mock_status2 = MagicMock()
            mock_status2.model_dump.return_value = {
                "repository": "org/repo2",
                "status": "pending",
            }

            mock_service.get_all_sync_status.return_value = {
                "org/repo1": mock_status1,
                "org/repo2": mock_status2,
            }
            mock_get_service.return_value = mock_service

            response = client.get("/webhooks/sync/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "org/repo1" in data
        assert data["org/repo1"]["status"] == "completed"
        assert "org/repo2" in data
        assert data["org/repo2"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_generate_unified_config_success(
        self, client: TestClient
    ) -> None:
        """Test generating unified configuration."""
        with patch(
            "ff_docs.pipeline.config_generator.generate_unified_config"
        ) as mock_generate:
            mock_config = {
                "site_name": "Unified Docs",
                "nav": [
                    {"Home": "index.md"},
                    {"Guide": "guide.md"},
                ],
                "plugins": ["search", "multirepo"],
            }
            mock_generate.return_value = mock_config

            response = client.post("/webhooks/build/unified-config")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["nav_items"] == 2
        assert data["plugins"] == 2

    @pytest.mark.asyncio
    async def test_generate_unified_config_error(
        self, client: TestClient
    ) -> None:
        """Test generating unified configuration with error."""
        with patch(
            "ff_docs.pipeline.config_generator.generate_unified_config"
        ) as mock_generate:
            mock_generate.side_effect = Exception("Config error")

            response = client.post("/webhooks/build/unified-config")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Config generation failed" in response.json()["detail"]
