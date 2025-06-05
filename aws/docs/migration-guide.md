# Migration Guide: Kubernetes to AWS

This guide details the process of migrating the FactFiber documentation infrastructure
from Kubernetes to AWS S3 + CloudFront.

## Overview

The migration moves documentation hosting from a Kubernetes cluster to:

- **S3**: Static file storage
- **CloudFront**: Global CDN with caching
- **Lambda@Edge**: Authentication via GitHub OAuth
- **GitHub Actions**: Automated deployments

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with `fc-aws-infra` profile
3. **Terraform** version 1.5.0 or later
4. **GitHub OAuth App** created with:
   - Authorization callback URL: `https://docs.factfiber.ai/auth/callback`
   - Required scopes: `read:org`

## Migration Steps

### Phase 1: Infrastructure Setup

1. **Clone and prepare the repository**:

   ```bash
   git clone https://github.com/factfiber/factfiber-ai-docs
   cd factfiber-ai-docs
   ```

2. **Configure AWS credentials**:

   ```bash
   aws configure --profile fc-aws-infra
   ```

3. **Set up Terraform variables**:

   ```bash
   cd aws/terraform/environments/prod
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

4. **Run the setup script**:

   ```bash
   cd ../../../../
   ./aws/scripts/setup.sh prod
   ```

### Phase 2: Initial Deployment

1. **Build and deploy documentation**:

   ```bash
   ./aws/scripts/deploy.sh prod
   ```

2. **Verify deployment**:
   - Check S3 bucket contents
   - Test CloudFront distribution
   - Verify Lambda@Edge authentication

### Phase 3: DNS Configuration

1. **Create Route 53 hosted zone** (if not exists):

   ```bash
   aws route53 create-hosted-zone \
     --name docs.factfiber.ai \
     --caller-reference "$(date +%s)"
   ```

2. **Update DNS records**:

   ```bash
   # Get CloudFront domain
   CLOUDFRONT_DOMAIN=$(cd aws/terraform/environments/prod && terraform output -raw cloudfront_domain_name)

   # Create CNAME record
   aws route53 change-resource-record-sets \
     --hosted-zone-id YOUR_ZONE_ID \
     --change-batch '{
       "Changes": [{
         "Action": "UPSERT",
         "ResourceRecordSet": {
           "Name": "docs.factfiber.ai",
           "Type": "CNAME",
           "TTL": 300,
           "ResourceRecords": [{"Value": "'${CLOUDFRONT_DOMAIN}'"}]
         }
       }]
     }'
   ```

### Phase 4: Testing and Validation

1. **Test authentication flow**:

   ```bash
   # Test public path
   curl -I https://docs.factfiber.ai/

   # Test protected path (should redirect to GitHub)
   curl -I https://docs.factfiber.ai/guide/
   ```

2. **Verify team access**:
   - Log in with GitHub account
   - Ensure team members can access
   - Verify non-team members are blocked

3. **Performance testing**:

   ```bash
   # Test CDN performance
   curl -w "@curl-format.txt" -o /dev/null -s https://docs.factfiber.ai/
   ```

### Phase 5: Cutover

1. **Update GitHub repository settings**:

   ```bash
   # Add GitHub secrets
   gh secret set AWS_DEPLOY_ROLE_ARN --body "$(cd aws/terraform/environments/prod && terraform output -raw github_actions_role_arn)"
   gh secret set DOCS_S3_BUCKET --body "$(cd aws/terraform/environments/prod && terraform output -raw s3_bucket_name)"
   gh secret set CLOUDFRONT_DISTRIBUTION_ID --body "$(cd aws/terraform/environments/prod && terraform output -raw cloudfront_distribution_id)"
   ```

2. **Test GitHub Actions deployment**:

   ```bash
   # Make a small change to docs
   echo "Test change" >> docs/index.md
   git add docs/index.md
   git commit -m "Test AWS deployment"
   git push
   ```

3. **Monitor deployment**:
   - Check GitHub Actions logs
   - Verify S3 sync completed
   - Confirm CloudFront invalidation

### Phase 6: Decommission Kubernetes

1. **Export any necessary data**:

   ```bash
   # Save Kubernetes configurations if needed
   kubectl get all -n ff-docs-dev -o yaml > k8s-backup.yaml
   ```

2. **Delete Kubernetes resources**:

   ```bash
   kubectl delete namespace ff-docs-dev
   ```

3. **Archive Kubernetes files**:
   - Already completed in `kubernetes/` directory

## Rollback Procedures

### Quick Rollback to Kubernetes

If issues arise, you can quickly rollback:

1. **Keep Kubernetes running** during initial migration
2. **Update DNS** to point back to Kubernetes ingress
3. **Debug AWS issues** while service remains available

### AWS Infrastructure Rollback

1. **Restore previous S3 version**:

   ```bash
   # List object versions
   aws s3api list-object-versions \
     --bucket YOUR_BUCKET \
     --prefix index.html

   # Restore specific version
   aws s3api copy-object \
     --bucket YOUR_BUCKET \
     --copy-source YOUR_BUCKET/index.html?versionId=PREVIOUS_VERSION \
     --key index.html
   ```

2. **Revert Terraform changes**:

   ```bash
   cd aws/terraform/environments/prod
   terraform state pull > backup.tfstate
   # Restore previous state if needed
   ```

## Monitoring and Alerts

### CloudWatch Alarms

The following alarms are automatically created:

- **CloudFront 4xx errors**: Authentication failures
- **CloudFront 5xx errors**: Server errors
- **Lambda errors**: Authentication function failures
- **Lambda throttles**: Rate limiting issues

### Viewing Logs

1. **CloudFront logs** (in S3):

   ```bash
   aws s3 ls s3://factfiber-prod-logs/cloudfront/
   ```

2. **Lambda@Edge logs** (CloudWatch):

   ```bash
   aws logs tail /aws/lambda/us-east-1.factfiber-prod-docs-auth
   ```

## Cost Optimization

### Initial Setup

- Enable S3 Intelligent-Tiering
- Set appropriate cache headers
- Configure CloudFront caching rules

### Ongoing Monitoring

```bash
# Check S3 costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE
```

## Troubleshooting

### Common Issues

1. **403 Forbidden**:
   - Check Lambda@Edge logs
   - Verify GitHub token validity
   - Ensure user is in allowed teams

2. **404 Not Found**:
   - Verify S3 object exists
   - Check CloudFront origin settings
   - Ensure index.html is set as default

3. **Slow Updates**:
   - Check CloudFront invalidation status
   - Verify GitHub Actions completed
   - Monitor S3 sync progress

### Debug Commands

```bash
# Test S3 access
aws s3 ls s3://YOUR_BUCKET/ --profile fc-aws-infra

# Check CloudFront distribution
aws cloudfront get-distribution --id YOUR_DIST_ID

# View Lambda function
aws lambda get-function --function-name factfiber-prod-docs-auth --region us-east-1
```

## Post-Migration Tasks

1. **Update documentation** references to new infrastructure
2. **Train team** on new deployment process
3. **Document runbooks** for common operations
4. **Schedule cost review** after first month
5. **Plan disaster recovery** testing

## Support

For issues during migration:

1. Check CloudWatch logs and alarms
2. Review Terraform state for drift
3. Contact platform team for AWS access issues
