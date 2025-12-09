#!/usr/bin/env python3
"""
Nova Custom Model Inferencer

This script processes a JSONL file containing image references in S3 and sends them to the
Amazon Bedrock Nova model for analysis. It includes robust error handling, retry logic,
and parallel processing capabilities.

Usage:
    python custom_model_inferencer.py --help
    python custom_model_inferencer.py infer --input test.jsonl --output results.jsonl --model-arn "arn:aws:bedrock:us-east-1:123456789012:provisioned-model/model-id"
    python custom_model_inferencer.py infer --input test.jsonl --output results.jsonl --model-id "us.amazon.nova-pro-v1:0"
"""

import argparse
import boto3
import json
import logging
import os
import sys
import time
import random
from typing import Dict, List, Any, Optional, Tuple
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('nova_inferencer.log')
    ]
)
logger = logging.getLogger('nova_inferencer')

# Constants
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
MAX_BACKOFF = 32  # seconds

# Model IDs
MODEL_IDS = {
    "nova-micro": "us.amazon.nova-micro-v1:0",
    "nova-lite": "us.amazon.nova-lite-v1:0",
    "nova-pro": "us.amazon.nova-pro-v1:0",
    "nova-premier": "us.amazon.nova-premier-v1:0"
}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Nova Custom Model Inferencer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run inference using a provisioned throughput ARN
  python custom_model_inferencer.py infer \\
    --input test.jsonl \\
    --output results.jsonl \\
    --model-arn "arn:aws:bedrock:us-east-1:123456789012:provisioned-model/model-id" \\
    --max-workers 5 \\
    --batch-size 20

  # Run inference using a standard model ID
  python custom_model_inferencer.py infer \\
    --input test.jsonl \\
    --output results.jsonl \\
    --model-id "nova-pro" \\
    --max-tokens 2048 \\
    --temperature 0.3

  # Validate a JSONL file
  python custom_model_inferencer.py validate \\
    --input test.jsonl
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Infer command
    infer_parser = subparsers.add_parser('infer', help='Run inference on a JSONL file')
    infer_parser.add_argument('--input', '-i', required=True, help='Input JSONL file path')
    infer_parser.add_argument('--output', '-o', required=True, help='Output JSONL file path')
    
    # Model selection (mutually exclusive group)
    model_group = infer_parser.add_mutually_exclusive_group(required=True)
    model_group.add_argument('--model-arn', help='ARN for provisioned throughput model')
    model_group.add_argument('--model-id', choices=list(MODEL_IDS.keys()) + ["custom"], 
                           help='Model ID (nova-micro, nova-lite, nova-pro, nova-premier, or custom)')
    infer_parser.add_argument('--custom-model-id', help='Custom model ID when --model-id=custom is specified')
    
    # AWS configuration
    infer_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    infer_parser.add_argument('--profile', help='AWS profile name to use')
    
    # Processing options
    infer_parser.add_argument('--max-workers', type=int, default=5, help='Maximum number of worker threads (default: 5)')
    infer_parser.add_argument('--retries', type=int, default=MAX_RETRIES, help=f'Maximum number of retries (default: {MAX_RETRIES})')
    infer_parser.add_argument('--batch-size', type=int, default=20, help='Number of entries to process before saving results (default: 20)')
    infer_parser.add_argument('--start-index', type=int, default=0, help='Start processing from this index (default: 0)')
    
    # Inference parameters
    infer_parser.add_argument('--max-tokens', type=int, default=2048, help='Maximum tokens for generation (default: 2048)')
    infer_parser.add_argument('--temperature', type=float, default=0.3, help='Temperature parameter (default: 0.3)')
    infer_parser.add_argument('--top-p', type=float, default=0.1, help='Top P parameter (default: 0.1)')
    
    # Debug options
    infer_parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a JSONL file')
    validate_parser.add_argument('--input', '-i', required=True, help='Input JSONL file path')
    
    # Version command
    version_parser = subparsers.add_parser('version', help='Show version information')
    
    return parser.parse_args()


def setup_boto3_client(region: str, profile: Optional[str] = None) -> boto3.client:
    """Set up the boto3 client with the appropriate credentials."""
    try:
        if profile:
            session = boto3.Session(profile_name=profile)
            client = session.client("bedrock-runtime", region_name=region)
        else:
            client = boto3.client("bedrock-runtime", region_name=region)
        return client
    except Exception as e:
        logger.error(f"Failed to set up boto3 client: {str(e)}")
        raise


