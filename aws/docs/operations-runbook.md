# AWS Infrastructure Operations Runbook

This runbook provides step-by-step procedures for common operational tasks.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Deployment Operations](#deployment-operations)
3. [Troubleshooting](#troubleshooting)
4. [Emergency Procedures](#emergency-procedures)
5. [Maintenance Tasks](#maintenance-tasks)

## Daily Operations

### Check System Health

**Frequency**: Daily (automated, manual check if alerts)

```bash
# 1. Check CloudFront distribution status
aws cloudfront get-distribution-health \
  --distribution-id $DISTRIBUTION_ID \
  --profile fc-aws-infra

# 2. Check recent errors in CloudWatch
aws logs filter-log-events \
  --log-group-name /aws/lambda/us-east-1.factfiber-prod-docs-auth \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern "[ERROR]" \
  --profile fc-aws-infra \
  --region us-east-1

# 3. Check S3 bucket status
aws s3api head-bucket --bucket factfiber-prod-docs --profile fc-aws-infra

# 4. Review CloudWatch alarms
aws cloudwatch describe-alarms \
  --state-value ALARM \
  --profile fc-aws-infra
```

### Monitor Costs

**Frequency**: Weekly

```bash
# Get current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --profile fc-aws-infra
```

## Deployment Operations

### Deploy Documentation Updates

**When**: Documentation changes pushed to main branch

#### Automated Deployment (GitHub Actions)

1. Push changes to main branch
2. Monitor GitHub Actions: <https://github.com/factfiber/factfiber-ai-docs/actions>
3. Verify deployment completed successfully

#### Manual Deployment

```bash
# 1. Build documentation
cd /path/to/factfiber-ai-docs
poetry run mkdocs build --strict

# 2. Sync to S3
aws s3 sync site/ s3://factfiber-prod-docs/ \
  --profile fc-aws-infra \
  --delete \
  --cache-control "public, max-age=3600"

# 3. Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*" \
  --profile fc-aws-infra
```

### Deploy Infrastructure Changes

**When**: Terraform configuration changes

```bash
# 1. Navigate to environment
cd aws/terraform/environments/prod

# 2. Review planned changes
terraform plan -out=tfplan

# 3. Apply changes (after review)
terraform apply tfplan

# 4. Verify resources
terraform output
```

## Troubleshooting

### 403 Forbidden Errors

**Symptoms**: Users getting 403 errors when accessing documentation

**Diagnosis**:

```bash
# Check Lambda logs for auth failures
aws logs tail /aws/lambda/us-east-1.factfiber-prod-docs-auth \
  --profile fc-aws-infra \
  --region us-east-1 \
  --follow
```

**Common Causes & Solutions**:

1. **Expired GitHub token**
   - User needs to re-authenticate
   - Clear browser cookies for docs.factfiber.ai

2. **User not in allowed teams**

   ```bash
   # Verify team membership
   gh api orgs/factfiber/teams/$TEAM_SLUG/memberships/$USERNAME
   ```

3. **Lambda function error**
   - Check Lambda environment variables
   - Verify GitHub OAuth app credentials

### 404 Not Found Errors

**Symptoms**: Pages not loading, 404 errors

**Diagnosis**:

```bash
# Check if object exists in S3
aws s3 ls s3://factfiber-prod-docs/path/to/file.html \
  --profile fc-aws-infra

# Check CloudFront cache
curl -I https://docs.factfiber.ai/path/to/file.html
```

**Solutions**:

1. **File missing in S3**

   ```bash
   # Re-deploy documentation
   ./aws/scripts/deploy.sh prod
   ```

2. **CloudFront cache issue**

   ```bash
   # Create targeted invalidation
   aws cloudfront create-invalidation \
     --distribution-id $DISTRIBUTION_ID \
     --paths "/path/to/file.html" \
     --profile fc-aws-infra
   ```

### Slow Page Loads

**Symptoms**: Documentation loading slowly

**Diagnosis**:

```bash
# Check CloudFront metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name OriginLatency \
  --dimensions Name=DistributionId,Value=$DISTRIBUTION_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --profile fc-aws-infra
```

**Solutions**:

1. **Poor cache hit ratio**
   - Review cache behaviors in CloudFront
   - Ensure proper cache headers on objects

2. **Lambda cold starts**
   - Monitor Lambda duration metrics
   - Consider Lambda provisioned concurrency if needed

## Emergency Procedures

### Complete Site Down

**Priority**: P1 - Critical

**Steps**:

1. **Verify the issue**

   ```bash
   # Check multiple endpoints
   curl -I https://docs.factfiber.ai/
   curl -I https://$CLOUDFRONT_DOMAIN/
   ```

2. **Check AWS service health**
   - <https://status.aws.amazon.com/>
   - Check us-east-1 region specifically

3. **Immediate mitigation**

   ```bash
   # Disable Lambda@Edge authentication temporarily
   # Update CloudFront behavior to remove Lambda association
   aws cloudfront get-distribution-config \
     --id $DISTRIBUTION_ID \
     --profile fc-aws-infra > dist-config.json

   # Edit dist-config.json to remove Lambda associations
   # Then update distribution
   ```

4. **Root cause analysis**
   - Collect logs from all components
   - Review recent changes
   - Create incident report

### Rollback Documentation

**When**: Deployed documentation has critical errors

**Quick Rollback** (Previous version):

```bash
# 1. List recent versions
aws s3api list-object-versions \
  --bucket factfiber-prod-docs \
  --prefix index.html \
  --max-items 10 \
  --profile fc-aws-infra

# 2. Restore previous version (example)
aws s3api copy-object \
  --bucket factfiber-prod-docs \
  --copy-source factfiber-prod-docs/index.html?versionId=PREVIOUS_VERSION_ID \
  --key index.html \
  --profile fc-aws-infra

# 3. Invalidate cache
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*" \
  --profile fc-aws-infra
```

**Full Rollback** (Git commit):

```bash
# 1. Checkout previous commit
cd /path/to/factfiber-ai-docs
git checkout PREVIOUS_COMMIT_SHA

# 2. Rebuild and deploy
poetry run mkdocs build --strict
aws s3 sync site/ s3://factfiber-prod-docs/ \
  --profile fc-aws-infra \
  --delete

# 3. Invalidate cache
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*" \
  --profile fc-aws-infra
```

### Security Incident

**When**: Unauthorized access detected, credentials compromised

**Immediate Actions**:

1. **Revoke compromised credentials**

   ```bash
   # Rotate GitHub OAuth app secret
   # Update Lambda environment variables
   aws lambda update-function-configuration \
     --function-name factfiber-prod-docs-auth \
     --environment Variables="{GITHUB_CLIENT_SECRET=NEW_SECRET}" \
     --profile fc-aws-infra \
     --region us-east-1
   ```

2. **Review access logs**

   ```bash
   # Download CloudFront logs
   aws s3 sync s3://factfiber-prod-logs/cloudfront/ ./incident-logs/ \
     --profile fc-aws-infra

   # Analyze for suspicious patterns
   grep -E "403|401" incident-logs/*.gz | gzip -d
   ```

3. **Block suspicious IPs** (if needed)
   - Create WAF rules in CloudFront
   - Update security groups if applicable

## Maintenance Tasks

### Monthly Tasks

#### Update Dependencies

```bash
# 1. Update Python dependencies
cd /path/to/factfiber-ai-docs
poetry update

# 2. Test thoroughly
poetry run pytest
poetry run mkdocs build --strict

# 3. Deploy if successful
```

#### Review and Rotate Logs

```bash
# 1. Archive old CloudFront logs
aws s3 sync s3://factfiber-prod-logs/cloudfront/ \
  s3://factfiber-archive/logs/$(date +%Y/%m)/ \
  --profile fc-aws-infra \
  --exclude "*" \
  --include "*.gz" \
  --include "*.log"

# 2. Delete old logs (after archiving)
aws s3 rm s3://factfiber-prod-logs/cloudfront/ \
  --recursive \
  --profile fc-aws-infra \
  --exclude "*$(date +%Y-%m)*"
```

#### Security Patching

```bash
# 1. Check for Lambda runtime updates
aws lambda get-function \
  --function-name factfiber-prod-docs-auth \
  --profile fc-aws-infra \
  --region us-east-1 | jq '.Configuration.Runtime'

# 2. Update if needed
aws lambda update-function-configuration \
  --function-name factfiber-prod-docs-auth \
  --runtime nodejs20.x \
  --profile fc-aws-infra \
  --region us-east-1
```

### Quarterly Tasks

#### Disaster Recovery Test

1. **Backup current state**

   ```bash
   # Terraform state
   cd aws/terraform/environments/prod
   terraform state pull > backup-$(date +%Y%m%d).tfstate

   # S3 bucket inventory
   aws s3api list-object-versions \
     --bucket factfiber-prod-docs \
     --profile fc-aws-infra > bucket-inventory-$(date +%Y%m%d).json
   ```

2. **Test recovery procedures**
   - Deploy to dev environment
   - Test rollback procedures
   - Verify backup restoration

#### Cost Optimization Review

```bash
# 1. Generate cost report
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '3 months ago' +%Y-%m-01),End=$(date +%Y-%m-01) \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --profile fc-aws-infra > cost-report-$(date +%Y%m%d).json

# 2. Analyze S3 storage classes
aws s3api list-objects-v2 \
  --bucket factfiber-prod-docs \
  --query 'Contents[?StorageClass!=`INTELLIGENT_TIERING`].[Key,StorageClass]' \
  --profile fc-aws-infra

# 3. Review CloudFront usage
aws cloudfront get-distribution \
  --id $DISTRIBUTION_ID \
  --profile fc-aws-infra | jq '.Distribution.DistributionConfig.PriceClass'
```

## Appendix

### Environment Variables

```bash
# Add to ~/.bashrc or ~/.zshrc
export AWS_PROFILE=fc-aws-infra
export DISTRIBUTION_ID=<your-cloudfront-distribution-id>
export DOCS_BUCKET=factfiber-prod-docs
export LOGS_BUCKET=factfiber-prod-logs
```

### Useful Aliases

```bash
# Add to ~/.bashrc or ~/.zshrc
alias docs-logs='aws logs tail /aws/lambda/us-east-1.factfiber-prod-docs-auth --region us-east-1 --follow'
alias docs-invalidate='aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"'
alias docs-deploy='cd ~/projects/factfiber-ai-docs && ./aws/scripts/deploy.sh prod'
```

### Emergency Contacts

- **Platform Team**: <platform-team@factfiber.ai>
- **AWS Support**: [AWS Support Console](https://console.aws.amazon.com/support/)
- **On-Call**: Check PagerDuty schedule

### Reference Documentation

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [Lambda@Edge Documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-edge.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)
