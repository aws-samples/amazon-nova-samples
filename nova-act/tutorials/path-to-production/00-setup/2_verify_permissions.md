# Nova Act Permissions Verification

## Prerequisites
- Completed `setup_aws_credentials.py`
- AWS credentials configured with `aws configure`
- IAM user with Nova Act permissions attached
- Python boto3 library: `pip install boto3`

## Overview
This script verifies AWS IAM permissions for Nova Act service access. It tests actual service connectivity and required permissions before workflow development. This prevents deployment failures and ensures proper access to monitoring and artifact storage services.

## Code Walkthrough

### Section 1: AWS Credentials Verification
```python
def check_aws_credentials():
    """Verify AWS credentials are configured and working."""
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
```
**Explanation**: Uses AWS STS (Security Token Service) to verify credentials are valid and retrieve caller identity. This confirms the previous credential setup worked and AWS API access is functional before testing Nova Act-specific permissions.

### Section 2: Nova Act Service Access Test
```python
def check_nova_act_permissions():
    """Check Nova Act service permissions."""
    nova_act = boto3.client('nova-act', region_name='us-east-1')
    response = nova_act.list_workflow_definitions(maxResults=1)
```
**Explanation**: Creates Nova Act service client and attempts a basic read operation (list workflow definitions). This tests actual service access and validates IAM permissions are correctly configured for Nova Act operations. Failure here indicates missing or incorrect IAM policies.

### Section 3: Required Services Check
```python
def check_required_services():
    """Check access to services required by Nova Act."""
    # CloudWatch (for metrics and monitoring)
    cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
    cloudwatch.list_metrics(MaxRecords=1)
```
**Explanation**: Tests access to AWS services that Nova Act integrates with for production operations. CloudWatch is required for metrics and monitoring, IAM for service-linked roles, and S3 for artifact storage. Limited access to these services may impact production functionality but won't prevent basic workflow execution.

### Section 4: IAM Policy Display
```python
def display_iam_policy_example():
    """Display example IAM policy for Nova Act."""
    policy = {
        "Statement": [{
            "Effect": "Allow",
            "Action": ["nova-act:*"],
            "Resource": "*"
        }]
    }
```
**Explanation**: Shows the exact IAM policy required for Nova Act access when permission errors are detected. This policy grants full Nova Act service access and permission to create service-linked roles. The policy is displayed only when verification fails to provide immediate remediation steps.

## Running the Example
```bash
cd /path/to/nova-act/tutorials/path-to-production/00-setup
python verify_permissions.py
```

**Expected Output (Success):**
```
Nova Act Permissions Verification
============================================================

AWS Credentials Check
============================================================
[OK] AWS credentials found:
  Account: 123456789012
  User ARN: arn:aws:iam::123456789012:user/nova-act-user
  Region: us-east-1

Nova Act Service Permissions
============================================================
Testing Nova Act service access...
[OK] Nova Act service access verified
  Service endpoint: nova-act.us-east-1.amazonaws.com
  Region: us-east-1

Required Services Check
============================================================
[OK] CloudWatch access verified
[OK] IAM access verified
[OK] S3 access verified

Verification Results
============================================================
✓ Completed: Nova Act service access verified
→ Next: Proceed to 01-workflow-basics tutorials
```

**Expected Output (Permission Error):**
```
Nova Act Service Permissions
============================================================
[ERROR] Insufficient Nova Act permissions
  Your IAM user/role needs Nova Act service permissions
  Required policy: nova-act:* actions

Required IAM Policy Example
============================================================
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["nova-act:*"],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting
- **No AWS credentials found**: Run `setup_aws_credentials.py` first
- **Insufficient Nova Act permissions**: Attach the displayed IAM policy to your user
- **Service unavailable**: Verify Nova Act is available in us-east-1 region
- **Access denied**: Check IAM user has programmatic access enabled

## Next Steps
- If verification succeeds: Proceed to `01-workflow-basics` tutorials
- If verification fails: Fix IAM permissions and re-run this script
- Begin developing Nova Act workflows with confirmed AWS service access
