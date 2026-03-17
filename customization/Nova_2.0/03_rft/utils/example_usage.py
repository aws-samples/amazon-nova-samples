#!/usr/bin/env python3
"""
Example usage of parse_hf_to_rft.py and s3_uploader.py

This example demonstrates how to:
1. Convert a Hugging Face dataset to RFT format
2. Upload the converted data to Amazon S3
"""

from datasets import load_dataset
from utils import parse_hf_dataset, upload_to_s3, upload_file_to_s3


# Example 1: Basic usage - Convert HF dataset to RFT format
def example_basic_conversion():
    """
    Basic example: Load a dataset and convert to RFT format
    """
    print("Example 1: Basic HF to RFT Conversion")
    print("-" * 80)
    
    # Load your Hugging Face dataset
    # Replace 'your-dataset-name' with the actual dataset identifier
    dataset = load_dataset('your-dataset-name')
    
    # Convert to RFT format
    parse_hf_dataset(
        dataset=dataset,
        output_file='output_train.jsonl',
        split='train'
    )
    
    print("\n")


# Example 2: Basic S3 upload
def example_basic_s3_upload():
    """
    Basic example: Upload a file to S3
    """
    print("Example 2: Basic S3 Upload")
    print("-" * 80)
    
    # Upload a file to S3
    s3_uri = upload_to_s3(
        file_path='rft_data.jsonl',
        bucket_name='my-training-bucket',
        s3_key='datasets/rft_data.jsonl',
        region='us-east-1'
    )
    
    print(f"\nFile available at: {s3_uri}")
    print("\n")


# Example 3: Complete workflow - HF to RFT to S3
def example_complete_workflow():
    """
    Complete workflow: Load dataset, convert to RFT, and upload to S3
    """
    print("Example 3: Complete Workflow (HF → RFT → S3)")
    print("-" * 80)
    
    # Step 1: Load dataset
    print("\nStep 1: Loading dataset...")
    dataset = load_dataset('your-dataset-name')
    print(f"Dataset loaded with {len(dataset['train'])} training examples")
    
    # Step 2: Convert to RFT format
    print("\nStep 2: Converting to RFT format...")
    output_file = 'rft_training_data.jsonl'
    parse_hf_dataset(
        dataset=dataset,
        output_file=output_file,
        split='train'
    )
    
    # Step 3: Upload to S3
    print("\nStep 3: Uploading to S3...")
    s3_uri = upload_to_s3(
        file_path=output_file,
        bucket_name='my-training-bucket',
        s3_key='rft-datasets/training_data.jsonl',
        region='us-east-1',
        metadata={
            'dataset': 'your-dataset-name',
            'split': 'train',
            'format': 'rft'
        }
    )
    
    print(f"\n✓ Complete! Data available at: {s3_uri}")
    print("\n")


# Example 4: Processing multiple splits and uploading to S3
def example_multiple_splits_to_s3():
    """
    Example: Process train, validation, and test splits, then upload all to S3
    """
    print("Example 4: Multiple Splits → S3")
    print("-" * 80)
    
    # Load dataset
    dataset = load_dataset('your-dataset-name')
    bucket_name = 'my-training-bucket'
    s3_prefix = 'rft-datasets'
    
    uploaded_files = []
    
    # Process each split
    for split_name in ['train', 'validation', 'test']:
        if split_name in dataset:
            print(f"\nProcessing {split_name} split...")
            
            # Convert to RFT
            output_file = f'rft_{split_name}.jsonl'
            parse_hf_dataset(
                dataset=dataset,
                output_file=output_file,
                split=split_name
            )
            
            # Upload to S3
            s3_uri = upload_to_s3(
                file_path=output_file,
                bucket_name=bucket_name,
                s3_key=f'{s3_prefix}/{output_file}',
                region='us-east-1'
            )
            
            uploaded_files.append(s3_uri)
            print(f"✓ {split_name} uploaded to: {s3_uri}")
    
    print("\n" + "="*80)
    print(f"All splits uploaded successfully ({len(uploaded_files)} files)")
    print("="*80)
    print("\n")


# Example 5: Upload with custom S3 options
def example_advanced_s3_upload():
    """
    Example: Upload with custom options (public access, metadata)
    """
    print("Example 5: Advanced S3 Upload Options")
    print("-" * 80)
    
    # Upload with custom options
    s3_uri = upload_to_s3(
        file_path='rft_data.jsonl',
        bucket_name='my-training-bucket',
        s3_key='public-datasets/rft_data.jsonl',
        region='us-east-1',
        public_read=True,  # Make publicly accessible
        metadata={
            'source': 'huggingface',
            'format': 'rft',
            'version': '1.0',
            'created_by': 'data-pipeline'
        }
    )
    
    print(f"\nFile uploaded with public access: {s3_uri}")
    print("\n")


