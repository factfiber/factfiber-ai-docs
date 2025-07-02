#!/bin/bash
# Create SSM parameters for GitHub OAuth credentials

set -euo pipefail

AWS_PROFILE="fc-aws-infra"
AWS_REGION="us-east-1"

echo "Setting up SSM parameters for GitHub OAuth credentials..."
echo ""

# Function to create or update parameter
create_or_update_parameter() {
    local param_name="$1"
    local param_type="$2"
    local description="$3"
    local prompt="$4"
    local secret_flag="$5"

    if aws ssm get-parameter --name "$param_name" --profile "$AWS_PROFILE" --region "$AWS_REGION" 2>/dev/null >/dev/null; then
        echo "⚠️  Parameter $param_name already exists"
        read -p "Update existing value? (y/N): " update_choice
        if [[ "$update_choice" =~ ^[Yy]$ ]]; then
            if [[ "$secret_flag" == "true" ]]; then
                read -s -p "$prompt: " param_value
                echo ""
            else
                read -p "$prompt: " param_value
            fi

            aws ssm put-parameter \
                --name "$param_name" \
                --value "$param_value" \
                --type "$param_type" \
                --overwrite \
                --profile "$AWS_PROFILE" \
                --region "$AWS_REGION"
            echo "✓ Parameter $param_name updated"
        else
            echo "→ Keeping existing value for $param_name"
        fi
    else
        echo "Creating parameter $param_name..."
        if [[ "$secret_flag" == "true" ]]; then
            read -s -p "$prompt: " param_value
            echo ""
        else
            read -p "$prompt: " param_value
        fi

        aws ssm put-parameter \
            --name "$param_name" \
            --value "$param_value" \
            --type "$param_type" \
            --description "$description" \
            --tags "Key=Project,Value=factfiber-docs" "Key=Environment,Value=prod" \
            --profile "$AWS_PROFILE" \
            --region "$AWS_REGION"
        echo "✓ Parameter $param_name created"
    fi
}

# Create/update GitHub Client ID
create_or_update_parameter \
    "/factfiber/docs/github-client-id" \
    "String" \
    "GitHub OAuth Client ID for FactFiber documentation" \
    "Enter GitHub OAuth Client ID" \
    "false"

echo ""

# Create/update GitHub Client Secret
create_or_update_parameter \
    "/factfiber/docs/github-client-secret" \
    "SecureString" \
    "GitHub OAuth Client Secret for FactFiber documentation" \
    "Enter GitHub OAuth Client Secret" \
    "true"

echo ""

# Create/update JWT Secret
echo "Creating JWT secret parameter..."
if aws ssm get-parameter --name "/factfiber/docs/jwt-secret" --profile "$AWS_PROFILE" --region "$AWS_REGION" 2>/dev/null >/dev/null; then
    echo "⚠️  Parameter /factfiber/docs/jwt-secret already exists"
    read -p "Update existing JWT secret? (y/N): " update_choice
    if [[ "$update_choice" =~ ^[Yy]$ ]]; then
        echo "Generating new JWT secret..."
        jwt_secret=$(openssl rand -base64 64 | tr -d '\n')

        aws ssm put-parameter \
            --name "/factfiber/docs/jwt-secret" \
            --value "$jwt_secret" \
            --type "SecureString" \
            --overwrite \
            --profile "$AWS_PROFILE" \
            --region "$AWS_REGION"
        echo "✓ Parameter /factfiber/docs/jwt-secret updated with new auto-generated value"
    else
        echo "→ Keeping existing value for /factfiber/docs/jwt-secret"
    fi
else
    echo "Generating JWT secret..."
    jwt_secret=$(openssl rand -base64 64 | tr -d '\n')

    aws ssm put-parameter \
        --name "/factfiber/docs/jwt-secret" \
        --value "$jwt_secret" \
        --type "SecureString" \
        --description "JWT secret key for token signing in FactFiber documentation" \
        --tags "Key=Project,Value=factfiber-docs" "Key=Environment,Value=prod" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION"
    echo "✓ Parameter /factfiber/docs/jwt-secret created with auto-generated value"
fi

echo ""
echo "✅ SSM parameters created successfully!"
echo ""
echo "Parameters created:"
echo "  - /factfiber/docs/github-client-id (String)"
echo "  - /factfiber/docs/github-client-secret (SecureString)"
echo "  - /factfiber/docs/jwt-secret (SecureString)"
echo ""
echo "Terraform will now read these values automatically."
echo "Run 'terraform apply' to update the infrastructure with the real credentials."
