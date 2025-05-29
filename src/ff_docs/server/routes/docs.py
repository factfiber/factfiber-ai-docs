# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Documentation serving endpoints."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ff_docs.auth.middleware import get_current_user
from ff_docs.auth.models import UserSession
from ff_docs.config.settings import settings

router = APIRouter()


@router.get("/")  # type: ignore[misc]
async def list_documentation(
    current_user: Annotated[UserSession, Depends(get_current_user)],
) -> dict[str, list[str]]:
    """List available documentation."""
    # TODO: Implement actual repository listing based on user permissions
    # For now, return placeholder for authenticated user
    _ = current_user  # Ensure user is authenticated
    return {"repositories": ["example-repo", "another-repo"]}


@router.get("/repo/{repo_name}")  # type: ignore[misc]
async def serve_repository_docs(repo_name: str) -> FileResponse:
    """Serve documentation for a specific repository."""
    # Repository access is already validated by RepositoryScopedAuthMiddleware
    # at this point, so we can serve the documentation

    docs_path = Path(settings.output_dir) / repo_name / "index.html"

    if not docs_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Documentation not found for repository: {repo_name}",
        )

    return FileResponse(docs_path, media_type="text/html")


@router.get("/repo/{repo_name}/static/{file_path:path}")  # type: ignore[misc]
async def serve_repository_static(
    repo_name: str, file_path: str
) -> FileResponse:
    """Serve static files for repository documentation."""
    # Repository access is already validated by middleware

    static_file_path = Path(settings.output_dir) / repo_name / file_path

    if not static_file_path.exists() or not static_file_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"Static file not found: {file_path}"
        )

    # Ensure the file is within the repository's documentation directory
    if not str(static_file_path.resolve()).startswith(
        str((Path(settings.output_dir) / repo_name).resolve())
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(static_file_path)


@router.get("/build")  # type: ignore[misc]
async def build_documentation(
    current_user: Annotated[UserSession, Depends(get_current_user)],
) -> dict[str, str]:
    """Trigger documentation build."""
    # TODO: Implement documentation build for authenticated user
    _ = current_user  # Ensure user is authenticated
    return {"message": "Build started - TODO"}


@router.post("/build/{repo_name}")  # type: ignore[misc]
async def build_repository_documentation(
    repo_name: str,
    current_user: Annotated[UserSession, Depends(get_current_user)],
) -> dict[str, str]:
    """Trigger documentation build for a specific repository."""
    # Repository access is already validated by middleware
    # TODO: Implement repository-specific documentation build for user
    _ = current_user  # Ensure user is authenticated
    return {"message": f"Build started for repository: {repo_name}"}
