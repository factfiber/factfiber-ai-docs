# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Repository management endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")  # type: ignore[misc]
async def list_repositories() -> dict[str, str]:
    """List enrolled repositories."""
    # TODO: Implement repository listing
    return {"message": "Repository endpoints - TODO"}


@router.post("/enroll")  # type: ignore[misc]
async def enroll_repository() -> dict[str, str]:
    """Enroll a new repository."""
    # TODO: Implement repository enrollment
    return {"message": "Repository enrollment - TODO"}
