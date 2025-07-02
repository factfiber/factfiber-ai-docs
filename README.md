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
- **Kubernetes deployment** with DevSpace ✅
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

- **Production**: GitHub OAuth with Lambda@Edge authentication at docs.factfiber.ai
- **Development**: OAuth2-Proxy integration for local development
- **Team-based access control**: factfiber-ai-dev, factfiber-ai-learn, factfiber.ai, ff-analytics, ff-operations
- **Repository-level permissions**: Dynamic access validation
- **Secure credential management**: AWS SSM Parameter Store

### Deployment

- **Development**: DevSpace with hot-reloading ✅
- **Production**: AWS infrastructure with complete OAuth authentication ✅
  - **Custom Domain**: <https://docs.factfiber.ai> with SSL/TLS certificate
  - **Static Hosting**: S3 + CloudFront for global content delivery
  - **Authentication**: Lambda@Edge GitHub OAuth with team validation
  - **Security**: SSM Parameter Store for credential management
  - Kubernetes: With Helm charts (alternative deployment)
- **CI/CD**: GitHub Actions workflows

## AWS Infrastructure

The project includes Terraform configuration for AWS deployment:

### Components

- **S3 Buckets**: Static site hosting with versioning
- **CloudFront**: Global CDN with custom domain (docs.factfiber.ai)
- **ACM Certificate**: SSL/TLS certificate for HTTPS
- **Lambda@Edge**: Complete GitHub OAuth authentication flow
- **SSM Parameter Store**: Secure credential storage
- **DynamoDB**: Terraform state locking
- **CloudWatch**: Monitoring and alerts
- **Route53**: DNS validation for ACM certificate

### Quick AWS Setup

    # 1. Create DynamoDB table for state locking
    ./aws/scripts/create-dynamodb-table.sh

    # 2. Configure Terraform
    cd aws/terraform/environments/prod
    cp terraform.tfvars.example terraform.tfvars
    # Edit terraform.tfvars with your values

    # 3. Deploy infrastructure
    terraform init
    terraform plan
    terraform apply

    # 4. Deploy documentation
    ./aws/scripts/deploy.sh prod

See `aws/docs/setup-guide.md` for detailed instructions.

## Contributing

1. Follow the code style guidelines in `CLAUDE.md`
2. Add tests for new functionality
3. Update documentation as needed
4. Run pre-commit hooks before committing

## License

Copyright 2025 Fact Fiber Inc. All rights reserved. See `LICENSE` file for
details.
