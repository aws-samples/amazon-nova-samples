# Phone Service Deployment Guide

This guide covers deploying the Pipecat Phone Service with Twilio integration to AWS ECS.

## Overview

The phone service deployment creates a separate ECS service that handles Twilio phone calls using the Nova Sonic AI agent. Unlike local development where you might use serveo or ngrok for tunneling, the cloud deployment provides a public Application Load Balancer that Twilio can reach directly.

## Architecture

```
Twilio Phone Call → Twilio Webhook → Phone ALB → Phone ECS Service → Nova Sonic
```

### Key Components

1. **Separate ECS Service**: Dedicated service running `server_clean.py`
2. **Separate ALB**: Public load balancer for Twilio webhooks
3. **ECR Repository**: Dedicated repository for phone service images
4. **Security Groups**: Configured to allow Twilio webhook traffic

## Prerequisites

1. **Infrastructure Deployed**: Main infrastructure must be deployed first
2. **Twilio Account**: Active Twilio account with phone number
3. **Secrets Configured**: Twilio credentials in AWS Secrets Manager
4. **Docker**: For building container images

## Deployment Steps

### 1. Deploy Infrastructure (if not already done)

```bash
cd infrastructure
./deploy.sh -e test -r eu-north-1
cd ..
```

### 2. Build and Deploy Phone Service

```bash
# Full deployment (build + deploy)
./scripts/deployment/deploy-phone-service.sh

# Or step by step:
./scripts/build-phone-service.sh
./scripts/deployment/deploy-phone-service.sh --deploy-only
```

### 3. Configure Twilio Webhook

After deployment, you'll get a webhook URL like:

```
http://pipecat-phone-alb-123456789.eu-north-1.elb.amazonaws.com/incoming-call
```

**Manual Configuration Required:**

