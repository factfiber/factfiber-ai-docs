# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ff_docs.auth.repository_middleware import RepositoryScopedAuthMiddleware
from ff_docs.config.settings import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="FactFiber Documentation Server",
        description="Centralized multi-repository documentation system",
        version="0.1.0",
        debug=settings.debug,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add repository-scoped authentication middleware
    app.add_middleware(RepositoryScopedAuthMiddleware)

    # Include routers
    from ff_docs.server.routes import auth, docs, health, repos, webhooks

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(auth.router, prefix="/auth", tags=["authentication"])
    app.include_router(docs.router, prefix="/docs", tags=["documentation"])
    app.include_router(repos.router, prefix="/repos", tags=["repositories"])
    app.include_router(webhooks.router, tags=["webhooks"])

    return app


app = create_app()


def run_server() -> None:  # pragma: no cover
    """Run the development server."""
    import uvicorn

    uvicorn.run(
        "ff_docs.server.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        workers=settings.server.workers if not settings.server.reload else 1,
    )
