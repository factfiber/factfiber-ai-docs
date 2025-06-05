# DevSpace Development Guide

This guide explains how to use DevSpace for developing the FactFiber
Documentation Infrastructure with Kubernetes.

## Prerequisites

### Required Tools

1. **DevSpace CLI** - Install from [devspace.sh](https://devspace.sh)

   ```bash
   # Install DevSpace CLI
   curl -s -L "https://github.com/loft-sh/devspace/releases/latest" |
     sed -nE 's!.*"([^"]*devspace-linux-amd64)".*!https://github.com\1!p' |
     xargs -n 1 curl -L -o devspace
   chmod +x devspace
   sudo mv devspace /usr/local/bin
   ```

2. **Kubernetes Cluster** - Local or remote
   - **Local**: minikube, kind, k3d, Docker Desktop
   - **Remote**: EKS, GKE, AKS, or any Kubernetes cluster

3. **kubectl** - Configured to access your cluster

4. **Docker** - For building container images

### Optional Tools

- **Helm** - For managing complex deployments
- **k9s** - For interactive cluster management
- **GitHub CLI** - For authentication setup

## Quick Start

### 1. Initialize Development Environment

```bash
# Clone the repository
git clone https://github.com/factfiber/factfiber-ai-docs
cd factfiber-ai-docs

# Set up development environment
devspace run setup

# Start development
devspace dev
```

### 2. Development Workflow

Once `devspace dev` is running:

- **FastAPI server** available at: <http://localhost:8000>
- **API documentation** at: <http://localhost:8000/docs>
- **MkDocs server** (when running) at: <http://localhost:8001>
- **Auto-sync** enabled for code changes

### 3. Common Development Commands

```bash
# Start development with hot-reloading
devspace dev

# Run tests in the development container
devspace run test

# Check linting
devspace run lint

# Access container shell
devspace run shell

# Start MkDocs development server
devspace run docs-serve

# Start FastAPI server manually
devspace run api-serve

# View application logs
devspace run logs

# Reset development environment
devspace run reset
```

## Development Profiles

DevSpace supports different development scenarios through profiles:

### Standard Development (default)

```bash
devspace dev
```

- Full application stack
- Hot-reloading enabled
- Both FastAPI and MkDocs ports available

### API-Only Development

```bash
devspace dev -p api-only
```

- Focus on FastAPI development
- Only port 8000 exposed
- Optimized for backend work

### Documentation-Only Development

```bash
devspace dev -p docs-only
```

- Focus on MkDocs documentation
- Only port 8001 exposed
- Optimized for documentation authoring

### OAuth2-Proxy Development

```bash
devspace dev -p oauth2-proxy
```

- Includes OAuth2-Proxy service
- Authentication flow testing
- GitHub OAuth integration

### Full Stack Development

```bash
devspace dev -p full-stack
```

- Includes PostgreSQL and Redis
- Complete infrastructure stack
- Integration testing environment

### Staging Environment

```bash
devspace dev -p staging
```

- Production-like settings
- No debug mode
- Performance testing

## Configuration

### Environment Variables

DevSpace uses these environment variables:

```bash
# Required for GitHub integration
export GITHUB_TOKEN="your-github-token"

# Optional OAuth2-Proxy setup
export OAUTH2_PROXY_CLIENT_ID="your-github-app-id"
export OAUTH2_PROXY_CLIENT_SECRET="your-github-app-secret"

# Kubernetes namespace (default: ff-docs-dev)
export NAMESPACE="ff-docs-dev"
```

### Custom Configuration

You can override DevSpace configuration:

```yaml
# devspace.local.yaml (gitignored)
vars:
  NAMESPACE: "my-custom-namespace"
  IMAGE: "my-registry/ff-docs"

dev:
  app:
    env:
      - name: CUSTOM_ENV_VAR
        value: "my-value"
```

## File Synchronization

DevSpace automatically syncs these paths:

- `./src/` → `/app/src/` (triggers container restart)
- `./docs/` → `/app/docs/` (no restart needed)
- `./mkdocs.yml` → `/app/mkdocs.yml` (triggers restart)

### Sync Behavior

- **Python source changes** → Container restarts automatically
- **Documentation changes** → Live reload in MkDocs
- **Configuration changes** → Container restarts

## Port Forwarding

| Service | Local Port | Container Port | Description |
|---------|------------|----------------|-------------|
| FastAPI | 8000 | 8000 | Main application server |
| MkDocs | 8001 | 8001 | Documentation server |
| OAuth2-Proxy | 4180 | 4180 | Authentication proxy |
| PostgreSQL | 5432 | 5432 | Database (full-stack profile) |
| Redis | 6379 | 6379 | Cache (full-stack profile) |

## Debugging

### Container Access

```bash
# Open shell in main container
devspace enter

# Open shell in specific container
devspace enter --container oauth2-proxy

# Run specific command
devspace enter -- poetry run pytest tests/unit/
```

### Logs and Monitoring

```bash
# Follow all logs
devspace logs -f

# Logs from specific container
devspace logs -c oauth2-proxy -f

# Kubernetes events
kubectl get events -n ff-docs-dev --sort-by=.metadata.creationTimestamp
```

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health/

# Check OAuth2-Proxy health
curl http://localhost:4180/ping

# Kubernetes pod status
kubectl get pods -n ff-docs-dev
```

## Testing in Development

### Unit Tests

```bash
devspace run test
# or
devspace enter -- poetry run pytest tests/unit/ -v
```

### Integration Tests

```bash
devspace enter -- poetry run pytest tests/integration/ -v
```

### API Testing

```bash
# Test API endpoints
curl http://localhost:8000/health/
curl http://localhost:8000/repos/
curl -X POST http://localhost:8000/webhooks/github/test
```

### Authentication Testing

With OAuth2-Proxy profile:

```bash
# Access protected endpoint
curl http://localhost:4180/repos/

# Check authentication headers
curl -H "Authorization: Bearer token" http://localhost:8000/repos/
```

## Troubleshooting

### Common Issues

1. **Port already in use**

   ```bash
   # Kill processes using ports
   sudo lsof -ti:8000 | xargs kill -9
   sudo lsof -ti:8001 | xargs kill -9
   ```

2. **Container won't start**

   ```bash
   # Check container logs
   devspace logs

   # Rebuild image
   devspace build --force-rebuild
   ```

3. **File sync not working**

   ```bash
   # Restart DevSpace
   devspace dev --force-rebuild

   # Check sync status
   devspace status
   ```

4. **Kubernetes connection issues**

   ```bash
   # Check cluster access
   kubectl cluster-info

   # Verify namespace
   kubectl get ns ff-docs-dev
   ```

### Reset Development Environment

```bash
# Full reset
devspace run reset

# Or manual cleanup
devspace reset
kubectl delete namespace ff-docs-dev
```

## Advanced Usage

### Custom Build Context

```yaml
# Build with custom context
images:
  app:
    build:
      buildArgs:
        ENVIRONMENT: development
        POETRY_VERSION: 1.8.0
```

### Multiple Services

```yaml
# Add additional services
deployments:
  my-service:
    kubectl:
      manifests:
        - kubernetes/manifests/my-service.yaml
```

### Production Deployment

```bash
# Deploy to production-like environment
devspace deploy -p staging --namespace ff-docs-staging
```

## Best Practices

1. **Use appropriate profiles** for your development focus
2. **Keep containers lightweight** during development
3. **Use file sync** instead of rebuilding for quick iteration
4. **Monitor resource usage** with `kubectl top pods -n ff-docs-dev`
5. **Clean up regularly** with `devspace run reset`
6. **Version your DevSpace config** with profiles for team consistency

## Integration with IDE

### VS Code

Install the DevSpace extension for:

- One-click development startup
- Integrated terminal access
- Log streaming
- Kubernetes resource management

### IntelliJ/PyCharm

Configure remote interpreter:

1. Add Docker interpreter
2. Point to DevSpace container
3. Enable automatic upload/sync

## CI/CD Integration

DevSpace can be used in CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Deploy to development
  run: |
    devspace deploy --profile staging
    devspace run test
```

## Support

For issues with DevSpace setup:

1. Check [DevSpace documentation](https://devspace.sh/docs)
2. Review container logs: `devspace logs`
3. Verify Kubernetes access: `kubectl get pods -n ff-docs-dev`
4. Reset environment: `devspace run reset`

For application-specific issues, see the main [Development Guide](getting-started.md).
