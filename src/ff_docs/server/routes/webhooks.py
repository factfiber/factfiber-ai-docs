# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""
GitHub webhook handler for real-time documentation synchronization.

This module handles incoming GitHub webhooks to trigger documentation updates
when repository content changes. It validates webhook signatures, processes
push events, and triggers the documentation sync pipeline.
"""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class GitHubWebhookPayload(BaseModel):
    """
    GitHub webhook payload model for push events.

    This model captures the essential information from GitHub webhook
    push events needed for documentation synchronization.
    """

    action: str | None = None
    repository: dict[str, Any] = Field(default_factory=dict)
    commits: list[dict[str, Any]] = Field(default_factory=list)
    head_commit: dict[str, Any] | None = None
    ref: str = ""
    before: str = ""
    after: str = ""
    pusher: dict[str, Any] = Field(default_factory=dict)


class WebhookResponse(BaseModel):
    """Response model for webhook processing."""

    status: str
    message: str
    repository: str | None = None
    commit_sha: str | None = None
    docs_updated: bool = False


def verify_github_signature(
    payload: bytes, signature: str, secret: str
) -> bool:
    """
    Verify GitHub webhook signature for security.

    Args:
        payload: Raw webhook payload bytes
        signature: GitHub signature header (sha256=...)
        secret: Webhook secret configured in GitHub

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature.startswith("sha256="):
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    received_signature = signature[7:]  # Remove 'sha256=' prefix

    return hmac.compare_digest(expected_signature, received_signature)


def contains_docs_changes(commits: list[dict[str, Any]]) -> bool:
    """
    Check if any commits contain documentation changes.

    Args:
        commits: List of commit objects from webhook payload

    Returns:
        True if documentation files were modified
    """
    docs_patterns = {
        "docs/",
        "*.md",
        "*.rst",
        "mkdocs.yml",
        "mkdocs.yaml",
        ".factfiber-docs.yml",
        ".factfiber-docs.yaml",
    }

    for commit in commits:
        # Check added, modified, and removed files
        for file_list in ["added", "modified", "removed"]:
            files = commit.get(file_list, [])
            for file_path in files:
                if any(pattern in file_path for pattern in docs_patterns):
                    return True

    return False


