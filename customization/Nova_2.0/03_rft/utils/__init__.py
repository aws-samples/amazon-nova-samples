"""
Utils package for RFT data processing, S3 operations, and Lambda deployment.

This package provides utilities for:
- Converting Hugging Face datasets to RFT format with automatic train/val/test splitting
- Uploading files to Amazon S3 with progress tracking
- Deploying and managing AWS Lambda functions with layer support
- Creating and configuring IAM roles for Lambda execution
"""

from .parse_hf_to_rft import parse_hf_dataset, parse_and_split_dataset
from .s3_uploader import (
    upload_to_s3,
    upload_file_to_s3,
    upload_directory_to_s3,
    verify_s3_file_exists,
    get_s3_file_info,
    S3UploadError
)

from .lambda_deployer import (
    create_lambda_function,
    create_lambda_with_dependencies,
    delete_lambda_function,
    get_lambda_info,
    update_lambda_layers,
)

# Lambda Role Helper utilities
from .lambda_role_helper import (
    create_lambda_execution_role,
    get_or_create_lambda_role,
    add_bedrock_permissions_to_role,
    add_lambda_invoke_permission_to_customization_role,
    create_custom_policy_for_role,
    list_lambda_roles,
    delete_lambda_role,
)

__all__ = [
    # HF to RFT conversion
    'parse_hf_dataset',
    'parse_and_split_dataset',
    
    # S3 operations
    'upload_to_s3',
    'upload_file_to_s3',
    'upload_directory_to_s3',
    'verify_s3_file_exists',
    'get_s3_file_info',
    'S3UploadError',
    
    # Lambda deployment
    'create_lambda_function',
    'create_lambda_with_dependencies',
    'delete_lambda_function',
    'get_lambda_info',
    'update_lambda_layers',
    
    # Lambda role management
    'create_lambda_execution_role',
    'get_or_create_lambda_role',
    'add_bedrock_permissions_to_role',
    'add_lambda_invoke_permission_to_customization_role',
    'create_custom_policy_for_role',
    'list_lambda_roles',
    'delete_lambda_role',
]

__version__ = '1.0.0'
