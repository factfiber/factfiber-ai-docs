# Getting Started

This guide walks you through setting up and using the FactFiber Documentation Infrastructure.

## Overview

The FactFiber Documentation Infrastructure is a centralized multi-repository documentation system that:

- Aggregates documentation from multiple repositories
- Provides unified search across all projects
- Handles real-time synchronization via GitHub webhooks
- Supports team-based access control and authentication
- Offers both REST API and web interface

## Prerequisites

- Python 3.13+
- Git
- GitHub account with access to FactFiber repositories
- Docker (optional, for containerized deployment)
- Kubernetes cluster (optional, for production deployment)

## Installation

### Local Development Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/factfiber/factfiber-ai-docs.git
   cd factfiber-ai-docs
   ```

2. **Install dependencies**:

   ```bash
   # Install with development dependencies
   pip install -e .[dev]

   # Install pre-commit hooks (required for development)
   pre-commit install
   ```

3. **Configuration**:

   ```bash
   # Copy example configuration
   cp .env.example .env

   # Edit configuration with your settings
   export GITHUB_TOKEN="your_github_token"
   export GITHUB_ORG="factfiber"
   ```

### Docker Setup

1. **Build the container**:

   ```bash
   docker build -t factfiber/factfiber-ai-docs .
   ```

2. **Run with Docker Compose**:

   ```bash
   docker-compose up -d
   ```

### Kubernetes Deployment

1. **DevSpace Development**:

   ```bash
   # Install DevSpace
   curl -s -L "https://github.com/loft-sh/devspace/releases/latest" | sed -nE 's!.*"([^"]*devspace-linux-amd64)".*!https://github.com\1!p' | xargs -n 1 curl -L -o devspace && chmod +x devspace

   # Start development environment
   ./devspace dev
   ```

2. **Production Deployment**:

   ```bash
   # Apply Kubernetes manifests
   kubectl apply -f kubernetes/manifests/
   ```

## Usage

### Running the Documentation Server

#### Development Mode

```bash
# Start FastAPI server with hot-reloading
ff-docs serve-api --reload

# Start MkDocs development server
docs-serve

# Access services
# - FastAPI: http://localhost:8000
# - FastAPI Docs: http://localhost:8000/docs
# - MkDocs: http://localhost:8001
```

#### Production Mode

```bash
# Start production server (with custom host/port)
ff-docs serve-api --host 0.0.0.0 --port 8000

# Or use environment variables
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8000
ff-docs serve-api

# Build static documentation
docs-build
```

### Using the REST API

#### Repository Management

```bash
# List enrolled repositories
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/repos/

# Enroll a new repository
curl -X POST -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"repository_url": "https://github.com/factfiber/new-repo"}' \
     http://localhost:8000/repos/enroll

# Search documentation
curl "http://localhost:8000/docs/search?q=context+graph"
```

#### Webhook Setup

1. **Configure GitHub webhook**:
   - URL: `https://your-domain.com/webhooks/github`
   - Content type: `application/json`
   - Events: `push`, `pull_request`

2. **Test webhook**:

   ```bash
   curl -X POST -H "X-GitHub-Event: push" \
        -H "Content-Type: application/json" \
        -d @webhook-payload.json \
        http://localhost:8000/webhooks/github
   ```

### Documentation Workflow

#### Adding a New Repository

1. **Prepare the repository** (see [Repository Onboarding](repository_onboarding.md))
2. **Enroll via API** or web interface
3. **Configure webhooks** for real-time updates
4. **Set permissions** for team access

#### Writing Documentation

1. **Follow standards** in [Documentation Standards](documentation_standards.md)
2. **Use proper structure**:

   ```text
   docs/
   ├── index.md
   ├── guide/
   ├── reference/
   └── assets/
   ```

3. **Generate API docs**:

   ```bash
   docs-code  # Generate pdoc documentation
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | Required |
| `GITHUB_ORG` | GitHub organization name | `factfiber` |
| `SERVER_HOST` | FastAPI server host | `127.0.0.1` |
| `SERVER_PORT` | FastAPI server port | `8000` |
| `AUTH_SECRET_KEY` | JWT secret key | Required for auth |
| `ENVIRONMENT` | Deployment environment | `development` |

### MkDocs Configuration

The system uses standardized MkDocs configuration with:

- **Material theme** with FactFiber branding
- **Mathematical notation** support (MathJax)
- **Mermaid diagrams** for architecture
- **Multi-repo plugin** for aggregation
- **Search optimization** for global search

### Authentication

#### GitHub OAuth Setup

1. **Create GitHub OAuth App**:
   - Authorization callback URL: `https://your-domain.com/auth/callback`
   - Client ID and secret required

2. **Configure OAuth2-Proxy**:

   ```yaml
   # oauth2-proxy-config.yaml
   provider: github
   github_org: factfiber
   client_id: your_client_id
   client_secret: your_client_secret
   ```

#### Team-Based Permissions

- **admin-team**: Full repository management
- **platform-team**: Documentation administration
- **docs-team**: Documentation writing and editing
- **developers**: Read access to enrolled repositories

## Troubleshooting

### Common Issues

#### **Documentation Build Fails**

```bash
# Debug build process
docs-build --verbose

# Check for broken links
mkdocs build --strict
```

#### **API Authentication Errors**

```bash
# Verify token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/me

# Check token permissions
gh auth status
```

#### **Webhook Not Working**

1. **Verify webhook URL** is accessible
2. **Check webhook secret** configuration
3. **Review logs** for processing errors:

   ```bash
   # Docker logs
   docker logs factfiber-docs

   # Kubernetes logs
   kubectl logs -f deployment/ff-docs-app
   ```

#### **Search Not Working**

1. **Rebuild search index**:

   ```bash
   curl -X POST http://localhost:8000/webhooks/build/unified-config
   ```

2. **Check repository enrollment**:

   ```bash
   curl http://localhost:8000/repos/
   ```

### Performance Optimization

#### **Large Repositories**

- Use `.gitignore` to exclude unnecessary files
- Optimize image sizes in documentation
- Consider pagination for large API responses

#### **Build Performance**

```bash
# Parallel documentation generation
docs-build --num-procs 4

# Cache dependencies
pip install --cache-dir .pip-cache -e .[dev]
```

## Next Steps

1. **Explore the [Architecture Guide](architecture.md)** to understand system design
2. **Read [Development Guide](development.md)** for contribution guidelines
3. **Try the [API Reference](../api/)** for programmatic access
4. **Review [Documentation Standards](documentation_standards.md)** for best practices

## Getting Help

- **Documentation Portal**: [https://docs.factfiber.ai](https://docs.factfiber.ai)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Development Guide**: [Development Documentation](development.md)
- **GitHub Issues**: Report bugs and feature requests

---

*This guide covers the essential setup and usage patterns. For advanced topics, see the specific guides in the [User Guide](index.md) section.*
