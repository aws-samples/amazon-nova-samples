#!/usr/bin/env python3
"""
Nova Format Converter

This script converts between different data formats used in the Nova ecosystem:
- Bedrock Conversation Format (output by data-prep.py)
- gen_qa Format (required by nova_eval_cli.py)

Usage:
    python format_converter.py --input input.jsonl --output gen_qa.jsonl --is-bedrock-format
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any


def convert_bedrock_to_genqa(bedrock_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Convert a single entry from Bedrock Conversation Format to gen_qa format.
    
    Args:
        bedrock_data: A dictionary in Bedrock Conversation Format
        
    Returns:
        Dictionary in gen_qa format with query, response, and optional system fields
    """
    # Initialize the output dictionary
    genqa_data = {}
    
    # Extract system message if present
    if "system" in bedrock_data and bedrock_data["system"] and len(bedrock_data["system"]) > 0:
        # Get the text from the first system message
        system_text = bedrock_data["system"][0].get("text", "")
        if system_text:
            genqa_data["system"] = system_text
    
    # Extract user and assistant messages
    if "messages" in bedrock_data:
        user_message = None
        assistant_message = None
        
        # Find the first user and assistant messages
        for message in bedrock_data["messages"]:
            if message["role"] == "user" and not user_message:
                # Extract text content from user message
                for content_item in message.get("content", []):
                    if "text" in content_item:
                        user_message = content_item["text"]
                        break
            
            if message["role"] == "assistant" and not assistant_message:
                # Extract text content from assistant message
                for content_item in message.get("content", []):
                    if "text" in content_item:
                        assistant_message = content_item["text"]
                        break
        
        # Add user message as query
        if user_message:
            genqa_data["query"] = user_message
        else:
            raise ValueError("No user message found in the input data")
        
        # Add assistant message as response
        if assistant_message:
            genqa_data["response"] = assistant_message
        else:
            raise ValueError("No assistant message found in the input data")
    else:
        raise ValueError("No messages found in the input data")
    
    return genqa_data


def convert_file(input_path: str, output_path: str, is_bedrock_format: bool) -> int:
    """
    Convert a file from one format to another.
    
    Args:
        input_path: Path to the input file
        output_path: Path to the output file
        is_bedrock_format: Whether the input is in Bedrock Conversation Format
        
    Returns:
        Number of successfully converted entries
    """
    # Check if input file exists
    if not Path(input_path).exists():
        print(f"Error: Input file '{input_path}' not found")
        return 0
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    converted_count = 0
    error_count = 0
    
    # Process the file line by line
    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
        for line_num, line in enumerate(infile, 1):
            try:
                # Parse the JSON line
                data = json.loads(line.strip())
                
                # Convert if needed
                if is_bedrock_format:
                    # Convert from Bedrock Conversation Format to gen_qa format
                    converted_data = convert_bedrock_to_genqa(data)
                else:
                    # Already in gen_qa format or other format, pass through
                    converted_data = data
                
                # Validate the output has required fields for gen_qa
                if "query" not in converted_data or "response" not in converted_data:
                    print(f"Warning: Line {line_num} missing required fields after conversion")
                    error_count += 1
                    continue
                
                # Write the converted data
                outfile.write(json.dumps(converted_data, ensure_ascii=False) + '\n')
                converted_count += 1
                
            except json.JSONDecodeError:
                print(f"Error: Line {line_num} contains invalid JSON")
                error_count += 1
            except ValueError as e:
                print(f"Error on line {line_num}: {e}")
                error_count += 1
            except Exception as e:
                print(f"Unexpected error on line {line_num}: {e}")
                error_count += 1
    
    print(f"Conversion complete: {converted_count} entries converted successfully")
    if error_count > 0:
        print(f"Warning: {error_count} entries had errors during conversion")
    
    return converted_count


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Convert between Nova data formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert from Bedrock Conversation Format to gen_qa format
  python format_converter.py --input test.jsonl --output gen_qa.jsonl --is-bedrock-format
  
  # Pass through data already in gen_qa format
  python format_converter.py --input data.jsonl --output gen_qa.jsonl
        """
    )
    
    parser.add_argument('--input', required=True, help='Path to the input JSONL file')
    parser.add_argument('--output', required=True, help='Path to the output JSONL file')
    parser.add_argument('--is-bedrock-format', action='store_true', 
                      help='Flag indicating the input is in Bedrock Conversation Format')
    
    args = parser.parse_args()
    
    try:
        converted_count = convert_file(args.input, args.output, args.is_bedrock_format)
        if converted_count > 0:
            print(f"✅ Successfully converted {converted_count} entries")
            print(f"Output saved to: {args.output}")
            sys.exit(0)
        else:
            print("❌ No entries were converted")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
