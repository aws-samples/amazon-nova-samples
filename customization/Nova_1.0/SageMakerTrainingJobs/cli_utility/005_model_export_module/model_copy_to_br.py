#!/usr/bin/env python3
"""
Bedrock Model Export and Provisioned Throughput Setup
Exports a custom model to Bedrock and sets up provisioned throughput

Example:
python3 model_copy_to_br.py -m my-model -s s3://my-bucket/model-path/ -a arn:aws:iam::123456789012:role/MyRole -p 2
"""

import boto3
import time
import argparse
import sys
from datetime import datetime

def clear_line():
    """Clear current line for status updates"""
    print('\r' + ' ' * 80 + '\r', end='', flush=True)

def create_provisioned_throughput(bedrock_client, model_arn, provisioned_units):
    """
    Create provisioned throughput for a Bedrock model
    
    Args:
        bedrock_client: Boto3 Bedrock client
        model_arn (str): ARN of the model
        provisioned_units (int): Number of provisioned throughput units
        
    Returns:
        str: ARN of the provisioned throughput model
    """
    try:
        response = bedrock_client.create_provisioned_model(
            modelId=model_arn,
            provisionedThroughput=provisioned_units
        )
        return response['provisionedModelArn']
    except Exception as e:
        print(f"\n❌ Failed to create provisioned throughput: {str(e)}")
        raise

def monitor_provisioned_model(bedrock_client, provisioned_model_arn, check_interval=10):
    """
    Monitor provisioned model status until it becomes Active
    
    Args:
        bedrock_client: Boto3 Bedrock client
        provisioned_model_arn (str): ARN of the provisioned model
        check_interval (int): Time in seconds between status checks
    """
    print(f"\n🔄 Monitoring provisioned model setup...")
    start_time = datetime.now()
    
    while True:
        try:
            response = bedrock_client.get_provisioned_model(
                provisionedModelArn=provisioned_model_arn
            )
            status = response['status']
            
            elapsed_time = datetime.now() - start_time
            elapsed_str = str(elapsed_time).split('.')[0]
            
            clear_line()
            print(f"📊 Provisioned Model Status: {status} | Elapsed: {elapsed_str}", end='', flush=True)
            
            if status.upper() == 'ACTIVE':
                print(f"\n\n✅ SUCCESS! Provisioned model is now ACTIVE!")
                print(f"🎉 Total provisioning time: {elapsed_str}")
                break
            elif status.upper() in ['FAILED', 'STOPPED']:
                print(f"\n\n❌ ERROR! Provisioned model status is: {status}")
                print("Please check the AWS console for more details.")
                sys.exit(1)
                
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"\n❌ Error checking provisioned model status: {str(e)}")
            raise

