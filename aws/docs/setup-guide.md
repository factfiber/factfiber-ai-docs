# AWS Infrastructure Setup Guide

This guide walks through setting up the AWS infrastructure for FactFiber documentation.

## Prerequisites

1. **AWS CLI** installed and configured
2. **Terraform** 1.5.0 or later
3. **AWS Profile** `fc-aws-infra` configured with appropriate permissions
4. **GitHub OAuth App** created for authentication

## Step 1: Verify AWS Access

```bash
# Test AWS access
aws sts get-caller-identity --profile fc-aws-infra

# Verify S3 access
aws s3 ls --profile fc-aws-infra
```

## Step 2: Create DynamoDB Table for State Locking

The Terraform state is stored in the existing `ff-crypto-tf-state` bucket. We need to create a DynamoDB table for state locking:

```bash
# Run the setup script
./aws/scripts/create-dynamodb-table.sh
```

This creates the `ff-crypto-tf-state-lock` table with:

- Pay-per-request billing (no fixed costs)
- Proper tagging for cost allocation
- LockID as the hash key

## Step 3: Prepare Terraform Variables

### For Production Environment

```bash
cd aws/terraform/environments/prod

# Copy the example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars
```

Required variables:

- `github_client_id` - From your GitHub OAuth App
- `github_client_secret` - From your GitHub OAuth App
- `github_org` - Your GitHub organization (e.g., "factfiber")
- `allowed_teams` - List of GitHub teams with access
- `alert_email` - Email for CloudWatch alerts

### For Development Environment

```bash
cd aws/terraform/environments/dev

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
```

## Step 4: Initialize Terraform

### Production Environment

```bash
cd aws/terraform/environments/prod

# Initialize Terraform with S3 backend
terraform init
```

Expected output:

```
Initializing the backend...
Successfully configured the backend "s3"!
Initializing modules...
Initializing provider plugins...
Terraform has been successfully initialized!
```

### Development Environment

```bash
cd aws/terraform/environments/dev
terraform init
```

## Step 5: Review Infrastructure Plan

```bash
# Review what will be created
terraform plan

# Save plan for apply
terraform plan -out=tfplan
```

Review the plan carefully. It should create:

- S3 buckets for documentation and logs
- CloudFront distribution
- Lambda@Edge function for authentication
- IAM roles and policies
- CloudWatch alarms
- SNS topic for alerts

## Step 6: Deploy Infrastructure

```bash
# Apply the saved plan
terraform apply tfplan

# Or apply interactively
terraform apply
```

## Step 7: Configure GitHub Repository

After deployment, add these secrets to your GitHub repository:

1. Go to Settings → Secrets and variables → Actions
2. Add the following secrets:

```bash
# Get values from Terraform output
terraform output -json

# Add to GitHub:
AWS_DEPLOY_ROLE_ARN     # From github_actions_role_arn output
DOCS_S3_BUCKET          # From docs_bucket_name output
CLOUDFRONT_DISTRIBUTION_ID  # From cloudfront_distribution_id output
```

## Step 8: Test the Deployment

### Test S3 Access

```bash
# Upload a test file
echo "Test" > test.html
aws s3 cp test.html s3://$(terraform output -raw docs_bucket_name)/ \
    --profile fc-aws-infra

# Clean up
aws s3 rm s3://$(terraform output -raw docs_bucket_name)/test.html \
    --profile fc-aws-infra
rm test.html
```

### Test CloudFront

```bash
# Get the CloudFront URL
CLOUDFRONT_URL=$(terraform output -raw cloudfront_domain_name)

# Test public access
curl -I https://$CLOUDFRONT_URL/

# Test authentication redirect
curl -I https://$CLOUDFRONT_URL/guide/
```

### Test Lambda@Edge

Check CloudWatch logs:

```bash
# View Lambda logs
aws logs tail /aws/lambda/us-east-1.factfiber-prod-docs-auth \
    --profile fc-aws-infra \
    --region us-east-1 \
    --follow
```

## Step 9: Deploy Documentation

### Manual Deployment

```bash
# Build and deploy docs
cd /path/to/factfiber-ai-docs
poetry run mkdocs build --strict

# Sync to S3
aws s3 sync site/ s3://$(cd aws/terraform/environments/prod && terraform output -raw docs_bucket_name)/ \
    --profile fc-aws-infra \
    --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
    --distribution-id $(cd aws/terraform/environments/prod && terraform output -raw cloudfront_distribution_id) \
    --paths "/*" \
    --profile fc-aws-infra
```

### GitHub Actions Deployment

Push to main branch - GitHub Actions will automatically deploy.

## Troubleshooting

### Terraform State Issues

If you encounter state locking issues:

```bash
# List locks
aws dynamodb scan \
    --table-name ff-crypto-tf-state-lock \
    --profile fc-aws-infra

# Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

### Permission Issues

Ensure your AWS profile has these permissions:

- S3: Full access to documentation buckets
- CloudFront: Create and manage distributions
- Lambda: Create and manage functions
- IAM: Create roles and policies
- CloudWatch: Create alarms and log groups
- DynamoDB: Access to state lock table

### CloudFront 403 Errors

1. Check Lambda@Edge logs for authentication issues
2. Verify GitHub OAuth credentials in Lambda environment
3. Ensure user is in allowed GitHub teams

## Maintenance

### Update GitHub OAuth Credentials

```bash
# Update Lambda environment variables
aws lambda update-function-configuration \
    --function-name factfiber-prod-docs-auth \
    --environment Variables="{GITHUB_CLIENT_ID=new-id,GITHUB_CLIENT_SECRET=new-secret}" \
    --profile fc-aws-infra \
    --region us-east-1
```

### Add New Team Access

1. Update `allowed_teams` in terraform.tfvars
2. Run `terraform apply`
3. Changes take effect immediately

### Monitor Costs

```bash
# Check current month costs
aws ce get-cost-and-usage \
    --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
    --granularity MONTHLY \
    --metrics "BlendedCost" \
    --group-by Type=TAG,Key=Project \
    --filter '{"Tags": {"Key": "Project", "Values": ["FactFiber"]}}' \
    --profile fc-aws-infra
```

## Next Steps

1. Set up monitoring dashboards in CloudWatch
2. Configure automated backups
3. Implement CI/CD pipeline
4. Add custom domain with Route53
5. Enable AWS WAF for additional security
