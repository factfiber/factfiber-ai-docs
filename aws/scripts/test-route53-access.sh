#!/bin/bash
# Test Route53 cross-account access

set -euo pipefail

# Configuration
INFRA_PROFILE="fc-aws-infra"
ROLE_ARN="${1:-}"
EXTERNAL_ID="factfiber-docs-route53-access"

if [ -z "$ROLE_ARN" ]; then
    echo "Usage: $0 <cross-account-role-arn>"
    echo "Example: $0 arn:aws:iam::123456789012:role/FactFiberDocsRoute53CrossAccount"
    exit 1
fi

echo "Testing Route53 cross-account access..."
echo "Role ARN: $ROLE_ARN"
echo ""

# Test assuming the role
echo "1. Testing role assumption..."
CREDS=$(aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "route53-test" \
    --external-id "$EXTERNAL_ID" \
    --profile "$INFRA_PROFILE" \
    --output json 2>&1) || {
    echo "❌ Failed to assume role"
    echo "$CREDS"
    exit 1
}

echo "✓ Successfully assumed role"

# Extract credentials
export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.Credentials.SessionToken')

# Test listing hosted zones
echo ""
echo "2. Testing Route53 access..."
ZONES=$(aws route53 list-hosted-zones --output json 2>&1) || {
    echo "❌ Failed to list hosted zones"
    echo "$ZONES"
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
    exit 1
}

echo "✓ Successfully accessed Route53"
echo ""
echo "Hosted zones found:"
echo "$ZONES" | jq -r '.HostedZones[] | "  - \(.Name) (ID: \(.Id))"'

# Test getting factfiber.ai zone details
echo ""
echo "3. Testing factfiber.ai zone access..."
ZONE_ID="Z04527812OYH5L6PJJUT7"
ZONE_DETAILS=$(aws route53 get-hosted-zone --id "$ZONE_ID" --output json 2>&1) || {
    echo "❌ Failed to get zone details"
    echo "$ZONE_DETAILS"
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
    exit 1
}

echo "✓ Successfully accessed factfiber.ai zone"
echo "  Name servers:"
echo "$ZONE_DETAILS" | jq -r '.DelegationSet.NameServers[] | "    - \(.)"'

# Clean up
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN

echo ""
echo "✅ All tests passed! Cross-account access is working correctly."
echo ""
echo "You can now use this role ARN in your Terraform configuration:"
echo "  route53_cross_account_role_arn = \"$ROLE_ARN\""