@router.post("/github")
async def handle_github_webhook(request: Request) -> WebhookResponse:
    """
    Handle incoming GitHub webhook for documentation updates.

    This endpoint receives GitHub webhook events and triggers documentation
    synchronization when relevant changes are detected. It validates the
    webhook signature and processes push events for enrolled repositories.

    Args:
        request: FastAPI request containing webhook payload

    Returns:
        WebhookResponse indicating processing status

    Raises:
        HTTPException: For invalid signatures or processing errors
    """
    settings = get_settings()

    # Get webhook signature and event type
    signature = request.headers.get("x-hub-signature-256", "")
    event_type = request.headers.get("x-github-event", "")
    delivery_id = request.headers.get("x-github-delivery", "")

    logger.info(
        "Received GitHub webhook: event=%s, delivery=%s",
        event_type,
        delivery_id,
    )

    # Read raw payload for signature verification
    payload_bytes = await request.body()

    # Verify webhook signature
    if settings.github.webhook_secret and not verify_github_signature(
        payload_bytes, signature, settings.github.webhook_secret
    ):
        logger.warning("Invalid webhook signature for delivery %s", delivery_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse payload
    try:
        payload_dict = await request.json()
        webhook_payload = GitHubWebhookPayload(**payload_dict)
    except (ValueError, TypeError) as e:
        logger.exception("Failed to parse webhook payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        ) from e

    # Only process push events
    if event_type != "push":
        return WebhookResponse(
            status="ignored", message=f"Event type '{event_type}' not processed"
        )

    # Extract repository information
    repo_info = webhook_payload.repository
    repo_name = repo_info.get("name", "")
    repo_full_name = repo_info.get("full_name", "")

    if not repo_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository name not found in payload",
        )

    # Check if repository is enrolled
    from ff_docs.aggregator.enrollment import get_enrolled_repositories

    try:
        enrolled_repos = await get_enrolled_repositories()
        enrolled_names = [repo["name"] for repo in enrolled_repos]

        if repo_full_name not in enrolled_names:
            return WebhookResponse(
                status="ignored",
                message=f"Repository '{repo_full_name}' not enrolled",
                repository=repo_full_name,
            )
    except (ValueError, RuntimeError) as e:
        logger.warning(
            "Could not check enrollment status for %s: %s", repo_full_name, e
        )
        # Continue processing to avoid breaking webhooks

    # Check if changes include documentation
    docs_changed = contains_docs_changes(webhook_payload.commits)

    if not docs_changed:
        return WebhookResponse(
            status="ignored",
            message="No documentation changes detected",
            repository=repo_full_name,
        )

    # Extract commit information
    commit_sha = webhook_payload.after
    if webhook_payload.head_commit:
        commit_sha = webhook_payload.head_commit.get("id", commit_sha)

    logger.info(
        "Processing docs update: repo=%s, commit=%s", repo_full_name, commit_sha
    )

    # Trigger documentation sync pipeline
    from ff_docs.pipeline.sync import trigger_docs_sync

    try:
        sync_status = await trigger_docs_sync(repo_full_name, commit_sha)
        logger.info(
            "Sync initiated: repo=%s, status=%s",
            repo_full_name,
            sync_status.status,
        )
    except Exception:
        logger.exception("Failed to trigger sync for %s", repo_full_name)
        # Continue with success response as webhook was processed

    return WebhookResponse(
        status="processed",
        message="Documentation sync triggered",
        repository=repo_full_name,
        commit_sha=commit_sha,
        docs_updated=True,
    )


@router.get("/github/test")
async def test_webhook_endpoint() -> dict[str, str]:
    """
    Test endpoint for webhook configuration validation.

    Returns:
        Simple response to verify webhook endpoint is accessible
    """
    return {
        "status": "ok",
        "message": "Webhook endpoint is operational",
        "endpoint": "/webhooks/github",
    }


@router.get("/sync/status/{repo_name}")
async def get_sync_status(repo_name: str) -> dict[str, Any]:
    """
    Get synchronization status for a specific repository.

    Args:
        repo_name: Repository name (org/repo format)

    Returns:
        Sync status information
    """
    from ff_docs.pipeline.sync import get_content_sync_service

    service = get_content_sync_service()
    status = service.get_sync_status(repo_name)

    if status is None:
        from fastapi import status as http_status

        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"No sync status found for repository '{repo_name}'",
        )

    return status.model_dump()


@router.get("/sync/status")
async def get_all_sync_status() -> dict[str, Any]:
    """
    Get synchronization status for all repositories.

    Returns:
        Dictionary of repository sync statuses
    """
    from ff_docs.pipeline.sync import get_content_sync_service

    service = get_content_sync_service()
    all_status = service.get_all_sync_status()

    return {repo: status.model_dump() for repo, status in all_status.items()}


@router.post("/build/unified-config")
async def generate_unified_config() -> dict[str, Any]:
    """
    Generate unified MkDocs configuration for all enrolled repositories.

    Returns:
        Generated configuration and status
    """
    try:
        from pathlib import Path

        from ff_docs.pipeline.config_generator import generate_unified_config

        # Generate config in current directory
        output_path = Path("mkdocs-unified.yml")
        config = await generate_unified_config(output_path)

        return {
            "status": "success",
            "message": f"Generated unified config with {len(config.get('nav', []))} navigation items",  # noqa: E501
            "config_file": str(output_path),
            "nav_items": len(config.get("nav", [])),
            "plugins": len(config.get("plugins", [])),
        }

    except Exception as e:
        logger.exception("Failed to generate unified config")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Config generation failed: {e}",
        ) from e
