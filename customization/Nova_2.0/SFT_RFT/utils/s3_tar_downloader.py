import boto3
import tarfile
import os
import tempfile
from typing import List, Optional


def download_and_unpack_s3_tar(
    bucket_name: str,
    s3_key: str,
    extract_to: Optional[str] = None,
    aws_region: str = 'us-east-1'
) -> List[str]:
    """
    Download a tar.gz file from S3, unpack it, and display its contents.
    
    Args:
        bucket_name (str): Name of the S3 bucket (can include or exclude 's3://' prefix)
        s3_key (str): Key/path of the tar.gz file in S3. Can be:
                     - Just the key: 'path/to/file.tar.gz'
                     - Full S3 URI: 's3://bucket/path/to/file.tar.gz'
                     - Key with bucket prefix: 'bucket/path/to/file.tar.gz'
        extract_to (str, optional): Directory to extract files to. If None, uses a temp directory
        aws_region (str): AWS region for the S3 bucket (default: 'us-east-1')
    
    Returns:
        List[str]: List of extracted file paths
    
    Example:
        >>> files = download_and_unpack_s3_tar(
        ...     bucket_name='my-bucket',
        ...     s3_key='data/archive.tar.gz',
        ...     extract_to='./extracted_data'
        ... )
        >>> print(f"Extracted {len(files)} files")
    """
    
    # Clean bucket_name - remove s3:// prefix if present
    bucket_name = bucket_name.replace("s3://", "").strip("/")
    
    # Clean s3_key - handle various formats
    s3_key = s3_key.strip()
    
    # If s3_key starts with s3://, parse it as full URI
    if s3_key.startswith("s3://"):
        # Extract bucket and key from full URI
        s3_key = s3_key.replace("s3://", "")
        if "/" in s3_key:
            _, s3_key = s3_key.split("/", 1)
    
    # If s3_key starts with bucket name, remove it
    if s3_key.startswith(bucket_name + "/"):
        s3_key = s3_key[len(bucket_name) + 1:]
    elif s3_key.startswith(bucket_name):
        s3_key = s3_key[len(bucket_name):].lstrip("/")
    
    # Remove leading slash if present
    s3_key = s3_key.lstrip("/")
    
    # Initialize S3 client
    s3_client = boto3.client('s3', region_name=aws_region)
    
    # Create temporary directory for download if extract_to is not specified
    if extract_to is None:
        extract_to = tempfile.mkdtemp(prefix='s3_tar_extract_')
        print(f"No extraction directory specified. Using temporary directory: {extract_to}")
    else:
        # Create extraction directory if it doesn't exist
        os.makedirs(extract_to, exist_ok=True)
    
    # Download the tar.gz file to a temporary location
    with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
        tmp_filepath = tmp_file.name
        
        try:
            print(f"Downloading s3://{bucket_name}/{s3_key}...")
            s3_client.download_file(bucket_name, s3_key, tmp_filepath)
            file_size = os.path.getsize(tmp_filepath)
            print(f"Downloaded {file_size:,} bytes")
            
            # Extract the tar.gz file
            print(f"\nExtracting to: {extract_to}")
            extracted_files = []
            
            with tarfile.open(tmp_filepath, 'r:gz') as tar:
                # Get list of members
                members = tar.getmembers()
                print(f"Found {len(members)} items in archive\n")
                
                # Extract all files
                tar.extractall(path=extract_to)
                
                # Display contents
                print("=" * 80)
                print("ARCHIVE CONTENTS:")
                print("=" * 80)
                
                for member in members:
                    # Determine item type
                    if member.isdir():
                        item_type = "DIR "
                    elif member.isfile():
                        item_type = "FILE"
                    elif member.issym():
                        item_type = "LINK"
                    else:
                        item_type = "OTHER"
                    
                    # Format size
                    size_str = f"{member.size:>12,}" if member.isfile() else " " * 12
                    
                    # Full extracted path
                    extracted_path = os.path.join(extract_to, member.name)
                    extracted_files.append(extracted_path)
                    
                    # Display information
                    print(f"[{item_type}] {size_str} bytes  {member.name}")
                
                print("=" * 80)
                print(f"\nTotal items extracted: {len(extracted_files)}")
                print(f"Extraction directory: {extract_to}")
                
            return extracted_files
            
        except Exception as e:
            print(f"Error: {e}")
            raise
            
        finally:
            # Clean up the temporary tar.gz file
            if os.path.exists(tmp_filepath):
                os.remove(tmp_filepath)
                print(f"\nCleaned up temporary file: {tmp_filepath}")


def list_directory_tree(directory: str, prefix: str = "", max_depth: int = 3, current_depth: int = 0):
    """
    Display a tree view of the extracted directory.
    
    Args:
        directory (str): Directory path to display
        prefix (str): Prefix for tree formatting
        max_depth (int): Maximum depth to traverse
        current_depth (int): Current depth level
    """
    if current_depth >= max_depth:
        return
    
    try:
        entries = sorted(os.listdir(directory))
        
        for i, entry in enumerate(entries):
            path = os.path.join(directory, entry)
            is_last = i == len(entries) - 1
            
            # Tree characters
            connector = "└── " if is_last else "├── "
            
            if os.path.isdir(path):
                print(f"{prefix}{connector}{entry}/")
                # Recursive call for subdirectories
                extension = "    " if is_last else "│   "
                list_directory_tree(path, prefix + extension, max_depth, current_depth + 1)
            else:
                size = os.path.getsize(path)
                print(f"{prefix}{connector}{entry} ({size:,} bytes)")
                
    except PermissionError:
        print(f"{prefix}[Permission Denied]")
