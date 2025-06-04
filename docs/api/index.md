# API Reference

Documentation Infrastructure REST API for repository management, webhooks, and
search.

## Overview

This service provides a FastAPI-based REST API for managing the FactFiber
documentation infrastructure. The API handles repository enrollment, GitHub
webhooks, and global search across all documentation.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://docs-api.factfiber.ai`

## Authentication

Most endpoints require GitHub-based authentication via JWT tokens or OAuth2-Proxy.

## Available Endpoints

### Repository Management

#### `GET /repos/`

List all enrolled repositories.

**Response**: List of repository information including status and documentation paths.

#### `POST /repos/enroll`

Enroll a new repository in the documentation system.

**Request Body**:

```json
{
  "repository_url": "https://github.com/factfiber/repo-name",
  "documentation_path": "docs/",
  "access_permissions": ["team-docs", "team-platform"]
}
```

#### `POST /repos/unenroll`

Remove a repository from the documentation system.

#### `GET /repos/config`

Get current repository configuration.

#### `GET /repos/discover`

Discover available repositories for enrollment.

### Webhook Endpoints

#### `POST /webhooks/github`

GitHub webhook handler for real-time documentation updates.

**Headers Required**:

- `X-GitHub-Event`: Event type (push, pull_request, etc.)
- `X-Hub-Signature-256`: Webhook signature for verification

**Triggers**:

- Documentation rebuilds on push to main branch
- Link rewriting and content synchronization
- Unified MkDocs configuration updates

#### `GET /webhooks/sync/status/{repo}`

Get synchronization status for a specific repository.

#### `POST /webhooks/build/unified-config`

Trigger rebuild of unified MkDocs configuration.

### Search API

#### `GET /docs/search`

Global search across all enrolled repositories.

**Query Parameters**:

- `q`: Search query string
- `repositories`: Filter by specific repositories (optional)
- `limit`: Maximum results (default: 50)

**Response**: Filtered search results respecting repository access permissions.

### Health and Status

#### `GET /health/`

Service health check endpoint.

**Response**:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "database": "connected",
    "github_api": "accessible"
  }
}
```

## Interactive Documentation

### FastAPI Docs

Visit `/docs` on any running instance for interactive Swagger/OpenAPI documentation:

- **Development**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Authentication Flow

1. **GitHub OAuth**: Users authenticate via GitHub OAuth2-Proxy
2. **JWT Tokens**: API endpoints accept JWT tokens for programmatic access
3. **Team Permissions**: Access controlled by GitHub team membership

## Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `201`: Created (for enrollment)
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (authentication required)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (repository not enrolled)
- `500`: Internal Server Error

Error responses include detailed messages:

```json
{
  "error": "Repository not found",
  "details": "Repository 'factfiber/nonexistent' is not enrolled in documentation system",
  "code": "REPO_NOT_FOUND"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Webhook endpoints**: 100 requests per minute per repository
- **Search endpoints**: 60 requests per minute per user
- **Management endpoints**: 30 requests per minute per user

## Development

### Local Development

```bash
# Start the development server
poetry run ff-docs serve-api --reload

# Access interactive docs
open http://localhost:8000/docs
```

### Testing API Endpoints

```bash
# Health check
curl http://localhost:8000/health/

# List repositories (requires auth)
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/repos/

# Search documentation
curl "http://localhost:8000/docs/search?q=context+graph"
```

## WebSocket Support

### Real-time Updates

The API provides WebSocket endpoints for real-time updates:

#### `ws://localhost:8000/ws/build-status`

Real-time build status updates for documentation synchronization.

## SDK and Client Libraries

### Python Client

```python
from ff_docs.client import DocsAPIClient

client = DocsAPIClient(base_url="http://localhost:8000")
await client.enroll_repository("https://github.com/factfiber/new-repo")
```

### JavaScript/TypeScript

Client libraries are available for frontend integration.

---

*This API documentation is automatically updated from the FastAPI application
code. For the most current information, visit the interactive documentation at
`/docs`.*
