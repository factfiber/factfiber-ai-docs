#!/bin/bash
# Setup infrastructure deployment role following AWS best practices

set -euo pipefail

# Configuration
ADMIN_PROFILE="fc-aws-admin"
ROLE_NAME="FactFiberDocsInfrastructureRole"
EXTERNAL_ID="factfiber-docs-infrastructure"

echo "Setting up infrastructure deployment role..."
echo "This follows AWS best practices for service-specific permissions"
echo ""

# Check if role already exists
if aws iam get-role --role-name "$ROLE_NAME" --profile "$ADMIN_PROFILE" 2>/dev/null; then
    echo "Role $ROLE_NAME already exists. Updating policies..."

    # Update trust policy
    aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document file://aws/iam/infrastructure-trust-policy.json \
        --profile "$ADMIN_PROFILE"
else
    echo "Creating IAM role $ROLE_NAME..."
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file://aws/iam/infrastructure-trust-policy.json \
        --description "Infrastructure deployment role for FactFiber docs" \
        --profile "$ADMIN_PROFILE"
fi

# Create or update the permissions policy
POLICY_NAME="FactFiberDocsInfrastructurePolicy"
if aws iam get-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --profile "$ADMIN_PROFILE" 2>/dev/null; then
    echo "Updating inline policy..."
else
    echo "Creating inline policy..."
fi

aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --policy-document file://aws/iam/infrastructure-role-policy.json \
    --profile "$ADMIN_PROFILE"

# Get the role ARN
ROLE_ARN=$(aws iam get-role \
    --role-name "$ROLE_NAME" \
    --profile "$ADMIN_PROFILE" \
    --query 'Role.Arn' \
    --output text)

echo ""
echo "✓ Infrastructure role created successfully!"
echo ""
echo "Role ARN: $ROLE_ARN"
echo "External ID: $EXTERNAL_ID"
echo ""
echo "Usage:"
echo "1. For Terraform operations:"
echo "   export AWS_PROFILE=fc-aws-infra"
echo "   aws sts assume-role \\"
echo "     --role-arn $ROLE_ARN \\"
echo "     --role-session-name terraform-deploy \\"
echo "     --external-id $EXTERNAL_ID"
echo ""
echo "2. Or configure a profile in ~/.aws/config:"
echo "   [profile factfiber-docs-deploy]"
echo "   role_arn = $ROLE_ARN"
echo "   source_profile = fc-aws-infra"
echo "   external_id = $EXTERNAL_ID"
echo ""
echo "Benefits of this approach:"
echo "• Principle of least privilege - only necessary permissions"
echo "• Clear separation between user and service permissions"
echo "• Auditable role assumption for deployments"
echo "• Follows AWS IAM best practices"
