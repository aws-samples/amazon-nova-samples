# Pipecat Voice AI Agent - AWS Cloud Deployment

A production-ready containerized deployment of the Pipecat Voice AI Agent on AWS, featuring both WebRTC and Twilio phone integration with AWS Nova Sonic for natural voice conversations. Supports both ECS and EKS deployment options.

## Overview

This sample demonstrates how to deploy a voice AI agent using:
- **AWS Nova Sonic** for speech-to-text and text-to-speech
- **Pipecat framework** for voice AI conversations
- **Twilio** for phone call integration
- **Daily.co** for WebRTC browser-based voice chat
- **AWS ECS/EKS** for scalable container deployment
- **AWS CDK** for infrastructure as code

## Architecture

The solution provides two deployment options:
- **ECS**: Managed container orchestration with Fargate
- **EKS**: Kubernetes-native deployment with Fargate

Both support:
- Phone calls via Twilio WebSocket integration
- Browser voice chat via WebRTC
- AWS Nova Sonic for natural voice processing
- Production-ready monitoring and scaling

## Prerequisites

- AWS CLI configured with appropriate permissions
- Node.js 18+ and npm
- Docker
- Python 3.10+
- AWS CDK CLI (`npm install -g aws-cdk`)

## Quick Start

1. **Clone and setup**:
```bash
git clone <repository-url>
cd speech-to-speech/sample-codes/pipecat-voice-agent
./setup-project.sh
```

2. **Configure secrets**:
```bash
cp .env.example .env
# Edit .env with your API keys
python3 scripts/setup-secrets.py
```

3. **Deploy infrastructure** (choose ECS or EKS):

**ECS Deployment:**
```bash
cd infrastructure
./deploy.sh --environment test --region us-east-1
```

**EKS Deployment:**
```bash
cd infrastructure/-eks
cdk deploy PipecatEksStack --parameters environment=test
```

4. **Build and deploy application**:
```bash
./scripts/build-and-push.sh -e test -t latest
./scripts/deploy-service.sh -e test -t latest
```

## Key Features

### Voice AI Capabilities
- **Natural Conversations**: AWS Nova Sonic provides human-like speech synthesis
- **Real-time Processing**: Low-latency speech-to-text and text-to-speech
- **Multi-channel Support**: Both phone calls and web browser voice chat
- **Function Calling**: Example weather function with extensible architecture

### Production Infrastructure
- **Auto-scaling**: ECS/EKS services scale based on demand
- **High Availability**: Multi-AZ deployment with load balancing
- **Security**: AWS Secrets Manager, IAM roles, VPC isolation
- **Monitoring**: CloudWatch logs, metrics, and health checks
- **SSL/TLS**: Automatic certificate management for Twilio webhooks

### Twilio Integration
- **Phone Number Support**: Inbound calls to your Twilio number
- **WebSocket Streaming**: Real-time bidirectional audio
- **SSL Certificate Requirements**: Production-ready HTTPS endpoints
- **Call Management**: Active call monitoring and session handling

## Environment Variables

Required configuration (stored in AWS Secrets Manager):

```bash
# Daily.co WebRTC
DAILY_API_KEY=your_daily_api_key

# AWS Configuration  
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Twilio Phone Integration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

## Testing Your Deployment

### WebRTC Voice Chat
1. Visit your load balancer URL
2. Click "Connect" to join a voice room
3. Speak to interact with the AI agent

### Phone Integration
1. Configure Twilio webhook to point to your deployment
2. Call your Twilio phone number
3. Have a voice conversation with the AI

## Important: Twilio SSL Requirements

For production Twilio integration:
- **Valid SSL Certificate**: Must be from a trusted CA (Let's Encrypt, etc.)
- **No Self-Signed Certificates**: Twilio rejects untrusted certificates
- **HTTPS Required**: Use standard port 443
- **Load Balancer SSL**: AWS automatically handles certificate management

## Documentation

- [EKS Architecture Overview](docs/EKS_ARCHITECTURE.md)
- [Deployment Guide](infrastructure/DEPLOYMENT_GUIDE.md)
- [Cleanup Guide](docs/CLEANUP_GUIDE.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING_GUIDE.md)

## Cost Considerations

- **Fargate**: Pay only for running containers
- **Nova Sonic**: Usage-based pricing for speech processing
- **Load Balancers**: Fixed hourly cost plus data transfer
- **Twilio**: Per-minute charges for phone calls

## Security Best Practices

- Secrets stored in AWS Secrets Manager
- IAM roles with least-privilege access
- VPC isolation with security groups
- Container runs as non-root user
- TLS encryption for all external communication

## Contributing

This sample follows AWS best practices for:
- Infrastructure as Code (CDK)
- Container security
- Monitoring and observability
- Cost optimization
- Multi-AZ high availability

## License

This sample code is made available under the MIT-0 license. See the LICENSE file.