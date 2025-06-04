# ff_docs Package

The main package for the FactFiber Documentation Infrastructure, providing a
comprehensive multi-repository documentation system with real-time synchronization
and secure access control.

## Package Overview

The `ff_docs` package is organized into several specialized modules, each
handling specific aspects of the documentation infrastructure:

```text
ff_docs/
├── aggregator/          # Repository discovery and enrollment
├── auth/                # Authentication and authorization
├── config/              # Configuration management
├── pipeline/            # Documentation processing pipeline
├── search/              # Global search functionality
├── server/              # FastAPI REST API server
├── utils/               # Utility functions and helpers
├── cli.py               # Command-line interface
└── templates/           # Template files and assets
```

## Core Modules

### [aggregator/](aggregator/)

Repository management and GitHub integration for automated discovery and enrollment of documentation repositories.

**Key Components:**

- **Repository Enrollment**: Automated onboarding process for new repositories
- **GitHub Client**: API integration for repository discovery and webhook management
- **Access Validation**: Team-based permission verification

### [auth/](auth/)

Comprehensive authentication and authorization system supporting multiple authentication providers.

**Key Components:**

- **JWT Authentication**: Secure token-based authentication for API access
- **GitHub OAuth**: GitHub-based authentication for developers
- **OAuth2-Proxy Integration**: Enterprise authentication gateway
- **Repository Permissions**: Fine-grained access control for documentation

### [server/](server/)

FastAPI-based REST API server providing all core functionality through well-documented endpoints.

**Key Components:**

- **Main Application**: FastAPI app with middleware and routing
- **Route Handlers**: Repository, webhook, search, and authentication endpoints
- **Authentication Middleware**: Request-level security and authorization

### [pipeline/](pipeline/)

Documentation processing pipeline for multi-repository content synchronization and aggregation.

**Key Components:**

- **Content Synchronization**: Git-based repository cloning and content processing
- **Configuration Generation**: Dynamic MkDocs configuration for unified sites
- **Link Rewriting**: Transparent URL transformation for seamless navigation
- **API Documentation**: Automated Python API documentation generation

### [config/](config/)

Centralized configuration management with environment-based settings and validation.

**Key Components:**

- **Settings Management**: Pydantic-based configuration with comprehensive validation
- **Environment Integration**: Environment variable processing and defaults

### [search/](search/)

Global search functionality with security filtering and permission-based access control.

**Key Components:**

- **Security Filtering**: Search results filtered by user repository access
- **Cross-Repository Search**: Unified search across all enrolled repositories

### [utils/](utils/)

Utility functions and helper modules providing common functionality across components.

**Key Components:**

- **Common Utilities**: Shared functions for validation, formatting, and processing
- **Error Handling**: Custom exception classes and error management

## Command-Line Interface

### [`cli.py`](cli.md)

Comprehensive command-line interface for administrative tasks and development workflows.

**Available Commands:**

- **Server Management**: Start API server, documentation server
- **Repository Operations**: Enroll, unenroll, and manage repositories
- **Documentation Building**: Generate and serve documentation
- **Administrative Tasks**: User management, system configuration

## Usage Patterns

### Basic Package Import

```python
# Core functionality
from ff_docs.server import create_app
from ff_docs.config import settings
from ff_docs.aggregator import RepositoryEnroller

# Authentication
from ff_docs.auth import JWTHandler, GitHubAuthenticator
from ff_docs.auth.models import User, RepositoryPermission

# Pipeline operations
from ff_docs.pipeline import ContentSynchronizer, ConfigGenerator
```

### Application Initialization

```python
from ff_docs.server.main import create_app
from ff_docs.config.settings import get_settings

# Initialize application with configuration
settings = get_settings()
app = create_app(settings)

# Run with uvicorn
import uvicorn
uvicorn.run(app, host=settings.server_host, port=settings.server_port)
```

### Repository Management

```python
from ff_docs.aggregator.enrollment import RepositoryEnroller
from ff_docs.aggregator.github_client import GitHubClient

# Initialize with authentication
github_client = GitHubClient(token=settings.github_token)
enroller = RepositoryEnroller(github_client)

# Enroll new repository
result = await enroller.enroll_repository(
    repository_url="https://github.com/factfiber/new-repo",
    documentation_path="docs/",
    access_permissions=["docs-team"]
)
```

### Authentication Setup

