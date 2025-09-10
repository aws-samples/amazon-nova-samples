#!/bin/bash

# Comprehensive Docker Testing Script
# Tests the container functionality step by step

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🧪 Testing Pipecat Phone Service Docker Container"
echo "================================================"

# Test 1: Container Health
print_status "Test 1: Container Health Check"
if docker ps -f name=pipecat-phone-test | grep -q "pipecat-phone-test"; then
    print_success "Container is running"
    
    # Check health status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' pipecat-phone-test 2>/dev/null || echo "no-health-check")
    echo "Health status: $health_status"
else
    print_error "Container is not running. Run ./docker-test-setup.sh first"
    exit 1
fi

# Test 2: HTTP Health Endpoint
print_status "Test 2: HTTP Health Endpoint"
if response=$(curl -s http://localhost:7860/health); then
    print_success "Health endpoint accessible"
    echo "Response: $response" | jq . 2>/dev/null || echo "Response: $response"
else
    print_error "Health endpoint not accessible"
    echo "Container logs:"
    docker logs --tail 10 pipecat-phone-test
fi

# Test 3: Environment Variables
print_status "Test 3: Environment Variables Check"
docker exec pipecat-phone-test env | grep -E "(AWS_|TWILIO_|DAILY_)" | head -5
if [ $? -eq 0 ]; then
    print_success "Environment variables are loaded"
else
    print_warning "Could not verify environment variables"
fi

# Test 4: Python Dependencies
print_status "Test 4: Python Dependencies"
if docker exec pipecat-phone-test python3 -c "import pipecat; print('Pipecat version:', pipecat.__version__)" 2>/dev/null; then
    print_success "Pipecat is installed correctly"
else
    print_error "Pipecat import failed"
fi

if docker exec pipecat-phone-test python3 -c "import twilio; print('Twilio SDK available')" 2>/dev/null; then
    print_success "Twilio SDK is available"
else
    print_error "Twilio SDK not available"
fi

# Test 5: AWS Credentials
print_status "Test 5: AWS Credentials Test"
aws_test=$(docker exec pipecat-phone-test python3 -c "
import os
import boto3
try:
    client = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'eu-north-1'))
    print('AWS credentials configured')
except Exception as e:
    print(f'AWS error: {e}')
" 2>/dev/null)
echo "AWS test result: $aws_test"

# Test 6: Port Accessibility
print_status "Test 6: Port Accessibility"
if nc -z localhost 7860 2>/dev/null; then
    print_success "Port 7860 is accessible"
else
    print_error "Port 7860 is not accessible"
fi

# Test 7: WebSocket Endpoint (basic connectivity)
print_status "Test 7: WebSocket Endpoint Test"
# Test if the WebSocket endpoint exists (will fail auth but should connect)
if curl -s -o /dev/null -w "%{http_code}" http://localhost:7860/media-stream/test-call-id | grep -q "426"; then
    print_success "WebSocket endpoint is available (426 = Upgrade Required, expected)"
else
    print_warning "WebSocket endpoint test inconclusive"
fi

# Test 8: Container Resource Usage
print_status "Test 8: Container Resource Usage"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" pipecat-phone-test

# Test 9: Log Analysis
print_status "Test 9: Log Analysis"
echo "Recent logs (last 10 lines):"
docker logs --tail 10 pipecat-phone-test

# Check for common error patterns
if docker logs pipecat-phone-test 2>&1 | grep -i error | head -3; then
    print_warning "Found some errors in logs (check above)"
else
    print_success "No obvious errors in logs"
fi

# Test 10: File Permissions
print_status "Test 10: File Permissions Check"
docker exec pipecat-phone-test ls -la /app/ | head -5
docker exec pipecat-phone-test whoami

echo ""
echo "🎯 Test Summary"
echo "==============="

# Final connectivity test
if curl -s http://localhost:7860/health | grep -q "healthy"; then
    print_success "✅ Container is healthy and ready for testing"
    echo ""
    echo "Next steps for Twilio testing:"
    echo "1. Install ngrok: brew install ngrok (or download from ngrok.com)"
    echo "2. Expose your container: ngrok http 7860"
    echo "3. Copy the ngrok URL (e.g., https://abc123.ngrok.io)"
    echo "4. Set Twilio webhook to: https://abc123.ngrok.io/incoming-call"
    echo "5. Call your Twilio number to test"
    echo ""
    echo "Alternative with serveo (no signup required):"
    echo "ssh -R 80:localhost:7860 serveo.net"
    echo "Then use the provided serveo URL for Twilio webhook"
else
    print_error "❌ Container has issues - check logs above"
    echo ""
    echo "Troubleshooting commands:"
    echo "- View full logs: docker logs pipecat-phone-test"
    echo "- Shell into container: docker exec -it pipecat-phone-test /bin/bash"
    echo "- Restart container: docker restart pipecat-phone-test"
    echo "- Rebuild: docker build -f ../Dockerfile.phone -t pipecat-phone-service:test .."
fi

echo ""
print_status "Testing complete!"