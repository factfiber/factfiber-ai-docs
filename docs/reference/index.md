# Technical Reference

This section contains component-specific technical documentation organized by the
package structure of the FactFiber Documentation Infrastructure.

## Package Documentation

### Core Components

#### [`ff_docs.server`](components/ff_docs/server/)

FastAPI-based REST API server providing core documentation infrastructure functionality.

- **Main Application**: Central FastAPI app with routing and middleware
- **Authentication**: JWT, GitHub OAuth, and OAuth2-Proxy integration
- **Route Handlers**: Repository management, webhooks, search, and health endpoints
- **Middleware**: CORS, authentication, and request logging

#### [`ff_docs.pipeline`](components/ff_docs/pipeline/)

Documentation processing and aggregation pipeline for multi-repository synchronization.

- **Content Sync**: Repository cloning and content processing
- **Configuration Generation**: Dynamic MkDocs configuration creation
- **Link Rewriting**: Transparent URL transformation for unified navigation
- **API Documentation**: pdoc integration for automatic code documentation

#### [`ff_docs.aggregator`](components/ff_docs/aggregator/)

Repository discovery, enrollment, and management system.

- **GitHub Integration**: Repository discovery and webhook management
- **Enrollment System**: Automated onboarding of new repositories
- **Access Control**: GitHub team-based permission validation

#### [`ff_docs.auth`](components/ff_docs/auth/)

Comprehensive authentication and authorization system supporting multiple providers.

- **JWT Handling**: Secure token generation and validation
- **GitHub Authentication**: OAuth integration and team membership verification
- **Repository Permissions**: Fine-grained access control for documentation
- **Middleware**: Request-level authentication and authorization

### Infrastructure Components

#### [`ff_docs.config`](components/ff_docs/config/)

Centralized configuration management with environment-based settings.

- **Settings Management**: Pydantic-based configuration with validation
- **Environment Variables**: Comprehensive environment-based configuration
- **Default Values**: Sensible defaults for development and production

#### [`ff_docs.search`](components/ff_docs/search/)

Global search functionality with security filtering and permission-based results.

- **Security Filtering**: Search results filtered by user access rights
- **Cross-Repository Search**: Unified search across all enrolled repositories
- **Permission Integration**: GitHub team-based search scope limitation

#### [`ff_docs.utils`](components/ff_docs/utils/)

Utility functions and helper modules for common operations.

- **Common Utilities**: Shared functionality across components
- **Validation Helpers**: Input validation and sanitization utilities
- **Error Handling**: Custom exception classes and error management

## Auto-Generated Documentation

### [Code Documentation](code/)

Complete API reference automatically generated from source code docstrings using pdoc.

- **Function Reference**: Complete function signatures and parameters
- **Class Documentation**: Detailed class hierarchy and methods
- **Type Information**: Comprehensive type annotations and hints
- **Usage Examples**: Code examples embedded in docstrings

**Features:**

- **Mathematical Notation**: LaTeX/MathJax support for complex formulas
- **Mermaid Diagrams**: Architecture diagrams and flowcharts
- **Cross-References**: Linking between modules and functions
- **Source Code**: Direct links to source code on GitHub

## Cross-References

### Related Documentation

- **[User Guide](../guide/)** - High-level usage and workflow documentation
- **[API Reference](../api/)** - FastAPI REST endpoint documentation
- **[Development Guide](../guide/development.md)** - Development setup and contribution guidelines
- **[Architecture Guide](../guide/architecture.md)** - System design and component relationships

### External Resources

- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** - Web framework documentation
- **[MkDocs Material](https://squidfunk.github.io/mkdocs-material/)** - Documentation theme
- **[GitHub API](https://docs.github.com/en/rest)** - GitHub integration reference
- **[OAuth2-Proxy](https://oauth2-proxy.github.io/oauth2-proxy/)** - Authentication proxy

## Navigation Guide

### By Functionality

**Authentication & Security:**

- [`ff_docs.auth`](components/ff_docs/auth/) - Authentication system
- [`ff_docs.server.routes.auth`](components/ff_docs/server/routes/auth.md) - Authentication endpoints

**Repository Management:**

- [`ff_docs.aggregator`](components/ff_docs/aggregator/) - Repository enrollment
- [`ff_docs.server.routes.repos`](components/ff_docs/server/routes/repos.md) - Repository API

**Documentation Processing:**

- [`ff_docs.pipeline`](components/ff_docs/pipeline/) - Content processing
- [`ff_docs.server.routes.webhooks`](components/ff_docs/server/routes/webhooks.md) - Webhook handling

**Search & Discovery:**

- [`ff_docs.search`](components/ff_docs/search/) - Search functionality
- Global search endpoints in API reference

### By Development Task

**Setting Up Authentication:**

1. Review [`ff_docs.auth.models`](components/ff_docs/auth/models.md) for data structures
2. Configure [`ff_docs.auth.github_auth`](components/ff_docs/auth/github_auth.md) for GitHub OAuth
3. Set up [`ff_docs.auth.oauth2_proxy`](components/ff_docs/auth/oauth2_proxy.md) for enterprise auth

**Adding New Repositories:**

1. Use [`ff_docs.aggregator.enrollment`](components/ff_docs/aggregator/enrollment.md) for onboarding
2. Configure [`ff_docs.aggregator.github_client`](components/ff_docs/aggregator/github_client.md) for API access
3. Set up webhooks via repository management API

**Processing Documentation:**

1. Understand [`ff_docs.pipeline.sync`](components/ff_docs/pipeline/sync.md) for content synchronization
2. Configure [`ff_docs.pipeline.config_generator`](components/ff_docs/pipeline/config_generator.md) for MkDocs
3. Set up [`ff_docs.pipeline.pdoc_integration`](components/ff_docs/pipeline/pdoc_integration.md) for API docs

## Implementation Patterns

### Common Patterns

Each package section includes:

- **Overview**: Purpose and scope of the package
- **Key Concepts**: Important concepts and terminology specific to the component
- **Usage Examples**: Practical code examples and integration patterns
- **Configuration**: Component-specific configuration options and environment variables
- **Implementation Details**: Technical specifications and internal architecture

### Code Examples

Most reference documentation includes working code examples:

```python
# Example: Repository enrollment
from ff_docs.aggregator import RepositoryEnroller
from ff_docs.config import settings

enroller = RepositoryEnroller(
    github_token=settings.github_token,
    organization=settings.github_org
)

result = await enroller.enroll_repository(
    repository_url="https://github.com/factfiber/new-repo",
    documentation_path="docs/",
    access_permissions=["docs-team", "platform-team"]
)
```

### Error Handling

Standard error handling patterns are documented throughout:

```python
# Example: Handling enrollment errors
try:
    result = await enroller.enroll_repository(repo_url)
except RepositoryAccessError as e:
    logger.error(f"Access denied for {repo_url}: {e}")
    raise HTTPException(status_code=403, detail=str(e))
except ValidationError as e:
    logger.error(f"Invalid repository configuration: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

## Documentation Standards

### Component Documentation Requirements

Each component package should include:

- **`index.md`**: Package overview and navigation
- **Module Documentation**: Detailed documentation for each module
- **Usage Examples**: Practical code examples and integration patterns
- **Configuration**: Environment variables and settings
- **Error Handling**: Exception handling and error codes

### Cross-Reference Conventions

- **Internal Links**: Use relative paths within reference section
- **External Links**: Link to user guide, API docs, and external resources
- **Code Links**: Link directly to source code where relevant
- **API Links**: Reference specific API endpoints when applicable

---

This technical reference provides comprehensive documentation for all components
of the FactFiber Documentation Infrastructure, organized for both reference
lookup and guided learning.