```python
from ff_docs.auth.jwt_handler import JWTHandler
from ff_docs.auth.github_auth import GitHubAuthenticator

# Initialize authentication components
jwt_handler = JWTHandler(secret_key=settings.auth_secret_key)
github_auth = GitHubAuthenticator(
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret
)

# Generate access token
token = jwt_handler.generate_token(user_id="user123", permissions=["docs:read"])
```

## Configuration

### Environment Variables

The package uses environment-based configuration managed through `ff_docs.config.settings`:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | Required |
| `GITHUB_ORG` | GitHub organization name | `factfiber` |
| `SERVER_HOST` | FastAPI server host | `0.0.0.0` |
| `SERVER_PORT` | FastAPI server port | `8000` |
| `AUTH_SECRET_KEY` | JWT secret key | Required |
| `ENVIRONMENT` | Deployment environment | `development` |

### Settings Management

```python
from ff_docs.config import settings

# Access configuration
print(f"GitHub org: {settings.github_org}")
print(f"Server port: {settings.server_port}")

# Environment-specific behavior
if settings.environment == "development":
    # Enable debug features
    pass
```

## Error Handling

### Custom Exceptions

The package defines custom exception classes for specific error scenarios:

```python
from ff_docs.auth.models import AuthenticationError, PermissionError
from ff_docs.aggregator.enrollment import RepositoryEnrollmentError
from ff_docs.pipeline.sync import SynchronizationError

try:
    result = await enroll_repository(repo_url)
except RepositoryEnrollmentError as e:
    logger.error(f"Enrollment failed: {e}")
    # Handle enrollment-specific error
except AuthenticationError as e:
    logger.error(f"Authentication failed: {e}")
    # Handle authentication error
```

### Error Response Format

API endpoints return standardized error responses:

```json
{
  "error": "Repository not found",
  "details": "Repository 'factfiber/nonexistent' is not enrolled",
  "code": "REPO_NOT_FOUND",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Development Guidelines

### Code Standards

- **Type Annotations**: All functions must have complete type annotations
- **Docstrings**: Google-style docstrings required for all public functions
- **Error Handling**: Use specific exception types with descriptive messages
- **Async Operations**: Use async/await for I/O operations

### Testing Patterns

```python
# Unit test example
import pytest
from ff_docs.auth.jwt_handler import JWTHandler

def test_jwt_token_generation():
    """Test JWT token generation with valid payload."""
    handler = JWTHandler(secret_key="test-secret")
    token = handler.generate_token(user_id="test-user")

    assert token is not None
    assert isinstance(token, str)

    # Verify token can be decoded
    payload = handler.decode_token(token)
    assert payload["user_id"] == "test-user"
```

## Integration Examples

### FastAPI Application

```python
from fastapi import FastAPI
from ff_docs.server.routes import auth, repos, webhooks
from ff_docs.auth.middleware import AuthenticationMiddleware

app = FastAPI(title="Documentation Infrastructure API")

# Add authentication middleware
app.add_middleware(AuthenticationMiddleware)

# Include route modules
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(repos.router, prefix="/repos", tags=["repositories"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
```

### Background Processing

```python
import asyncio
from ff_docs.pipeline.sync import ContentSynchronizer

async def process_repository_updates():
    """Background task for processing repository updates."""
    synchronizer = ContentSynchronizer()

    while True:
        try:
            # Process pending updates
            await synchronizer.process_pending_updates()
            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Error processing updates: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error
```

## Performance Considerations

### Async Operations

The package is designed for high-performance async operations:

- **Non-blocking I/O**: All GitHub API calls use async HTTP clients
- **Concurrent Processing**: Multiple repositories processed in parallel
- **Background Tasks**: Long-running operations handled asynchronously

### Resource Management

- **Connection Pooling**: HTTP clients use connection pooling for efficiency
- **Memory Management**: Large repository processing uses streaming operations
- **Rate Limiting**: GitHub API rate limits handled automatically

## Security Features

### Authentication Security

- **JWT Tokens**: Stateless, cryptographically signed tokens
- **OAuth2 Integration**: Secure third-party authentication
- **Team-based Permissions**: Fine-grained access control

### Input Validation

- **Pydantic Models**: Comprehensive input validation and serialization
- **URL Validation**: GitHub repository URL format validation
- **Permission Checking**: Access validation before operations

---

The `ff_docs` package provides a robust foundation for multi-repository
documentation infrastructure with enterprise-grade security, performance, and
maintainability.
