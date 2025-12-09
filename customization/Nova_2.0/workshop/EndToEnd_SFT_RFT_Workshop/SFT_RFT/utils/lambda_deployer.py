"""
AWS Lambda Deployment Utility

This module provides utilities to deploy Python scripts as AWS Lambda functions.
"""

import boto3
import zipfile
import io
import os
from pathlib import Path
from typing import Optional, Dict, Any
import json


def create_lambda_function(
    lambda_script_path: str,
    function_name: str,
    role_arn: str,
    handler: str = "lambda_function.lambda_handler",
    runtime: str = "python3.11",
    timeout: int = 300,
    memory_size: int = 512,
    environment_variables: Optional[Dict[str, str]] = None,
    layers: Optional[list] = None,
    description: str = "",
    region: str = "us-east-1",
    skip_if_exists: bool = False
) -> str:
    """
    Create or update an AWS Lambda function from a Python script.
    
    Args:
        lambda_script_path: Path to the Python script file (e.g., "lambda_function.py")
        function_name: Name for the Lambda function
        role_arn: IAM role ARN with Lambda execution permissions
        handler: Handler function in format "filename.function_name" (default: "lambda_function.lambda_handler")
        runtime: Python runtime version (default: "python3.11")
        timeout: Function timeout in seconds (default: 300)
        memory_size: Memory allocation in MB (default: 512)
        environment_variables: Dictionary of environment variables (optional)
        layers: List of Lambda layer ARNs (optional)
        description: Function description (optional)
        region: AWS region (default: "us-east-1")
    
    Returns:
        str: The ARN of the created/updated Lambda function
        
    Examples:
        >>> arn = create_lambda_function(
        ...     lambda_script_path="rft-lambda.py",
        ...     function_name="my-rft-evaluator",
        ...     role_arn="arn:aws:iam::123456789012:role/lambda-execution-role"
        ... )
        >>> print(f"Lambda ARN: {arn}")
    """
    # Validate inputs
    script_path = Path(lambda_script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"Lambda script not found: {lambda_script_path}")
    
    # Initialize boto3 Lambda client
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Determine the name to use in the zip file
        # If handler specifies a different filename, use that
        zip_filename = handler.split('.')[0] + '.py'
        
        # Add the main Lambda script
        zip_file.write(script_path, arcname=zip_filename)
        
        # Check if there's a requirements.txt in the same directory
        requirements_path = script_path.parent / "requirements.txt"
        if requirements_path.exists():
            print(f"📦 Found requirements.txt - Note: You may need to include dependencies as a Lambda layer")
    
    # Get ZIP file bytes
    zip_buffer.seek(0)
    zip_bytes = zip_buffer.read()
    
    # Prepare function configuration
    function_config = {
        'FunctionName': function_name,
        'Runtime': runtime,
        'Role': role_arn,
        'Handler': handler,
        'Code': {'ZipFile': zip_bytes},
        'Timeout': timeout,
        'MemorySize': memory_size,
    }
    
    if description:
        function_config['Description'] = description
    
    if environment_variables:
        function_config['Environment'] = {'Variables': environment_variables}
    
    if layers:
        function_config['Layers'] = layers
    
    try:
        # Try to create the function
        print(f"🚀 Creating Lambda function: {function_name}")
        response = lambda_client.create_function(**function_config)
        arn = response['FunctionArn']
        print(f"✅ Lambda function created successfully!")
        print(f"   ARN: {arn}")
        print(f"   Runtime: {runtime}")
        print(f"   Handler: {handler}")
        print(f"   Timeout: {timeout}s")
        print(f"   Memory: {memory_size}MB")
        
        return arn
        
    except lambda_client.exceptions.ResourceConflictException:
        # Function already exists
        if skip_if_exists:
            print(f"ℹ️  Function {function_name} already exists. Skipping update.")
            response = lambda_client.get_function(FunctionName=function_name)
            arn = response['Configuration']['FunctionArn']
            print(f"✅ Using existing Lambda: {arn}")
            return arn
        
        # Update the function
        print(f"♻️  Function {function_name} already exists. Updating...")
        
        # Update function code
        code_response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_bytes
        )
        
        # Update function configuration
        config_update = {
            'FunctionName': function_name,
            'Runtime': runtime,
            'Role': role_arn,
            'Handler': handler,
            'Timeout': timeout,
            'MemorySize': memory_size,
        }
        
        if description:
            config_update['Description'] = description
        
        if environment_variables:
            config_update['Environment'] = {'Variables': environment_variables}
        
        if layers:
            config_update['Layers'] = layers
        
        config_response = lambda_client.update_function_configuration(**config_update)
        
        arn = config_response['FunctionArn']
        print(f"✅ Lambda function updated successfully!")
        print(f"   ARN: {arn}")
        
        return arn
    
    except Exception as e:
        print(f"❌ Error creating/updating Lambda function: {e}")
        raise


