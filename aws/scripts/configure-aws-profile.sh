#!/bin/bash
# Configure AWS profile for FactFiber docs deployment

echo "Configuring AWS profile for FactFiber docs deployment..."

# Add the deployment profile to ~/.aws/config
PROFILE_CONFIG="
[profile factfiber-docs-deploy]
role_arn = arn:aws:iam::221017573558:role/FactFiberDocsInfrastructureRole
source_profile = fc-aws-infra
external_id = factfiber-docs-infrastructure
region = us-east-1
"

# Check if profile already exists
if grep -q "factfiber-docs-deploy" ~/.aws/config 2>/dev/null; then
    echo "Profile factfiber-docs-deploy already exists in ~/.aws/config"
else
    echo "Adding factfiber-docs-deploy profile to ~/.aws/config..."
    echo "$PROFILE_CONFIG" >> ~/.aws/config
    echo "✓ Profile added successfully!"
fi

echo ""
echo "Test the profile:"
echo "  aws sts get-caller-identity --profile factfiber-docs-deploy"
echo ""
echo "Use with Terraform:"
echo "  export AWS_PROFILE=factfiber-docs-deploy"
echo "  terraform plan"
