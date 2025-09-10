# Pipecat ECS Infrastructure

This CDK project creates the AWS infrastructure needed to deploy the Pipecat voice AI agent to Amazon ECS.

## Architecture

The infrastructure includes:

- **VPC**: Uses default VPC or creates a new one with public/private subnets
- **ECS Cluster**: Fargate-enabled cluster for running containers
- **ECR Repository**: For storing container images
- **Application Load Balancer**: Internet-facing ALB for routing traffic
- **Security Groups**: Proper network security configuration
- **IAM Roles**: Task and execution roles with minimal required permissions
- **CloudWatch**: Log groups for monitoring

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Node.js and npm** installed
3. **AWS CDK** installed globally: `npm install -g aws-cdk`
4. **Docker** installed (for building container images)

## Quick Start

1. **Install dependencies**:

   ```bash
   npm install
   ```

2. **Build the project**:

   ```bash
   npm run build
   ```

3. **Deploy the infrastructure**:

   ```bash
   ./deploy.sh
   ```

   Or with custom options:

   ```bash
   ./deploy.sh --environment prod --custom-vpc --region us-west-2
   ```

4. **Create the Daily API key secret**:
   ```bash
   aws secretsmanager create-secret \
     --name 'pipecat/daily-api-key' \
     --secret-string 'YOUR_DAILY_API_KEY' \
     --region eu-north-1
   ```

## Available Scripts

- `npm run build` - Compile TypeScript to JavaScript
- `npm run deploy` - Deploy using default settings
- `npm run deploy:test` - Deploy test environment
- `npm run deploy:prod` - Deploy production environment with custom VPC
- `npm run synth` - Synthesize CloudFormation template
- `npm run diff` - Show differences between deployed and current state
- `npm run destroy` - Destroy the stack
- `npm run ecr:login` - Login to ECR
- `npm run ecr:get-uri` - Get ECR repository URI

## Configuration

### Environment Variables

The deployment can be customized using these context variables:

- `environment` - Environment name (default: "test")
- `useDefaultVpc` - Use default VPC (default: true)

### Deployment Options

```bash
# Test environment with default VPC
./deploy.sh --environment test

# Production environment with custom VPC
./deploy.sh --environment prod --custom-vpc

# Different AWS region
./deploy.sh --region eu-west-1
```

## Outputs

After deployment, the stack provides these outputs:

- **VpcId** - VPC ID for the deployment
- **ClusterName** - ECS cluster name
- **RepositoryUri** - ECR repository URI for container images
- **LoadBalancerDnsName** - DNS name to access the application
- **TaskRoleArn** - ARN of the ECS task role
- **ExecutionRoleArn** - ARN of the ECS execution role

## Security

The infrastructure follows AWS security best practices:

- **IAM Roles**: Minimal permissions for Bedrock and Secrets Manager access
- **Security Groups**: Restrictive ingress rules
- **Secrets Management**: API keys stored in AWS Secrets Manager
- **Network Security**: Private subnets for ECS tasks (when using custom VPC)

## Cost Considerations

For testing environments:

- Uses default VPC to avoid NAT Gateway costs
- Minimal resource allocation
- Short log retention periods

For production environments:

- Consider using custom VPC with NAT Gateways
- Adjust resource limits and retention policies
- Enable detailed monitoring

## Next Steps

After deploying the infrastructure:

1. Build and push your container image to ECR
2. Create the ECS service and task definition
3. Configure auto-scaling policies
4. Set up monitoring and alerting

## Troubleshooting

### Common Issues

1. **CDK Bootstrap Required**:

   ```bash
   cdk bootstrap --region your-region
   ```

2. **Insufficient Permissions**:
   Ensure your AWS credentials have permissions for ECS, ECR, ALB, VPC, and IAM.

3. **Default VPC Not Found**:
   Use `--custom-vpc` flag to create a new VPC.

4. **Secret Not Found**:
   Create the Daily API key secret before deploying the ECS service.

### Useful Commands

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name PipecatEcsStack-test

# View logs
aws logs describe-log-groups --log-group-name-prefix "/ecs/pipecat"

# List ECR repositories
aws ecr describe-repositories --repository-names pipecat-voice-agent-test
```
