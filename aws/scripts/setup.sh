#!/bin/bash

# Setup AWS infrastructure for FactFiber documentation
# Usage: ./setup.sh [environment]

set -euo pipefail

# Configuration
ENVIRONMENT="${1:-prod}"
AWS_PROFILE="fc-aws-infra"
AWS_REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        error "Terraform is not installed"
    fi

    TERRAFORM_VERSION=$(terraform version -json | jq -r '.terraform_version')
    log "Terraform version: ${TERRAFORM_VERSION}"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed"
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        error "jq is not installed"
    fi

    # Check AWS profile
    if ! aws configure list-profiles | grep -q "^${AWS_PROFILE}$"; then
        error "AWS profile '${AWS_PROFILE}' not found. Run: aws configure --profile ${AWS_PROFILE}"
    fi

    # Test AWS credentials
    if ! aws sts get-caller-identity --profile "${AWS_PROFILE}" &> /dev/null; then
        error "Unable to authenticate with AWS using profile '${AWS_PROFILE}'"
    fi

    success "All prerequisites met"
}

# Create S3 backend for Terraform state
create_terraform_backend() {
    log "Creating Terraform backend resources..."

    BACKEND_BUCKET="ff-crypto-tf-state"
    BACKEND_TABLE="ff-crypto-tf-state-lock"

    # Check if bucket exists
    if aws s3api head-bucket --bucket "${BACKEND_BUCKET}" --profile "${AWS_PROFILE}" 2> /dev/null; then
        warning "Backend bucket '${BACKEND_BUCKET}' already exists"
    else
        log "Creating S3 bucket for Terraform state..."
        aws s3api create-bucket \
            --bucket "${BACKEND_BUCKET}" \
            --profile "${AWS_PROFILE}" \
            --region "${AWS_REGION}"

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${BACKEND_BUCKET}" \
            --profile "${AWS_PROFILE}" \
            --versioning-configuration Status=Enabled

        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "${BACKEND_BUCKET}" \
            --profile "${AWS_PROFILE}" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'

        success "Created S3 bucket: ${BACKEND_BUCKET}"
    fi

    # Check if DynamoDB table exists
    if aws dynamodb describe-table --table-name "${BACKEND_TABLE}" --profile "${AWS_PROFILE}" --region "${AWS_REGION}" 2> /dev/null; then
        warning "DynamoDB table '${BACKEND_TABLE}' already exists"
    else
        log "Creating DynamoDB table for state locking..."
        aws dynamodb create-table \
            --table-name "${BACKEND_TABLE}" \
            --profile "${AWS_PROFILE}" \
            --region "${AWS_REGION}" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
            --tags Key=Project,Value=factfiber-docs Key=Purpose,Value=terraform-state-lock

        # Wait for table to be active
        aws dynamodb wait table-exists \
            --table-name "${BACKEND_TABLE}" \
            --profile "${AWS_PROFILE}" \
            --region "${AWS_REGION}"

        success "Created DynamoDB table: ${BACKEND_TABLE}"
    fi
}

# Initialize Terraform
init_terraform() {
    log "Initializing Terraform..."

    cd "aws/terraform/environments/${ENVIRONMENT}"

    # Initialize with backend config
    terraform init \
        -backend-config="profile=${AWS_PROFILE}" \
        -backend-config="region=${AWS_REGION}"

    success "Terraform initialized"
}

# Check for required variables
check_variables() {
    log "Checking for required variables..."

    if [ ! -f "terraform.tfvars" ]; then
        warning "terraform.tfvars not found. Creating from example..."
        cp terraform.tfvars.example terraform.tfvars
        error "Please edit terraform.tfvars with your configuration values"
    fi

    # Validate variables are set
    if grep -q "your-github-oauth-client-id" terraform.tfvars; then
        error "Please update GitHub OAuth credentials in terraform.tfvars"
    fi
}

# Plan Terraform deployment
plan_terraform() {
    log "Planning Terraform deployment..."

    terraform plan -out=tfplan

    echo ""
    read -p "Do you want to apply this plan? (yes/no): " -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        warning "Deployment cancelled"
        exit 0
    fi
}

# Apply Terraform
apply_terraform() {
    log "Applying Terraform configuration..."

    terraform apply tfplan

    success "Infrastructure deployed successfully!"

    # Show outputs
    echo ""
    log "Infrastructure outputs:"
    terraform output
}

# Setup GitHub secrets
setup_github_secrets() {
    log "GitHub Actions secrets needed:"
    echo ""
    echo "Add these secrets to your GitHub repository:"
    echo "  AWS_DEPLOY_ROLE_ARN: $(terraform output -raw github_actions_role_arn)"
    echo "  DOCS_S3_BUCKET: $(terraform output -raw s3_bucket_name)"
    echo "  CLOUDFRONT_DISTRIBUTION_ID: $(terraform output -raw cloudfront_distribution_id)"
    echo ""
    echo "You can add these using GitHub CLI:"
    echo "  gh secret set AWS_DEPLOY_ROLE_ARN --body \"$(terraform output -raw github_actions_role_arn)\""
    echo "  gh secret set DOCS_S3_BUCKET --body \"$(terraform output -raw s3_bucket_name)\""
    echo "  gh secret set CLOUDFRONT_DISTRIBUTION_ID --body \"$(terraform output -raw cloudfront_distribution_id)\""
}

# Main setup flow
main() {
    log "Starting AWS infrastructure setup for environment: ${ENVIRONMENT}"

    check_prerequisites
    create_terraform_backend
    init_terraform
    check_variables
    plan_terraform
    apply_terraform
    setup_github_secrets

    success "Setup completed!"
    echo ""
    echo "Next steps:"
    echo "1. Add the GitHub secrets shown above"
    echo "2. Configure your custom domain (if using)"
    echo "3. Run the deployment: ./deploy.sh ${ENVIRONMENT}"
    echo ""
}

# Run main function
main "$@"
