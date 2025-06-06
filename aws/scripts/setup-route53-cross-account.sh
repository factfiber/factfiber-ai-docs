#!/bin/bash
# Setup cross-account Route53 access
# This script must be run with the k8 profile to create the IAM role

set -euo pipefail

# Configuration
ROUTE53_PROFILE="k8"
INFRA_PROFILE="fc-aws-infra"
ROLE_NAME="FactFiberDocsRoute53CrossAccount"
EXTERNAL_ID="factfiber-docs-route53-access"
HOSTED_ZONE_ID="Z04527812OYH5L6PJJUT7"

echo "Setting up cross-account Route53 access..."
echo "This script will create an IAM role in the Route53 account (k8)"
echo ""

# Get the infrastructure account ID
INFRA_ACCOUNT_ID=$(aws sts get-caller-identity \
    --profile "$INFRA_PROFILE" \
    --query Account \
    --output text)

echo "Infrastructure account ID: $INFRA_ACCOUNT_ID"

# Create the trust policy document
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${INFRA_ACCOUNT_ID}:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "${EXTERNAL_ID}"
        }
      }
    }
  ]
}
EOF

# Create the permissions policy document
cat > /tmp/permissions-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:GetHostedZone",
        "route53:ListResourceRecordSets",
        "route53:ChangeResourceRecordSets",
        "route53:GetChange"
      ],
      "Resource": [
        "arn:aws:route53:::hostedzone/${HOSTED_ZONE_ID}",
        "arn:aws:route53:::change/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Check if role already exists
if aws iam get-role --role-name "$ROLE_NAME" --profile "$ROUTE53_PROFILE" 2>/dev/null; then
    echo "Role $ROLE_NAME already exists. Updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document file:///tmp/trust-policy.json \
        --profile "$ROUTE53_PROFILE"
else
    echo "Creating IAM role $ROLE_NAME..."
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Cross-account Route53 access for FactFiber docs infrastructure" \
        --profile "$ROUTE53_PROFILE"
fi

# Check if policy exists and update/create it
POLICY_NAME="Route53RecordManagement"
if aws iam get-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --profile "$ROUTE53_PROFILE" 2>/dev/null; then
    echo "Updating inline policy..."
else
    echo "Creating inline policy..."
fi

aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --policy-document file:///tmp/permissions-policy.json \
    --profile "$ROUTE53_PROFILE"

# Get the role ARN
ROLE_ARN=$(aws iam get-role \
    --role-name "$ROLE_NAME" \
    --profile "$ROUTE53_PROFILE" \
    --query 'Role.Arn' \
    --output text)

# Clean up temporary files
rm -f /tmp/trust-policy.json /tmp/permissions-policy.json

echo ""
echo "✓ Cross-account role created successfully!"
echo ""
echo "Role ARN: $ROLE_ARN"
echo "External ID: $EXTERNAL_ID"
echo ""
echo "Next steps:"
echo "1. Add the following to your Terraform variables:"
echo "   cross_account_role_arn = \"$ROLE_ARN\""
echo ""
echo "2. Test the role assumption:"
echo "   aws sts assume-role \\"
echo "     --role-arn $ROLE_ARN \\"
echo "     --role-session-name test \\"
echo "     --external-id $EXTERNAL_ID \\"
echo "     --profile $INFRA_PROFILE"
