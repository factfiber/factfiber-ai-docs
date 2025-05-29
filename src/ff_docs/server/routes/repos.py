# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Repository management endpoints."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ff_docs.aggregator.enrollment import RepositoryEnrollment
from ff_docs.aggregator.github_client import RepositoryAggregator
from ff_docs.auth.middleware import (
    get_current_user,
    require_permission,
)
from ff_docs.auth.models import UserSession

logger = logging.getLogger(__name__)
router = APIRouter()


class EnrollRepositoryRequest(BaseModel):
    """Request model for repository enrollment."""

    repository: str = Field(..., description="Repository name or URL")
    section: str | None = Field(None, description="Navigation section name")


class EnrollRepositoryResponse(BaseModel):
    """Response model for repository enrollment."""

    success: bool = Field(..., description="Whether enrollment was successful")
    message: str = Field(..., description="Status message")
    repository: str = Field(..., description="Repository name")


class UnenrollRepositoryRequest(BaseModel):
    """Request model for repository unenrollment."""

    repository_name: str = Field(..., description="Repository name to remove")


class RepositoryInfo(BaseModel):
    """Repository information model."""

    name: str = Field(..., description="Repository name")
    import_url: str = Field(..., description="Import URL for documentation")


class RepositoryListResponse(BaseModel):
    """Response model for repository listing."""

    repositories: list[RepositoryInfo] = Field(
        ..., description="List of enrolled repositories"
    )
    count: int = Field(..., description="Total number of repositories")


class DiscoveredRepository(BaseModel):
    """Discovered repository model."""

    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name")
    description: str | None = Field(None, description="Repository description")
    private: bool = Field(..., description="Whether repository is private")
    has_docs: bool = Field(
        ..., description="Whether repository has documentation"
    )
    docs_path: str | None = Field(None, description="Path to documentation")
    clone_url: str = Field(..., description="Clone URL")


class DiscoveryResponse(BaseModel):
    """Response model for repository discovery."""

    repositories: list[DiscoveredRepository] = Field(
        ..., description="Discovered repositories"
    )
    count: int = Field(
        ..., description="Total number of discovered repositories"
    )
    organization: str | None = Field(None, description="Organization name")


@router.get("/config")  # type: ignore[misc]
async def get_configuration() -> dict[str, Any]:
    """Get configuration status for repository management."""
    from ff_docs.aggregator.github_client import GitHubClient

    github_client = GitHubClient()

    return {
        "github_configured": github_client.is_configured(),
        "github_org": github_client.settings.github.org,
        "service": "ff-docs-repository-api",
    }


@router.get("/")  # type: ignore[misc]
async def list_repositories() -> RepositoryListResponse:
    """List all enrolled repositories."""
    try:
        enrollment = RepositoryEnrollment()
        enrolled_repos = enrollment.list_enrolled_repositories()

        repositories = [
            RepositoryInfo(name=repo["name"], import_url=repo["import_url"])
            for repo in enrolled_repos
        ]

        return RepositoryListResponse(
            repositories=repositories, count=len(repositories)
        )
    except Exception as e:
        logger.exception("Failed to list repositories")
        raise HTTPException(
            status_code=500, detail=f"Failed to list repositories: {e}"
        ) from e


@router.get("/discover")  # type: ignore[misc]
async def discover_repositories(
    _: Annotated[UserSession, Depends(get_current_user)],
    org: Annotated[
        str | None, Query(description="GitHub organization name")
    ] = None,
) -> DiscoveryResponse:
    """Discover repositories with documentation in organization."""
    try:
        aggregator = RepositoryAggregator()
        repositories = await aggregator.discover_documentation_repositories(org)

        discovered_repos = [
            DiscoveredRepository(
                name=repo.name,
                full_name=repo.full_name,
                description=repo.description,
                private=repo.private,
                has_docs=repo.has_docs,
                docs_path=repo.docs_path,
                clone_url=repo.clone_url,
            )
            for repo in repositories
        ]

        return DiscoveryResponse(
            repositories=discovered_repos,
            count=len(discovered_repos),
            organization=org,
        )
    except ValueError as e:
        # GitHub token not configured
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to discover repositories")
        raise HTTPException(
            status_code=500, detail=f"Failed to discover repositories: {e}"
        ) from e


@router.post("/enroll")  # type: ignore[misc]
async def enroll_repository(
    request: EnrollRepositoryRequest,
    _: Annotated[UserSession, Depends(require_permission(["repos:manage"]))],
) -> EnrollRepositoryResponse:
    """Enroll a repository in the documentation system."""
    try:
        enrollment = RepositoryEnrollment()
        success = await enrollment.enroll_repository(
            repository=request.repository, section=request.section
        )

        if success:
            return EnrollRepositoryResponse(
                success=True,
                message=(
                    f"Successfully enrolled repository: {request.repository}"
                ),
                repository=request.repository,
            )
        return EnrollRepositoryResponse(
            success=False,
            message=f"Failed to enroll repository: {request.repository}",
            repository=request.repository,
        )
    except Exception as e:
        logger.exception("Failed to enroll repository: %s", request.repository)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enroll repository {request.repository}: {e}",
        ) from e


@router.delete("/unenroll")  # type: ignore[misc]
async def unenroll_repository(
    request: UnenrollRepositoryRequest,
    _: Annotated[UserSession, Depends(require_permission(["repos:manage"]))],
) -> dict[str, Any]:
    """Remove a repository from the documentation system."""
    try:
        enrollment = RepositoryEnrollment()
        success = enrollment.unenroll_repository(request.repository_name)

        if success:
            return {
                "success": True,
                "message": (
                    "Successfully unenrolled repository: "
                    f"{request.repository_name}"
                ),
                "repository": request.repository_name,
            }
        return {  # noqa: TRY300
            "success": False,
            "message": f"Repository not found: {request.repository_name}",
            "repository": request.repository_name,
        }
    except Exception as e:
        logger.exception(
            "Failed to unenroll repository: %s", request.repository_name
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to unenroll repository {request.repository_name}: {e}"
            ),
        ) from e


@router.post("/enroll-all")  # type: ignore[misc]
async def enroll_all_repositories(
    _: Annotated[UserSession, Depends(require_permission(["repos:manage"]))],
    org: Annotated[
        str | None, Query(description="GitHub organization name")
    ] = None,
    exclude: Annotated[
        list[str] | None, Query(description="Repository names to exclude")
    ] = None,
) -> dict[str, Any]:
    """Enroll all repositories with documentation from organization."""
    try:
        enrollment = RepositoryEnrollment()
        exclude_list = exclude if exclude is not None else []
        results = await enrollment.enroll_all_repositories(org, exclude_list)

        successful = [name for name, success in results.items() if success]
        failed = [name for name, success in results.items() if not success]

        return {
            "success": True,
            "message": (
                f"Enrolled {len(successful)}/{len(results)} repositories"
            ),
            "successful": successful,
            "failed": failed,
            "total": len(results),
        }
    except ValueError as e:
        # GitHub token not configured
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to enroll all repositories")
        raise HTTPException(
            status_code=500, detail=f"Failed to enroll all repositories: {e}"
        ) from e
