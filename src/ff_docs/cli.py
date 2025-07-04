# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Command-line interface for FactFiber documentation system."""

from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group()  # type: ignore[misc]
@click.version_option()  # type: ignore[misc]
def main() -> None:
    """FactFiber.ai documentation system CLI."""


@main.command()  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--host",
    default="127.0.0.1",
    help="Host to bind to",
)
@click.option("--port", default=8000, help="Port to bind to")  # type: ignore[misc]
@click.option("--reload", is_flag=True, help="Enable auto-reload")  # type: ignore[misc]
def serve(host: str, port: int, *, reload: bool) -> None:
    """Start the MkDocs development server."""
    import subprocess
    import sys

    console.print(f"🚀 Starting MkDocs development server on {host}:{port}")

    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent.parent

    cmd = ["poetry", "run", "mkdocs", "serve", "--dev-addr", f"{host}:{port}"]
    if reload:
        cmd.append("--livereload")

    try:
        subprocess.run(cmd, cwd=project_root, check=True)  # noqa: S603
    except subprocess.CalledProcessError as e:
        console.print("❌ MkDocs server failed to start!")
        console.print(f"Error code: {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n👋 MkDocs server stopped")


@main.command("serve-api")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--host",
    default=None,
    help="Host to bind to (defaults to SERVER_HOST env or 127.0.0.1)",
)
@click.option(  # type: ignore[misc]
    "--port",
    default=None,
    type=int,
    help="Port to bind to (defaults to SERVER_PORT env or 8000)",
)
@click.option("--reload", is_flag=True, help="Enable auto-reload")  # type: ignore[misc]
def serve_api(host: str | None, port: int | None, *, reload: bool) -> None:
    """Start the FastAPI documentation management server."""
    import uvicorn

    from ff_docs.config.settings import get_settings

    settings = get_settings()
    # Use CLI args, then env vars, then defaults
    actual_host = host or settings.server.host
    actual_port = port or settings.server.port

    console.print(f"🔥 Starting FastAPI server on {actual_host}:{actual_port}")
    uvicorn.run(
        "ff_docs.server.main:app",
        host=actual_host,
        port=actual_port,
        reload=reload,
    )


@main.group()  # type: ignore[misc]
def repo() -> None:
    """Repository management commands."""


@repo.command("discover")  # type: ignore[misc]
@click.option("--org", help="GitHub organization (defaults to configured org)")  # type: ignore[misc]
@click.option("--output", type=click.Path(), help="Save results to file")  # type: ignore[misc]
def discover_repos(org: str, output: str) -> None:
    """Discover repositories with documentation in organization."""
    import asyncio
    import json

    from ff_docs.aggregator.github_client import RepositoryAggregator

    async def _discover() -> None:
        aggregator = RepositoryAggregator()
        repositories = await aggregator.discover_documentation_repositories(org)

        console.print(
            f"📚 Found {len(repositories)} repositories with documentation:"
        )

        for repo in repositories:
            status = "🔒" if repo.private else "🌍"
            docs_info = (
                f"docs: {repo.docs_path or 'detected'}"
                if repo.has_docs
                else "no docs"
            )
            console.print(f"  {status} {repo.name} ({docs_info})")
            if repo.description:
                console.print(f"    {repo.description}")

        if output:
            output_path = Path(output)
            repo_data = [
                {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "private": repo.private,
                    "default_branch": repo.default_branch,
                    "has_docs": repo.has_docs,
                    "docs_path": repo.docs_path,
                    "clone_url": repo.clone_url,
                }
                for repo in repositories
            ]

            import aiofiles

            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(repo_data, indent=2))

            console.print(f"💾 Results saved to {output_path}")

    asyncio.run(_discover())


@repo.command("enroll")  # type: ignore[misc]
@click.argument("repository")  # type: ignore[misc]
@click.option("--section", help="Navigation section name")  # type: ignore[misc]
def enroll_repo(repository: str, section: str) -> None:
    """Enroll a repository in the documentation system."""
    import asyncio

    from ff_docs.aggregator.enrollment import RepositoryEnrollment

    async def _enroll() -> None:
        enrollment = RepositoryEnrollment()

        console.print(f"📝 Enrolling repository: {repository}")

        success = await enrollment.enroll_repository(repository, section)

        if success:
            console.print(f"✅ Successfully enrolled {repository}")
        else:
            console.print(f"❌ Failed to enroll {repository}")

    asyncio.run(_enroll())


