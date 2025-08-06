#!/bin/bash

# DNSSEC Validator - Portainer Deployment Script
# This script deploys the DNSSEC Validator to Portainer via API

set -e

# Configuration
PORTAINER_URL="https://portainer.bonde.ninja"
STACK_NAME="dnssec-validator"
COMPOSE_FILE="docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_warning "jq is not installed. JSON parsing will be limited."
    fi
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Compose file $COMPOSE_FILE not found"
        exit 1
    fi
}

# Get Portainer authentication token
get_auth_token() {
    print_status "Authenticating with Portainer..."
    
    read -p "Portainer Username: " username
    read -s -p "Portainer Password: " password
    echo
    
    AUTH_RESPONSE=$(curl -s -X POST "$PORTAINER_URL/api/auth" \
        -H "Content-Type: application/json" \
        -d "{\"Username\":\"$username\",\"Password\":\"$password\"}")
    
    if command -v jq &> /dev/null; then
        JWT_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.jwt')
        if [ "$JWT_TOKEN" = "null" ]; then
            print_error "Authentication failed"
            exit 1
        fi
    else
        JWT_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"jwt":"[^"]*"' | cut -d'"' -f4)
        if [ -z "$JWT_TOKEN" ]; then
            print_error "Authentication failed"
            exit 1
        fi
    fi
    
    print_status "Authentication successful"
}

# Get endpoint ID (usually 1 for local Docker)
get_endpoint_id() {
    print_status "Getting endpoint information..."
    
    ENDPOINTS_RESPONSE=$(curl -s -X GET "$PORTAINER_URL/api/endpoints" \
        -H "Authorization: Bearer $JWT_TOKEN")
    
    if command -v jq &> /dev/null; then
        ENDPOINT_ID=$(echo "$ENDPOINTS_RESPONSE" | jq -r '.[0].Id')
    else
        ENDPOINT_ID=1  # Default to 1
    fi
    
    print_status "Using endpoint ID: $ENDPOINT_ID"
}

# Check if stack already exists
check_existing_stack() {
    print_status "Checking for existing stack..."
    
    STACKS_RESPONSE=$(curl -s -X GET "$PORTAINER_URL/api/stacks" \
        -H "Authorization: Bearer $JWT_TOKEN")
    
    if command -v jq &> /dev/null; then
        EXISTING_STACK=$(echo "$STACKS_RESPONSE" | jq -r ".[] | select(.Name == \"$STACK_NAME\") | .Id")
        if [ "$EXISTING_STACK" != "" ] && [ "$EXISTING_STACK" != "null" ]; then
            print_warning "Stack '$STACK_NAME' already exists with ID: $EXISTING_STACK"
            read -p "Do you want to update it? (y/N): " update_stack
            if [ "$update_stack" = "y" ] || [ "$update_stack" = "Y" ]; then
                UPDATE_EXISTING=true
                STACK_ID=$EXISTING_STACK
            else
                print_error "Deployment cancelled"
                exit 1
            fi
        fi
    fi
}

# Deploy new stack
deploy_stack() {
    print_status "Deploying stack to Portainer..."
    
    # Encode the compose file in base64
    COMPOSE_CONTENT=$(base64 -w 0 < "$COMPOSE_FILE")
    
    # Prepare the payload
    PAYLOAD=$(cat <<EOF
{
    "Name": "$STACK_NAME",
    "ComposeFile": "$COMPOSE_CONTENT",
    "Env": [
        {"name": "FLASK_ENV", "value": "production"},
        {"name": "CORS_ORIGINS", "value": "https://dnssec-validator.bondit.dk"}
    ]
}
EOF
    )
    
    if [ "$UPDATE_EXISTING" = "true" ]; then
        print_status "Updating existing stack..."
        DEPLOY_RESPONSE=$(curl -s -X PUT "$PORTAINER_URL/api/stacks/$STACK_ID?endpointId=$ENDPOINT_ID" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            -d "$PAYLOAD")
    else
        print_status "Creating new stack..."
        DEPLOY_RESPONSE=$(curl -s -X POST "$PORTAINER_URL/api/stacks?type=2&method=string&endpointId=$ENDPOINT_ID" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            -d "$PAYLOAD")
    fi
    
    # Check response
    if echo "$DEPLOY_RESPONSE" | grep -q "error\|Error"; then
        print_error "Deployment failed:"
        echo "$DEPLOY_RESPONSE"
        exit 1
    fi
    
    print_status "Stack deployed successfully!"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Wait a moment for container to start
    sleep 5
    
    # Check if the service responds
    if curl -s -f "http://localhost:8080/" > /dev/null; then
        print_status "Local service is responding"
    else
        print_warning "Local service check failed (this might be normal if running on remote server)"
    fi
    
    print_status "Deployment verification completed"
}

# Main execution
main() {
    echo "======================================"
    echo "DNSSEC Validator - Portainer Deployment"
    echo "======================================"
    echo
    
    check_prerequisites
    get_auth_token
    get_endpoint_id
    check_existing_stack
    deploy_stack
    verify_deployment
    
    echo
    print_status "Deployment completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Configure Nginx Proxy Manager to proxy dnssec-validator.bondit.dk to the container"
    echo "2. Set up SSL certificate in Nginx Proxy Manager"
    echo "3. Test the deployment at: https://dnssec-validator.bondit.dk"
    echo
    echo "For detailed configuration, see DEPLOYMENT.md"
}

# Run main function
main "$@"
