"""
S3 Upload Utility

This module provides utilities to upload files to Amazon S3.
"""

import boto3
from pathlib import Path
from typing import Optional
from botocore.exceptions import ClientError


def upload_file_to_s3(
    local_file_path: str,
    bucket_name: str,
    s3_key: str,
    region: str = "us-east-1",
    extra_args: Optional[dict] = None
) -> str:
    """
    Upload a file from local filesystem to S3 and return the S3 URI.
    
    Args:
        local_file_path: Path to the local file to upload
        bucket_name: Name of the S3 bucket
        s3_key: The S3 key (path) where the file will be stored
                (e.g., "data/training/file.jsonl")
        region: AWS region (default: "us-east-1")
        extra_args: Optional dict of extra arguments for the upload
                   (e.g., {'ContentType': 'application/json'})
    
    Returns:
        str: The S3 URI of the uploaded file (s3://bucket-name/path/to/file)
        
    Examples:
        >>> s3_uri = upload_file_to_s3(
        ...     local_file_path="data/train.jsonl",
        ...     bucket_name="my-training-bucket",
        ...     s3_key="datasets/train.jsonl"
        ... )
        >>> print(s3_uri)
        s3://my-training-bucket/datasets/train.jsonl
        
        >>> # Upload to a nested path
        >>> s3_uri = upload_file_to_s3(
        ...     local_file_path="model/config.yaml",
        ...     bucket_name="my-training-bucket",
        ...     s3_key="experiments/exp-001/config.yaml"
        ... )
    """
    # Validate local file exists
    local_path = Path(local_file_path)
    if not local_path.exists():
        raise FileNotFoundError(f"Local file not found: {local_file_path}")
    
    # Initialize S3 client
    s3_client = boto3.client('s3', region_name=region)
    
    try:
        # Get file size for progress
        file_size = local_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"📤 Uploading file to S3...")
        print(f"   Local: {local_file_path}")
        print(f"   Size: {file_size_mb:.2f} MB")
        print(f"   Bucket: {bucket_name}")
        print(f"   S3 Key: {s3_key}")
        
        # Upload file
        s3_client.upload_file(
            Filename=str(local_path),
            Bucket=bucket_name,
            Key=s3_key,
            ExtraArgs=extra_args
        )
        
        # Construct S3 URI
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        
        print(f"✅ Upload successful!")
        print(f"   S3 URI: {s3_uri}")
        
        return s3_uri
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"❌ Error: Bucket '{bucket_name}' does not exist")
        elif error_code == 'AccessDenied':
            print(f"❌ Error: Access denied to bucket '{bucket_name}'")
        else:
            print(f"❌ Error uploading file: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


def upload_directory_to_s3(
    local_dir_path: str,
    bucket_name: str,
    s3_prefix: str = "",
    region: str = "us-east-1"
) -> list:
    """
    Upload an entire directory to S3 recursively.
    
    Args:
        local_dir_path: Path to the local directory to upload
        bucket_name: Name of the S3 bucket
        s3_prefix: Prefix (folder path) in S3 where files will be uploaded
        region: AWS region (default: "us-east-1")
    
    Returns:
        list: List of S3 URIs for all uploaded files
        
    Example:
        >>> s3_uris = upload_directory_to_s3(
        ...     local_dir_path="data/final/RFT",
        ...     bucket_name="my-training-bucket",
        ...     s3_prefix="training-data/rft"
        ... )
    """
    local_path = Path(local_dir_path)
    if not local_path.exists() or not local_path.is_dir():
        raise ValueError(f"Local directory not found: {local_dir_path}")
    
    s3_client = boto3.client('s3', region_name=region)
    uploaded_uris = []
    
    print(f"📤 Uploading directory to S3...")
    print(f"   Local: {local_dir_path}")
    print(f"   Bucket: {bucket_name}")
    print(f"   Prefix: {s3_prefix}")
    
    # Walk through directory
    for file_path in local_path.rglob('*'):
        if file_path.is_file():
            # Calculate relative path
            relative_path = file_path.relative_to(local_path)
            
            # Construct S3 key
            if s3_prefix:
                s3_key = f"{s3_prefix}/{relative_path}".replace('\\', '/')
            else:
                s3_key = str(relative_path).replace('\\', '/')
            
            try:
                # Upload file
                s3_client.upload_file(
                    Filename=str(file_path),
                    Bucket=bucket_name,
                    Key=s3_key
                )
                
                s3_uri = f"s3://{bucket_name}/{s3_key}"
                uploaded_uris.append(s3_uri)
                print(f"  ✓ {relative_path} → {s3_key}")
                
            except Exception as e:
                print(f"  ✗ Error uploading {relative_path}: {e}")
    
    print(f"✅ Uploaded {len(uploaded_uris)} files")
    return uploaded_uris


def check_s3_file_exists(
    bucket_name: str,
    s3_key: str,
    region: str = "us-east-1"
) -> bool:
    """
    Check if a file exists in S3.
    
    Args:
        bucket_name: Name of the S3 bucket
        s3_key: The S3 key to check
        region: AWS region (default: "us-east-1")
    
    Returns:
        bool: True if file exists, False otherwise
    """
    s3_client = boto3.client('s3', region_name=region)
    
    try:
        s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise


def get_s3_uri(bucket_name: str, s3_key: str) -> str:
    """
    Construct an S3 URI from bucket name and key.
    
    Args:
        bucket_name: Name of the S3 bucket
        s3_key: The S3 key (path)
    
    Returns:
        str: The S3 URI
        
    Example:
        >>> uri = get_s3_uri("my-bucket", "data/file.json")
        >>> print(uri)
        s3://my-bucket/data/file.json
    """
    return f"s3://{bucket_name}/{s3_key}"


def download_file_from_s3(
    bucket_name: str,
    s3_key: str,
    local_file_path: str,
    region: str = "us-east-1"
) -> str:
    """
    Download a file from S3 to local filesystem.
    
    Args:
        bucket_name: Name of the S3 bucket
        s3_key: The S3 key (path) of the file to download
        local_file_path: Path where the file will be saved locally
        region: AWS region (default: "us-east-1")
    
    Returns:
        str: Path to the downloaded file
        
    Example:
        >>> local_path = download_file_from_s3(
        ...     bucket_name="my-bucket",
        ...     s3_key="data/file.json",
        ...     local_file_path="downloads/file.json"
        ... )
    """
    s3_client = boto3.client('s3', region_name=region)
    
    # Create parent directories if needed
    local_path = Path(local_file_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        print(f"📥 Downloading from S3...")
        print(f"   S3: s3://{bucket_name}/{s3_key}")
        print(f"   Local: {local_file_path}")
        
        s3_client.download_file(
            Bucket=bucket_name,
            Key=s3_key,
            Filename=str(local_path)
        )
        
        print(f"✅ Download successful!")
        return str(local_path)
        
    except Exception as e:
        print(f"❌ Error downloading file: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python s3_uploader.py <local_file> <bucket_name> <s3_key>")
        print("\nExample:")
        print("  python s3_uploader.py data/train.jsonl my-bucket datasets/train.jsonl")
        sys.exit(1)
    
    local_file = sys.argv[1]
    bucket = sys.argv[2]
    key = sys.argv[3]
    
    try:
        s3_uri = upload_file_to_s3(
            local_file_path=local_file,
            bucket_name=bucket,
            s3_key=key
        )
        print(f"\n🎉 Success! S3 URI: {s3_uri}")
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        sys.exit(1)
