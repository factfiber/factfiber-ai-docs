#!/bin/bash
# Create DynamoDB table for Terraform state locking

set -euo pipefail

# Configuration
AWS_PROFILE="fc-aws-infra"
AWS_REGION="us-east-1"
TABLE_NAME="ff-crypto-tf-state-lock"

echo "Creating DynamoDB table for Terraform state locking..."

# Check if table already exists
if aws dynamodb describe-table \
    --table-name "$TABLE_NAME" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    2>/dev/null; then
    echo "✓ Table $TABLE_NAME already exists"
    exit 0
fi

# Create the table
echo "Creating table $TABLE_NAME..."
aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --tags Key=Project,Value=FactFiber \
           Key=Environment,Value=shared \
           Key=Purpose,Value=terraform-state-lock \
           Key=ManagedBy,Value=terraform

# Wait for table to be active
echo "Waiting for table to become active..."
aws dynamodb wait table-exists \
    --table-name "$TABLE_NAME" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION"

echo "✓ DynamoDB table $TABLE_NAME created successfully"

# Display table information
echo ""
echo "Table details:"
aws dynamodb describe-table \
    --table-name "$TABLE_NAME" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Table.{Name:TableName,Status:TableStatus,ARN:TableArn}' \
    --output table
