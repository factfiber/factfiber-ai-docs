# OAuth2-Proxy Repository-Scoped Authentication Setup

This guide explains how to set up OAuth2-Proxy for repository-scoped
authentication with FactFiber.ai documentation infrastructure.

## Overview

OAuth2-Proxy provides enterprise-grade authentication by integrating with
GitHub OAuth, ensuring that users can only access documentation for
repositories they have permission to view in GitHub. This creates a seamless
security model where documentation access mirrors code access permissions.

## Architecture

```text
User Browser → OAuth2-Proxy → GitHub OAuth → FF-Docs API → GitHub API
                     ↓              ↓             ↓
               Authentication   User Info    Repository Permissions
```

### Key Components

1. **OAuth2-Proxy**: Handles GitHub OAuth authentication and forwards user information
2. **FF-Docs API**: Validates repository access using GitHub API
3. **GitHub OAuth App**: Provides authentication and user information
4. **GitHub API**: Used for real-time repository permission checking

## Prerequisites

Before setting up OAuth2-Proxy, ensure you have:

- A GitHub organization with repositories
- Administrative access to create GitHub OAuth applications
- A GitHub Personal Access Token with appropriate scopes
- Docker and Docker Compose (for local development)
- Kubernetes cluster (for production deployment)

## Quick Start

### 1. Run the Setup Script

```bash
./scripts/setup-oauth2-proxy.sh
```

This script will:

- Generate secure secrets
- Create environment configuration
- Provide GitHub OAuth App setup instructions

### 2. Create GitHub OAuth Application

