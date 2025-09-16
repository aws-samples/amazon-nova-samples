#!/bin/bash

# Build script for Pipecat Phone Service container

set -e

echo "🔨 Building Pipecat Phone Service container..."

# Build the container image
docker build -f ../Dockerfile.phone -t pipecat-phone-service:latest ..

echo "✅ Container built successfully!"

# Test the container locally (optional)
if [ "$1" = "--test" ]; then
    echo "🧪 Testing container locally..."
    
    # Check if .env file exists
    if [ -f ".env" ]; then
        echo "📋 Using .env file for environment variables"
        docker run --rm -p 7860:7860 --env-file .env pipecat-phone-service:latest &
    else
        echo "⚠️  No .env file found. Running with minimal environment..."
        docker run --rm -p 7860:7860 \
            -e HOST=0.0.0.0 \
            -e FAST_API_PORT=7860 \
            pipecat-phone-service:latest &
    fi
    
    CONTAINER_PID=$!
    
    # Wait a bit for container to start
    sleep 10
    
    # Test health endpoint
    echo "🏥 Testing health endpoint..."
    if curl -f http://localhost:7860/health; then
        echo "✅ Health check passed!"
    else
        echo "❌ Health check failed!"
    fi
    
    # Stop the container
    kill $CONTAINER_PID 2>/dev/null || true
    
    echo "🧪 Container test completed!"
fi

echo "🚀 Phone service container is ready for deployment!"
echo ""
echo "To run locally:"
echo "  docker run --rm -p 7860:7860 --env-file .env pipecat-phone-service:latest"
echo ""
echo "To test health endpoint:"
echo "  curl http://localhost:7860/health"