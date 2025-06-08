# AWS Infrastructure for FactFiber Documentation

This directory contains the AWS infrastructure code for hosting the FactFiber documentation
portal using S3, CloudFront, and Lambda@Edge for authentication.

## Architecture Overview

```text
GitHub Push → GitHub Actions → Build Docs → S3 Upload → CloudFront CDN → Users
                                               ↓
                                         Lambda@Edge
                                               ↓
                                         GitHub OAuth
```

## Cost Breakdown

Estimated monthly costs for US-only serving with EU CloudFront:

- **S3 Storage**: ~$5/month (100GB documentation)
- **CloudFront**: ~$10/month (US + EU distribution)
- **Lambda@Edge**: ~$3/month (authentication checks)
- **Total**: ~$18/month (vs $150/month for Kubernetes)

## Directory Structure

```
aws/
├── terraform/              # Infrastructure as Code
│   ├── modules/           # Reusable Terraform modules
│   │   ├── s3/           # S3 bucket configuration
│   │   ├── cloudfront/   # CloudFront distribution
│   │   ├── lambda-edge/  # Lambda@Edge authentication
│   │   └── iam/          # IAM roles and policies
│   └── environments/      # Environment-specific configs
│       ├── dev/          # Development environment
│       └── prod/         # Production environment
├── lambda/                # Lambda function source code
│   └── auth/             # GitHub OAuth authentication
├── scripts/               # Deployment and utility scripts
└── docs/                  # Infrastructure documentation
```

## Prerequisites

1. **AWS CLI** configured with profile `fc-aws-infra`:

   ```bash
   aws configure --profile fc-aws-infra
   ```

2. **Terraform** version 1.5.0 or later:

   ```bash
   terraform version
   ```

3. **GitHub OAuth App** with credentials:
   - Client ID
   - Client Secret
   - Authorization callback URL

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform/environments/prod
terraform init
```

### 2. Configure Variables

Create `terraform.tfvars`:

```hcl
github_client_id     = "your-github-oauth-client-id"
github_client_secret = "your-github-oauth-client-secret"
github_org          = "factfiber"
allowed_teams       = ["platform-team", "docs-team", "admin-team"]
```

### 3. Deploy Infrastructure

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

## Key Components

### S3 Buckets

- **Primary bucket**: Hosts documentation files
- **Log bucket**: Stores CloudFront access logs
- **Versioning**: Enabled for rollback capability
- **Lifecycle**: Old versions deleted after 30 days

### CloudFront Distribution

- **Origins**: S3 bucket with OAC (Origin Access Control)
- **Behaviors**: Static file serving with caching
- **Geo-restriction**: US primary, EU secondary
- **SSL**: AWS Certificate Manager certificate

### Lambda@Edge Authentication

- **Viewer Request**: Validates GitHub OAuth tokens
- **Teams check**: Verifies user belongs to allowed teams
- **Token caching**: Reduces GitHub API calls
- **Fallback**: Public docs for unauthenticated users

### IAM Configuration

- **S3 bucket policy**: CloudFront OAC access only
- **Lambda execution role**: Minimal permissions
- **GitHub Actions role**: S3 write, CloudFront invalidation

## Security Features

1. **Authentication**: GitHub OAuth with team-based access
2. **Encryption**: S3 bucket encryption at rest
3. **TLS**: HTTPS-only access via CloudFront
4. **Access logs**: CloudFront logs to dedicated S3 bucket
5. **Principle of least privilege**: Minimal IAM permissions

## Deployment Process

### GitHub Actions Workflow

1. **Build documentation**: MkDocs generates static files
2. **Upload to S3**: Sync built files to S3 bucket
3. **Invalidate cache**: Clear CloudFront cache for updates
4. **Notify completion**: Post deployment status

### Manual Deployment

```bash
# Build documentation
mkdocs build

# Sync to S3
aws s3 sync site/ s3://factfiber-docs-prod/ \
  --profile fc-aws-infra \
  --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --profile fc-aws-infra \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"
```

## Monitoring and Maintenance

### CloudWatch Alarms

- **5xx errors**: Alert on server errors
- **4xx errors**: Monitor authentication failures
- **Origin latency**: Track S3 response times
- **Lambda errors**: Authentication function failures

### Cost Optimization

- **S3 Intelligent-Tiering**: Automatic cost optimization
- **CloudFront caching**: Reduce origin requests
- **Lambda bundling**: Minimize cold starts
- **Log retention**: 7-day retention for cost control

## Rollback Procedures

1. **Documentation rollback**:

   ```bash
   # List S3 object versions
   aws s3api list-object-versions \
     --bucket factfiber-docs-prod \
     --prefix index.html

   # Restore previous version
   aws s3api copy-object \
     --bucket factfiber-docs-prod \
     --copy-source factfiber-docs-prod/index.html?versionId=abc123 \
     --key index.html
   ```

2. **Infrastructure rollback**:

   ```bash
   # Terraform state rollback
   terraform state pull > backup.tfstate
   terraform apply -target=module.affected_resource
   ```

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Check Lambda@Edge logs for auth failures
2. **404 Not Found**: Verify S3 object exists and CloudFront path
3. **502 Bad Gateway**: Check Lambda function errors
4. **Slow updates**: CloudFront cache invalidation pending

### Debug Commands

```bash
# Check CloudFront distribution
aws cloudfront get-distribution --id $DISTRIBUTION_ID

# View Lambda@Edge logs (us-east-1)
aws logs tail /aws/lambda/us-east-1.auth-function \
  --profile fc-aws-infra \
  --region us-east-1

# Test S3 access
aws s3 ls s3://factfiber-docs-prod/ --profile fc-aws-infra
```

## Migration from Kubernetes

See [Migration Guide](docs/migration-guide.md) for detailed steps on:

- DNS cutover process
- Data migration from existing system
- Rollback procedures
- Validation checklist

## Support

For infrastructure issues:

- Check CloudWatch logs and alarms
- Review Terraform state for drift
- Contact platform team for AWS access issues
