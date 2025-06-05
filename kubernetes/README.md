# Kubernetes Deployment (Archived)

**Note**: We have migrated to AWS S3 + CloudFront for documentation hosting.
These Kubernetes manifests are preserved for reference and potential future use.

## Directory Structure

```
kubernetes/
├── manifests/          # Core Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── oauth2-proxy/       # OAuth2-Proxy authentication
│   ├── k8s-oauth2-proxy.yaml
│   ├── oauth2-proxy-deployment.yaml
│   ├── oauth2-proxy-service.yaml
│   └── docker-compose.oauth2-proxy.yml
├── devspace/           # DevSpace development workflow (archived)
│   └── (files moved to repository root)
└── docker/             # Docker build artifacts
    └── Dockerfile
```

## Previous Usage

This infrastructure was designed to run the FactFiber documentation portal on Kubernetes with:

- OAuth2-Proxy for GitHub team authentication
- DevSpace for local development
- Multi-stage Docker builds

## Migration Notice

As of January 2025, we've migrated to:

- **Hosting**: AWS S3 + CloudFront
- **Authentication**: Lambda@Edge with GitHub OAuth
- **Deployment**: GitHub Actions + Terraform
- **Cost**: ~$20/month (vs ~$150/month for K8s)

See `../aws/` for the current infrastructure.

## Building Docker Images

If you need to build the Docker image for other purposes:

```bash
# Build from repository root (not from kubernetes directory)
docker build -t factfiber-docs .

# The Dockerfile expects the context to include:
# - pyproject.toml
# - poetry.lock
# - src/
# - docs/
# - mkdocs.yml
```

## DevSpace Usage (Historical)

DevSpace configuration files (`devspace.yaml` and `devspace-profiles.yaml`) are now in the
repository root for active use. DevSpace was used for local Kubernetes development:

```bash
# From repository root
devspace dev --profile development
```

This provided:

- Hot-reloading
- Port forwarding
- Log streaming
- Interactive debugging

DevSpace can still be used for local development even after the AWS migration.
