# Pipecat ECS Deployment Process

This document provides a comprehensive guide for deploying the Pipecat Voice AI Agent to AWS ECS, including both WebRTC and Twilio phone integration capabilities.

## Overview

The deployment process consists of several phases:

1. **Prerequisites Setup** - AWS account, credentials, and service configuration
2. **Infrastructure Deployment** - AWS resources using CDK
3. **Application Deployment** - Container build and ECS service deployment
4. **Configuration** - Secrets management and environment setup
5. **Testing & Validation** - End-to-end functionality verification

## Prerequisites

### AWS Account Setup

1. **AWS Account Requirements**:

   - Active AWS account with billing enabled
   - Sufficient service limits for ECS Fargate tasks
   - Access to required AWS regions (eu-north-1 recommended)

2. **Required AWS Services**:

   - Amazon ECS (Elastic Container Service)
   - Amazon ECR (Elastic Container Registry)
   - Application Load Balancer (ALB)
   - AWS Secrets Manager
   - Amazon CloudWatch
   - Amazon Bedrock (with Nova Sonic model access)
   - AWS VPC and related networking services

3. **AWS CLI Configuration**:

   ```bash
   # Install AWS CLI v2
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # Configure credentials
   aws configure
   # Enter: Access Key ID, Secret Access Key, Region (eu-north-1), Output format (json)

   # Verify configuration
   aws sts get-caller-identity
   ```

### Development Environment Setup

1. **Required Tools**:

   ```bash
   # Node.js and npm (for CDK)
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs

   # AWS CDK
   npm install -g aws-cdk

   # Docker
   sudo apt-get update
   sudo apt-get install docker.io
   sudo usermod -aG docker $USER

   # Python 3.10+ (for application)
   sudo apt-get install python3.10 python3-pip
   ```

2. **Service Account Setup**:
   - **Daily.co**: Create account and obtain API key
   - **Twilio** (for phone integration): Create account, purchase phone number, obtain API credentials

### AWS Service Configuration

1. **Amazon Bedrock Setup**:

   ```bash
   # Enable Bedrock service in your region
   aws bedrock list-foundation-models --region eu-north-1

   # Request access to Nova Sonic model through AWS Console
   # Navigate to: Bedrock Console > Model Access > Request Access
   ```

2. **IAM Permissions**:
   Required permissions for deployment user/role:
   - ECS: Full access for cluster and service management
   - ECR: Full access for container registry
   - ALB: Full access for load balancer management
   - VPC: Full access for networking
   - IAM: Role creation and policy attachment
   - CloudFormation: Stack management
   - Secrets Manager: Secret creation and access
   - CloudWatch: Log group and metrics management
   - Bedrock: Model invocation permissions

## Infrastructure Deployment

### Phase 1: CDK Infrastructure

1. **Navigate to Infrastructure Directory**:

   ```bash
   cd infrastructure
   ```

2. **Install Dependencies**:

   ```bash
   npm install
   npm run build
   npm test  # Verify everything works
   ```

3. **Bootstrap CDK** (first time only):

   ```bash
   cdk bootstrap --region eu-north-1
   ```

4. **Deploy Infrastructure**:

   ```bash
   # Basic deployment (test environment, default VPC)
   ./deploy.sh

   # Production deployment with custom VPC
   ./deploy.sh --environment prod --custom-vpc --region eu-north-1
   ```

5. **Verify Infrastructure**:

   ```bash
   # Check stack status
   aws cloudformation describe-stacks --stack-name PipecatEcsStack-test

   # Get important outputs
   aws cloudformation describe-stacks \
     --stack-name PipecatEcsStack-test \
     --query 'Stacks[0].Outputs'
   ```

### Phase 2: Secrets Configuration

1. **Set Up Environment Variables**:

   ```bash
   # Create .env file in project root
   cat > .env << EOF
   DAILY_API_KEY=your_daily_api_key_here
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_REGION=eu-north-1

   # Twilio credentials (for phone integration)
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_API_SID=your_twilio_api_sid
   TWILIO_API_SECRET=your_twilio_api_secret
   EOF
   ```

2. **Deploy Secrets to AWS**:

   ```bash
   # Navigate back to project root
   cd ..

   # Run secrets setup script
   python3 scripts/setup-secrets.py

   # Verify secrets were created
   python3 tests/test-secrets-integration.py
   ```

## Application Deployment

### Phase 3: Container Build and Deployment

1. **Build and Push Container**:

   ```bash
   # Make scripts executable
   chmod +x scripts/build-and-push.sh
   chmod +x scripts/deploy-service.sh

   # Build and push to ECR
   ./scripts/build-and-push.sh -e test -t latest

   # Deploy to ECS
   ./scripts/deploy-service.sh -e test -t latest --update
   ```

2. **Alternative: Full Automated Deployment**:
   ```bash
   # Complete deployment in one command
   ./scripts/deployment/full-deploy.sh -e test
   ```

### Phase 4: Service Configuration

1. **ECS Service Settings**:

   - **Task Definition**: 1 vCPU, 2GB memory
   - **Desired Count**: 2 tasks (for high availability)
   - **Health Check**: `/health` endpoint
   - **Auto Scaling**: CPU-based scaling (70% threshold)

2. **Load Balancer Configuration**:
   - **Scheme**: Internet-facing
   - **Listeners**: HTTP (80), optional HTTPS (443)
   - **Target Group**: ECS tasks on port 7860
   - **Health Check**: GET `/health` with 30s interval

## Configuration Management

### Environment Variables

**Required Environment Variables**:

- `DAILY_API_KEY`: Daily.co API key (from Secrets Manager)
- `AWS_REGION`: AWS region for Bedrock services
- `HOST`: Server host (0.0.0.0 for containers)
- `FAST_API_PORT`: Server port (7860)

