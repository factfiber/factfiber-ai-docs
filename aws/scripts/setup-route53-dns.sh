#!/bin/bash
# Setup Route53 DNS record for docs.factfiber.ai

set -euo pipefail

# Configuration
DOMAIN="docs.factfiber.ai"
CLOUDFRONT_DOMAIN="d3kn4jyqa45d4p.cloudfront.net"
CLOUDFRONT_HOSTED_ZONE_ID="Z2FDTNDATAQYW2"  # Standard CloudFront hosted zone ID
AWS_PROFILE="k8"

echo "Setting up Route53 DNS record for $DOMAIN..."

# Find the hosted zone ID for factfiber.ai
echo "Finding hosted zone for factfiber.ai..."
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
    --profile "$AWS_PROFILE" \
    --query 'HostedZones[?Name==`factfiber.ai.`].Id' \
    --output text | sed 's|/hostedzone/||')

if [[ -z "$HOSTED_ZONE_ID" ]]; then
    echo "❌ Error: Could not find hosted zone for factfiber.ai"
    echo "Available hosted zones:"
    aws route53 list-hosted-zones --profile "$AWS_PROFILE" --query 'HostedZones[].{Name:Name,Id:Id}' --output table
    exit 1
fi

echo "✓ Found hosted zone: $HOSTED_ZONE_ID"

# Create the change batch JSON
CHANGE_BATCH=$(cat <<EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$DOMAIN",
        "Type": "A",
        "AliasTarget": {
          "DNSName": "$CLOUDFRONT_DOMAIN",
          "EvaluateTargetHealth": false,
          "HostedZoneId": "$CLOUDFRONT_HOSTED_ZONE_ID"
        }
      }
    }
  ]
}
EOF
)

# Create temporary file for change batch
TEMP_FILE=$(mktemp)
echo "$CHANGE_BATCH" > "$TEMP_FILE"

echo "Creating DNS record..."
echo "Domain: $DOMAIN"
echo "Target: $CLOUDFRONT_DOMAIN"
echo "Hosted Zone: $HOSTED_ZONE_ID"

# Apply the DNS change
CHANGE_ID=$(aws route53 change-resource-record-sets \
    --hosted-zone-id "$HOSTED_ZONE_ID" \
    --change-batch "file://$TEMP_FILE" \
    --profile "$AWS_PROFILE" \
    --query 'ChangeInfo.Id' \
    --output text)

# Clean up temp file
rm "$TEMP_FILE"

echo "✓ DNS change submitted: $CHANGE_ID"

# Wait for change to propagate
echo "Waiting for DNS change to propagate..."
aws route53 wait resource-record-sets-changed \
    --id "$CHANGE_ID" \
    --profile "$AWS_PROFILE"

echo "✓ DNS change completed successfully!"

# Verify the record
echo ""
echo "Verifying DNS record..."
aws route53 list-resource-record-sets \
    --hosted-zone-id "$HOSTED_ZONE_ID" \
    --profile "$AWS_PROFILE" \
    --query "ResourceRecordSets[?Name=='$DOMAIN.']" \
    --output table

echo ""
echo "🎉 DNS setup complete!"
echo "Domain: https://$DOMAIN"
echo "Note: SSL certificate warning expected until ACM certificate is configured"
echo ""
echo "Test with:"
echo "  curl -I https://$DOMAIN"
echo "  nslookup $DOMAIN"
