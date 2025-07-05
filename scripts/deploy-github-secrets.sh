#!/bin/bash
# Deploy GitHub Secrets from AWS SSM and Terraform Outputs
# This script sets up all required GitHub Actions secrets for a repository

set -euo pipefail

# Check required commands
for cmd in aws gh terraform jq; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "❌ Error: $cmd command not found. Please install it first."
        exit 1
    fi
done

# Configuration
REPO="${1:-}"
AWS_PROFILE="${AWS_PROFILE:-factfiber-docs-deploy}"
AWS_ADMIN_PROFILE="${AWS_ADMIN_PROFILE:-fc-aws-admin}"
AWS_REGION="${AWS_REGION:-us-east-1}"
TERRAFORM_DIR="aws/terraform/environments/prod"

# Validate inputs
if [ -z "$REPO" ]; then
    echo "Usage: $0 <github-repo>"
    echo "Example: $0 factfiber/factfiber-ai-docs"
    exit 1
fi

echo "🔧 Deploying GitHub Secrets for repository: $REPO"
echo "   AWS Profile (Terraform): $AWS_PROFILE"
echo "   AWS Profile (SSM): $AWS_ADMIN_PROFILE"
echo "   AWS Region: $AWS_REGION"
echo ""

# Function to check if secret exists
secret_exists() {
    local repo="$1"
    local secret_name="$2"
    gh secret list -R "$repo" | grep -q "^${secret_name}" || return 1
}

# Function to set GitHub secret
set_github_secret() {
    local repo="$1"
    local secret_name="$2"
    local secret_value="$3"

    if secret_exists "$repo" "$secret_name"; then
        echo "   ⚠️  Secret $secret_name already exists. Updating..."
    else
        echo "   ✅ Creating secret $secret_name..."
    fi

    echo "$secret_value" | gh secret set "$secret_name" -R "$repo"
}

# Step 1: Get Terraform outputs
echo "📋 Getting Terraform outputs..."
cd "$TERRAFORM_DIR" || exit 1

# Initialize Terraform if needed
if [ ! -d .terraform ]; then
    echo "   Initializing Terraform..."
    terraform init -input=false
fi

# Get outputs
S3_BUCKET=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "")
CLOUDFRONT_ID=$(terraform output -raw cloudfront_distribution_id 2>/dev/null || echo "")
GITHUB_ROLE_ARN=$(terraform output -raw github_actions_role_arn 2>/dev/null || echo "")

cd - > /dev/null

if [ -z "$S3_BUCKET" ] || [ -z "$CLOUDFRONT_ID" ] || [ -z "$GITHUB_ROLE_ARN" ]; then
    echo "❌ Error: Could not get Terraform outputs. Make sure Terraform is applied."
    exit 1
fi

echo "   ✅ S3 Bucket: $S3_BUCKET"
echo "   ✅ CloudFront ID: $CLOUDFRONT_ID"
echo "   ✅ GitHub Role ARN: $GITHUB_ROLE_ARN"
echo ""

# Step 2: Get private repo token from SSM
echo "🔑 Getting private repository token from SSM..."
# Use admin profile for SSM access
PRIVATE_REPO_TOKEN=$(aws ssm get-parameter \
    --name "/factfiber/docs/github-private-repo-token" \
    --with-decryption \
    --query 'Parameter.Value' \
    --output text \
    --profile "$AWS_ADMIN_PROFILE" \
    --region "$AWS_REGION" 2>/dev/null || echo "")

if [ -z "$PRIVATE_REPO_TOKEN" ] || [ "$PRIVATE_REPO_TOKEN" = "placeholder-set-manually" ]; then
    echo "❌ Error: Private repo token not found or not set in SSM."
    echo "   Please update the SSM parameter /factfiber/docs/github-private-repo-token with a valid GitHub PAT."
    echo ""
    echo "   To update it, run:"
    echo "   aws ssm put-parameter \\"
    echo "     --name '/factfiber/docs/github-private-repo-token' \\"
    echo "     --value 'YOUR_GITHUB_PAT' \\"
    echo "     --type SecureString \\"
    echo "     --overwrite \\"
    echo "     --profile $AWS_ADMIN_PROFILE \\"
    echo "     --region $AWS_REGION"
    exit 1
fi

echo "   ✅ Private repo token retrieved from SSM"
echo ""

# Step 3: Deploy GitHub secrets
echo "🚀 Deploying GitHub secrets to $REPO..."

# AWS secrets
set_github_secret "$REPO" "AWS_DEPLOY_ROLE_ARN" "$GITHUB_ROLE_ARN"
set_github_secret "$REPO" "DOCS_S3_BUCKET" "$S3_BUCKET"
set_github_secret "$REPO" "CLOUDFRONT_DISTRIBUTION_ID" "$CLOUDFRONT_ID"

# Private repo token
set_github_secret "$REPO" "PRIVATE_REPO_TOKEN" "$PRIVATE_REPO_TOKEN"

echo ""
echo "✅ All secrets deployed successfully!"
echo ""
echo "📝 Summary of deployed secrets:"
echo "   - AWS_DEPLOY_ROLE_ARN: $GITHUB_ROLE_ARN"
echo "   - DOCS_S3_BUCKET: $S3_BUCKET"
echo "   - CLOUDFRONT_DISTRIBUTION_ID: $CLOUDFRONT_ID"
echo "   - PRIVATE_REPO_TOKEN: ****** (hidden)"
echo ""
echo "🎉 Repository $REPO is now ready for CI/CD deployment!"
