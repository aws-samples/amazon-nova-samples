#!/bin/bash

# Change to the backend directory
cd "$(dirname "$0")"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "Loaded environment variables from .env"
else
    echo "Warning: .env file not found"
fi

# # Run the server with OpenTelemetry instrumentation and collector config
# opentelemetry-instrument --config otel-collector-config.yaml python banking_agent.py
# Run the server with OpenTelemetry instrumentation and collector-less
opentelemetry-instrument python banking_agent.py