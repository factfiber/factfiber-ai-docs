#!/bin/bash
# Update FactFiber docs infrastructure role with additional permissions

set -euo pipefail

ROLE_NAME="FactFiberDocsInfrastructureRole"
POLICY_NAME="FactFiberDocsInfrastructurePolicy"
POLICY_FILE="aws/iam/infrastructure-role-policy.json"

echo "Updating IAM policy for infrastructure deployment role..."

# Verify policy file exists
if [[ ! -f "$POLICY_FILE" ]]; then
    echo "Error: Policy file $POLICY_FILE not found"
    exit 1
fi

# Validate JSON syntax
if ! jq empty "$POLICY_FILE" 2>/dev/null; then
    echo "Error: Invalid JSON in policy file $POLICY_FILE"
    exit 1
fi

echo "Policy file validated successfully"

# Update the role policy
echo "Updating role policy $POLICY_NAME for role $ROLE_NAME..."
aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --policy-document "file://$POLICY_FILE" \
    --profile fc-aws-admin

echo "✓ IAM policy updated successfully"

# Test role assumption to verify permissions
echo ""
echo "Testing role assumption..."
if aws sts assume-role \
    --role-arn "arn:aws:iam::221017573558:role/FactFiberDocsInfrastructureRole" \
    --role-session-name "test-permissions" \
    --external-id "factfiber-docs-infrastructure" \
    --profile fc-aws-admin \
    --query 'Credentials.AccessKeyId' \
    --output text >/dev/null; then
    echo "✓ Role assumption test successful"
else
    echo "⚠ Role assumption test failed"
fi

echo ""
echo "Updated infrastructure role with enhanced permissions:"
echo "- Added iam:ListRolePolicies for policy management"
echo "- Added OIDC provider permissions for GitHub Actions integration"
echo "- Added resource access for token.actions.githubusercontent.com"
