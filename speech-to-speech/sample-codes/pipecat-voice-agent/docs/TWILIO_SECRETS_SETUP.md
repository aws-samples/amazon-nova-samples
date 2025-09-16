# Twilio Credentials Setup for AWS Secrets Manager

This document explains how Twilio credentials are managed in AWS Secrets Manager for the Pipecat ECS deployment.

## Overview

The Twilio credentials are stored securely in AWS Secrets Manager and automatically injected into ECS tasks as environment variables. This allows the phone service to access Twilio APIs without hardcoding credentials in the container image.

## Secret Structure

The Twilio credentials are stored in AWS Secrets Manager under the name `pipecat/twilio-credentials` with the following structure:

```json
{
  "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "TWILIO_AUTH_TOKEN": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "TWILIO_PHONE_NUMBER": "+1234567890",
  "TWILIO_API_SID": "SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "TWILIO_API_SECRET": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

## Environment Variables

When the ECS task starts, these credentials are automatically injected as environment variables:

- `TWILIO_ACCOUNT_SID`: Your Twilio Account SID (starts with "AC")
- `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token (32 characters)
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number (E.164 format, e.g., "+441182304072")
- `TWILIO_API_SID`: Your Twilio API Key SID (starts with "SK")
- `TWILIO_API_SECRET`: Your Twilio API Key Secret

## Setup Process

### 1. Create/Update Secrets

Run the setup script to create or update the Twilio credentials secret:

```bash
python3 scripts/setup-secrets.py
```

This script will:

- Read Twilio credentials from your `.env` file
- Create or update the `pipecat/twilio-credentials` secret in AWS Secrets Manager
- Verify the secret can be accessed

### 2. Test Secret Access

Verify that the secret can be retrieved:

```bash
python3 scripts/test-twilio-secret.py
```

### 3. Test ECS Integration

Simulate how ECS tasks will access all secrets:

```bash
python3 scripts/test-ecs-secret-access.py
```

## IAM Permissions

The ECS task role and execution role have been configured with the necessary permissions to access the Twilio credentials secret:

```typescript
// Task Role - for application runtime access
SecretsManagerAccess: new iam.PolicyDocument({
  statements: [
    new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ["secretsmanager:GetSecretValue"],
      resources: [
        "arn:aws:secretsmanager:REGION:ACCOUNT:secret:pipecat/twilio-credentials*"
      ],
    }),
  ],
}),
```

## Application Usage

In your Python application, the Twilio credentials will be available as environment variables:

```python
import os
from twilio.rest import Client

# Credentials are automatically available from Secrets Manager
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
phone_number = os.getenv('TWILIO_PHONE_NUMBER')

# Initialize Twilio client
client = Client(account_sid, auth_token)

# Use the phone number for outbound calls or webhook configuration
print(f"Twilio phone number: {phone_number}")
```

## Security Considerations

1. **No Hardcoded Credentials**: Credentials are never stored in the container image or code
2. **Encrypted at Rest**: AWS Secrets Manager encrypts secrets using AWS KMS
3. **Encrypted in Transit**: Secrets are retrieved over HTTPS
4. **IAM Access Control**: Only authorized ECS tasks can access the secrets
5. **Audit Trail**: All secret access is logged in CloudTrail

## Troubleshooting

### Secret Not Found

If you get a "secret not found" error:

1. Verify the secret exists: `aws secretsmanager list-secrets --region eu-north-1`
2. Check the secret name matches exactly: `pipecat/twilio-credentials`
3. Ensure you're using the correct AWS region

### Access Denied

If you get an "access denied" error:

1. Verify your AWS credentials have Secrets Manager permissions
2. Check that the ECS task role has the correct permissions
3. Ensure the secret ARN in the IAM policy is correct

### Invalid Credentials

If Twilio API calls fail:

1. Verify credentials in the AWS console: Secrets Manager → `pipecat/twilio-credentials`
2. Test credentials locally with the Twilio CLI
3. Check that the Account SID starts with "AC" and is 34 characters
4. Verify the Auth Token is 32 characters

## Manual Secret Management

You can also manage the secret manually using the AWS CLI:

### View Secret

```bash
aws secretsmanager get-secret-value \
  --secret-id pipecat/twilio-credentials \
  --region eu-north-1
```

### Update Secret

```bash
aws secretsmanager update-secret \
  --secret-id pipecat/twilio-credentials \
  --secret-string '{"TWILIO_ACCOUNT_SID":"ACxxx","TWILIO_AUTH_TOKEN":"xxx","TWILIO_PHONE_NUMBER":"+1234567890","TWILIO_API_SID":"SKxxx","TWILIO_API_SECRET":"xxx"}' \
  --region eu-north-1
```

## Next Steps

After setting up the Twilio credentials secret:

1. Deploy the updated CDK infrastructure: `npm run deploy` (in infrastructure/)
2. Build and push the phone service container image
3. Deploy the phone service ECS task
4. Configure Twilio webhook URL to point to your phone service ALB
5. Test inbound phone calls to verify the integration works

## Related Documentation

- [SECRETS_SETUP.md](SECRETS_SETUP.md) - General secrets setup
- [DEPLOYMENT_PROCESS.md](DEPLOYMENT_PROCESS.md) - Full deployment guide
- [Twilio Integration Tasks](../.kiro/specs/pipecat-ecs-deployment/tasks.md) - Implementation tasks
