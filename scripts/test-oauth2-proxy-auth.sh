#!/bin/bash
# Test script for OAuth2-Proxy repository-scoped authentication
# This script validates that OAuth2-Proxy correctly enforces repository access

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
OAUTH2_PROXY_URL="${OAUTH2_PROXY_URL:-http://localhost:4180}"
API_URL="${API_URL:-http://localhost:8000}"
TEST_REPO="${TEST_REPO:-test-repo}"
TEST_USER="${TEST_USER:-testuser}"

echo -e "${BLUE}🧪 OAuth2-Proxy Repository Authentication Tests${NC}"
echo "=============================================================="
echo "OAuth2-Proxy URL: $OAUTH2_PROXY_URL"
echo "Direct API URL: $API_URL"
echo "Test Repository: $TEST_REPO"
echo

# Function to print test results
print_test_result() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"

    if [[ "$expected" == "$actual" ]]; then
        echo -e "${GREEN}✓ PASS${NC} $test_name"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} $test_name (expected: $expected, got: $actual)"
        return 1
    fi
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to make HTTP request and return status code
http_status() {
    local url="$1"
    local auth_header="${2:-}"

    if [[ -n "$auth_header" ]]; then
        curl -s -o /dev/null -w "%{http_code}" -H "$auth_header" "$url" || echo "000"
    else
        curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000"
    fi
}

# Function to make HTTP request and return response body
http_response() {
    local url="$1"
    local auth_header="${2:-}"

    if [[ -n "$auth_header" ]]; then
        curl -s -H "$auth_header" "$url" 2>/dev/null || echo ""
    else
        curl -s "$url" 2>/dev/null || echo ""
    fi
}

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Health endpoint should be accessible without authentication
echo -e "\n${BLUE}Test 1: Public Health Endpoint${NC}"
print_info "Testing public health endpoint access..."

status=$(http_status "$OAUTH2_PROXY_URL/health/")
if print_test_result "Health endpoint accessible" "200" "$status"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 2: Auth status endpoint should be accessible without authentication
echo -e "\n${BLUE}Test 2: Public Auth Status Endpoint${NC}"
print_info "Testing public auth status endpoint..."

status=$(http_status "$OAUTH2_PROXY_URL/auth/status")
if print_test_result "Auth status endpoint accessible" "200" "$status"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 3: Protected endpoint should require authentication
echo -e "\n${BLUE}Test 3: Protected Endpoint Requires Authentication${NC}"
print_info "Testing that protected endpoints require authentication..."

status=$(http_status "$OAUTH2_PROXY_URL/repos/")
if print_test_result "Protected endpoint redirects to auth" "302" "$status"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 4: Repository-specific endpoint should require authentication
echo -e "\n${BLUE}Test 4: Repository-Specific Authentication${NC}"
print_info "Testing repository-specific endpoint protection..."

status=$(http_status "$OAUTH2_PROXY_URL/docs/repo/$TEST_REPO")
if print_test_result "Repository endpoint requires auth" "302" "$status"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 5: Direct API access (bypassing OAuth2-Proxy) should work for health
echo -e "\n${BLUE}Test 5: Direct API Health Check${NC}"
print_info "Testing direct API access for health endpoint..."

status=$(http_status "$API_URL/health/")
if print_test_result "Direct API health check" "200" "$status"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 6: Direct API protected endpoint should require authentication
echo -e "\n${BLUE}Test 6: Direct API Authentication Requirement${NC}"
print_info "Testing direct API protected endpoint..."

status=$(http_status "$API_URL/repos/")
if print_test_result "Direct API requires auth" "401" "$status"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 7: OAuth2-Proxy configuration endpoints
echo -e "\n${BLUE}Test 7: OAuth2-Proxy Configuration${NC}"
print_info "Testing OAuth2-Proxy specific endpoints..."

# Check ping endpoint
status=$(http_status "$OAUTH2_PROXY_URL/ping")
if print_test_result "OAuth2-Proxy ping endpoint" "200" "$status"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Check ready endpoint
status=$(http_status "$OAUTH2_PROXY_URL/ready")
if print_test_result "OAuth2-Proxy ready endpoint" "200" "$status"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 8: OAuth2-Proxy sign-in page
echo -e "\n${BLUE}Test 8: OAuth2-Proxy Sign-in Page${NC}"
print_info "Testing OAuth2-Proxy sign-in page..."