1. Log in to [Twilio Console](https://console.twilio.com/)
2. Go to **Phone Numbers > Manage > Active numbers**
3. Click on your Twilio phone number
4. In **Voice Configuration**:
   - Set **"A call comes in"** webhook to the provided URL
   - Set HTTP method to **POST**
5. Click **Save configuration**

## Key Differences from Local Development

### Local Development (with serveo/ngrok)

```bash
# Local server
python server_clean.py --host 0.0.0.0 --port 7860

# Tunnel (example with serveo)
ssh -R 80:localhost:7860 serveo.net

# Twilio webhook: https://yoursubdomain.serveo.net/incoming-call
```

### Cloud Deployment

```bash
# Container in ECS
# Public ALB provides direct access
# No tunneling needed

# Twilio webhook: http://phone-alb-dns-name/incoming-call
```

## Service Configuration

### Container Specifications

- **CPU**: 2 vCPU (2048 units)
- **Memory**: 4 GB (4096 MB)
- **Port**: 7860
- **Health Check**: `/health` endpoint

### Auto Scaling

- **Min Capacity**: 1 task
- **Max Capacity**: 4 tasks
- **CPU Target**: 75%
- **Memory Target**: 85%

### Security

- **ALB Security Group**: Allows HTTP (80) and HTTPS (443) from anywhere
- **ECS Security Group**: Allows traffic from ALB only
- **IAM Roles**: Bedrock, Secrets Manager, and Daily.co permissions

## Environment Variables

The phone service uses the same environment variables as the main service:

```bash
# AWS Configuration
AWS_REGION=eu-north-1
AWS_ACCESS_KEY_ID=<from-secrets-manager>
AWS_SECRET_ACCESS_KEY=<from-secrets-manager>

# Twilio Configuration
TWILIO_ACCOUNT_SID=<from-secrets-manager>
TWILIO_AUTH_TOKEN=<from-secrets-manager>
TWILIO_PHONE_NUMBER=<from-secrets-manager>
TWILIO_API_SID=<from-secrets-manager>
TWILIO_API_SECRET=<from-secrets-manager>

# Daily.co (for potential WebRTC fallback)
DAILY_API_KEY=<from-secrets-manager>
DAILY_API_URL=<from-secrets-manager>

# Service Configuration
HOST=0.0.0.0
FAST_API_PORT=7860
SERVICE_TYPE=phone
```

## Monitoring and Troubleshooting

### Health Check

```bash
# Check service health
curl http://phone-alb-dns-name/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "service": "fixed-nova-sonic-server",
  "webrtc_enabled": true,
  "twilio_enabled": true,
  "nova_sonic_enabled": true,
  "phone_number": "+1234567890"
}
```

### Logs

```bash
# View phone service logs
aws logs tail /ecs/pipecat-phone-service-test --follow --region eu-north-1

# View specific log streams
aws logs describe-log-streams \
  --log-group-name /ecs/pipecat-phone-service-test \
  --region eu-north-1
```

### Service Status

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster pipecat-cluster-test \
  --services pipecat-phone-service-test \
  --region eu-north-1

# Check running tasks
aws ecs list-tasks \
  --cluster pipecat-cluster-test \
  --service-name pipecat-phone-service-test \
  --region eu-north-1
```

### Active Calls

```bash
# Check active calls via API
curl http://phone-alb-dns-name/active-calls
```

## Testing

### 1. Health Check Test

```bash
curl http://phone-alb-dns-name/health
```

### 2. Phone Call Test

1. Call your Twilio phone number
2. You should hear the Nova Sonic AI agent
3. Try asking for weather information
4. Check logs for call processing

### 3. Load Testing

```bash
# Multiple concurrent calls can be tested
# Monitor CPU/Memory usage during testing
```

## Common Issues

### 1. Twilio Webhook Not Working

- **Check**: ALB DNS name is correct in Twilio configuration
- **Check**: Security groups allow HTTP traffic from anywhere
- **Check**: ECS tasks are healthy and running

### 2. Nova Sonic Connection Issues

- **Check**: AWS credentials in Secrets Manager
- **Check**: Bedrock permissions in IAM role
- **Check**: Nova Sonic model availability in region

### 3. Call Quality Issues

- **Check**: ECS task resources (CPU/Memory)
- **Check**: Network connectivity to Daily.co and AWS services
- **Check**: Audio processing logs

### 4. Deployment Failures

- **Check**: ECR repository exists and is accessible
- **Check**: ECS service has proper IAM roles
- **Check**: Task definition is valid

## Cost Considerations

### ECS Fargate Costs

- **2 vCPU, 4GB RAM**: ~$0.08/hour per task
- **2 tasks minimum**: ~$0.16/hour = ~$115/month
- **Auto-scaling**: Additional costs during peak usage

### ALB Costs

- **Load Balancer**: ~$16/month
- **LCU (Load Balancer Capacity Units)**: Based on usage

### Data Transfer

- **Twilio to ALB**: Minimal cost
- **ALB to ECS**: No cost (same AZ)
- **ECS to external APIs**: Standard data transfer rates

## Security Best Practices

1. **Use HTTPS**: Configure SSL certificate for production
2. **Webhook Validation**: Enable Twilio signature validation
3. **Network Security**: Use private subnets for ECS tasks
4. **Secrets Management**: Never hardcode credentials
5. **IAM Roles**: Use least privilege principle

## Production Considerations

1. **SSL/TLS**: Configure HTTPS listener on ALB
2. **Domain Name**: Use custom domain instead of ALB DNS
3. **Monitoring**: Set up CloudWatch alarms
4. **Backup**: Regular ECR image backups
5. **Scaling**: Adjust auto-scaling based on call volume

## Cleanup

To remove the phone service:

```bash
# Delete ECS service
aws ecs update-service \
  --cluster pipecat-cluster-test \
  --service pipecat-phone-service-test \
  --desired-count 0 \
  --region eu-north-1

aws ecs delete-service \
  --cluster pipecat-cluster-test \
  --service pipecat-phone-service-test \
  --region eu-north-1

# Remove from infrastructure (requires CDK redeployment)
# Or destroy entire stack:
cd infrastructure
cdk destroy PipecatEcsStack-test
```

## Support

For issues with:

- **Twilio Integration**: Check Twilio Console logs
- **AWS Infrastructure**: Check CloudFormation events
- **Nova Sonic**: Check Bedrock service status
- **Container Issues**: Check ECS task logs

Remember: The phone service runs independently from the main WebRTC service, so both can operate simultaneously.