def monitor_model_status(model_name, s3_uri, role_arn, provisioned_units=None, region="us-east-1", check_interval=10):
    """
    Monitor Bedrock model status and set up provisioned throughput
    
    Args:
        model_name (str): Name of the model to monitor
        s3_uri (str): S3 URI where the model is stored
        role_arn (str): ARN of the IAM role for model creation
        provisioned_units (int): Number of provisioned throughput units (optional)
        region (str): AWS region
        check_interval (int): Time in seconds between status checks
    """
    
    try:
        # Initialize Bedrock client
        bedrock_client = boto3.Session().client(service_name="bedrock", region_name=region)
        
        # Model configuration
        model_tags = [{"key": "Environment", "value": "Production"}]
        request_token = f"model-request-{int(time.time())}"
        
        request_params = {
            "modelName": model_name,
            "modelSourceConfig": {
                "s3DataSource": {
                    "s3Uri": s3_uri
                }
            },
            "roleArn": role_arn,
            "modelTags": model_tags,
            "clientRequestToken": request_token
        }
        
        print(f"🚀 Creating and monitoring model: {model_name}")
        print(f"📦 S3 URI: {s3_uri}")
        print(f"🌍 Region: {region}")
        print("-" * 60)
        
        bedrock_client.create_custom_model(**request_params)
        
        model_found = False
        start_time = datetime.now()
        model_arn = None
        
        while True:
            try:
                model_summaries = bedrock_client.list_custom_models(
                    sortBy='CreationTime', 
                    sortOrder='Descending'
                )['modelSummaries']
                
                target_model = None
                for model in model_summaries:
                    if model['modelName'] == model_name:
                        target_model = model
                        model_found = True
                        model_arn = target_model.get('modelArn')
                        break
                
                if not model_found:
                    clear_line()
                    print(f"⏳ Model '{model_name}' not found yet... Waiting for creation to start", end='', flush=True)
                else:
                    current_status = target_model['modelStatus']
                    elapsed_time = datetime.now() - start_time
                    elapsed_str = str(elapsed_time).split('.')[0]
                    
                    clear_line()
                    print(f"📊 Status: {current_status} | Elapsed: {elapsed_str}", end='', flush=True)
                    
                    if current_status.upper() == 'ACTIVE':
                        print(f"\n\n✅ SUCCESS! Model '{model_name}' is now ACTIVE!")
                        print(f"🎉 Total time elapsed: {elapsed_str}")
                        print(f"🔗 Model ARN: {model_arn}")
                        
                        # Set up provisioned throughput if requested
                        if provisioned_units:
                            print(f"\n🔄 Setting up provisioned throughput with {provisioned_units} units...")
                            provisioned_model_arn = create_provisioned_throughput(
                                bedrock_client, 
                                model_arn, 
                                provisioned_units
                            )
                            monitor_provisioned_model(
                                bedrock_client,
                                provisioned_model_arn,
                                check_interval
                            )
                            print(f"🔗 Provisioned Model ARN: {provisioned_model_arn}")
                        
                        break
                    elif current_status.upper() in ['FAILED', 'STOPPED']:
                        print(f"\n\n❌ ERROR! Model '{model_name}' status is: {current_status}")
                        print("Please check the AWS console for more details.")
                        sys.exit(1)
                
            except Exception as e:
                clear_line()
                print(f"⚠️  Error checking status: {str(e)}", end='', flush=True)
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Monitoring stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n💥 Fatal error: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Export model to Bedrock and set up provisioned throughput",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python model_copy_to_br.py -m my-model -s s3://my-bucket/model-path/
  python model_copy_to_br.py -m my-model -s s3://my-bucket/model-path/ -r us-west-2
  python model_copy_to_br.py -m my-model -s s3://my-bucket/model-path/ -a arn:aws:iam::123456789012:role/MyRole -p 2
        """
    )
    
    parser.add_argument(
        '-m', '--model-name',
        required=True,
        help='Name of the Bedrock model to create'
    )
    
    parser.add_argument(
        '-s', '--s3-uri',
        required=True,
        help='S3 URI where the model is stored (e.g., s3://bucket/path/)'
    )
    
    parser.add_argument(
        '-a', '--role-arn',
        required=True,
        help='IAM role ARN for model creation'
    )
    
    parser.add_argument(
        '-p', '--provisioned-units',
        type=int,
        help='Number of provisioned throughput units to create (optional)'
    )
    
    parser.add_argument(
        '-r', '--region',
        default="us-east-1",
        help='AWS region (default: us-east-1)'
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=10,
        help='Check interval in seconds (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Validate S3 URI format
    if not args.s3_uri.startswith('s3://'):
        print("❌ Error: S3 URI must start with 's3://'")
        sys.exit(1)
    
    # Validate provisioned units if specified
    if args.provisioned_units is not None and args.provisioned_units < 1:
        print("❌ Error: Provisioned units must be greater than 0")
        sys.exit(1)
    
    # Start monitoring
    monitor_model_status(
        model_name=args.model_name,
        s3_uri=args.s3_uri,
        role_arn=args.role_arn,
        provisioned_units=args.provisioned_units,
        region=args.region,
        check_interval=args.interval
    )

if __name__ == "__main__":
    main()