def read_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Read data from a JSONL file."""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for i, line in enumerate(file):
                try:
                    if line.strip():
                        entry = json.loads(line)
                        data.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON at line {i+1}: {str(e)}")
        logger.info(f"Loaded {len(data)} entries from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise


def save_to_jsonl(data: List[Dict[str, Any]], output_file: str, mode: str = 'w') -> None:
    """Save data to a JSONL file, either in write mode or append mode."""
    try:
        with open(output_file, mode, encoding='utf-8') as file:
            for item in data:
                file.write(json.dumps(item, ensure_ascii=False) + '\n')
        logger.info(f"Saved {len(data)} entries to {output_file} in {mode} mode")
    except Exception as e:
        logger.error(f"Error saving to {output_file}: {str(e)}")
        # Save to a backup file in case the main file is inaccessible
        backup_file = f"{output_file}.backup.{int(time.time())}.jsonl"
        with open(backup_file, 'w', encoding='utf-8') as file:
            for item in data:
                file.write(json.dumps(item, ensure_ascii=False) + '\n')
        logger.info(f"Saved backup to {backup_file}")


def exponential_backoff(retry_number: int, jitter: bool = True) -> float:
    """Calculate the exponential backoff time with optional jitter."""
    backoff = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** retry_number))
    if jitter:
        backoff = backoff * (0.5 + random.random())
    return backoff


def call_nova(
    client: boto3.client,
    entry: Dict[str, Any],
    model_identifier: str,
    max_retries: int,
    max_tokens: int,
    temperature: float,
    top_p: float
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Call the Nova model with retry logic, returning both the original entry and the response.
    If the call fails after max_retries, returns the entry and None for the response.
    
    Args:
        client: boto3 client for bedrock-runtime
        entry: The input entry containing messages
        model_identifier: The model ID or ARN to use
        max_retries: Maximum number of retry attempts
        max_tokens: Maximum tokens to generate
        temperature: Temperature parameter for generation
        top_p: Top P parameter for generation
        
    Returns:
        Tuple of (original entry, model response or None if failed)
    """
    # Extract the system prompt and messages from the entry
    system_prompt = None
    if "system" in entry and entry["system"]:
        # Handle system prompt if present
        if isinstance(entry["system"], list) and len(entry["system"]) > 0:
            system_content = entry["system"][0].get("text", "") if entry["system"] else ""
            system_prompt = [{"text": system_content}]
        elif isinstance(entry["system"], str):
            system_prompt = [{"text": entry["system"]}]
    
    # Process messages
    messages = entry.get("messages", [])
    if not messages:
        logger.warning("No messages found in entry")
        return entry, None
    
    # Set up inference parameters
    inference_params = {
        "maxTokens": max_tokens,
        "topP": top_p,
        "temperature": temperature
    }
    
    # Prepare payload for API call
    payload = []
    payload.extend(messages)
    
    # Initialize retry counter
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # Make the API call to Nova model
            if system_prompt:
                model_response = client.converse(
                    modelId=model_identifier,
                    messages=payload,
                    system=system_prompt,
                    inferenceConfig=inference_params
                )
            else:
                model_response = client.converse(
                    modelId=model_identifier,
                    messages=payload,
                    inferenceConfig=inference_params
                )
            
            # Add the response to the original entry
            result = entry.copy()
            result["model_response"] = model_response
            
            # Extract and add the text response for convenience
            try:
                response_text = model_response["output"]["message"]["content"][0]["text"]
                result["response_text"] = response_text
            except (KeyError, IndexError) as e:
                logger.warning(f"Could not extract response text: {str(e)}")
                result["response_text"] = None
            
            return entry, result
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            # Check if this is a retriable error
            if error_code in ['ThrottlingException', 'ServiceUnavailableException', 
                              'InternalServerException', 'RequestTimeout']:
                
                retry_count += 1
                if retry_count <= max_retries:
                    backoff_time = exponential_backoff(retry_count - 1)
                    logger.warning(
                        f"Retriable error ({error_code}): {error_msg}. "
                        f"Retry {retry_count}/{max_retries} in {backoff_time:.2f}s"
                    )
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(
                        f"Max retries reached. Last error ({error_code}): {error_msg}"
                    )
            else:
                # Non-retriable error
                logger.error(f"Non-retriable error ({error_code}): {error_msg}")
                
            # Return the original entry and None to indicate failure
            return entry, None
        
        except Exception as e:
            # Handle unexpected exceptions
            logger.error(f"Unexpected error: {str(e)}")
            
            retry_count += 1
            if retry_count <= max_retries:
                backoff_time = exponential_backoff(retry_count - 1)
                logger.warning(
                    f"Unexpected error. Retry {retry_count}/{max_retries} in {backoff_time:.2f}s"
                )
                time.sleep(backoff_time)
                continue
            
            # Return the original entry and None to indicate failure
            return entry, None
    
    # This should never be reached, but just in case
    return entry, None


