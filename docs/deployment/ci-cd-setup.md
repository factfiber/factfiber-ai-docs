# CI/CD Pipeline Setup

This document describes how to set up the continuous integration and deployment pipeline for the
FactFiber.ai documentation system.

> **Note**: For infrastructure automation and secret deployment scripts, see the [CI/CD and Infrastructure Guide](../guide/cicd-infrastructure.md).

## Required GitHub Secrets

The CI/CD pipeline requires several secrets to be configured in the GitHub repository settings:

### Authentication Secrets

#### `PRIVATE_REPO_TOKEN`

**Required for**: Accessing private dependencies during build

A GitHub Personal Access Token (classic) with the following permissions:

- `repo` (Full control of private repositories)

**How to create**:

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name like "CI/CD Private Repo Access"
4. Set expiration (recommend 1 year)
5. Select scopes:
   - ✅ `repo` (Full control of private repositories)
6. Click "Generate token"
7. Copy the token immediately (you won't be able to see it again)

**How to add to repository**:

1. Go to your repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `PRIVATE_REPO_TOKEN`
4. Value: Paste the personal access token
5. Click "Add secret"

### AWS Deployment Secrets

#### `AWS_DEPLOY_ROLE_ARN`

**Required for**: AWS authentication using OIDC

The ARN of the AWS IAM role that has permissions to:

- Upload to S3 bucket
- Invalidate CloudFront distribution

Example: `arn:aws:iam::123456789012:role/GitHubActionsDeployRole`

#### `DOCS_S3_BUCKET`

**Required for**: S3 deployment target

The name of the S3 bucket where documentation will be deployed.

Example: `factfiber-docs-prod`

#### `CLOUDFRONT_DISTRIBUTION_ID`

**Required for**: Cache invalidation

The CloudFront distribution ID for the documentation site.

Example: `E1ABCDEFGHIJKL`

## Pipeline Stages

### 1. Quality Gates

Runs on every push to `main` branch and validates:

- **Security Check**: Scans for vulnerabilities using `pip-audit`
- **Test Coverage**: Requires minimum 98% coverage, prefers 100%
- **Code Quality**: Runs all pre-commit hooks (ruff, mypy, markdownlint)
- **Risk Assessment**: Detects major dependency changes requiring review

### 2. Automatic Deployment

Triggers when all quality gates pass and no risky changes detected:

- Builds documentation with MkDocs
- Deploys to S3
- Invalidates CloudFront cache
- Available at: <https://docs.factfiber.ai>

### 3. Manual Approval Deployment

Triggers when there are warnings or risky changes:

- Requires manual approval in GitHub Actions
- Same deployment process as automatic
- Used for major dependency updates or security fixes

## Private Dependencies

The project includes private dependencies that require authentication:

```toml
[tool.poetry.group.dev.dependencies]
ingolstadt = {git = "https://github.com/factfiber/ingolstadt.git"}
```

The CI pipeline handles this by:

1. Using the `PRIVATE_REPO_TOKEN` secret
2. Configuring Git URL rewriting to use the token:

   ```bash
   git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "https://github.com/"
   ```

## Security Considerations

- **Token Rotation**: Rotate the `PRIVATE_REPO_TOKEN` annually
- **Least Privilege**: The token only has `repo` scope, no additional permissions
- **Audit Trail**: All deployments are logged in GitHub Actions
- **Quality Gates**: Prevent deployment of vulnerable or untested code

## Troubleshooting

### Private Repository Access Denied

```
CalledProcessError: Command '['git', 'clone', '--recurse-submodules', '--', 'https://github.com/factfiber/ingolstadt.git']' returned non-zero exit status 128.
```

**Solution**: Ensure `PRIVATE_REPO_TOKEN` secret is configured with `repo` permissions.

### Coverage Below Threshold

```
❌ Test coverage below 98% minimum threshold
```

**Solution**: Add tests to increase coverage or use manual approval workflow.

### Security Vulnerabilities Found

```
❌ Found X high/critical vulnerabilities without fixes
```

**Solution**: Update dependencies to fix vulnerabilities or wait for upstream fixes.

## Environment Configuration

The pipeline supports different environments:

- **prod**: Production deployment to main S3 bucket
- **dev**: Development deployment (manual trigger only)

Environment-specific configuration is managed through GitHub environment settings and corresponding secret sets.