def create_lambda_with_dependencies(
    lambda_script_path: str,
    function_name: str,
    role_arn: str,
    dependencies_dir: Optional[str] = None,
    **kwargs
) -> str:
    """
    Create Lambda function including a directory of dependencies.
    
    Args:
        lambda_script_path: Path to the Python script file
        function_name: Name for the Lambda function
        role_arn: IAM role ARN with Lambda execution permissions
        dependencies_dir: Path to directory containing dependencies (e.g., site-packages)
        **kwargs: Additional arguments passed to create_lambda_function
    
    Returns:
        str: The ARN of the created/updated Lambda function
    """
    script_path = Path(lambda_script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"Lambda script not found: {lambda_script_path}")
    
    # Initialize boto3 Lambda client
    region = kwargs.get('region', 'us-east-1')
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Create ZIP file in memory with dependencies
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Determine the name to use in the zip file
        handler = kwargs.get('handler', 'lambda_function.lambda_handler')
        zip_filename = handler.split('.')[0] + '.py'
        
        # Add the main Lambda script
        zip_file.write(script_path, arcname=zip_filename)
        
        # Add dependencies if directory is provided
        if dependencies_dir:
            dep_path = Path(dependencies_dir)
            if dep_path.exists() and dep_path.is_dir():
                print(f"📦 Including dependencies from: {dependencies_dir}")
                for root, dirs, files in os.walk(dep_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(dep_path)
                        zip_file.write(file_path, arcname=str(arcname))
    
    # Get ZIP file bytes
    zip_buffer.seek(0)
    zip_bytes = zip_buffer.read()
    
    # Prepare function configuration
    function_config = {
        'FunctionName': function_name,
        'Runtime': kwargs.get('runtime', 'python3.11'),
        'Role': role_arn,
        'Handler': kwargs.get('handler', 'lambda_function.lambda_handler'),
        'Code': {'ZipFile': zip_bytes},
        'Timeout': kwargs.get('timeout', 300),
        'MemorySize': kwargs.get('memory_size', 512),
    }
    
    if kwargs.get('description'):
        function_config['Description'] = kwargs['description']
    
    if kwargs.get('environment_variables'):
        function_config['Environment'] = {'Variables': kwargs['environment_variables']}
    
    if kwargs.get('layers'):
        function_config['Layers'] = kwargs['layers']
    
    try:
        print(f"🚀 Creating Lambda function with dependencies: {function_name}")
        response = lambda_client.create_function(**function_config)
        arn = response['FunctionArn']
        print(f"✅ Lambda function created successfully!")
        print(f"   ARN: {arn}")
        return arn
        
    except lambda_client.exceptions.ResourceConflictException:
        print(f"♻️  Function {function_name} already exists. Updating...")
        
        # Update function code
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_bytes
        )
        
        # Update configuration
        config_update = {k: v for k, v in function_config.items() if k != 'Code'}
        config_response = lambda_client.update_function_configuration(**config_update)
        
        arn = config_response['FunctionArn']
        print(f"✅ Lambda function updated successfully!")
        print(f"   ARN: {arn}")
        return arn
    
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


def delete_lambda_function(function_name: str, region: str = "us-east-1") -> bool:
    """
    Delete an AWS Lambda function.
    
    Args:
        function_name: Name of the Lambda function to delete
        region: AWS region (default: "us-east-1")
    
    Returns:
        bool: True if deletion was successful
    """
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        print(f"🗑️  Deleting Lambda function: {function_name}")
        lambda_client.delete_function(FunctionName=function_name)
        print(f"✅ Lambda function deleted successfully!")
        return True
    except Exception as e:
        print(f"❌ Error deleting Lambda function: {e}")
        return False


def get_lambda_info(function_name: str, region: str = "us-east-1") -> Dict[str, Any]:
    """
    Get information about an AWS Lambda function.
    
    Args:
        function_name: Name of the Lambda function
        region: AWS region (default: "us-east-1")
    
    Returns:
        dict: Lambda function configuration
    """
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        return response
    except Exception as e:
        print(f"❌ Error getting Lambda info: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python lambda_deployer.py <script_path> <function_name> <role_arn>")
        print("\nExample:")
        print("  python lambda_deployer.py rft-lambda.py my-rft-function arn:aws:iam::123456789012:role/lambda-role")
        sys.exit(1)
    
    script_path = sys.argv[1]
    function_name = sys.argv[2]
    role_arn = sys.argv[3]
    
    try:
        arn = create_lambda_function(
            lambda_script_path=script_path,
            function_name=function_name,
            role_arn=role_arn
        )
        print(f"\n🎉 Success! Lambda ARN: {arn}")
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        sys.exit(1)
