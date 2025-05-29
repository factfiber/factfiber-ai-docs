# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Health check endpoints."""

from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/")  # type: ignore[misc]
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "ff-docs"}


@router.get("/ready")  # type: ignore[misc]
async def readiness_check() -> dict[str, Any]:
    """Readiness check endpoint."""
    # TODO: Add checks for database, external services, etc.
    return {"status": "ready", "service": "ff-docs"}


@router.get("/live")  # type: ignore[misc]
async def liveness_check() -> dict[str, Any]:
    """Liveness check endpoint."""
    return {"status": "alive", "service": "ff-docs"}
