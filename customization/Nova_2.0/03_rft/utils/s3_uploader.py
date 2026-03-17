#!/usr/bin/env python3
"""
S3 Uploader utility for uploading files to Amazon S3.

This module provides functions to upload files to S3 buckets with progress tracking
and error handling.

Usage:
    from utils.s3_uploader import upload_to_s3, upload_file_to_s3
    
    # Simple upload
    upload_file_to_s3('local_file.jsonl', 'my-bucket', 's3/path/file.jsonl')
    
    # Upload with custom configuration
    upload_to_s3(
        file_path='local_file.jsonl',
        bucket_name='my-bucket',
        s3_key='data/file.jsonl',
        region='us-east-1'
    )
"""

import boto3
import os
from pathlib import Path
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError


class S3UploadError(Exception):
    """Custom exception for S3 upload errors."""
    pass


def upload_file_to_s3(
    file_path: str,
    bucket_name: str,
    s3_key: str,
    region: Optional[str] = None,
    extra_args: Optional[Dict[str, Any]] = None,
    show_progress: bool = True
) -> str:
    """
    Upload a file to an S3 bucket.
    
    Args:
        file_path: Local path to the file to upload
        bucket_name: Name of the S3 bucket
        s3_key: S3 object key (path within the bucket)
        region: AWS region (optional, uses default from AWS config if not specified)
        extra_args: Extra arguments to pass to S3 upload (e.g., {'ACL': 'public-read'})
        show_progress: Whether to show upload progress (default: True)
        
    Returns:
        S3 URI of the uploaded file (s3://bucket/key)
        
    Raises:
        S3UploadError: If upload fails
        FileNotFoundError: If local file doesn't exist
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file size for progress tracking
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    
    print(f"Preparing to upload: {file_name}")
    print(f"File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
    print(f"Destination: s3://{bucket_name}/{s3_key}")
    
    try:
        # Create S3 client
        if region:
            s3_client = boto3.client('s3', region_name=region)
        else:
            s3_client = boto3.client('s3')
        
        # Upload with progress callback if requested
        if show_progress:
            uploaded_bytes = [0]
            
            def progress_callback(bytes_amount):
                uploaded_bytes[0] += bytes_amount
                percentage = (uploaded_bytes[0] / file_size) * 100
                print(f"\rUploading: {percentage:.1f}% ({uploaded_bytes[0]:,} / {file_size:,} bytes)", end='')
            
            s3_client.upload_file(
                file_path,
                bucket_name,
                s3_key,
                ExtraArgs=extra_args,
                Callback=progress_callback
            )
            print()  # New line after progress
        else:
            s3_client.upload_file(
                file_path,
                bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
        
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        print(f"✓ Successfully uploaded to: {s3_uri}")
        return s3_uri
        
    except NoCredentialsError:
        raise S3UploadError(
            "AWS credentials not found. Please configure AWS credentials using:\n"
            "  - AWS CLI: aws configure\n"
            "  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
            "  - IAM role (if running on EC2/ECS)"
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise S3UploadError(f"AWS S3 error ({error_code}): {error_message}")
    except Exception as e:
        raise S3UploadError(f"Unexpected error during upload: {str(e)}")


def upload_to_s3(
    file_path: str,
    bucket_name: str,
    s3_key: Optional[str] = None,
    region: Optional[str] = None,
    public_read: bool = False,
    metadata: Optional[Dict[str, str]] = None,
    show_progress: bool = True
) -> str:
    """
    Upload a file to S3 with additional options.
    
    Args:
        file_path: Local path to the file to upload
        bucket_name: Name of the S3 bucket
        s3_key: S3 object key (optional, uses filename if not specified)
        region: AWS region (optional)
        public_read: Whether to make the file publicly readable (default: False)
        metadata: Custom metadata to attach to the S3 object
        show_progress: Whether to show upload progress (default: True)
        
    Returns:
        S3 URI of the uploaded file
    """
    # Use filename as s3_key if not provided
    if s3_key is None:
        s3_key = os.path.basename(file_path)
    
    # Build extra args
    extra_args = {}
    if public_read:
        extra_args['ACL'] = 'public-read'
    if metadata:
        extra_args['Metadata'] = metadata
    
    return upload_file_to_s3(
        file_path=file_path,
        bucket_name=bucket_name,
        s3_key=s3_key,
        region=region,
        extra_args=extra_args if extra_args else None,
        show_progress=show_progress
    )


def upload_directory_to_s3(
    directory_path: str,
    bucket_name: str,
    s3_prefix: str = '',
    region: Optional[str] = None,
    file_pattern: str = '*',
    show_progress: bool = True
) -> list:
    """
    Upload all files from a directory to S3.
    
    Args:
        directory_path: Local directory path
        bucket_name: Name of the S3 bucket
        s3_prefix: Prefix for S3 keys (like a folder path)
        region: AWS region (optional)
        file_pattern: Glob pattern to filter files (default: '*' for all files)
        show_progress: Whether to show upload progress
        
    Returns:
        List of S3 URIs for uploaded files
    """
    directory = Path(directory_path)
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"Directory not found: {directory_path}")
    
    uploaded_files = []
    files_to_upload = list(directory.glob(file_pattern))
    
    print(f"Found {len(files_to_upload)} files to upload")
    
    for idx, file_path in enumerate(files_to_upload, 1):
        if file_path.is_file():
            # Construct S3 key preserving directory structure
            relative_path = file_path.relative_to(directory)
            s3_key = f"{s3_prefix}/{relative_path}".lstrip('/')
            
            print(f"\n[{idx}/{len(files_to_upload)}] Uploading {file_path.name}")
            
            try:
                s3_uri = upload_file_to_s3(
                    str(file_path),
                    bucket_name,
                    s3_key,
                    region=region,
                    show_progress=show_progress
                )
                uploaded_files.append(s3_uri)
            except Exception as e:
                print(f"✗ Failed to upload {file_path.name}: {e}")
    
    print(f"\n{'='*80}")
    print(f"Upload complete: {len(uploaded_files)}/{len(files_to_upload)} files uploaded successfully")
    print(f"{'='*80}")
    
    return uploaded_files


def verify_s3_file_exists(bucket_name: str, s3_key: str, region: Optional[str] = None) -> bool:
    """
    Check if a file exists in S3.
    
    Args:
        bucket_name: Name of the S3 bucket
        s3_key: S3 object key
        region: AWS region (optional)
        
    Returns:
        True if file exists, False otherwise
    """
    try:
        if region:
            s3_client = boto3.client('s3', region_name=region)
        else:
            s3_client = boto3.client('s3')
        
        s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        return True
    except ClientError:
        return False


def get_s3_file_info(bucket_name: str, s3_key: str, region: Optional[str] = None) -> Dict[str, Any]:
    """
    Get information about an S3 object.
    
    Args:
        bucket_name: Name of the S3 bucket
        s3_key: S3 object key
        region: AWS region (optional)
        
    Returns:
        Dictionary with file information (size, last_modified, etc.)
    """
    try:
        if region:
            s3_client = boto3.client('s3', region_name=region)
        else:
            s3_client = boto3.client('s3')
        
        response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        
        return {
            'size': response['ContentLength'],
            'last_modified': response['LastModified'],
            'etag': response['ETag'],
            'content_type': response.get('ContentType', 'unknown'),
            's3_uri': f"s3://{bucket_name}/{s3_key}"
        }
    except ClientError as e:
        raise S3UploadError(f"Failed to get file info: {e}")


def main():
    """
    Main function for CLI usage examples.
    """
    print("S3 Uploader Utility")
    print("=" * 80)
    print("\nThis utility provides functions to upload files to Amazon S3.")
    print("\nExample usage:")
    print("""
from utils.s3_uploader import upload_to_s3

# Upload a file
s3_uri = upload_to_s3(
    file_path='my_data.jsonl',
    bucket_name='my-bucket',
    s3_key='data/my_data.jsonl',
    region='us-east-1'
)

print(f"Uploaded to: {s3_uri}")
    """)


if __name__ == "__main__":
    main()
