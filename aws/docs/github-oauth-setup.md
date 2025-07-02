# GitHub OAuth App Setup for FactFiber Documentation

This guide walks through creating a GitHub OAuth App for authenticating access to the FactFiber documentation infrastructure.

## Prerequisites

- GitHub organization admin access
- Access to factfiber organization settings
- CloudFront distribution domain name from Terraform output

## Step 1: Create GitHub OAuth App

1. **Navigate to GitHub Organization Settings**
   - Go to [GitHub](https://github.com)
   - Click on your organization: `factfiber`
   - Go to Settings → Developer settings → OAuth Apps
   - Or visit: `https://github.com/organizations/factfiber/settings/applications`

2. **Create New OAuth App**
   - Click "New OAuth App"
   - Fill in the application details:

### Application Details

| Field | Value |
|-------|-------|
| **Application name** | `FactFiber Documentation` |
| **Homepage URL** | `https://docs.factfiber.ai` |
| **Authorization callback URL** | `https://docs.factfiber.ai/auth/callback` |
| **Application description** | `Authentication for FactFiber internal documentation portal` |

**Important Notes:**

- The production system uses the custom domain `docs.factfiber.ai`
- The callback URL format is: `https://docs.factfiber.ai/auth/callback`
- For development/testing, you can temporarily use the CloudFront domain: `https://d3kn4jyqa45d4p.cloudfront.net/auth/callback`

1. **Save OAuth App**
   - Click "Register application"
   - Note the **Client ID** (immediately visible)
   - Click "Generate a new client secret"
   - Copy and securely store the **Client Secret** (only shown once)

## Step 2: Configure Team Access

The OAuth app will check GitHub team membership. Ensure users are in allowed teams:

### Default Allowed Teams

- `factfiber-ai-dev`
- `factfiber-ai-learn`
- `factfiber.ai`
- `ff-analytics`
- `ff-operations`

### Add Users to Teams

1. Go to `https://github.com/orgs/factfiber/teams`
2. Select appropriate team
3. Click "Members" → "Add member"
4. Add users who need documentation access

### Modify Allowed Teams (Optional)

Edit `terraform.tfvars`:

```hcl
allowed_teams = [
  "factfiber-ai-dev",
  "factfiber-ai-learn",
  "factfiber.ai",
  "ff-analytics",
  "ff-operations",
  "your-custom-team"
]
```

## Step 3: Update Terraform Configuration

1. **Edit terraform.tfvars**

   ```bash
   cd aws/terraform/environments/prod
   vim terraform.tfvars
   ```

2. **Update OAuth Credentials**

   ```hcl
   # GitHub OAuth App credentials
   github_client_id     = "your-actual-client-id"
   github_client_secret = "your-actual-client-secret"
   ```

3. **Deploy Updated Configuration**

   ```bash
   terraform plan
   terraform apply
   ```

## Step 4: Test Authentication

1. **Visit Documentation Site**
   - Go to: `https://docs.factfiber.ai/`
   - You should be redirected to GitHub for authentication

2. **GitHub OAuth Flow**
   - Click "Authorize FactFiber Documentation"
   - You'll be redirected back to the documentation site
   - Should see successful authentication

3. **Verify Team Access**
   - Only users in allowed teams should gain access
   - Others should see an "Access Denied" message

## Step 5: Update OAuth App for Production (If Needed)

If you initially set up the OAuth app with a CloudFront domain, update it for production:

1. **Go to GitHub OAuth Settings**
   - Visit: `https://github.com/organizations/factfiber/settings/applications`
   - Find your "FactFiber Documentation" OAuth App
   - Click "Edit"

2. **Update URLs**
   - **Homepage URL**: `https://docs.factfiber.ai`
   - **Authorization callback URL**: `https://docs.factfiber.ai/auth/callback`
   - Click "Update application"

3. **Test Production URL**
   - Visit: `https://docs.factfiber.ai/`
   - Verify authentication works with updated callback URL

## Security Considerations

### OAuth App Security

- **Keep Client Secret secure** - store in password manager
- **Limit organization access** - ensure app is org-scoped
- **Regular rotation** - consider rotating secrets periodically
- **Monitor usage** - check OAuth app access logs

### Team-Based Access Control

- **Principle of least privilege** - only add necessary teams
- **Regular access review** - audit team memberships quarterly
- **Remove departing users** - immediately remove from teams

### Network Security

- **HTTPS only** - all OAuth URLs must use HTTPS
- **Valid redirect URLs** - GitHub validates callback URLs
- **CloudFront security** - Lambda@Edge validates requests

## Troubleshooting

### Authentication Issues

#### "Application not found" Error

- Verify OAuth app exists in correct organization
- Check Client ID is correct in terraform.tfvars
- Ensure OAuth app is not suspended

#### "Redirect URI mismatch" Error

- Verify callback URL in OAuth app settings
- Format: `https://docs.factfiber.ai/auth/callback`
- Must match exactly (no trailing slash)
- For development: `https://d3kn4jyqa45d4p.cloudfront.net/auth/callback`

#### "Access Denied" Error

- User not in allowed GitHub teams
- Add user to appropriate team
- Verify team names in terraform.tfvars

#### Lambda@Edge Errors

- Check CloudWatch logs: `/aws/lambda/us-east-1.factfiber-prod-docs-auth`
- Verify environment variables in Lambda function
- Check GitHub API rate limits

### OAuth App Configuration Issues

#### Client Secret Errors

- Regenerate client secret if compromised
- Update terraform.tfvars with new secret
- Redeploy with `terraform apply`

#### Team Access Issues

- Verify GitHub organization permissions
- Check team visibility (public vs private)
- Ensure OAuth app has organization access

## Monitoring and Maintenance

### CloudWatch Monitoring

- **Lambda Errors**: `factfiber-prod-lambda-auth-errors`
- **Lambda Throttles**: `factfiber-prod-lambda-auth-throttles`
- **CloudFront 4xx/5xx**: Monitor authentication failures

### GitHub OAuth App

- **Usage metrics**: Check OAuth app usage in GitHub settings
- **Rate limits**: Monitor GitHub API usage
- **Security events**: Review OAuth app access logs

### Regular Tasks

- **Quarterly access review**: Audit team memberships
- **Annual secret rotation**: Rotate OAuth credentials
- **Monitor failed authentications**: Check for unauthorized access attempts

## Advanced Configuration

### Custom Teams per Environment

```hcl
# Production - restrictive access
allowed_teams = ["platform-team", "docs-team"]

# Development - broader access
allowed_teams = ["platform-team", "docs-team", "developers", "qa-team"]
```

### Multiple OAuth Apps

Consider separate OAuth apps for different environments:

- `FactFiber Documentation (Production)`
- `FactFiber Documentation (Development)`

### Session Management

- **Session duration**: Currently set to 24 hours
- **Automatic logout**: Handled by Lambda@Edge
- **Remember me**: Not implemented (for security)

## Support

For issues with OAuth setup:

1. Check this documentation
2. Review CloudWatch logs
3. Test with different GitHub accounts
4. Verify team memberships in GitHub
5. Contact platform team for assistance
