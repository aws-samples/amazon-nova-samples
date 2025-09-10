# Deployment Scripts

This directory contains scripts for building, pushing, and deploying the Pipecat voice AI agent to AWS ECS.

## Scripts Overview

### 1. `build-and-push.sh`

Builds the Docker image and pushes it to Amazon ECR.

**Usage:**

```bash
./build-and-push.sh [OPTIONS]
```

**Options:**

- `-e, --environment ENV`: Set environment (default: test)
- `-r, --region REGION`: Set AWS region (default: eu-north-1)
- `-t, --tag TAG`: Set image tag (default: latest)
- `-f, --dockerfile PATH`: Set Dockerfile path (default: .)
- `--force`: Force rebuild even if image exists
- `-h, --help`: Show help message

**Examples:**

```bash
# Build with defaults
./build-and-push.sh

# Build for production with specific tag
./build-and-push.sh -e prod -t v1.2.3

# Force rebuild
./build-and-push.sh --force
```

### 2. `deploy-service.sh`

Creates or updates the ECS service with a new container image.

**Usage:**

```bash
./deploy-service.sh [OPTIONS]
```

**Options:**

- `-e, --environment ENV`: Set environment (default: test)
- `-r, --region REGION`: Set AWS region (default: eu-north-1)
- `-t, --tag TAG`: Set image tag (default: latest)
- `--update`: Update existing service (default action)
- `--create`: Create new service
- `--scale COUNT`: Scale service to specified count
- `--no-wait`: Don't wait for deployment to complete
- `-h, --help`: Show help message

**Examples:**

```bash
# Update service with latest image
./deploy-service.sh

# Update with specific tag
./deploy-service.sh -t v1.2.3

# Scale to 4 tasks
./deploy-service.sh --scale 4
```

### 3. `../deploy.sh` (Main Deployment Script)

Orchestrates the complete deployment process by running both build and deploy scripts.

**Usage:**

```bash
./deploy.sh [OPTIONS]
```

**Options:**

- `-e, --environment ENV`: Set environment (default: test)
- `-r, --region REGION`: Set AWS region (default: eu-north-1)
- `-t, --tag TAG`: Set image tag (default: latest)
- `--skip-build`: Skip Docker build and push
- `--skip-deploy`: Skip ECS service deployment
- `--force-build`: Force rebuild even if image exists
- `--build-only`: Only build and push image
- `--deploy-only`: Only deploy to ECS (skip build)
- `-h, --help`: Show help message

**Examples:**

```bash
# Full deployment with defaults
./deploy.sh

# Deploy to production with specific tag
./deploy.sh -e prod -t v1.2.3

# Only build and push image
./deploy.sh --build-only

# Only deploy existing image
./deploy.sh --deploy-only -t v1.2.3
```

## Prerequisites

Before using these scripts, ensure you have:

1. **AWS CLI configured** with appropriate credentials:

   ```bash
   aws configure
   ```

2. **Docker installed** and running:

   ```bash
   docker --version
   ```

3. **Infrastructure deployed** using CDK:

   ```bash
   cd infrastructure
   ./deploy.sh
   ```

4. **Secrets configured** in AWS Secrets Manager:
   ```bash
   python3 setup-secrets.py
   ```

## Deployment Workflow

### Standard Deployment Process

1. **Deploy Infrastructure** (one-time setup):

   ```bash
   cd infrastructure
   ./deploy.sh
   ```

2. **Set up Secrets** (one-time setup):

   ```bash
   python3 setup-secrets.py
   ```

3. **Deploy Application**:
   ```bash
   ./deploy.sh
   ```

### Development Workflow

For development and testing:

```bash
# Build and test locally first
docker build -t pipecat-test .
docker run -p 7860:7860 --env-file .env pipecat-test

# Deploy to test environment
./deploy.sh -e test

# Deploy to staging
./deploy.sh -e staging -t staging-$(date +%Y%m%d-%H%M%S)

# Deploy to production
./deploy.sh -e prod -t v1.0.0
```

### CI/CD Integration

The scripts are designed to work with the GitHub Actions workflow in `.github/workflows/deploy.yml`. The workflow automatically:

- Runs tests on pull requests
- Builds and pushes images on main/develop branches
- Deploys to appropriate environments based on branch
- Provides deployment status and URLs

