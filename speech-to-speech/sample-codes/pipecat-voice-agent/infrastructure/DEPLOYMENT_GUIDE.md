# Pipecat ECS Deployment Guide

This guide walks you through deploying the Pipecat voice AI agent infrastructure to AWS ECS.

## Prerequisites Checklist

Before deploying, ensure you have:

- [x] AWS CLI configured with appropriate credentials
- [x] Node.js and npm installed
- [x] AWS CDK installed globally: `npm install -g aws-cdk`
- [x] Docker installed (for building container images)
- [x] Daily.co API key available
- [x] AWS account with sufficient permissions for ECS, ECR, ALB, VPC, IAM, and Secrets Manager

## Step-by-Step Deployment

### 1. Prepare the Infrastructure

```bash
# Navigate to infrastructure directory
cd pipecat-ecs-deployment/infrastructure

# Install dependencies
npm install

# Build the project
npm run build

# Run tests to verify everything is working
npm test
```

### 2. Bootstrap CDK (if not done before)

```bash
# Bootstrap CDK in your target region
cdk bootstrap --region eu-north-1
```

### 3. Deploy the Infrastructure

```bash
# Deploy with default settings (test environment, default VPC)
./deploy.sh

# Or deploy with custom options
./deploy.sh --environment prod --custom-vpc --region us-west-2
```

### 4. Set Up AWS Secrets Manager

Before deploying the infrastructure, set up the required secrets:

```bash
# Navigate back to the main directory
cd ..

# Set up secrets using the automated script
python3 setup-secrets.py

# Verify secrets were created successfully
python3 test-secrets-integration.py
```

This will create two secrets:

- `pipecat/daily-api-key`: Contains Daily.co API credentials
- `pipecat/aws-credentials`: Contains AWS credentials for Bedrock access

**Note**: Ensure your `.env` file contains the required credentials before running the setup script.

### 5. Verify Deployment

Check that all resources were created successfully:

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name PipecatEcsStack-test

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name PipecatEcsStack-test \
  --query 'Stacks[0].Outputs'
```

## What Gets Created

The infrastructure deployment creates:

### Core Infrastructure

- **ECS Cluster**: `pipecat-cluster-{environment}`
- **ECR Repository**: `pipecat-voice-agent-{environment}`
- **Application Load Balancer**: `pipecat-alb-{environment}`
- **Target Group**: For routing traffic to ECS tasks

### Networking

- **VPC**: Uses default VPC or creates new one
- **Security Groups**:
  - ALB security group (allows HTTP/HTTPS from internet)
  - ECS security group (allows traffic from ALB on port 7860)

### IAM Roles

- **Task Role**: For Pipecat application with Bedrock and Secrets Manager permissions
- **Execution Role**: For ECS task execution with ECR and CloudWatch permissions

### Monitoring

- **CloudWatch Log Group**: `/ecs/pipecat-voice-agent-{environment}`

## Important Outputs

After deployment, note these key outputs:

- **LoadBalancerDnsName**: URL to access your application
- **RepositoryUri**: ECR repository for pushing container images
- **ClusterName**: ECS cluster name for service deployment
- **TaskRoleArn**: IAM role ARN for ECS tasks
- **ExecutionRoleArn**: IAM role ARN for ECS execution

## Next Steps

After infrastructure deployment:

1. **Build and push container image** to the ECR repository
2. **Create ECS service and task definition** (next task in the implementation plan)
3. **Test the deployment** by accessing the Load Balancer DNS name
4. **Set up monitoring and alerting** as needed

## Troubleshooting

### Common Issues

1. **CDK Bootstrap Required**

   ```bash
   cdk bootstrap --region your-region
   ```

2. **Insufficient Permissions**
   Ensure your AWS credentials have permissions for all required services.

3. **Default VPC Not Found**
   Use `--custom-vpc` flag to create a new VPC.

4. **Region Not Supported**
   Ensure Amazon Bedrock Nova Sonic is available in your target region.

### Useful Commands

```bash
# View detailed stack information
aws cloudformation describe-stack-resources --stack-name PipecatEcsStack-test

# Check ECR repository
aws ecr describe-repositories --repository-names pipecat-voice-agent-test

# View CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix "/ecs/pipecat"

# Clean up (destroy stack)
cdk destroy PipecatEcsStack-test
```

## Cost Considerations

### Test Environment

- Uses default VPC (no NAT Gateway costs)
- Minimal resource allocation
- Short log retention (1 week)

### Production Environment

- Consider custom VPC with NAT Gateways
- Adjust resource limits based on usage
- Longer log retention periods
- Enable detailed monitoring

## Security Notes

- All secrets are stored in AWS Secrets Manager with encryption at rest
- IAM roles follow principle of least privilege
- Security groups restrict network access appropriately
- Container runs as non-root user (when Dockerfile is updated)
- Secrets are injected as environment variables by ECS (not stored in container images)
- All secret access is logged in CloudTrail for audit purposes

For detailed information about secrets management, see [SECRETS_SETUP.md](../SECRETS_SETUP.md).

This infrastructure provides a solid foundation for deploying the Pipecat voice AI agent to AWS ECS with proper security, monitoring, and scalability considerations.
