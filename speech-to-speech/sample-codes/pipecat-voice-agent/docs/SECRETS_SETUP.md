# AWS Secrets Manager Integration

This document describes how AWS Secrets Manager is integrated with the Pipecat ECS deployment to securely manage sensitive configuration data.

## Overview

The Pipecat ECS deployment uses AWS Secrets Manager to store and inject sensitive configuration data into ECS tasks. This approach provides several benefits:

- **Security**: Secrets are encrypted at rest and in transit
- **Rotation**: Secrets can be rotated without redeploying the application
- **Audit**: All secret access is logged in CloudTrail
- **Separation**: Secrets are managed separately from application code

## Secrets Structure

### 1. Daily API Credentials (`pipecat/daily-api-key`)

Contains Daily.co API credentials required for WebRTC functionality:

```json
{
  "DAILY_API_KEY": "your-daily-api-key",
  "DAILY_API_URL": "https://api.daily.co/v1"
}
```

### 2. AWS Credentials (`pipecat/aws-credentials`)

Contains AWS credentials for Bedrock access (alternative to IAM roles):

```json
{
  "AWS_ACCESS_KEY_ID": "your-aws-access-key",
  "AWS_SECRET_ACCESS_KEY": "your-aws-secret-key",
  "AWS_REGION": "eu-north-1"
}
```

## Setup Process

### 1. Create Secrets

Run the setup script to create the secrets in AWS Secrets Manager:

```bash
python3 setup-secrets.py
```

This script will:

- Read credentials from your `.env` file
- Create the secrets in AWS Secrets Manager
- Verify the secrets can be retrieved
- Display the secret ARNs for CDK configuration

### 2. CDK Infrastructure

The CDK infrastructure automatically:

- References the secrets by name
- Grants the ECS execution role permission to retrieve secrets
- Configures the ECS task definition to inject secrets as environment variables

### 3. ECS Task Injection

When ECS starts a task, it automatically:

- Retrieves the secret values from Secrets Manager
- Injects them as environment variables into the container
- Makes them available to the application code

## Environment Variables

The following environment variables are injected into ECS tasks:

| Variable                | Source                    | Description           |
| ----------------------- | ------------------------- | --------------------- |
| `DAILY_API_KEY`         | `pipecat/daily-api-key`   | Daily.co API key      |
| `DAILY_API_URL`         | `pipecat/daily-api-key`   | Daily.co API URL      |
| `AWS_ACCESS_KEY_ID`     | `pipecat/aws-credentials` | AWS access key        |
| `AWS_SECRET_ACCESS_KEY` | `pipecat/aws-credentials` | AWS secret key        |
| `AWS_REGION`            | Environment/CDK           | AWS region            |
| `HOST`                  | CDK                       | Server host (0.0.0.0) |
| `FAST_API_PORT`         | CDK                       | Server port (7860)    |

## IAM Permissions

### ECS Execution Role

The ECS execution role needs permission to retrieve secrets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": ["arn:aws:secretsmanager:REGION:ACCOUNT:secret:pipecat/*"]
    }
  ]
}
```

### ECS Task Role

The ECS task role needs permissions for:

- Bedrock model invocation
- Optional Secrets Manager access (for runtime secret retrieval)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": ["arn:aws:bedrock:*::foundation-model/amazon.nova-sonic-v1:0"]
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": ["arn:aws:secretsmanager:REGION:ACCOUNT:secret:pipecat/*"]
    }
  ]
}
```

## Testing

### 1. Test Secrets Access

Verify that secrets can be retrieved:

```bash
python3 test-secrets-integration.py
```

### 2. Test Bedrock Access

Verify that Bedrock Nova Sonic can be accessed:

```bash
python3 test-bedrock-access.py
```

### 3. Health Check

The application includes a comprehensive health check that verifies:

- Daily API helper initialization
- Required environment variables
- Active bot processes

Access the health check at: `http://your-alb-dns/health`

## Security Best Practices

### 1. Least Privilege

- ECS execution role only has permission to retrieve specific secrets
- ECS task role only has permission for required AWS services
- Secrets are scoped to the `pipecat/` namespace

### 2. Encryption

- Secrets are encrypted at rest using AWS KMS
- Secrets are encrypted in transit using TLS
- Environment variables in ECS are encrypted

### 3. Rotation

- Secrets can be rotated in AWS Secrets Manager
- ECS tasks will pick up new secret values on restart
- No application code changes required for rotation

### 4. Monitoring

- All secret access is logged in CloudTrail
- ECS task logs include environment variable validation
- Health checks verify secret availability

## Troubleshooting

### Common Issues

1. **Secret Not Found**

   - Verify the secret exists in AWS Secrets Manager
   - Check the secret name matches the CDK configuration
   - Ensure you're in the correct AWS region

2. **Permission Denied**

   - Verify the ECS execution role has `secretsmanager:GetSecretValue` permission
   - Check the resource ARN in the IAM policy
   - Ensure the secret ARN is correct

3. **Environment Variables Not Set**

   - Check the ECS task definition includes the secret mappings
   - Verify the secret keys match the expected names
   - Check ECS task logs for secret retrieval errors

4. **Bedrock Access Issues**
   - Verify Nova Sonic model access has been requested
   - Check the ECS task role has Bedrock permissions
   - Ensure the model is available in your region

### Debugging Commands

```bash
# List secrets
aws secretsmanager list-secrets --region eu-north-1

# Get secret value
aws secretsmanager get-secret-value --secret-id pipecat/daily-api-key --region eu-north-1

# Check ECS task logs
aws logs get-log-events --log-group-name /ecs/pipecat-voice-agent-test --log-stream-name ecs/pipecat-container/TASK-ID

# Test Bedrock access
aws bedrock list-foundation-models --region eu-north-1
```

## Cost Considerations

- AWS Secrets Manager charges per secret per month
- Additional charges for API calls (retrievals)
- ECS automatically caches secrets to minimize API calls
- Consider consolidating secrets to reduce costs

## Next Steps

After setting up secrets:

1. Deploy the updated CDK infrastructure
2. Build and push the container image to ECR
3. Deploy the ECS service
4. Test the application end-to-end
5. Monitor logs and metrics
