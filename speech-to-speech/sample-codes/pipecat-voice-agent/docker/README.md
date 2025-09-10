# Docker Configuration

This directory contains all Docker-related files for the Pipecat ECS deployment project.

## Files

### Dockerfiles

- `Dockerfile` - Main application container for the Pipecat voice AI agent
- `Dockerfile.phone` - Phone service container for Twilio integration using server_clean.py

### Docker Compose

- `docker-compose.test.yml` - Test configuration for local development and testing

### Scripts

- `scripts/build-phone-service.sh` - Build the phone service container
- `scripts/build-phone-quick.sh` - Quick build script for phone service
- `scripts/docker-test-setup.sh` - Setup script for Docker testing environment
- `scripts/test-docker-locally.sh` - Local Docker testing script

## Usage

### Building Images

From the project root directory:

```bash
# Build main application
docker build -f docker/Dockerfile -t pipecat-app .

# Build phone service
docker build -f docker/Dockerfile.phone -t pipecat-phone-service .
```

### Using Scripts

```bash
# Quick phone service build
./docker/scripts/build-phone-quick.sh

# Full phone service build and test
./docker/scripts/build-phone-service.sh

# Local testing setup
./docker/scripts/docker-test-setup.sh
```

### Docker Compose Testing

```bash
# Run test environment
docker-compose -f docker/docker-compose.test.yml up
```

## Notes

- All Docker builds should be run from the project root directory
- The phone service container uses `server_clean.py` for Twilio integration
- Health checks are configured for ECS compatibility
- Images use non-root users for security
