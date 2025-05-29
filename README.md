# FactFiber.ai Documentation Infrastructure

!!! danger "🔒 PROPRIETARY DOCUMENTATION - AUTHENTICATION REQUIRED"

    **SECURITY WARNING**: This documentation system serves strictly proprietary
    FactFiber.ai content.

    - **NEVER serve this documentation publicly without authentication**
    - **LOCAL DEVELOPMENT**: Only accessible on localhost/internal networks
    - **PRODUCTION**: Requires GitHub OAuth and team-based access control
    - **CI/CD**: Must validate no proprietary content exposed to public endpoints

Centralized multi-repository documentation system for FactFiber.ai, built
with MkDocs and FastAPI.

## Overview

This project implements a comprehensive documentation infrastructure that
aggregates content from multiple repositories into a unified documentation
portal. It follows the architecture outlined in
`docs/doc-server-preliminary-plan.md`.

## Features

- **Multi-repository aggregation** using mkdocs-multirepo-plugin
- **FastAPI-based documentation server** with REST API
- **GitHub OAuth integration** via OAuth2-Proxy
- **Automated CI/CD pipelines** with GitHub Actions
- **Kubernetes deployment** with DevSpace
- **Advanced documentation features** (mathematical notation, diagrams,
  interactive content)

## Quick Start

### Prerequisites

- Python 3.12+
- Poetry
- Git

### Installation

    # Clone the repository
    git clone https://github.com/factfiber/factfiber-ai-docs.git
    cd factfiber-ai-docs

    # Install dependencies (including dev dependencies for development)
    poetry install --extras dev

    # Install pre-commit hooks (REQUIRED for development)
    poetry run pre-commit install

### Development

    # Start the development server
    poetry run ff-docs serve --reload

    # Or use uvicorn directly
    poetry run uvicorn ff_docs.server.main:app --reload

    # Build documentation
    poetry run ff-docs build

    # Run tests
    poetry run pytest

    # Run linting
    poetry run pre-commit run --all-files

## Project Structure

    ├── src/ff_docs/           # Main package
    │   ├── config/            # Configuration management
    │   ├── server/            # FastAPI server
    │   ├── auth/              # Authentication & authorization
    │   ├── aggregator/        # Documentation aggregation
    │   ├── templates/         # MkDocs templates
    │   └── utils/             # Utility functions
    ├── tests/                 # Test suite
    │   ├── unit/              # Unit tests
    │   ├── integration/       # Integration tests
    │   └── fixtures/          # Test fixtures
    ├── docs/                  # Project documentation
    ├── kubernetes/            # Kubernetes manifests
    ├── scripts/               # Automation scripts
    └── .github/workflows/     # CI/CD pipelines

## Configuration

The application uses environment variables and settings files for
configuration. See `src/ff_docs/config/settings.py` for available options.

Key environment variables:

- `GITHUB_TOKEN`: GitHub personal access token
- `GITHUB_ORG`: GitHub organization name
- `AUTH_SECRET_KEY`: JWT secret key
- `SERVER_HOST`: Server host (default: 0.0.0.0)
- `SERVER_PORT`: Server port (default: 8000)

## Development Workflow

1. **Code Style**: We use Ruff for linting and formatting
   (80-character line limit)
2. **Type Checking**: MyPy is required for all code
3. **Testing**: Pytest with coverage reporting
4. **Pre-commit Hooks**: Automated code quality checks

## Architecture

### Multi-Repository Documentation

The system supports multiple patterns for aggregating documentation:

1. **Git Submodules**: Version-controlled external repositories
2. **API Aggregation**: Dynamic fetching via GitHub API
3. **Plugin-based**: Using mkdocs-multirepo-plugin

### Authentication

- GitHub OAuth integration via OAuth2-Proxy
- Team-based access control
- Repository-level permissions

### Deployment

- **Development**: DevSpace with hot-reloading
- **Production**: Kubernetes with Helm charts
- **CI/CD**: GitHub Actions workflows

## Contributing

1. Follow the code style guidelines in `CLAUDE.md`
2. Add tests for new functionality
3. Update documentation as needed
4. Run pre-commit hooks before committing

## License

Copyright 2025 Fact Fiber Inc. All rights reserved. See `LICENSE` file for
details.
