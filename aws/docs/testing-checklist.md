# AWS Infrastructure Testing Checklist

This checklist ensures the AWS documentation infrastructure is properly deployed and functioning.

## Pre-Deployment Checklist

### Prerequisites

- [ ] AWS CLI installed and configured
- [ ] Terraform 1.5.0+ installed
- [ ] AWS profile `fc-aws-infra` configured
- [ ] GitHub OAuth App created with:
  - [ ] Client ID obtained
  - [ ] Client Secret obtained
  - [ ] Callback URL set to `https://docs.factfiber.ai/auth/callback`
- [ ] GitHub personal access token with `repo` scope

### Terraform Configuration

- [ ] `terraform.tfvars` created from example
- [ ] All required variables set:
  - [ ] `github_client_id`
  - [ ] `github_client_secret`
  - [ ] `github_org`
  - [ ] `allowed_teams`
  - [ ] `alert_email`
- [ ] No placeholder values remain
- [ ] State bucket `ff-crypto-tf-state` exists
- [ ] DynamoDB table `ff-crypto-tf-state-lock` exists

## Deployment Testing

### Infrastructure Deployment

- [ ] Run `terraform init` successfully
- [ ] Run `terraform plan` - review output
- [ ] No unexpected resources to be created/destroyed
- [ ] Run `terraform apply` successfully
- [ ] All resources created without errors

### S3 Bucket Verification

- [ ] Primary docs bucket created
- [ ] Logs bucket created
- [ ] Bucket policies applied correctly
- [ ] Versioning enabled on docs bucket
- [ ] Lifecycle rules configured
- [ ] Server-side encryption enabled
- [ ] Public access blocked

```bash
# Test commands
aws s3api get-bucket-versioning --bucket factfiber-prod-docs
aws s3api get-bucket-encryption --bucket factfiber-prod-docs
aws s3api get-bucket-lifecycle-configuration --bucket factfiber-prod-docs
```

### CloudFront Distribution

- [ ] Distribution created and enabled
- [ ] Origin configured to S3 bucket
- [ ] Origin Access Control (OAC) configured
- [ ] Custom error pages configured (403, 404)
- [ ] Geo-restrictions applied (US + EU)
- [ ] CloudFront logs enabled
- [ ] Distribution domain accessible

```bash
# Test commands
aws cloudfront get-distribution --id $DISTRIBUTION_ID
curl -I https://$CLOUDFRONT_DOMAIN/
```

### Lambda@Edge Function

- [ ] Function deployed to us-east-1
- [ ] Environment variables set correctly
- [ ] Function associated with CloudFront
- [ ] Execution role has correct permissions
- [ ] CloudWatch logs group created

```bash
# Test commands
aws lambda get-function --function-name factfiber-prod-docs-auth --region us-east-1
aws logs tail /aws/lambda/us-east-1.factfiber-prod-docs-auth --region us-east-1
```

### IAM Configuration

- [ ] GitHub Actions role created
- [ ] OIDC provider configured
- [ ] Role trust policy correct
- [ ] S3 permissions granted
- [ ] CloudFront invalidation permissions granted

```bash
# Test commands
aws iam get-role --role-name factfiber-prod-github-actions
aws iam list-role-policies --role-name factfiber-prod-github-actions
```

## Functional Testing

### Documentation Deployment

- [ ] Run `./aws/scripts/deploy.sh prod`
- [ ] MkDocs builds successfully
- [ ] Files sync to S3
- [ ] CloudFront invalidation created
- [ ] Documentation accessible via CloudFront

### Authentication Flow

- [ ] Access public path without auth:

  ```bash
  curl -I https://docs.factfiber.ai/
  ```

- [ ] Access protected path redirects to GitHub:

  ```bash
  curl -I https://docs.factfiber.ai/guide/
  ```

- [ ] GitHub OAuth flow completes
- [ ] Authorized users can access protected content
- [ ] Unauthorized users see 403 error

### Team-Based Access

- [ ] Member of allowed team can access
- [ ] Non-member cannot access
- [ ] Team changes reflected immediately
- [ ] Token caching works (5-minute TTL)

### Content Delivery

- [ ] Static assets cached properly
- [ ] HTML files served correctly
- [ ] Images and CSS load
- [ ] JavaScript executes
- [ ] Search functionality works

## Performance Testing

### Page Load Times

- [ ] Homepage loads in < 2 seconds
- [ ] Documentation pages load in < 3 seconds
- [ ] Search results return in < 1 second
- [ ] CloudFront cache hit ratio > 80%

