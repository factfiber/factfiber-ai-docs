#!/bin/bash

# Deploy documentation to AWS S3 and CloudFront
# Usage: ./deploy.sh [environment]

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

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed"
    fi

    # Check AWS profile
    if ! aws configure list-profiles | grep -q "^${AWS_PROFILE}$"; then
        error "AWS profile '${AWS_PROFILE}' not found"
    fi

    # Check Poetry
    if ! command -v poetry &> /dev/null; then
        error "Poetry is not installed"
    fi

    # Check MkDocs
    if ! poetry run mkdocs --version &> /dev/null; then
        error "MkDocs is not available in Poetry environment"
    fi

    success "All prerequisites met"
}

# Get Terraform outputs
get_terraform_outputs() {
    log "Getting Terraform outputs..."

    cd "aws/terraform/environments/${ENVIRONMENT}"

    if ! terraform output &> /dev/null; then
        error "Failed to get Terraform outputs. Is the infrastructure deployed?"
    fi

    S3_BUCKET=$(terraform output -raw s3_bucket_name)
    CLOUDFRONT_ID=$(terraform output -raw cloudfront_distribution_id)
    CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain_name)

    cd - > /dev/null

    log "S3 Bucket: ${S3_BUCKET}"
    log "CloudFront Distribution: ${CLOUDFRONT_ID}"
    log "CloudFront Domain: ${CLOUDFRONT_DOMAIN}"
}

# Build documentation
build_docs() {
    log "Building documentation..."

    # Clean previous build
    rm -rf site/

    # Build with MkDocs
    if ! poetry run mkdocs build --strict; then
        error "Documentation build failed"
    fi

    # Check build output
    if [ ! -d "site" ]; then
        error "Build directory 'site' not found"
    fi

    success "Documentation built successfully"
}

# Deploy to S3
deploy_to_s3() {
    log "Deploying to S3 bucket: ${S3_BUCKET}..."

    # Sync files to S3
    aws s3 sync site/ "s3://${S3_BUCKET}/" \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}" \
        --delete \
        --cache-control "public, max-age=3600" \
        --metadata-directive REPLACE

    # Set cache headers for static assets
    aws s3 cp "s3://${S3_BUCKET}/" "s3://${S3_BUCKET}/" \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}" \
        --recursive \
        --exclude "*" \
        --include "*.css" \
        --include "*.js" \
        --include "*.woff*" \
        --include "*.ttf" \
        --include "*.eot" \
        --include "*.svg" \
        --include "*.png" \
        --include "*.jpg" \
        --include "*.jpeg" \
        --include "*.gif" \
        --include "*.ico" \
        --cache-control "public, max-age=31536000, immutable" \
        --metadata-directive REPLACE

    success "Deployed to S3"
}

# Invalidate CloudFront cache
invalidate_cloudfront() {
    log "Invalidating CloudFront cache..."

    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --profile "${AWS_PROFILE}" \
        --distribution-id "${CLOUDFRONT_ID}" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)

    log "Created invalidation: ${INVALIDATION_ID}"

    # Wait for invalidation to complete (optional)
    if [ "${WAIT_FOR_INVALIDATION:-false}" = "true" ]; then
        log "Waiting for invalidation to complete..."
        aws cloudfront wait invalidation-completed \
            --profile "${AWS_PROFILE}" \
            --distribution-id "${CLOUDFRONT_ID}" \
            --id "${INVALIDATION_ID}"
        success "Invalidation completed"
    else
        warning "Not waiting for invalidation to complete. Check status with:"
        echo "aws cloudfront get-invalidation --distribution-id ${CLOUDFRONT_ID} --id ${INVALIDATION_ID}"
    fi
}

# Main deployment flow
main() {
    log "Starting deployment for environment: ${ENVIRONMENT}"

    check_prerequisites
    get_terraform_outputs
    build_docs
    deploy_to_s3
    invalidate_cloudfront

    success "Deployment completed!"
    echo ""
    echo "Documentation is available at:"
    echo "  https://${CLOUDFRONT_DOMAIN}"
    echo ""
}

# Run main function
main "$@"
