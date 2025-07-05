#!/bin/bash
# Update GitHub Private Repository Token in AWS SSM
# This token is used by CI/CD to access private dependencies

set -euo pipefail

# Configuration
TOKEN="${1:-}"
AWS_PROFILE="${AWS_PROFILE:-factfiber-docs-deploy}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SSM_PARAMETER="/factfiber/docs/github-private-repo-token"

# Validate inputs
if [ -z "$TOKEN" ]; then
    echo "Usage: $0 <github-personal-access-token>"
    echo ""
    echo "This script updates the GitHub PAT used for accessing private repositories in CI/CD."
    echo ""
    echo "To create a new token:"
    echo "1. Go to https://github.com/settings/tokens/new"
    echo "2. Give it a name like 'FactFiber CI/CD Private Repo Access'"
    echo "3. Set expiration (recommend 1 year)"
    echo "4. Select scope: ✅ repo (Full control of private repositories)"
    echo "5. Click 'Generate token' and copy it"
    echo ""
    exit 1
fi

# Check if aws CLI is available
if ! command -v aws &> /dev/null; then
    echo "❌ Error: aws CLI not found. Please install it first."
    exit 1
fi

echo "🔑 Updating GitHub private repository token in SSM..."
echo "   Parameter: $SSM_PARAMETER"
echo "   AWS Profile: $AWS_PROFILE"
echo "   AWS Region: $AWS_REGION"
echo ""

# Update the SSM parameter
if aws ssm put-parameter \
    --name "$SSM_PARAMETER" \
    --value "$TOKEN" \
    --type SecureString \
    --overwrite \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --output text > /dev/null 2>&1; then

    echo "✅ Token updated successfully!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Run ./scripts/deploy-github-secrets.sh <repo> to deploy secrets to a GitHub repository"
    echo "2. The CI/CD pipeline will now be able to access private dependencies"
    echo ""
    echo "⚠️  Security notes:"
    echo "- This token has access to all private repositories in the organization"
    echo "- Rotate it annually for security"
    echo "- The token is stored encrypted in AWS SSM"
else
    echo "❌ Error: Failed to update SSM parameter"
    echo "   Make sure you have the correct AWS credentials and permissions"
    exit 1
fi