```bash
# Test commands
curl -w "@curl-format.txt" -o /dev/null -s https://docs.factfiber.ai/
```

### Concurrent Users

- [ ] Site handles 100 concurrent users
- [ ] No Lambda throttling errors
- [ ] CloudFront doesn't return 503 errors
- [ ] S3 doesn't rate limit

## Security Testing

### Access Control

- [ ] Cannot access S3 bucket directly
- [ ] Cannot bypass CloudFront
- [ ] Cannot access without proper GitHub auth
- [ ] Token validation rejects expired tokens
- [ ] Invalid tokens return 403, not 500

### SSL/TLS

- [ ] HTTPS enforced (HTTP redirects)
- [ ] TLS 1.2 minimum
- [ ] Valid SSL certificate
- [ ] No mixed content warnings

```bash
# Test SSL configuration
curl -I -H "X-Forwarded-Proto: http" https://docs.factfiber.ai/
nmap --script ssl-enum-ciphers -p 443 docs.factfiber.ai
```

### Headers Security

- [ ] X-Content-Type-Options: nosniff
- [ ] X-Frame-Options: DENY
- [ ] Content-Security-Policy configured
- [ ] Strict-Transport-Security enabled

## Monitoring & Alerts

### CloudWatch Alarms

- [ ] 4xx error rate alarm created
- [ ] 5xx error rate alarm created
- [ ] Lambda error alarm created
- [ ] Lambda throttle alarm created
- [ ] All alarms have SNS topic configured

### Testing Alarms

- [ ] Generate 4xx errors - verify alarm triggers
- [ ] Generate 5xx errors - verify alarm triggers
- [ ] Email notifications received
- [ ] Alarm auto-resolves when errors stop

```bash
# Generate test errors
for i in {1..10}; do curl https://docs.factfiber.ai/nonexistent; done
```

## GitHub Actions Integration

### Repository Secrets

- [ ] `AWS_DEPLOY_ROLE_ARN` set correctly
- [ ] `DOCS_S3_BUCKET` set correctly
- [ ] `CLOUDFRONT_DISTRIBUTION_ID` set correctly

### Workflow Testing

- [ ] Make documentation change
- [ ] Push to main branch
- [ ] GitHub Actions workflow triggers
- [ ] Build completes successfully
- [ ] S3 sync executes
- [ ] CloudFront invalidation runs
- [ ] Changes visible on site

## Rollback Testing

### Content Rollback

- [ ] List S3 object versions
- [ ] Restore previous version
- [ ] Invalidate CloudFront cache
- [ ] Verify old content is served

```bash
# Rollback test
aws s3api list-object-versions --bucket factfiber-prod-docs --prefix index.html
aws s3api copy-object --bucket factfiber-prod-docs \
  --copy-source factfiber-prod-docs/index.html?versionId=PREVIOUS_VERSION \
  --key index.html
```

### Infrastructure Rollback

- [ ] Terraform state backup exists
- [ ] Can revert to previous state
- [ ] No data loss during rollback
- [ ] Services remain available

## Cost Verification

### Initial Costs

- [ ] Enable Cost Explorer
- [ ] Tag all resources properly
- [ ] Set up cost allocation tags
- [ ] Create cost budget (~$20/month)

### Cost Monitoring

- [ ] S3 storage costs as expected
- [ ] CloudFront data transfer reasonable
- [ ] Lambda invocation costs minimal
- [ ] No unexpected charges

```bash
# Check costs
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE
```

## Documentation & Training

### Documentation Complete

- [ ] README.md accurate
- [ ] Migration guide complete
- [ ] Troubleshooting guide useful
- [ ] All commands tested and working

### Team Readiness

- [ ] Team knows how to deploy
- [ ] Team can troubleshoot issues
- [ ] Runbooks available
- [ ] Escalation path defined

## Sign-off

- [ ] All tests passed
- [ ] No critical issues found
- [ ] Performance meets requirements
- [ ] Security review complete
- [ ] Documentation complete
- [ ] Team trained
- [ ] Ready for production use

### Approvals

- [ ] Technical Lead: _________________ Date: _______
- [ ] Security Team: _________________ Date: _______
- [ ] Platform Team: _________________ Date: _______

## Post-Deployment

### 24-Hour Check

- [ ] No unexpected alarms
- [ ] Costs tracking as expected
- [ ] No user complaints
- [ ] Performance stable

### 1-Week Review

- [ ] Review CloudWatch metrics
- [ ] Check cost trends
- [ ] Gather user feedback
- [ ] Document any issues
- [ ] Plan improvements
