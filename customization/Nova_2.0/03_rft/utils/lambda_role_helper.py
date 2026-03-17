"""
AWS Lambda IAM Role Helper

This module provides utilities to create and manage IAM roles for Lambda functions.
"""

import boto3
import json
from typing import Optional, List


def create_lambda_execution_role(
    role_name: str,
    managed_policies: Optional[List[str]] = None,
    region: str = "us-east-1"
) -> str:
    """
    Create an IAM role that can be assumed by Lambda with necessary permissions.
    
    Args:
        role_name: Name for the IAM role
        managed_policies: List of managed policy ARNs to attach (optional)
                         Defaults to AWSLambdaBasicExecutionRole
        region: AWS region (default: "us-east-1")
    
    Returns:
        str: The ARN of the created role
        
    Example:
        >>> role_arn = create_lambda_execution_role(
        ...     role_name="my-lambda-role",
        ...     managed_policies=[
        ...         "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        ...         "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
        ...     ]
        ... )
        >>> print(role_arn)
    """
    iam_client = boto3.client('iam', region_name=region)
    
    # Define trust policy that allows Lambda to assume this role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Default policies if none provided
    if managed_policies is None:
        managed_policies = [
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        ]
    
    try:
        # Create the role
        print(f"🔐 Creating IAM role: {role_name}")
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Execution role for Lambda function with permissions to run and access AWS services"
        )
        
        role_arn = response['Role']['Arn']
        print(f"✅ Role created: {role_arn}")
        
        # Attach managed policies
        for policy_arn in managed_policies:
            print(f"📎 Attaching policy: {policy_arn}")
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
        
        print(f"✅ All policies attached successfully!")
        print(f"⏳ Note: Wait 10-15 seconds before using this role with Lambda")
        
        return role_arn
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"ℹ️  Role {role_name} already exists, retrieving ARN...")
        response = iam_client.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        print(f"✅ Using existing role: {role_arn}")
        return role_arn
        
    except Exception as e:
        print(f"❌ Error creating role: {e}")
        raise


def get_or_create_lambda_role(
    role_name: str = "lambda-execution-role",
    managed_policies: Optional[List[str]] = None,
    region: str = "us-east-1"
) -> str:
    """
    Get an existing Lambda execution role or create one if it doesn't exist.
    
    Args:
        role_name: Name for the IAM role (default: "lambda-execution-role")
        managed_policies: List of managed policy ARNs to attach
        region: AWS region (default: "us-east-1")
    
    Returns:
        str: The ARN of the role
    """
    iam_client = boto3.client('iam', region_name=region)
    
    try:
        # Try to get existing role
        response = iam_client.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        print(f"✅ Using existing role: {role_arn}")
        return role_arn
    except iam_client.exceptions.NoSuchEntityException:
        # Role doesn't exist, create it
        return create_lambda_execution_role(role_name, managed_policies, region)


def add_bedrock_permissions_to_role(role_name: str, region: str = "us-east-1") -> None:
    """
    Add Amazon Bedrock permissions to an existing IAM role.
    
    Args:
        role_name: Name of the IAM role
        region: AWS region (default: "us-east-1")
    """
    iam_client = boto3.client('iam', region_name=region)
    
    bedrock_policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
    
    try:
        print(f"📎 Adding Bedrock permissions to role: {role_name}")
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=bedrock_policy_arn
        )
        print(f"✅ Bedrock permissions added successfully!")
    except Exception as e:
        print(f"❌ Error adding Bedrock permissions: {e}")
        raise


def create_custom_policy_for_role(
    role_name: str,
    policy_name: str,
    policy_document: dict,
    region: str = "us-east-1"
) -> str:
    """
    Create and attach a custom inline policy to an IAM role.
    
    Args:
        role_name: Name of the IAM role
        policy_name: Name for the inline policy
        policy_document: Policy document as a dictionary
        region: AWS region (default: "us-east-1")
    
    Returns:
        str: The name of the created policy
    """
    iam_client = boto3.client('iam', region_name=region)
    
    try:
        print(f"📝 Creating inline policy: {policy_name}")
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"✅ Custom policy created and attached!")
        return policy_name
    except Exception as e:
        print(f"❌ Error creating custom policy: {e}")
        raise


