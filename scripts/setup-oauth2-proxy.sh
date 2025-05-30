#!/bin/bash
# Setup script for OAuth2-Proxy with repository-scoped authentication
# This script helps configure OAuth2-Proxy for FactFiber.ai docs

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🔧 FactFiber.ai OAuth2-Proxy Setup${NC}"
echo "=================================================="

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to generate secure random string
generate_secret() {
    openssl rand -base64 32 | tr -d '\n'
}

# Function to generate JWT secret
generate_jwt_secret() {
    openssl rand -hex 32
}

# Check prerequisites
echo -e "\n${BLUE}Checking prerequisites...${NC}"

if ! command_exists openssl; then
    print_error "OpenSSL is required but not installed"
    exit 1
fi
print_status "OpenSSL found"

if ! command_exists docker; then
    print_warning "Docker not found - required for local development"
else
    print_status "Docker found"
fi

if ! command_exists docker-compose; then
    print_warning "Docker Compose not found - required for local development"
else
    print_status "Docker Compose found"
fi

# Check for existing environment file
ENV_FILE="$PROJECT_ROOT/.env.oauth2-proxy"
if [[ -f "$ENV_FILE" ]]; then
    print_warning "Environment file already exists: $ENV_FILE"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Using existing environment file"
        source "$ENV_FILE"
    else
        rm "$ENV_FILE"
    fi
fi

# Create environment file if it doesn't exist
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "\n${BLUE}Creating OAuth2-Proxy environment configuration...${NC}"

    # Copy example file
    cp "$PROJECT_ROOT/.env.oauth2-proxy.example" "$ENV_FILE"

    # Generate secrets
    COOKIE_SECRET=$(generate_secret)
    JWT_SECRET=$(generate_jwt_secret)

    # Replace placeholders in environment file
    sed -i.bak "s/your_32_byte_base64_encoded_secret_here/$COOKIE_SECRET/g" "$ENV_FILE"
    sed -i.bak "s/your_jwt_secret_key_for_fallback_auth/$JWT_SECRET/g" "$ENV_FILE"
    rm "$ENV_FILE.bak"

    print_status "Generated OAuth2-Proxy cookie secret"
    print_status "Generated JWT secret key"
    print_status "Created environment file: $ENV_FILE"
fi

# GitHub OAuth App setup instructions
echo -e "\n${BLUE}GitHub OAuth Application Setup${NC}"
echo "=============================================="
print_info "You need to create a GitHub OAuth Application:"
echo
echo "1. Go to: https://github.com/settings/applications/new"
echo "2. Fill in the application details:"
echo "   - Application name: FactFiber.ai Documentation"
echo "   - Homepage URL: http://localhost:4180 (for development)"
echo "   - Authorization callback URL: http://localhost:4180/oauth2/callback"
echo
echo "3. After creating the app, you'll get a Client ID and Client Secret"
echo "4. Update these values in your environment file: $ENV_FILE"
echo

# GitHub Personal Access Token setup
echo -e "${BLUE}GitHub Personal Access Token Setup${NC}"
echo "=============================================="
print_info "You need a GitHub Personal Access Token for API access:"
echo
echo "1. Go to: https://github.com/settings/tokens"
echo "2. Click 'Generate new token (classic)'"
echo "3. Select the following scopes:"
echo "   - repo (Full control of private repositories)"
echo "   - read:org (Read org and team membership)"
echo "   - user:email (Access user email address)"
echo "4. Copy the token and update GITHUB_TOKEN in: $ENV_FILE"
echo

# Organization configuration
echo -e "${BLUE}Organization Configuration${NC}"
echo "=============================================="
print_info "Update the GITHUB_ORG value in your environment file with your organization name"
echo

# Test OAuth2-Proxy configuration
echo -e "\n${BLUE}Testing OAuth2-Proxy Configuration${NC}"
echo "=============================================="