def process_batch(
    client: boto3.client,
    batch: List[Dict[str, Any]],
    model_identifier: str,
    max_retries: int,
    max_tokens: int,
    temperature: float,
    top_p: float,
    max_workers: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Process a batch of entries in parallel."""
    results = []
    failures = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_entry = {
            executor.submit(
                call_nova, client, entry, model_identifier, max_retries, max_tokens, temperature, top_p
            ): entry for entry in batch
        }
        
        for future in as_completed(future_to_entry):
            entry, result = future.result()
            if result:
                results.append(result)
            else:
                failures.append(entry)
    
    return results, failures


def validate_jsonl(file_path: str) -> bool:
    """
    Validate a JSONL file for compatibility with the inferencer.
    
    Args:
        file_path: Path to the JSONL file
        
    Returns:
        True if validation passes, False otherwise
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            return False
        
        # Check file extension
        if not file_path.endswith('.jsonl'):
            print(f"Error: File must have .jsonl extension: {file_path}")
            return False
        
        # Validate each line
        with open(file_path, 'r', encoding='utf-8') as f:
            valid_entries = 0
            invalid_entries = 0
            
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    
                    # Check for messages field
                    if "messages" not in data:
                        print(f"Warning on line {line_num}: Missing 'messages' field")
                        invalid_entries += 1
                        continue
                    
                    # Check that messages is a list
                    if not isinstance(data["messages"], list):
                        print(f"Warning on line {line_num}: 'messages' field must be a list")
                        invalid_entries += 1
                        continue
                    
                    # Check that there's at least one message
                    if len(data["messages"]) == 0:
                        print(f"Warning on line {line_num}: 'messages' list is empty")
                        invalid_entries += 1
                        continue
                    
                    # Check system field if present
                    if "system" in data:
                        if isinstance(data["system"], list):
                            # Check that system is a list of objects with text field
                            for i, system_msg in enumerate(data["system"]):
                                if not isinstance(system_msg, dict) or "text" not in system_msg:
                                    print(f"Warning on line {line_num}: 'system[{i}]' must have a 'text' field")
                                    invalid_entries += 1
                                    break
                        elif not isinstance(data["system"], str):
                            print(f"Warning on line {line_num}: 'system' must be a list or string")
                            invalid_entries += 1
                            continue
                    
                    valid_entries += 1
                    
                except json.JSONDecodeError:
                    print(f"Error on line {line_num}: Invalid JSON")
                    invalid_entries += 1
                except Exception as e:
                    print(f"Error on line {line_num}: {e}")
                    invalid_entries += 1
        
        # Print validation summary
        print(f"\nValidation Summary for {file_path}:")
        print(f"  Valid entries: {valid_entries}")
        print(f"  Invalid entries: {invalid_entries}")
        print(f"  Total entries: {valid_entries + invalid_entries}")
        
        if invalid_entries > 0:
            print(f"\nWarning: {invalid_entries} invalid entries found.")
            print("The file can still be processed, but these entries may fail during inference.")
            return False
        else:
            print("\n✅ Validation passed! All entries are valid.")
            return True
            
    except Exception as e:
        print(f"Error validating file: {e}")
        return False


def cmd_infer(args):
    """Run inference on a JSONL file."""
    # Set log level based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        # Set boto3 logging to INFO for more details on requests
        boto3_logger = logging.getLogger('botocore')
        boto3_logger.setLevel(logging.INFO)
    
    # Determine model identifier (ARN or ID)
    if args.model_arn:
        model_identifier = args.model_arn
        logger.info(f"Using provisioned throughput ARN: {model_identifier}")
    else:
        if args.model_id == "custom":
            if not args.custom_model_id:
                logger.error("Error: --custom-model-id is required when --model-id=custom")
                sys.exit(1)
            model_identifier = args.custom_model_id
        else:
            model_identifier = MODEL_IDS[args.model_id]
        logger.info(f"Using model ID: {model_identifier}")
    
    logger.info(f"Starting inference with arguments: {args}")
    
    # Set up the boto3 client
    client = setup_boto3_client(args.region, args.profile)
    
    # Load data from input file
    data = read_jsonl(args.input)
    
    # Start from the specified index
    if args.start_index > 0:
        if args.start_index >= len(data):
            logger.error(f"Start index {args.start_index} is out of range (total entries: {len(data)})")
            sys.exit(1)
        logger.info(f"Starting from index {args.start_index} out of {len(data)} entries")
        data = data[args.start_index:]
    
    # Create output file directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    
    # Check if output file exists (for append mode after batch processing)
    output_file_exists = os.path.exists(args.output)
    
    # Process data in batches
    total_entries = len(data)
    all_results = []
    all_failures = []
    
    for i in range(0, len(data), args.batch_size):
        batch = data[i:i + args.batch_size]
        logger.info(f"Processing batch {i//args.batch_size + 1}/{(total_entries-1)//args.batch_size + 1} ({len(batch)} entries)")
        
        results, failures = process_batch(
            client, batch, model_identifier, args.retries, args.max_tokens, args.temperature, args.top_p, args.max_workers
        )
        
        # Save batch results immediately to avoid losing progress
        if results:
            mode = 'a' if output_file_exists or all_results else 'w'
            save_to_jsonl(results, args.output, mode)
            output_file_exists = True
        
        # Save failures for retry or analysis
        if failures:
            failure_file = f"{args.output}.failures.jsonl"
            mode = 'a' if os.path.exists(failure_file) or all_failures else 'w'
            save_to_jsonl(failures, failure_file, mode)
            logger.warning(f"Saved {len(failures)} failed entries to {failure_file}")
        
        # Keep track of results and failures for summary
        all_results.extend(results)
        all_failures.extend(failures)
        
        logger.info(f"Completed batch {i//args.batch_size + 1}: {len(results)} successful, {len(failures)} failed")
    
    # Log summary
    logger.info("=" * 50)
    logger.info(f"Processing complete: {len(all_results)} successful, {len(all_failures)} failed")
    logger.info(f"Results saved to: {args.output}")
    if all_failures:
        logger.info(f"Failures saved to: {args.output}.failures.jsonl")
    logger.info("=" * 50)
    
    # Print summary to console
    print("\nInference Summary:")
    print(f"  Total entries processed: {len(all_results) + len(all_failures)}")
    print(f"  Successful: {len(all_results)}")
    print(f"  Failed: {len(all_failures)}")
    print(f"  Success rate: {len(all_results)/(len(all_results) + len(all_failures))*100:.1f}%")
    print(f"\nResults saved to: {args.output}")
    if all_failures:
        print(f"Failures saved to: {args.output}.failures.jsonl")


def cmd_validate(args):
    """Validate a JSONL file."""
    print(f"Validating file: {args.input}")
    validate_jsonl(args.input)


def cmd_version():
    """Show version information."""
    print("Nova Custom Model Inferencer v1.0.0")
    print("Compatible with Amazon Bedrock Nova models")
    print("\nSupported models:")
    for name, model_id in MODEL_IDS.items():
        print(f"  - {name}: {model_id}")


def main():
    """Main function to process the JSONL file and call Nova model."""
    args = parse_args()
    
    if not args.command:
        print("Error: No command specified")
        print("Use --help for usage information")
        sys.exit(1)
    
    if args.command == 'infer':
        cmd_infer(args)
    elif args.command == 'validate':
        cmd_validate(args)
    elif args.command == 'version':
        cmd_version()
    else:
        print(f"Error: Unknown command '{args.command}'")
        print("Use --help for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()
