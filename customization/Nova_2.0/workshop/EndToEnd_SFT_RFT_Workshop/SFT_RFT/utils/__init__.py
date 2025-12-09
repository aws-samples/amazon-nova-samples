"""
Utils package for code_talk_final

This package provides utilities for:
- Data formatting and transformation (RFT formatter)
- AWS Lambda deployment
- IAM role management for Lambda functions
"""

# RFT Formatter utilities
from .rft_formatter import (
    # Main function
    convert_sft_to_rft,
    
    # Individual utilities
    transform_single_record,
    flatten_message_content,
    extract_reference_answer,
    process_jsonl_file,
    
    # Backward compatibility (old names)
    data_sft_rft,
    transform_sft_to_rft,
    flatten_content,
    parse_assistant_response,
)

# Lambda Deployer utilities
from .lambda_deployer import (
    create_lambda_function,
    create_lambda_with_dependencies,
    delete_lambda_function,
    get_lambda_info,
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

# S3 Uploader utilities
from .s3_uploader import (
    upload_file_to_s3,
    upload_directory_to_s3,
    download_file_from_s3,
    check_s3_file_exists,
    get_s3_uri,
)

# S3 Tar Downloader utilities
from .s3_tar_downloader import (
    download_and_unpack_s3_tar,
    list_directory_tree,
)

# Plot Training Metrics utilities
from .plot_training_metrics import (
    plot_step_wise_training_metrics,
    plot_training_metrics_combined,
)

__all__ = [
    # RFT Formatter
    'convert_sft_to_rft',
    'transform_single_record',
    'flatten_message_content',
    'extract_reference_answer',
    'process_jsonl_file',
    'data_sft_rft',
    'transform_sft_to_rft',
    'flatten_content',
    'parse_assistant_response',
    
    # Lambda Deployer
    'create_lambda_function',
    'create_lambda_with_dependencies',
    'delete_lambda_function',
    'get_lambda_info',
    
    # Lambda Role Helper
    'create_lambda_execution_role',
    'get_or_create_lambda_role',
    'add_bedrock_permissions_to_role',
    'add_lambda_invoke_permission_to_customization_role',
    'create_custom_policy_for_role',
    'list_lambda_roles',
    'delete_lambda_role',
    
    # S3 Uploader
    'upload_file_to_s3',
    'upload_directory_to_s3',
    'download_file_from_s3',
    'check_s3_file_exists',
    'get_s3_uri',
    
    # S3 Tar Downloader
    'download_and_unpack_s3_tar',
    'list_directory_tree',
    
    # Plot Training Metrics
    'plot_step_wise_training_metrics',
    'plot_training_metrics_combined',
]