# Check if required environment variables are set
if [[ -f "$ENV_FILE" ]]; then
    source "$ENV_FILE"

    if [[ -z "${GITHUB_OAUTH_CLIENT_ID:-}" ]] || [[ "$GITHUB_OAUTH_CLIENT_ID" == "your_github_oauth_client_id_here" ]]; then
        print_warning "GITHUB_OAUTH_CLIENT_ID not configured"
    else
        print_status "GitHub OAuth Client ID configured"
    fi

    if [[ -z "${GITHUB_OAUTH_CLIENT_SECRET:-}" ]] || [[ "$GITHUB_OAUTH_CLIENT_SECRET" == "your_github_oauth_client_secret_here" ]]; then
        print_warning "GITHUB_OAUTH_CLIENT_SECRET not configured"
    else
        print_status "GitHub OAuth Client Secret configured"
    fi

    if [[ -z "${GITHUB_TOKEN:-}" ]] || [[ "$GITHUB_TOKEN" == "ghp_your_github_personal_access_token_here" ]]; then
        print_warning "GITHUB_TOKEN not configured"
    else
        print_status "GitHub Personal Access Token configured"
    fi
fi

# Docker Compose setup
echo -e "\n${BLUE}Docker Compose Setup${NC}"
echo "=============================================="

if command_exists docker-compose; then
    print_info "To start OAuth2-Proxy with FF-Docs API:"
    echo "  cd $PROJECT_ROOT"
    echo "  docker-compose -f docker-compose.oauth2-proxy.yml --env-file .env.oauth2-proxy up -d"
    echo
    print_info "To view logs:"
    echo "  docker-compose -f docker-compose.oauth2-proxy.yml logs -f"
    echo
    print_info "To stop services:"
    echo "  docker-compose -f docker-compose.oauth2-proxy.yml down"
fi

# Kubernetes deployment
echo -e "\n${BLUE}Kubernetes Deployment${NC}"
echo "=============================================="
print_info "For production deployment with Kubernetes:"
echo "1. Update the secrets in k8s-oauth2-proxy.yaml with base64 encoded values:"
echo "   - GitHub OAuth Client ID and Secret"
echo "   - Cookie secret (generated above)"
echo "   - GitHub Personal Access Token"
echo "   - JWT secret (generated above)"
echo
echo "2. Update domain names in the configuration files"
echo "3. Apply the configuration:"
echo "   kubectl apply -f k8s-oauth2-proxy.yaml"

# Testing endpoints
echo -e "\n${BLUE}Testing Endpoints${NC}"
echo "=============================================="
print_info "After starting the services, test these endpoints:"
echo
echo "Public endpoints (no authentication required):"
echo "  http://localhost:4180/health/"
echo "  http://localhost:4180/auth/status"
echo
echo "Protected endpoints (requires GitHub authentication):"
echo "  http://localhost:4180/repos/"
echo "  http://localhost:4180/repos/discover"
echo
echo "OAuth2-Proxy specific endpoints:"
echo "  http://localhost:4180/oauth2/sign_in"
echo "  http://localhost:4180/oauth2/sign_out"
echo "  http://localhost:8080/metrics (metrics)"

# Repository-scoped testing
echo -e "\n${BLUE}Repository-Scoped Authentication Testing${NC}"
echo "=============================================="
print_info "To test repository-scoped access:"
echo "1. Access a repository-specific endpoint:"
echo "   http://localhost:4180/docs/repo/your-repo-name"
echo "2. You should be redirected to GitHub OAuth if not authenticated"
echo "3. After authentication, access will be granted only if you have"
echo "   repository access in GitHub"

# Final notes
echo -e "\n${GREEN}Setup Complete!${NC}"
echo "=============================================="
print_status "OAuth2-Proxy configuration files created"
print_status "Environment template configured with generated secrets"
print_warning "Remember to configure your GitHub OAuth App and Personal Access Token"
print_info "Check the generated files:"
echo "  - $ENV_FILE"
echo "  - $PROJECT_ROOT/oauth2-proxy-config.yaml"
echo "  - $PROJECT_ROOT/docker-compose.oauth2-proxy.yml"
echo "  - $PROJECT_ROOT/k8s-oauth2-proxy.yaml"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "1. Configure GitHub OAuth App credentials in $ENV_FILE"
echo "2. Configure GitHub Personal Access Token in $ENV_FILE"
echo "3. Start the services using Docker Compose"
echo "4. Test authentication and repository-scoped access"

echo -e "\n${GREEN}Happy documenting! 📚${NC}"
