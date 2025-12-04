# AWS Credentials Setup for Nova Act Production

## Prerequisites
- AWS CLI installed: `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install`
- AWS account with IAM user created
- Access Key ID and Secret Access Key from AWS Console
- Python 3.10 or higher

## Overview
This script configures AWS credentials for Nova Act production deployment. Unlike the research-preview tutorials that use API key authentication, production workflows require AWS IAM authentication for security, monitoring, and integration with AWS services.

## Code Walkthrough

### Section 1: AWS CLI Verification
```python
def check_aws_cli_installed():
    """Check if AWS CLI is installed and accessible."""
    try:
        result = subprocess.run(['aws', '--version'], capture_output=True, text=True)
        print(f"\033[93m[OK]\033[0m AWS CLI found: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("\033[91m[ERROR]\033[0m AWS CLI not found. Please install it first:")
        return False
```
**Explanation**: Verifies AWS CLI installation before proceeding. Production Nova Act workflows require AWS CLI for deployment and service interaction. The script exits early if CLI is missing rather than failing later in the process.

### Section 2: Credentials Configuration
```python
def configure_aws_credentials():
    """Guide user through AWS credentials configuration."""
    print("You'll need your AWS Access Key ID and Secret Access Key.")
    subprocess.run(['aws', 'configure'], check=True)
```
**Explanation**: Runs the interactive `aws configure` command to collect Access Key ID, Secret Access Key, and default region. These credentials enable Nova Act SDK to authenticate with AWS services for workflow deployment and execution.

### Section 3: Region Setup
```python
def set_default_region():
    """Set default region for Nova Act (us-east-1 required)."""
    subprocess.run(['aws', 'configure', 'set', 'region', 'us-east-1'], check=True)
```
**Explanation**: Forces region to us-east-1 since Nova Act is currently only available in this region. This prevents deployment failures due to incorrect region selection and ensures all AWS resources are created in the supported region.

### Section 4: Credential Verification
```python
def verify_credentials():
    """Verify AWS credentials are working."""
    result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                          capture_output=True, text=True, check=True)
    identity = json.loads(result.stdout)
```
**Explanation**: Tests credentials by calling AWS STS to retrieve caller identity. This confirms credentials are valid and have basic AWS API access before proceeding to Nova Act-specific permission verification in the next script.

## Running the Example
```bash
cd /path/to/nova-act/tutorials/path-to-production/00-setup
python setup_aws_credentials.py
```

**Expected Output:**
```
AWS Credentials Setup for Nova Act Production
============================================================
[OK] AWS CLI found: aws-cli/2.x.x Python/3.x.x

AWS Credentials Configuration
============================================================
AWS Access Key ID [None]: AKIA...
AWS Secret Access Key [None]: ****
Default region name [None]: us-east-1
Default output format [None]: json

[OK] AWS credentials configured
[OK] Default region set to us-east-1
[OK] AWS credentials verified:
  Account: 123456789012
  User ARN: arn:aws:iam::123456789012:user/nova-act-user
```

## Troubleshooting
- **AWS CLI not found**: Install AWS CLI v2 from official documentation
- **Invalid credentials**: Verify Access Key ID and Secret Access Key in AWS Console
- **Permission denied**: Ensure IAM user has programmatic access enabled

## Next Steps
- Run `verify_permissions.py` to check Nova Act service access
- Proceed to 01-workflow-basics tutorials for workflow development
- Begin building production Nova Act workflows with AWS IAM authentication
