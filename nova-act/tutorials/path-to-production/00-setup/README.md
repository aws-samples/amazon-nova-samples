# Setup - AWS Configuration for Nova Act Production

## Purpose
Configure AWS credentials and verify service permissions required for Nova Act production deployment. This section establishes the foundation for AWS IAM authentication, which is required for production workflows, monitoring, and integration with AWS services.

## Tutorial Sequence
1. **1_setup_aws_credentials.py**: Configures AWS CLI with Access Key ID, Secret Access Key, and us-east-1 region. This replaces API key authentication used in research-preview tutorials.

2. **2_verify_permissions.py**: Tests Nova Act service access and validates IAM permissions. Confirms the credential setup enables actual service operations and identifies missing permissions before development begins.

## Prerequisites
- AWS account with IAM user created
- AWS CLI v2 installed from official documentation
- Access Key ID and Secret Access Key from AWS Console (IAM > Users > Security credentials)
- Python 3.10+ with boto3 library

## Production Considerations

### Security Implications
- AWS IAM authentication provides audit trails and fine-grained permissions
- Credentials are stored in AWS CLI configuration (~/.aws/credentials)
- Service-linked roles are created automatically for Nova Act operations
- Access keys should be rotated regularly following AWS security best practices

### Monitoring Requirements
- CloudWatch access enables Nova Act metrics collection (Invocations, Latency, Errors)
- IAM permissions allow service-linked role creation for automated monitoring
- S3 access supports artifact storage and trace file persistence

### Integration Patterns
- AWS IAM authentication enables integration with other AWS services
- Credentials support both local development and production deployment
- Region restriction (us-east-1) ensures service availability and resource locality
- Permission verification prevents deployment failures in later tutorials

## Common Issues
- **AWS CLI not found**: Install from https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
- **Invalid credentials**: Verify Access Key ID and Secret Access Key in AWS Console
- **Region errors**: Nova Act is only available in us-east-1 currently
- **Permission denied**: Attach Nova Act IAM policy to your user or role

## Next Steps
After completing this setup:
1. Proceed to `01-workflow-basics` for workflow development
2. Begin building production Nova Act workflows with AWS authentication
3. Deploy workflows to AWS infrastructure with proper monitoring and security