## Environment Configuration

### Supported Environments

- **test**: Development and testing environment
- **staging**: Pre-production environment
- **prod**: Production environment

### Environment-Specific Resources

Each environment creates separate AWS resources:

- ECS Cluster: `pipecat-cluster-{environment}`
- ECR Repository: `pipecat-voice-agent-{environment}`
- Load Balancer: `pipecat-alb-{environment}`
- CloudWatch Logs: `/ecs/pipecat-voice-agent-{environment}`

## Monitoring and Troubleshooting

### Useful Commands

**Check service status:**

```bash
aws ecs describe-services --cluster pipecat-cluster-test --services pipecat-service-test --region eu-north-1
```

**View service logs:**

```bash
aws logs tail /ecs/pipecat-voice-agent-test --follow --region eu-north-1
```

**List running tasks:**

```bash
aws ecs list-tasks --cluster pipecat-cluster-test --service-name pipecat-service-test --region eu-north-1
```

**Get load balancer URL:**

```bash
aws cloudformation describe-stacks --stack-name PipecatEcsStack-test --region eu-north-1 --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDnsName`].OutputValue' --output text
```

### Common Issues

1. **ECR Repository Not Found**

   - Ensure infrastructure is deployed: `cd infrastructure && ./deploy.sh`

2. **Docker Build Fails**

   - Check Dockerfile syntax and dependencies
   - Ensure Docker daemon is running

3. **ECS Service Update Fails**

   - Check task definition is valid
   - Verify IAM permissions
   - Check CloudWatch logs for container errors

4. **Health Check Failures**
   - Ensure `/health` endpoint is implemented in the application
   - Check security group allows traffic on port 7860
   - Verify container starts successfully

### Enhanced Monitoring and Logging

The deployment includes comprehensive monitoring and logging capabilities:

#### CloudWatch Log Groups

- `/ecs/pipecat-voice-agent-{environment}/application` - Structured application logs
- `/ecs/pipecat-voice-agent-{environment}/access` - HTTP access logs
- `/ecs/pipecat-voice-agent-{environment}/error` - Error-specific logs

#### Monitoring Tools

**Log Analysis Script:**

```bash
# View recent errors
./log-analysis.sh errors 2

# Monitor health checks
./log-analysis.sh health 1

# Real-time log monitoring
./log-analysis.sh monitor

# Export logs for analysis
./log-analysis.sh export 24
```

**Continuous Health Monitoring:**

```bash
# Run continuous monitoring
python ../monitoring.py --url http://your-alb-dns-name --interval 30

# Single health check
python ../monitoring.py --url http://your-alb-dns-name --single-check
```

#### CloudWatch Insights Queries

Pre-built queries are available in `../cloudwatch-queries.md`:

```bash
# Run custom query
./log-analysis.sh query 'fields @timestamp, message | filter level = "ERROR"' 1
```

#### CloudWatch Dashboard

Access the monitoring dashboard:

- Go to CloudWatch Console
- Navigate to Dashboards
- Select `pipecat-voice-agent-{environment}`

#### Alarms and Metrics

The deployment automatically creates alarms for:

- High CPU/Memory utilization
- Low task count
- High response times
- HTTP 5xx errors
- Unhealthy targets

### Log Analysis

**Application logs:**

```bash
aws logs filter-log-events --log-group-name /ecs/pipecat-voice-agent-test/application --region eu-north-1
```

**ECS service events:**

```bash
aws ecs describe-services --cluster pipecat-cluster-test --services pipecat-service-test --region eu-north-1 --query 'services[0].events[0:10]'
```

## Security Considerations

- All secrets are stored in AWS Secrets Manager
- Container images are scanned for vulnerabilities in ECR
- IAM roles follow principle of least privilege
- Network access is restricted by security groups
- All API calls are logged in CloudTrail

## Cost Optimization

- Use appropriate instance sizes for your workload
- Consider using Spot instances for non-production environments
- Set up auto-scaling to handle variable load
- Monitor CloudWatch metrics to optimize resource allocation
- Clean up unused images in ECR regularly

For more detailed information, see the main [DEPLOYMENT_GUIDE.md](../infrastructure/DEPLOYMENT_GUIDE.md).
