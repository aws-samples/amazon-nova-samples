#!/bin/bash

# Docker Test Setup Script for Pipecat Phone Service
# This script helps test the Docker container locally before cloud deployment

set -e

echo "🐳 Setting up Docker test environment for Pipecat Phone Service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    echo "Please create a .env file with your credentials first."
    exit 1
fi

# Create a test-specific environment file (sanitized for Docker)
print_status "Creating Docker test environment file..."

# Create .env.docker from .env but with Docker-friendly settings
cp .env .env.docker

# Override host settings for Docker
echo "" >> .env.docker
echo "# Docker-specific overrides" >> .env.docker
echo "HOST=0.0.0.0" >> .env.docker
echo "FAST_API_PORT=7860" >> .env.docker

print_success "Created .env.docker file"

# Build the Docker image
print_status "Building Docker image..."
docker build -f ../Dockerfile.phone -t pipecat-phone-service:test ..

if [ $? -eq 0 ]; then
    print_success "Docker image built successfully"
else
    print_error "Failed to build Docker image"
    exit 1
fi

# Check if container is already running
if [ "$(docker ps -q -f name=pipecat-phone-test)" ]; then
    print_warning "Stopping existing container..."
    docker stop pipecat-phone-test
    docker rm pipecat-phone-test
fi

print_status "Starting Docker container..."

# Run the container with environment variables
docker run -d \
    --name pipecat-phone-test \
    --env-file .env.docker \
    -p 7860:7860 \
    --health-cmd="curl -f http://localhost:7860/health || exit 1" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-start-period=90s \
    --health-retries=3 \
    pipecat-phone-service:test

if [ $? -eq 0 ]; then
    print_success "Container started successfully"
    echo "Container name: pipecat-phone-test"
    echo "Port mapping: 7860:7860"
    echo "Health check: enabled"
else
    print_error "Failed to start container"
    exit 1
fi

# Wait for container to be ready
print_status "Waiting for container to be ready..."
sleep 10

# Check container status
print_status "Checking container status..."
docker ps -f name=pipecat-phone-test

# Check container logs
print_status "Recent container logs:"
docker logs --tail 20 pipecat-phone-test

# Test health endpoint
print_status "Testing health endpoint..."
sleep 5

if curl -f http://localhost:7860/health > /dev/null 2>&1; then
    print_success "Health check passed!"
    echo ""
    echo "🎉 Container is running successfully!"
    echo ""
    echo "Available endpoints:"
    echo "  - Health check: http://localhost:7860/health"
    echo "  - Incoming calls: http://localhost:7860/incoming-call"
    echo "  - Active calls: http://localhost:7860/active-calls"
    echo "  - WebRTC: http://localhost:7860/"
    echo ""
    echo "To test with Twilio using serveo:"
    echo "  1. Run: ssh -R 80:localhost:7860 serveo.net"
    echo "  2. Copy the serveo URL from the output"
    echo "  3. Set Twilio webhook to: https://your-serveo-url/incoming-call"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker logs -f pipecat-phone-test"
    echo "  - Stop container: docker stop pipecat-phone-test"
    echo "  - Remove container: docker rm pipecat-phone-test"
    echo "  - Shell into container: docker exec -it pipecat-phone-test /bin/bash"
else
    print_error "Health check failed!"
    echo ""
    echo "Container logs:"
    docker logs pipecat-phone-test
    echo ""
    echo "Container status:"
    docker ps -a -f name=pipecat-phone-test
fi

echo ""
print_status "Test setup complete!"

# Optional: Start serveo tunnel
echo ""
read -p "Do you want to start a serveo tunnel now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Starting serveo tunnel..."
    echo "This will create a public tunnel to your local service."
    echo "Copy the URL that appears and use it for your Twilio webhook."
    echo "Press Ctrl+C to stop the tunnel when done testing."
    echo ""
    ssh -R 80:localhost:7860 serveo.net
fi