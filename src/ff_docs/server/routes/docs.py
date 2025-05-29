# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Documentation serving endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")  # type: ignore[misc]
async def list_documentation() -> dict[str, str]:
    """List available documentation."""
    # TODO: Implement documentation listing
    return {"message": "Documentation endpoints - TODO"}


@router.get("/build")  # type: ignore[misc]
async def build_documentation() -> dict[str, str]:
    """Trigger documentation build."""
    # TODO: Implement documentation build
    return {"message": "Build started - TODO"}