1. Go to [GitHub OAuth Apps](https://github.com/settings/applications/new)
2. Fill in the application details:
   - **Application name**: FactFiber.ai Documentation
   - **Homepage URL**: `http://localhost:4180` (development) or your domain
   - **Authorization callback URL**: `http://localhost:4180/oauth2/callback`
3. Copy the Client ID and Client Secret
4. Update `.env.oauth2-proxy` with these values

### 3. Create GitHub Personal Access Token

1. Go to [GitHub Tokens](https://github.com/settings/tokens)
2. Create a new token with these scopes:
   - `repo` (Full control of private repositories)
   - `read:org` (Read org and team membership)
   - `user:email` (Access user email address)
3. Update `.env.oauth2-proxy` with the token

### 4. Start Services

```bash
# For local development
docker-compose -f docker-compose.oauth2-proxy.yml \
  --env-file .env.oauth2-proxy up -d

# View logs
docker-compose -f docker-compose.oauth2-proxy.yml logs -f
```

## Configuration Files

### Environment Configuration

The `.env.oauth2-proxy` file contains all necessary configuration:

```bash
# GitHub OAuth Application
GITHUB_OAUTH_CLIENT_ID="your_client_id"
GITHUB_OAUTH_CLIENT_SECRET="your_client_secret"

# OAuth2-Proxy Security
OAUTH2_PROXY_COOKIE_SECRET="base64_encoded_secret"

# GitHub Configuration
GITHUB_ORG="your-organization"
GITHUB_TOKEN="your_personal_access_token"

# JWT Fallback
JWT_SECRET_KEY="your_jwt_secret"
```

### OAuth2-Proxy Configuration

The `oauth2-proxy-config.yaml` defines OAuth2-Proxy behavior:

- **Provider**: GitHub OAuth
- **Scopes**: `user:email read:org repo`
- **Headers**: User info forwarded to upstream
- **Security**: HTTPS, secure cookies, CSRF protection

### Docker Compose Configuration

The `docker-compose.oauth2-proxy.yml` sets up:

- OAuth2-Proxy service on port 4180
- FF-Docs API service on port 8000
- Optional Redis for session storage
- Network configuration for service communication

## Repository-Scoped Access Control

### How It Works

1. **User Authentication**: OAuth2-Proxy authenticates users via GitHub
2. **Request Routing**: Repository-specific URLs are identified
3. **Permission Check**: GitHub API validates user's repository access
4. **Access Decision**: Allow or deny based on repository permissions

### URL Patterns

The system recognizes these repository-specific patterns:

- `/docs/repo/{repo-name}` - Repository documentation
- `/api/repos/{repo-name}` - Repository API endpoints
- `/site/{repo-name}` - MkDocs site content
- `/projects/{repo-name}` - Project-specific documentation

### Permission Levels

GitHub repository roles map to internal permissions:

| GitHub Role | Permissions |
|-------------|------------|
| `read` | `repo:read` |
| `triage` | `repo:read`, `repo:triage` |
| `write` | `repo:read`, `repo:write` |
| `maintain` | `repo:read`, `repo:write`, `repo:maintain` |
| `admin` | `repo:read`, `repo:write`, `repo:maintain`, `repo:admin` |

## Testing

### Automated Testing

Run the comprehensive test suite:

```bash
./scripts/test-oauth2-proxy-auth.sh
```

This tests:

- Public endpoint access
- Authentication requirements
- Repository-specific access control
- OAuth2-Proxy configuration
- Header forwarding

### Manual Testing

1. **Access public endpoint**: `http://localhost:4180/health/`
   - Should return 200 without authentication

2. **Access protected endpoint**: `http://localhost:4180/repos/`
   - Should redirect to GitHub OAuth (302)

3. **Complete authentication**: Follow OAuth flow
   - Should return to original URL after authentication

4. **Test repository access**: `http://localhost:4180/docs/repo/test-repo`
   - Should check GitHub repository permissions
   - Allow access only if user has repository access

### Test Endpoints

| Endpoint | Authentication | Purpose |
|----------|---------------|---------|
| `/health/` | None | Health check |
| `/auth/status` | None | Authentication status |
| `/repos/` | Required | Repository listing |
| `/docs/repo/{name}` | Repository-scoped | Repository documentation |
| `/oauth2/sign_in` | None | OAuth sign-in page |
| `/oauth2/sign_out` | None | OAuth sign-out |

## Production Deployment

### Kubernetes Deployment

1. **Update secrets** in `k8s-oauth2-proxy.yaml`:

   ```bash
   # Encode secrets
   echo -n "your_client_id" | base64
   echo -n "your_client_secret" | base64
   openssl rand -base64 32 | tr -d '\n' | base64
   ```

2. **Update domains** throughout the configuration files

3. **Deploy to Kubernetes**:

   ```bash
   kubectl apply -f kubernetes/oauth2-proxy/k8s-oauth2-proxy.yaml
   ```

### Production Considerations

- **HTTPS**: Always use HTTPS in production
- **Session Storage**: Use Redis for session storage at scale
- **Monitoring**: Enable metrics and logging
- **Security Headers**: Configure appropriate security headers
- **Rate Limiting**: Implement rate limiting for OAuth endpoints

### Environment Variables

For production, set these environment variables:

```bash
# Security
OAUTH2_PROXY_COOKIE_SECURE=true
OAUTH2_PROXY_FORCE_HTTPS=true

# Session Storage
OAUTH2_PROXY_SESSION_STORE_TYPE=redis
OAUTH2_PROXY_REDIS_CONNECTION_URL=redis://redis:6379

# Domains
OAUTH2_PROXY_COOKIE_DOMAINS=.yourdomain.com
OAUTH2_PROXY_WHITELIST_DOMAINS=yourdomain.com
```

## Troubleshooting

### Common Issues

1. **OAuth callback URL mismatch**
   - Ensure GitHub OAuth App callback URL matches OAuth2-Proxy URL
   - Format: `https://yourdomain.com/oauth2/callback`

2. **Repository access denied**
   - Verify user has repository access in GitHub
   - Check GitHub Personal Access Token scopes
   - Verify organization membership

3. **Authentication loop**
   - Check cookie security settings
   - Verify HTTPS configuration
   - Check session storage configuration

### Debug Mode

Enable debug logging:

```bash
# In environment file
OAUTH2_PROXY_LOG_LEVEL=debug

# Or in Kubernetes
env:
- name: OAUTH2_PROXY_LOG_LEVEL
  value: "debug"
```

### Log Analysis

Check OAuth2-Proxy logs for:

- Authentication requests
- Header forwarding
- Upstream communication
- Error messages

### Health Checks

Monitor these endpoints:

- `/ping` - OAuth2-Proxy health
- `/ready` - OAuth2-Proxy readiness
- `/metrics` - Prometheus metrics
- `/health/` - FF-Docs API health

## Security Considerations

### OAuth2-Proxy Security

- **Secure cookies**: Always use secure cookies in production
- **CSRF protection**: Enabled by default
- **Session timeout**: Configure appropriate timeouts
- **Rate limiting**: Implement to prevent abuse

### API Security

- **Header validation**: Validate all OAuth2-Proxy headers
- **Token handling**: Secure GitHub token transmission
- **Permission caching**: Cache with appropriate TTL
- **Audit logging**: Log all repository access attempts

### GitHub Integration

- **Token scopes**: Use minimal required scopes
- **Token rotation**: Regularly rotate Personal Access Tokens
- **Organization policies**: Enforce GitHub organization policies
- **Team management**: Use GitHub teams for permission management

## Advanced Configuration

### Custom Headers

Add custom headers in OAuth2-Proxy configuration:

```yaml
headers:
  X-Auth-Request-User: "{{ .User }}"
  X-Auth-Request-Email: "{{ .Email }}"
  X-Custom-Header: "custom-value"
```

### Team-Based Access

Restrict access to specific teams:

```bash
OAUTH2_PROXY_GITHUB_TEAM=docs-team
```

### Multiple Organizations

Support multiple GitHub organizations:

```yaml
github:
  orgs:
    - org1
    - org2
```

### Custom Templates

Use custom sign-in templates:

```yaml
custom_templates_dir: "/templates"
```

## Monitoring and Metrics

### Prometheus Metrics

OAuth2-Proxy exposes metrics at `/metrics`:

- `oauth2_proxy_requests_total` - Total requests
- `oauth2_proxy_authentication_attempts_total` - Authentication attempts
- `oauth2_proxy_authenticated_sessions_total` - Active sessions

### Custom Metrics

FF-Docs API provides custom metrics:

- Repository access attempts
- Permission check latency
- GitHub API call rates
- Cache hit ratios

### Alerting

Set up alerts for:

- High authentication failure rates
- Repository access denials
- GitHub API rate limits
- Service health issues

## Migration and Upgrades

### Upgrading OAuth2-Proxy

1. **Backup configuration**
2. **Update container image**
3. **Test in staging environment**
4. **Rolling update in production**

### Configuration Changes

1. **Update ConfigMaps/environment files**
2. **Restart services**
3. **Validate functionality**
4. **Monitor for issues**

## Support and Resources

### Documentation Links

- [OAuth2-Proxy Documentation](https://oauth2-proxy.github.io/oauth2-proxy/)
- [GitHub OAuth Apps](https://docs.github.com/en/developers/apps/oauth-apps)
- [GitHub API Documentation](https://docs.github.com/en/rest)

### Community Resources

- [OAuth2-Proxy GitHub](https://github.com/oauth2-proxy/oauth2-proxy)
- [Community Examples](https://github.com/oauth2-proxy/oauth2-proxy/tree/main/examples)

### Getting Help

For issues specific to this setup:

1. Check the troubleshooting section
2. Review service logs
3. Run the test script
4. Consult the OAuth2-Proxy documentation