# Example 6: Using upload_file_to_s3 directly for more control
def example_direct_s3_upload():
    """
    Example: Using upload_file_to_s3 for fine-grained control
    """
    print("Example 6: Direct S3 Upload with Extra Arguments")
    print("-" * 80)
    
    from utils.s3_uploader import upload_file_to_s3
    
    # Upload with specific ACL and storage class
    s3_uri = upload_file_to_s3(
        file_path='rft_data.jsonl',
        bucket_name='my-training-bucket',
        s3_key='archive/rft_data.jsonl',
        region='us-east-1',
        extra_args={
            'StorageClass': 'STANDARD_IA',  # Infrequent Access
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'data-type': 'training',
                'compressed': 'false'
            }
        }
    )
    
    print(f"\nFile uploaded with custom configuration: {s3_uri}")
    print("\n")


# Example 7: Verify upload and get file info
def example_verify_upload():
    """
    Example: Verify file was uploaded and get its information
    """
    print("Example 7: Verify Upload and Get File Info")
    print("-" * 80)
    
    from utils import verify_s3_file_exists, get_s3_file_info
    
    bucket_name = 'my-training-bucket'
    s3_key = 'datasets/rft_data.jsonl'
    
    # Check if file exists
    exists = verify_s3_file_exists(bucket_name, s3_key)
    print(f"File exists in S3: {exists}")
    
    if exists:
        # Get file information
        info = get_s3_file_info(bucket_name, s3_key)
        print(f"\nFile Information:")
        print(f"  URI: {info['s3_uri']}")
        print(f"  Size: {info['size']:,} bytes ({info['size']/(1024*1024):.2f} MB)")
        print(f"  Last Modified: {info['last_modified']}")
        print(f"  Content Type: {info['content_type']}")
        print(f"  ETag: {info['etag']}")
    
    print("\n")


# Example 8: Complete pipeline with error handling
def example_production_pipeline():
    """
    Example: Production-ready pipeline with error handling
    """
    print("Example 8: Production Pipeline with Error Handling")
    print("-" * 80)
    
    try:
        # Configuration
        dataset_name = 'your-dataset-name'
        bucket_name = 'my-training-bucket'
        region = 'us-east-1'
        
        print(f"\n1. Loading dataset: {dataset_name}")
        dataset = load_dataset(dataset_name)
        
        print(f"\n2. Converting to RFT format...")
        output_file = 'rft_training_data.jsonl'
        parse_hf_dataset(dataset, output_file, split='train')
        
        print(f"\n3. Uploading to S3...")
        s3_uri = upload_to_s3(
            file_path=output_file,
            bucket_name=bucket_name,
            s3_key=f'rft-datasets/{dataset_name}/train.jsonl',
            region=region,
            metadata={'source': dataset_name}
        )
        
        print(f"\n4. Verifying upload...")
        from utils import verify_s3_file_exists
        if verify_s3_file_exists(bucket_name, f'rft-datasets/{dataset_name}/train.jsonl', region):
            print("✓ Upload verified successfully!")
        
        print(f"\n{'='*80}")
        print("Pipeline completed successfully!")
        print(f"Data location: {s3_uri}")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n✗ Error in pipeline: {e}")
        print("\nTroubleshooting:")
        print("1. Check AWS credentials: aws sts get-caller-identity")
        print("2. Verify bucket exists and you have write permissions")
        print("3. Check dataset name is correct")
    
    print("\n")


if __name__ == "__main__":
    print("=" * 80)
    print("Utils Package Usage Examples")
    print("=" * 80)
    print("\n")
    
    # Run examples (uncomment the ones you want to try)
    
    # example_basic_conversion()
    # example_basic_s3_upload()
    # example_complete_workflow()
    # example_multiple_splits_to_s3()
    # example_advanced_s3_upload()
    # example_direct_s3_upload()
    # example_verify_upload()
    # example_production_pipeline()
    
    # Quick Start Guide
    print("\n" + "=" * 80)
    print("Quick Start Guide")
    print("=" * 80)
    print("""
# 1. Convert HF dataset to RFT format
from datasets import load_dataset
from utils import parse_hf_dataset

ds = load_dataset('your-dataset-name')
parse_hf_dataset(ds, 'rft_data.jsonl', split='train')

# 2. Upload to S3
from utils import upload_to_s3

s3_uri = upload_to_s3(
    file_path='rft_data.jsonl',
    bucket_name='my-bucket',
    s3_key='datasets/rft_data.jsonl',
    region='us-east-1'
)

print(f"Uploaded to: {s3_uri}")

# 3. Complete pipeline
from datasets import load_dataset
from utils import parse_hf_dataset, upload_to_s3

# Load and convert
ds = load_dataset('your-dataset-name')
parse_hf_dataset(ds, 'output.jsonl', split='train')

# Upload to S3
s3_uri = upload_to_s3('output.jsonl', 'my-bucket', 'data/output.jsonl')
print(f"Available at: {s3_uri}")
    """)