status=$(http_status "$OAUTH2_PROXY_URL/oauth2/sign_in")
if print_test_result "OAuth2-Proxy sign-in page" "200" "$status"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 9: Check OAuth2-Proxy headers (simulated)
echo -e "\n${BLUE}Test 9: OAuth2-Proxy Header Simulation${NC}"
print_info "Testing OAuth2-Proxy header forwarding simulation..."

# Simulate OAuth2-Proxy headers for direct API testing
AUTH_HEADERS="-H X-Auth-Request-User:$TEST_USER -H X-Auth-Request-Email:$TEST_USER@example.com -H X-Forwarded-Groups:factfiber-ai:docs-team"

# Test that the API accepts OAuth2-Proxy headers
response=$(http_response "$API_URL/auth/status" "$AUTH_HEADERS")
if [[ "$response" == *"authenticated"* ]]; then
    if print_test_result "OAuth2-Proxy headers accepted" "true" "true"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
else
    if print_test_result "OAuth2-Proxy headers accepted" "true" "false"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
fi

# Test 10: Repository access validation (requires actual GitHub token)
echo -e "\n${BLUE}Test 10: Repository Access Validation${NC}"
print_info "Testing repository access validation..."

if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    # Test with actual GitHub token
    AUTH_HEADER_WITH_TOKEN="$AUTH_HEADERS -H X-Auth-Request-Access-Token:$GITHUB_TOKEN"

    status=$(http_status "$API_URL/repos/discover" "$AUTH_HEADER_WITH_TOKEN")
    if print_test_result "Repository discovery with token" "200" "$status"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
else
    print_warning "GITHUB_TOKEN not set - skipping repository access validation test"
    print_info "Set GITHUB_TOKEN environment variable to test repository access"
fi

# Test Summary
echo -e "\n${BLUE}Test Summary${NC}"
echo "=============================================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
echo -e "Total Tests: $TOTAL_TESTS"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All tests passed!${NC}"
    echo "OAuth2-Proxy repository-scoped authentication is working correctly."
else
    echo -e "\n${RED}❌ Some tests failed.${NC}"
    echo "Please check the OAuth2-Proxy and FF-Docs API configuration."
fi

# Additional Information
echo -e "\n${BLUE}Additional Information${NC}"
echo "=============================================================="
print_info "OAuth2-Proxy endpoints:"
echo "  - Sign in: $OAUTH2_PROXY_URL/oauth2/sign_in"
echo "  - Sign out: $OAUTH2_PROXY_URL/oauth2/sign_out"
echo "  - Auth callback: $OAUTH2_PROXY_URL/oauth2/callback"
echo

print_info "FF-Docs API endpoints:"
echo "  - Health: $API_URL/health/"
echo "  - Auth status: $API_URL/auth/status"
echo "  - Repository list: $API_URL/repos/"
echo "  - Repository discovery: $API_URL/repos/discover"
echo

print_info "Repository-scoped endpoints:"
echo "  - Repository docs: $OAUTH2_PROXY_URL/docs/repo/{repo-name}"
echo "  - Repository API: $OAUTH2_PROXY_URL/api/repos/{repo-name}"
echo

if [[ $TESTS_FAILED -gt 0 ]]; then
    echo -e "\n${YELLOW}Troubleshooting Tips:${NC}"
    echo "=============================================================="
    print_info "If tests are failing, check:"
    echo "1. OAuth2-Proxy and FF-Docs API services are running"
    echo "2. Environment variables are properly configured"
    echo "3. GitHub OAuth App is configured with correct callback URL"
    echo "4. GitHub Personal Access Token has required scopes"
    echo "5. Network connectivity between services"
    echo
    print_info "View service logs:"
    echo "  docker-compose -f docker-compose.oauth2-proxy.yml logs"
    echo
    print_info "Test manual authentication:"
    echo "  Open browser to: $OAUTH2_PROXY_URL/oauth2/sign_in"
fi

# Exit with appropriate code
if [[ $TESTS_FAILED -eq 0 ]]; then
    exit 0
else
    exit 1
fi
