# Cleanup Guide

This guide helps you clean up AWS resources and local development environment.

## Local Development Cleanup

### Clean Docker Resources
```bash
# Remove containers
docker container prune -f

# Remove images
docker image prune -f

# Remove volumes
docker volume prune -f

# Remove networks
docker network prune -f
```

### Clean Python Environment
```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf .venv

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

## AWS Environment Cleanup

### ECS Environment Cleanup

```bash
# Stop ECS service
aws ecs update-service \
  --cluster pipecat-cluster-test \
  --service pipecat-service-test \
  --desired-count 0

# Delete ECS service
aws ecs delete-service \
  --cluster pipecat-cluster-test \
  --service pipecat-service-test

# Delete CDK stack
cd infrastructure
cdk destroy PipecatEcsStack-test
```

### EKS Environment Cleanup

```bash
# Delete Kubernetes resources
kubectl delete namespace pipecat

# Delete CDK stack
cd infrastructure/-eks
cdk destroy PipecatEksStack

# Clean kubectl config (optional)
kubectl config delete-context arn:aws:eks:us-east-1:ACCOUNT:cluster/pipecat-eks-cluster-test
```

### Clean ECR Repositories

```bash
# List repositories
aws ecr describe-repositories --query 'repositories[?contains(repositoryName, `pipecat`)].repositoryName'

# Delete repository (replace with actual name)
aws ecr delete-repository --repository-name pipecat-voice-agent-test --force
```

### Clean Secrets Manager

```bash
# List secrets
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `pipecat`)].Name'

# Delete secret (replace with actual ARN)
aws secretsmanager delete-secret --secret-id arn:aws:secretsmanager:region:account:secret:name
```

### Clean CloudWatch Logs

```bash
# List log groups
aws logs describe-log-groups --query 'logGroups[?contains(logGroupName, `pipecat`)].logGroupName'

# Delete log group
aws logs delete-log-group --log-group-name /ecs/pipecat-voice-agent-test
```

## Complete Cleanup Script

Create a cleanup script for convenience:

```bash
#!/bin/bash
# cleanup.sh

ENVIRONMENT=${1:-test}

echo "Cleaning up environment: $ENVIRONMENT"

# ECS cleanup
aws ecs update-service --cluster pipecat-cluster-$ENVIRONMENT --service pipecat-service-$ENVIRONMENT --desired-count 0
aws ecs delete-service --cluster pipecat-cluster-$ENVIRONMENT --service pipecat-service-$ENVIRONMENT

# CDK cleanup
cd infrastructure
cdk destroy PipecatEcsStack-$ENVIRONMENT --force

# ECR cleanup
aws ecr delete-repository --repository-name pipecat-voice-agent-$ENVIRONMENT --force

echo "Cleanup complete for environment: $ENVIRONMENT"
```

## Verification

After cleanup, verify resources are removed:

```bash
# Check ECS
aws ecs list-clusters
aws ecs list-services --cluster pipecat-cluster-test

# Check ECR
aws ecr describe-repositories

# Check Secrets
aws secretsmanager list-secrets

# Check CloudWatch
aws logs describe-log-groups
```

## Cost Monitoring

Monitor costs to ensure cleanup was successful:
- Check AWS Cost Explorer
- Review billing dashboard
- Set up cost alerts for future deployments