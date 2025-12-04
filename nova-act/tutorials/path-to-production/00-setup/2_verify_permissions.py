#!/usr/bin/env python3
"""
Nova Act Permissions Verification

This script verifies that your AWS credentials have the necessary permissions
to use Nova Act service in production.

Prerequisites:
- Completed setup_aws_credentials.py
- AWS credentials configured
- IAM permissions for Nova Act service

Setup:
1. Ensure AWS credentials are configured
2. Run this script to verify Nova Act access
3. Address any permission issues before proceeding

Note: This script tests actual Nova Act service access, not just AWS API access.
"""

import boto3
import json
import sys
from botocore.exceptions import ClientError, NoCredentialsError


def check_aws_credentials():
    """Verify AWS credentials are configured and working."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mAWS Credentials Check\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"\n\033[93m[OK]\033[0m AWS credentials found:")
        print(f"  Account: {identity['Account']}")
        print(f"  User ARN: {identity['Arn']}")
        print(f"  Region: {boto3.Session().region_name}")
        return True
        
    except NoCredentialsError:
        print(f"\n\033[91m[ERROR]\033[0m No AWS credentials found")
        print("  Run setup_aws_credentials.py first")
        return False
    except ClientError as e:
        print(f"\n\033[91m[ERROR]\033[0m AWS credentials error: {e}")
        return False


def check_nova_act_permissions():
    """Check Nova Act service permissions."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mNova Act Service Permissions\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    try:
        # Test Nova Act service access
        nova_act = boto3.client('nova-act', region_name='us-east-1')
        
        # Try to list workflow definitions (basic read operation)
        print("\nTesting Nova Act service access...")
        response = nova_act.list_workflow_definitions(maxResults=1)
        
        print(f"\033[93m[OK]\033[0m Nova Act service access verified")
        print(f"  Service endpoint: {nova_act._endpoint.host}")
        print(f"  Region: us-east-1")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'UnauthorizedOperation':
            print(f"\033[91m[ERROR]\033[0m Insufficient Nova Act permissions")
            print("  Your IAM user/role needs Nova Act service permissions")
            print("  Required policy: nova-act:* actions")
            return False
        elif error_code == 'AccessDenied':
            print(f"\033[91m[ERROR]\033[0m Access denied to Nova Act service")
            print("  Check IAM policies and service availability")
            return False
        else:
            print(f"\033[91m[ERROR]\033[0m Nova Act service error: {error_code}")
            print(f"  Message: {e.response['Error']['Message']}")
            return False
            
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Unexpected error accessing Nova Act: {e}")
        return False


def check_required_services():
    """Check access to services required by Nova Act."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mRequired Services Check\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    services_status = {}
    
    # CloudWatch (for metrics and monitoring)
    try:
        cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
        cloudwatch.list_metrics(Namespace='AWS/NovaAct')
        services_status['CloudWatch'] = True
        print(f"\033[93m[OK]\033[0m CloudWatch access verified")
    except ClientError:
        services_status['CloudWatch'] = False
        print(f"\033[93m[WARNING]\033[0m CloudWatch access limited (monitoring may be affected)")
    
    # IAM (for service-linked roles)
    try:
        iam = boto3.client('iam')
        iam.get_user()
        services_status['IAM'] = True
        print(f"\033[93m[OK]\033[0m IAM access verified")
    except ClientError:
        services_status['IAM'] = False
        print(f"\033[93m[WARNING]\033[0m IAM access limited (service-linked role creation may fail)")
    
    # S3 (for artifacts and traces)
    try:
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.list_buckets()
        services_status['S3'] = True
        print(f"\033[93m[OK]\033[0m S3 access verified")
    except ClientError:
        services_status['S3'] = False
        print(f"\033[93m[WARNING]\033[0m S3 access limited (artifact storage may be affected)")
    
    return services_status


def display_iam_policy_example():
    """Display example IAM policy for Nova Act."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mRequired IAM Policy Example\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "NovaActFullAccess",
                "Effect": "Allow",
                "Action": [
                    "nova-act:*"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": "iam:CreateServiceLinkedRole",
                "Resource": "arn:aws:iam::*:role/aws-service-role/nova-act.amazonaws.com/AWSServiceRoleForNovaAct",
                "Condition": {
                    "StringLike": {
                        "iam:AWSServiceName": "nova-act.amazonaws.com"
                    }
                }
            }
        ]
    }
    
    print("\nAttach this policy to your IAM user or role:")
    print(json.dumps(policy, indent=2))
    print("\nTo attach via AWS CLI:")
    print("1. Save policy to file: nova-act-policy.json")
    print("2. Create policy: aws iam create-policy --policy-name NovaActFullAccess --policy-document file://nova-act-policy.json")
    print("3. Attach to user: aws iam attach-user-policy --user-name YOUR_USERNAME --policy-arn arn:aws:iam::ACCOUNT:policy/NovaActFullAccess")


def display_results(nova_act_access, services_status):
    """Display final verification results."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mVerification Results\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    if nova_act_access:
        print(f"\n\033[92m✓ Completed:\033[0m Nova Act service access verified")
        print(f"\033[38;5;214m→ Next:\033[0m Proceed to 01-workflow-basics tutorials")
        
        print(f"\n\033[38;5;214mService Status:\033[0m")
        for service, status in services_status.items():
            status_icon = "✓" if status else "⚠"
            print(f"  {status_icon} {service}")
        
        print(f"\n\033[38;5;214mReady for:\033[0m")
        print("1. Nova Act workflow development")
        print("2. Production deployment")
        print("3. AWS service integration")
        
    else:
        print(f"\n\033[91m✗ Failed:\033[0m Nova Act service access not available")
        print(f"\033[38;5;214m→ Next:\033[0m Fix IAM permissions before proceeding")
        
        print(f"\n\033[38;5;214mTroubleshooting:\033[0m")
        print("1. Check IAM policy attachment")
        print("2. Verify Nova Act service availability in us-east-1")
        print("3. Contact AWS support if issues persist")


def main():
    """Main verification function."""
    print("="*60)
    print("Nova Act Permissions Verification")
    print("="*60)
    
    # Check AWS credentials
    if not check_aws_credentials():
        sys.exit(1)
    
    # Check Nova Act permissions
    nova_act_access = check_nova_act_permissions()
    
    # Check required services
    services_status = check_required_services()
    
    # Show IAM policy if needed
    if not nova_act_access:
        display_iam_policy_example()
    
    # Display results
    display_results(nova_act_access, services_status)
    
    # Exit with appropriate code
    sys.exit(0 if nova_act_access else 1)


if __name__ == "__main__":
    main()