**Optional Environment Variables**:

- `ENVIRONMENT`: deployment environment (test/prod)
- `LOG_LEVEL`: logging level (INFO/DEBUG/WARNING/ERROR)
- `MAX_BOTS_PER_ROOM`: maximum bots per room (default: 1)
- `MAX_CONCURRENT_ROOMS`: maximum concurrent rooms (default: 10)

**Twilio Environment Variables** (for phone integration):

- `TWILIO_ACCOUNT_SID`: Twilio account identifier
- `TWILIO_API_SID`: Twilio API key SID
- `TWILIO_API_SECRET`: Twilio API key secret

### Secrets Management

All sensitive configuration is stored in AWS Secrets Manager:

1. **Daily API Credentials**:

   ```json
   {
     "name": "pipecat/daily-api-key",
     "value": "your_daily_api_key"
   }
   ```

2. **AWS Credentials** (if not using IAM roles):

   ```json
   {
     "name": "pipecat/aws-credentials",
     "value": {
       "access_key_id": "your_access_key",
       "secret_access_key": "your_secret_key"
     }
   }
   ```

3. **Twilio Credentials**:
   ```json
   {
     "name": "pipecat/twilio-credentials",
     "value": {
       "account_sid": "ACxxxxx",
       "api_sid": "SKxxxxx",
       "api_secret": "xxxxx"
     }
   }
   ```

## Testing and Validation

### Phase 5: Deployment Verification

1. **Health Check Validation**:

   ```bash
   # Get ALB DNS name
   ALB_DNS=$(aws cloudformation describe-stacks \
     --stack-name PipecatEcsStack-test \
     --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDnsName`].OutputValue' \
     --output text)

   # Test health endpoint
   curl http://$ALB_DNS/health

   # Test readiness endpoint
   curl http://$ALB_DNS/ready
   ```

2. **End-to-End Testing**:

   ```bash
   # Run comprehensive test suite
   python3 tests/test-end-to-end.py

   # Test specific functionality
   python3 tests/test-complete-user-journey.py

   # Test Bedrock integration
   python3 tests/test-bedrock-access.py
   ```

3. **WebRTC Functionality**:

   - Navigate to `http://$ALB_DNS` in browser
   - Test voice conversation with Nova Sonic
   - Verify function calling (weather queries)
   - Test multiple concurrent sessions

4. **Twilio Phone Integration** (if configured):
   - Call the configured Twilio phone number
   - Test voice conversation through phone
   - Verify function calling works via voice commands
   - Test call quality and responsiveness

### Monitoring and Logging

1. **CloudWatch Logs**:

   ```bash
   # View application logs
   aws logs tail /ecs/pipecat-voice-agent-test/application --follow

   # View ECS service logs
   aws logs tail /ecs/pipecat-voice-agent-test --follow
   ```

2. **ECS Service Monitoring**:

   ```bash
   # Check service status
   aws ecs describe-services \
     --cluster pipecat-cluster-test \
     --services pipecat-service-test

   # Check task health
   aws ecs list-tasks --cluster pipecat-cluster-test
   ```

3. **Application Metrics**:
   - CPU and memory utilization
   - Request count and response times
   - Error rates and health check status
   - Custom metrics for voice sessions and function calls

## Troubleshooting

### Common Deployment Issues

1. **CDK Bootstrap Required**:

   ```bash
   cdk bootstrap --region your-region
   ```

2. **Insufficient IAM Permissions**:

   - Verify deployment user has all required permissions
   - Check CloudFormation stack events for specific errors

3. **Docker Build Failures**:

   ```bash
   # Test container locally first
   ./scripts/deployment/test-container.sh
   ```

4. **ECS Task Failures**:

   - Check CloudWatch logs for application errors
   - Verify secrets are properly configured
   - Ensure Bedrock model access is granted

5. **Load Balancer Health Check Failures**:
   - Verify `/health` endpoint is responding
   - Check security group configurations
   - Ensure tasks are running and healthy

### Performance Optimization

1. **Resource Allocation**:

   - Monitor CPU and memory usage
   - Adjust task definition resources as needed
   - Configure auto-scaling based on metrics

2. **Cost Optimization**:
   - Use Spot instances for non-production environments
   - Implement proper log retention policies
   - Monitor and optimize data transfer costs

## Security Considerations

1. **Network Security**:

   - Use private subnets for ECS tasks
   - Implement proper security group rules
   - Enable VPC Flow Logs for monitoring

2. **Application Security**:

   - Run containers as non-root user
   - Use minimal base images
   - Regularly update dependencies

3. **Secrets Management**:

   - Never store secrets in container images
   - Use AWS Secrets Manager for all sensitive data
   - Implement proper IAM roles and policies

4. **Monitoring and Auditing**:
   - Enable CloudTrail for API auditing
   - Monitor access to secrets and resources
   - Set up alerts for security events

## Next Steps

After successful deployment:

1. **Production Readiness**:

   - Implement HTTPS/TLS termination
   - Set up custom domain names
   - Configure backup and disaster recovery

2. **Scaling and Performance**:

   - Implement advanced auto-scaling policies
   - Set up performance monitoring and alerting
   - Optimize for high availability

3. **CI/CD Pipeline**:

   - Set up automated testing and deployment
   - Implement blue-green deployment strategies
   - Configure automated rollback procedures

4. **Advanced Features**:
   - Implement Twilio phone integration
   - Add advanced monitoring and analytics
   - Integrate with additional AI services

This deployment process provides a solid foundation for running the Pipecat Voice AI Agent in a production AWS environment with proper security, monitoring, and scalability considerations.
