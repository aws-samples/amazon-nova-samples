"""
RFT Formatter - Transform SFT to RFT Format

This module provides utilities to convert Supervised Fine-Tuning (SFT) data
to Rejection Fine-Tuning (RFT) format. The transformation includes:
- Adding sequential IDs
- Flattening content arrays
- Moving assistant responses to reference_answer field
- Parsing JSON responses as structured data

Main function: convert_sft_to_rft()
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# CONTENT PROCESSING UTILITIES
# ============================================================================

def flatten_message_content(content: Any) -> str:
    """
    Flatten content from array format to string.
    
    Args:
        content: Content in format [{"text": "..."}] or string
        
    Returns:
        Flattened string content
    """
    if isinstance(content, list):
        # Extract text from list of dicts
        texts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                texts.append(item["text"])
        return " ".join(texts)
    elif isinstance(content, str):
        return content
    else:
        return str(content)


def extract_reference_answer(response_text: str) -> Dict[str, Any]:
    """
    Parse the assistant's JSON response into structured format.
    
    Args:
        response_text: The assistant's response containing JSON
        
    Returns:
        Parsed reference answer dictionary
    """
    try:
        # The response is a JSON string, parse it
        parsed = json.loads(response_text)
        
        # Extract Query analysis
        if "Query analysis" in parsed:
            return parsed["Query analysis"]
        else:
            # Response might be the Query analysis directly
            return parsed
            
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse assistant response as JSON: {e}")
        print(f"Response text: {response_text[:200]}...")
        return {"raw_response": response_text}


# ============================================================================
# RECORD TRANSFORMATION
# ============================================================================

def transform_single_record(sft_record: Dict[str, Any], record_id: str) -> Dict[str, Any]:
    """
    Transform a single SFT record to RFT format.
    
    Args:
        sft_record: Dictionary containing SFT format data with 'messages' field
        record_id: Unique identifier for the record (e.g., "00001")
        
    Returns:
        Dictionary in RFT format with 'id', 'messages', and 'reference_answer'
    """
    messages = sft_record.get("messages", [])
    
    # Separate user/system messages from assistant response
    rft_messages = []
    assistant_message = None
    
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        
        if role == "assistant":
            # Save assistant message for reference_answer
            assistant_message = content
        else:
            # Keep system and user messages, flatten content
            rft_messages.append({
                "role": role,
                "content": flatten_message_content(content)
            })
    
    # Extract reference answer from assistant's response
    reference_answer = {}
    if assistant_message:
        assistant_text = flatten_message_content(assistant_message)
        reference_answer = extract_reference_answer(assistant_text)
    
    # Build RFT format record
    return {
        "id": record_id,
        "messages": rft_messages,
        "reference_answer": reference_answer
    }


# ============================================================================
# FILE PROCESSING
# ============================================================================

def process_jsonl_file(input_path: Path, output_path: Path) -> Dict[str, int]:
    """
    Convert a single JSONL file from SFT to RFT format.
    
    Args:
        input_path: Path object pointing to input SFT JSONL file
        output_path: Path object pointing to output RFT JSONL file
        
    Returns:
        Dictionary with 'processed' and 'failed' counts
    """
    print(f"\n📖 Reading: {input_path}")
    print(f"📝 Writing: {output_path}")
    
    stats = {"processed": 0, "failed": 0}
    
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            try:
                # Parse SFT record
                sft_record = json.loads(line.strip())
                
                # Generate sequential ID (5-digit zero-padded)
                record_id = f"{line_num:05d}"
                
                # Transform to RFT format
                rft_record = transform_single_record(sft_record, record_id)
                
                # Write RFT record
                outfile.write(json.dumps(rft_record, ensure_ascii=False) + '\n')
                
                stats["processed"] += 1
                
                if stats["processed"] % 100 == 0:
                    print(f"  ✓ Processed {stats['processed']} records...")
                    
            except Exception as e:
                print(f"  ✗ Error on line {line_num}: {e}")
                stats["failed"] += 1
                continue
    
    print(f"✅ Completed {input_path.name}")
    print(f"   Processed: {stats['processed']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Output: {output_path}")
    
    return stats


# ============================================================================
# MAIN CONVERSION FUNCTION
# ============================================================================

def convert_sft_to_rft(input_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert SFT format data to RFT format.
    
    This is the main function to use. It handles both single files and directories:
    - Single file: Converts one JSONL file
    - Directory: Converts all .jsonl files in the directory
    
    Args:
        input_path: Path to input SFT file or directory
        output_path: Path to output RFT file or directory (optional)
                    If not provided, auto-generates:
                    - Files: adds '_rft' before extension (e.g., train.jsonl → train_rft.jsonl)
                    - Directories: creates 'RFT' subdirectory
    
    Returns:
        Dictionary with conversion statistics
        
    Examples:
        >>> convert_sft_to_rft("data/train.jsonl")
        >>> convert_sft_to_rft("data/train.jsonl", "data/rft/train.jsonl")
        >>> convert_sft_to_rft("data/sft_files/")
        >>> convert_sft_to_rft("data/sft_files/", "data/rft_files/")
    """
    input_p = Path(input_path)
    
    # Validate input exists
    if not input_p.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
    
    # Auto-generate output path if not provided
    if output_path is None:
        if input_p.is_dir():
            # For directories: create 'RFT' subdirectory
            output_p = input_p.parent / "RFT"
        else:
            # For files: add '_rft' suffix before extension
            output_p = input_p.parent / f"{input_p.stem}_rft{input_p.suffix}"
    else:
        output_p = Path(output_path)
    
    # Initialize stats
    total_stats = {"files": 0, "processed": 0, "failed": 0}
    
    # Process directory
    if input_p.is_dir():
        print(f"🗂️  Processing directory: {input_p}")
        
        # Find all .jsonl files
        jsonl_files = sorted(input_p.glob("*.jsonl"))
        
        if not jsonl_files:
            print(f"⚠️  No .jsonl files found in {input_p}")
            return total_stats
        
        print(f"📋 Found {len(jsonl_files)} .jsonl file(s)\n")
        
        # Create output directory
        output_p.mkdir(parents=True, exist_ok=True)
        
        # Process each file
        for jsonl_file in jsonl_files:
            output_file = output_p / jsonl_file.name
            file_stats = process_jsonl_file(jsonl_file, output_file)
            total_stats["files"] += 1
            total_stats["processed"] += file_stats["processed"]
            total_stats["failed"] += file_stats["failed"]
        
        print(f"\n🎉 All files processed!")
        print(f"   Total files: {total_stats['files']}")
        print(f"   Total records processed: {total_stats['processed']}")
        print(f"   Total records failed: {total_stats['failed']}")
    
    # Process single file
    else:
        # Create output directory if needed
        output_p.parent.mkdir(parents=True, exist_ok=True)
        file_stats = process_jsonl_file(input_p, output_p)
        total_stats["files"] = 1
        total_stats["processed"] = file_stats["processed"]
        total_stats["failed"] = file_stats["failed"]
    
    return total_stats


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Keep old function name for backward compatibility
data_sft_rft = convert_sft_to_rft
transform_sft_to_rft = transform_single_record
flatten_content = flatten_message_content
parse_assistant_response = extract_reference_answer


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python rft_formatter.py <input_path> [output_path]")
        print("\nExamples:")
        print("  python rft_formatter.py data/train.jsonl")
        print("  python rft_formatter.py data/train.jsonl data/rft/train.jsonl")
        print("  python rft_formatter.py data/sft_files/")
        sys.exit(1)
    
    input_arg = sys.argv[1]
    output_arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        convert_sft_to_rft(input_arg, output_arg)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