def list_lambda_roles(region: str = "us-east-1") -> List[dict]:
    """
    List all IAM roles that can be assumed by Lambda.
    
    Args:
        region: AWS region (default: "us-east-1")
    
    Returns:
        List of role dictionaries with RoleName and Arn
    """
    iam_client = boto3.client('iam', region_name=region)
    
    try:
        response = iam_client.list_roles()
        lambda_roles = []
        
        for role in response['Roles']:
            # Check if Lambda can assume this role
            trust_policy = role['AssumeRolePolicyDocument']
            for statement in trust_policy.get('Statement', []):
                principal = statement.get('Principal', {})
                service = principal.get('Service', '')
                # Properly validate the service - must be exactly lambda.amazonaws.com or in a list
                service_str = str(service)
                if service_str == 'lambda.amazonaws.com' or (isinstance(service, list) and 'lambda.amazonaws.com' in service):
                    lambda_roles.append({
                        'RoleName': role['RoleName'],
                        'Arn': role['Arn']
                    })
                    break
        
        return lambda_roles
    except Exception as e:
        print(f"❌ Error listing roles: {e}")
        return []


def add_lambda_invoke_permission_to_customization_role(
    role_arn: str,
    lambda_function_arn: str,
    policy_name: str = "LambdaInvokePolicy",
    region: str = "us-east-1"
) -> str:
    """
    Add Lambda invoke permissions to a Bedrock customization role.
    
    This allows the customization role to invoke a specific Lambda function,
    which is useful for custom evaluation metrics or reward functions in model fine-tuning.
    
    Args:
        role_arn: ARN of the IAM role to update (e.g., "arn:aws:iam::123456789012:role/BedrockCustomizationRole")
        lambda_function_arn: ARN of the Lambda function to allow invocation
        policy_name: Name for the inline policy (default: "LambdaInvokePolicy")
        region: AWS region (default: "us-east-1")
    
    Returns:
        str: The name of the created policy
        
    Example:
        >>> add_lambda_invoke_permission_to_customization_role(
        ...     role_arn="arn:aws:iam::123456789012:role/BedrockCustomizationRole",
        ...     lambda_function_arn="arn:aws:lambda:us-east-1:123456789012:function:my-reward-function"
        ... )
    """
    iam_client = boto3.client('iam', region_name=region)
    
    # Extract role name from ARN
    # ARN format: arn:aws:iam::account-id:role/role-name
    role_name = role_arn.split('/')[-1]
    
    # Create policy document for Lambda invocation
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": lambda_function_arn
            }
        ]
    }
    
    try:
        print(f"📝 Adding Lambda invoke permission to customization role")
        print(f"   Role ARN: {role_arn}")
        print(f"   Lambda ARN: {lambda_function_arn}")
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"✅ Lambda invoke permission added successfully!")
        print(f"   Policy name: {policy_name}")
        return policy_name
        
    except Exception as e:
        print(f"❌ Error adding Lambda invoke permission: {e}")
        raise


def delete_lambda_role(role_name: str, region: str = "us-east-1") -> bool:
    """
    Delete an IAM role (detaches policies first).
    
    Args:
        role_name: Name of the IAM role to delete
        region: AWS region (default: "us-east-1")
    
    Returns:
        bool: True if deletion was successful
    """
    iam_client = boto3.client('iam', region_name=region)
    
    try:
        print(f"🗑️  Deleting role: {role_name}")
        
        # Detach all managed policies
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in response['AttachedPolicies']:
            print(f"  Detaching policy: {policy['PolicyArn']}")
            iam_client.detach_role_policy(
                RoleName=role_name,
                PolicyArn=policy['PolicyArn']
            )
        
        # Delete all inline policies
        response = iam_client.list_role_policies(RoleName=role_name)
        for policy_name in response['PolicyNames']:
            print(f"  Deleting inline policy: {policy_name}")
            iam_client.delete_role_policy(
                RoleName=role_name,
                PolicyName=policy_name
            )
        
        # Delete the role
        iam_client.delete_role(RoleName=role_name)
        print(f"✅ Role deleted successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error deleting role: {e}")
        return False


if __name__ == "__main__":
    import sys
    import time
    
    if len(sys.argv) < 2:
        print("Usage: python lambda_role_helper.py <role_name> [bedrock]")
        print("\nExamples:")
        print("  python lambda_role_helper.py my-lambda-role")
        print("  python lambda_role_helper.py my-lambda-role bedrock")
        print("\nThis will create a Lambda execution role and return its ARN.")
        sys.exit(1)
    
    role_name = sys.argv[1]
    add_bedrock = len(sys.argv) > 2 and sys.argv[2].lower() == "bedrock"
    
    try:
        # Create role with basic permissions
        policies = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
        
        if add_bedrock:
            policies.append("arn:aws:iam::aws:policy/AmazonBedrockFullAccess")
        
        role_arn = create_lambda_execution_role(
            role_name=role_name,
            managed_policies=policies
        )
        
        print(f"\n🎉 Success!")
        print(f"Role ARN: {role_arn}")
        print(f"\n⏳ Important: Wait 10-15 seconds before using this role with Lambda")
        print(f"   AWS needs time to propagate the role permissions.")
        
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        sys.exit(1)
