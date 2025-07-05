# CI/CD and Infrastructure Guide

This guide explains the automated CI/CD pipeline and infrastructure management
for the FactFiber documentation system.

## Infrastructure Overview

The documentation system uses AWS infrastructure managed by Terraform:

- **S3 Buckets**: Static documentation hosting
- **CloudFront**: Global CDN with SSL/TLS
- **Lambda@Edge**: Authentication at the edge
- **SSM Parameter Store**: Secure secret storage
- **IAM Roles**: GitHub Actions OIDC authentication

## CI/CD Pipeline

### Quality Gates

Every push to `main` triggers comprehensive quality checks:

1. **Security Scanning**: `pip-audit` for vulnerability detection
2. **Test Coverage**: Minimum 98% required (100% preferred)
3. **Code Quality**: All pre-commit hooks must pass
4. **Risk Assessment**: Major changes require manual approval

### Deployment Stages

1. **Automatic Deployment**: Clean quality gates → immediate deployment
2. **Manual Approval**: Warnings or risky changes → requires review
3. **Failure Notification**: Automated alerts on deployment failures

## Secret Management

### Centralized Secret Storage

All secrets are stored in AWS SSM Parameter Store:

```bash
/factfiber/docs/github-private-repo-token  # GitHub PAT for private repos
/factfiber/docs/github-client-id           # OAuth client ID
/factfiber/docs/github-client-secret       # OAuth client secret
/factfiber/docs/jwt-secret                 # JWT signing secret
```

### Updating the Private Repository Token

The GitHub PAT is required for accessing private dependencies like `ingolstadt`:

```bash
# Update token in SSM (requires AWS permissions)
./scripts/update-private-repo-token.sh YOUR_GITHUB_PAT
```

**Token Requirements**:

- Scope: `repo` (Full control of private repositories)
- Expiration: Recommend 1 year
- Rotation: Update annually for security

### Deploying Secrets to Repositories

Deploy all required secrets to a repository:

```bash
# Deploy secrets from AWS to GitHub
./scripts/deploy-github-secrets.sh factfiber/repository-name
```

**What Gets Deployed**:

- `AWS_DEPLOY_ROLE_ARN` - From Terraform output
- `DOCS_S3_BUCKET` - From Terraform output
- `CLOUDFRONT_DISTRIBUTION_ID` - From Terraform output
- `PRIVATE_REPO_TOKEN` - From SSM Parameter Store

## Terraform Infrastructure

### Production Environment

Located in `aws/terraform/environments/prod/`:

```hcl
# Key outputs available
output "s3_bucket_name"             # Documentation S3 bucket
output "cloudfront_distribution_id"  # CDN distribution ID
output "github_actions_role_arn"     # OIDC role for deployments
```

### Applying Changes

```bash
cd aws/terraform/environments/prod
terraform init
terraform plan
terraform apply
```

### Adding New Parameters

To add a new SSM parameter:

```hcl
resource "aws_ssm_parameter" "new_secret" {
  name        = "/factfiber/docs/new-secret"
  description = "Description of the secret"
  type        = "SecureString"
  value       = "placeholder-set-manually"

  lifecycle {
    ignore_changes = [value]  # Don't overwrite manual updates
  }

  tags = merge(local.common_tags, {
    Name = "New Secret Name"
  })
}
```

## GitHub Actions Integration

### Workflow Configuration

The deployment workflow uses the deployed secrets:

```yaml
- name: Configure Git for private repositories
  env:
    GH_TOKEN: ${{ secrets.PRIVATE_REPO_TOKEN }}
  run: |
    git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "https://github.com/"

- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
    aws-region: us-east-1

- name: Deploy to S3
  run: |
    aws s3 sync site/ s3://${{ secrets.DOCS_S3_BUCKET }}/

- name: Invalidate CloudFront cache
  run: |
    aws cloudfront create-invalidation \
      --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
      --paths "/*"
```

### Private Dependencies

For repositories with private dependencies:

1. The `PRIVATE_REPO_TOKEN` enables Git authentication
2. URL rewriting redirects HTTPS to authenticated HTTPS
3. Poetry can then install private Git dependencies

## Automation Scripts

### update-private-repo-token.sh

Updates the GitHub PAT in AWS SSM:

```bash
Usage: ./scripts/update-private-repo-token.sh <github-pat>

Environment:
  AWS_PROFILE=factfiber-docs-deploy  # AWS profile to use
  AWS_REGION=us-east-1               # AWS region
```

### deploy-github-secrets.sh

Deploys secrets from AWS to GitHub:

```bash
Usage: ./scripts/deploy-github-secrets.sh <github-repo>

Example: ./scripts/deploy-github-secrets.sh factfiber/timbuktu

Environment:
  AWS_PROFILE=factfiber-docs-deploy  # AWS profile to use
  AWS_REGION=us-east-1               # AWS region
```

## Security Best Practices

1. **Least Privilege**: Tokens have minimal required permissions
2. **Rotation Schedule**: Annual rotation for all tokens
3. **Audit Trail**: All secret access logged in CloudTrail
4. **No Hardcoding**: Secrets never in code or Terraform state
5. **OIDC Authentication**: No long-lived AWS credentials

## Troubleshooting

### Private Repository Access Denied

```
CalledProcessError: git clone https://github.com/factfiber/ingolstadt.git
returned non-zero exit status 128
```

**Solution**:

1. Ensure `PRIVATE_REPO_TOKEN` is set in GitHub secrets
2. Verify token has `repo` scope
3. Check token hasn't expired

### AWS Permission Errors

```bash
# Verify AWS identity
aws sts get-caller-identity --profile factfiber-docs-deploy

# Test SSM access
aws ssm get-parameter \
  --name /factfiber/docs/github-private-repo-token \
  --profile factfiber-docs-deploy
```

### Terraform Output Missing

```bash
cd aws/terraform/environments/prod
terraform init
terraform output
```

### GitHub CLI Authentication

```bash
# Authenticate GitHub CLI
gh auth login

# Verify authentication
gh auth status
```

## Onboarding Checklist

For new repositories requiring CI/CD:

- [ ] GitHub PAT stored in SSM (one-time setup)
- [ ] Terraform infrastructure deployed
- [ ] AWS profile configured locally
- [ ] GitHub CLI authenticated
- [ ] Run `deploy-github-secrets.sh` for repository
- [ ] Add `.github/workflows/deploy-aws.yml` to repository
- [ ] Test deployment pipeline

## Maintenance

### Regular Tasks

- **Token Rotation**: Update GitHub PAT annually
- **Terraform Updates**: Keep infrastructure current
- **Security Scanning**: Monitor for vulnerabilities
- **Access Review**: Audit who has deployment access

### Monitoring

- **CloudWatch Alarms**: Deployment failures
- **SNS Notifications**: Email alerts for issues
- **GitHub Actions**: Build status and history
- **CloudFront Metrics**: CDN performance

---

This infrastructure enables secure, automated deployments while maintaining
flexibility for different repository configurations and requirements.