@repo.command("enroll-all")  # type: ignore[misc]
@click.option("--org", help="GitHub organization (defaults to configured org)")  # type: ignore[misc]
@click.option("--exclude", multiple=True, help="Repository names to exclude")  # type: ignore[misc]
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be enrolled without making changes",
)  # type: ignore[misc]
def enroll_all_repos(
    org: str, exclude: tuple[str, ...], *, dry_run: bool
) -> None:
    """Enroll all repositories with documentation from organization."""
    import asyncio

    from ff_docs.aggregator.enrollment import RepositoryEnrollment

    async def _enroll_all() -> None:
        enrollment = RepositoryEnrollment()

        org_name = org or "configured organization"
        console.print(f"🔍 Discovering repositories in {org_name}...")

        if dry_run:
            # Just discover and show what would be enrolled
            repositories = (
                await enrollment.aggregator.discover_documentation_repositories(
                    org
                )
            )
            filtered_repos = [
                repo for repo in repositories if repo.name not in exclude
            ]

            console.print(
                f"📋 Would enroll {len(filtered_repos)} repositories:"
            )
            for repo in filtered_repos:
                status = "🔒" if repo.private else "🌍"
                console.print(f"  {status} {repo.name}")
        else:
            results = await enrollment.enroll_all_repositories(
                org, list(exclude)
            )

            successful = [name for name, success in results.items() if success]
            failed = [name for name, success in results.items() if not success]

            console.print(
                f"✅ Successfully enrolled {len(successful)} repositories"
            )
            console.print(f"❌ Failed to enroll {len(failed)} repositories")

            if failed:
                console.print("Failed repositories:")
                for name in failed:
                    console.print(f"  • {name}")

    asyncio.run(_enroll_all())


@repo.command("unenroll")  # type: ignore[misc]
@click.argument("repository")  # type: ignore[misc]
def unenroll_repo(repository: str) -> None:
    """Remove a repository from the documentation system."""
    from ff_docs.aggregator.enrollment import RepositoryEnrollment

    enrollment = RepositoryEnrollment()

    console.print(f"🗑️ Removing repository: {repository}")

    success = enrollment.unenroll_repository(repository)

    if success:
        console.print(f"✅ Successfully removed {repository}")
    else:
        console.print(f"❌ Failed to remove {repository}")


@repo.command("list")  # type: ignore[misc]
def list_repos() -> None:
    """List all currently enrolled repositories."""
    from ff_docs.aggregator.enrollment import RepositoryEnrollment

    enrollment = RepositoryEnrollment()
    enrolled = enrollment.list_enrolled_repositories()

    if not enrolled:
        console.print("📭 No repositories currently enrolled")
        return

    console.print(f"📚 {len(enrolled)} enrolled repositories:")

    for repo in enrolled:
        console.print(f"  • {repo['name']}")
        console.print(f"    URL: {repo['import_url']}")


@main.command()  # type: ignore[misc]
@click.argument("repo_url")  # type: ignore[misc]
@click.option("--branch", default="main", help="Branch to track")  # type: ignore[misc]
@click.option("--docs-path", default="docs/", help="Path to documentation")  # type: ignore[misc]
def enroll(repo_url: str, branch: str, docs_path: str) -> None:
    """Legacy: Enroll a new repository in the documentation system."""
    console.print(
        "⚠️ This command is deprecated. Use 'ff-docs repo enroll' instead."
    )
    console.print(f"Enrolling repository: {repo_url}")
    console.print(f"Branch: {branch}, Docs path: {docs_path}")
    # TODO: Implement repository enrollment


@main.command()  # type: ignore[misc]
@click.option("--clean", is_flag=True, help="Clean site directory before build")  # type: ignore[misc]
@click.option("--strict", is_flag=True, help="Enable strict mode")  # type: ignore[misc]
def build(*, clean: bool, strict: bool) -> None:
    """Build the aggregated documentation."""
    import subprocess
    import sys

    console.print("🔨 Building documentation...")

    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent.parent

    cmd = ["poetry", "run", "mkdocs", "build"]
    if clean:
        cmd.append("--clean")
    if strict:
        cmd.append("--strict")

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
        console.print("✅ Documentation build completed successfully!")
        if result.stdout:
            console.print(result.stdout)

    except subprocess.CalledProcessError as e:
        console.print("❌ Documentation build failed!")
        console.print(f"Error: {e.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    main()
