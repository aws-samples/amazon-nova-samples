# AWS Configuration

This directory contains AWS-specific configuration files for the Pipecat ECS deployment.

## Structure

### Policies (`policies/`)

- `ecs-task-execution-role-trust-policy.json` - Trust policy for ECS task execution role
- `execution-role-secrets-policy.json` - Policy for accessing AWS Secrets Manager
- `pipecat-task-policy.json` - Task-specific permissions policy

### Task Definitions (`task-definitions/`)

- `phone-task-definition.json` - ECS task definition for the phone service

## Usage

These files are typically used by:

- AWS CDK infrastructure deployment (in `infrastructure/` directory)
- Manual AWS CLI commands for policy and role creation
- ECS service deployment scripts

## Policy Overview

### ECS Task Execution Role

Allows ECS to pull images from ECR and write logs to CloudWatch.

### Secrets Access Policy

Grants access to specific secrets in AWS Secrets Manager for:

- Daily.co API keys
- Twilio credentials
- Other application secrets

### Task Policy

Application-level permissions for:

- AWS Bedrock access
- CloudWatch logging
- Other AWS services used by the application

## Notes

- These policies follow the principle of least privilege
- Secrets are injected as environment variables by ECS
- All configurations are designed for production security standards
