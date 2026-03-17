#!/usr/bin/env python3
"""
Parser to transform Hugging Face dataset format to RFT format.
Preserves all original data exactly as-is (spaces, newlines, etc. all have meaning).

Usage:
    python parse_hf_to_rft.py <dataset_variable> <output_jsonl>
    
Or import and use the function:
    from utils.parse_hf_to_rft import parse_hf_dataset
    parse_hf_dataset(dataset, 'output.jsonl')
"""

import json
import sys
from typing import Dict, List, Any


def unescape_string_literals(text: str) -> str:
    """
    Convert string literals like \\n, \\t to actual newlines and tabs.
    
    Args:
        text: String potentially containing escape sequences
        
    Returns:
        String with escape sequences converted to actual characters
    """
    if not isinstance(text, str):
        return text
    
    # Use encode/decode to handle escape sequences
    try:
        # This converts \\n to actual newline, \\t to actual tab, etc.
        return text.encode('utf-8').decode('unicode_escape')
    except (UnicodeDecodeError, UnicodeEncodeError):
        # If decode fails, return original string
        return text


def normalize_value(value: Any) -> str:
    """
    Normalize a value to string format and convert escape sequences to actual characters.
    
    This prevents PyArrow errors about mixing list and non-list values by
    converting all values to strings. It also converts string literals like \\n
    to actual newlines.
    
    Args:
        value: Input value (can be string, list, tuple, number, etc.)
        
    Returns:
        String representation with escape sequences converted to actual characters
    """
    if isinstance(value, str):
        # Convert string literals like \n to actual newlines
        return unescape_string_literals(value)
    elif isinstance(value, (list, tuple)):
        # For lists/tuples, convert to JSON string first, then unescape
        json_str = json.dumps(value, ensure_ascii=False)
        return unescape_string_literals(json_str)
    elif value is None:
        return ""
    else:
        # Convert numbers, booleans, etc. to string
        return str(value)


def parse_hf_dataset(dataset, output_file: str, split: str = 'train') -> None:
    """
    Parse Hugging Face dataset format and convert to RFT format.
    
    Args:
        dataset: Hugging Face dataset object (with train/test/validation splits)
        output_file: Path to output JSONL file
        split: Dataset split to use (default: 'train')
    """
    transformed_data = []
    
    # Access the specified split
    data_split = dataset[split]
    
    print(f"Processing {len(data_split)} examples from '{split}' split...")
    
    for idx, example in enumerate(data_split):
        try:
            # Parse the info field which contains test cases
            info_str = example.get('info', '{}')
            info_dict = json.loads(info_str)
            
            # Extract tests from info
            tests_str = info_dict.get('tests', '{}')
            tests_dict = json.loads(tests_str)
            
            # Get inputs and outputs - preserve exactly as-is
            inputs = tests_dict.get('inputs', [])
            outputs = tests_dict.get('outputs', [])
            
            # Normalize to strings to prevent PyArrow type mixing errors
            # This does NOT modify content, only ensures type consistency
            normalized_inputs = [normalize_value(inp) for inp in inputs]
            normalized_outputs = [normalize_value(out) for out in outputs]
            
            # Get the question/problem description - preserve exactly as-is
            question = example.get('question', '')
            
            # Construct the transformed format
            transformed_example = {
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "reference_answer": {
                    "inputs": normalized_inputs,
                    "outputs": normalized_outputs
                }
            }
            
            transformed_data.append(transformed_example)
            
            # Progress indicator
            if (idx + 1) % 100 == 0:
                print(f"Processed {idx + 1} examples...")
                
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON for example {idx}: {e}")
            continue
        except Exception as e:
            print(f"Warning: Error processing example {idx}: {e}")
            continue
    
    # Write to JSONL file
    print(f"\nWriting {len(transformed_data)} examples to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in transformed_data:
            json_line = json.dumps(item, ensure_ascii=False)
            f.write(json_line + '\n')
    
    print(f"Successfully wrote {len(transformed_data)} examples to {output_file}")
    
    # Print sample output
    if transformed_data:
        print("\n" + "="*80)
        print("Sample output (first example):")
        print("="*80)
        print(json.dumps(transformed_data[0], indent=2, ensure_ascii=False))
        print("="*80)


def parse_and_split_dataset(
    dataset,
    output_prefix: str = 'rft_data',
    split: str = 'train',
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    shuffle: bool = True,
    seed: int = 42
) -> Dict[str, str]:
    """
    Parse HF dataset, split into train/val/test, and write three separate JSONL files.
    
    This function combines parsing and splitting, making it easy to prepare data for
    uploading to S3 with proper train/validation/test splits.
    
    Args:
        dataset: Hugging Face dataset object
        output_prefix: Prefix for output files (e.g., 'rft_data' -> 'rft_data_train.jsonl')
        split: Dataset split to use from the input dataset (default: 'train')
        train_ratio: Ratio of data for training (default: 0.8)
        val_ratio: Ratio of data for validation (default: 0.1)
        test_ratio: Ratio of data for testing (default: 0.1)
        shuffle: Whether to shuffle data before splitting (default: True)
        seed: Random seed for reproducibility (default: 42)
    
    Returns:
        Dictionary with paths to the created files:
        {'train': 'path/to/train.jsonl', 'val': 'path/to/val.jsonl', 'test': 'path/to/test.jsonl'}
    
    Example:
        >>> from datasets import load_dataset
        >>> from utils import parse_and_split_dataset, upload_to_s3
        >>> 
        >>> dataset = load_dataset('your-dataset-name')
        >>> files = parse_and_split_dataset(dataset, output_prefix='rft_data')
        >>> 
        >>> # Upload all splits to S3
        >>> for split_name, file_path in files.items():
        ...     upload_to_s3(file_path, 'my-bucket', f'datasets/{split_name}.jsonl')
    """
    import random
    
    # Validate ratios
    total_ratio = train_ratio + val_ratio + test_ratio
    if abs(total_ratio - 1.0) > 0.01:
        raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio}")
    
    print(f"Parsing and splitting dataset with ratios - Train: {train_ratio}, Val: {val_ratio}, Test: {test_ratio}")
    
    # Parse the entire dataset into memory first
    transformed_data = []
    data_split = dataset[split]
    
    print(f"Processing {len(data_split)} examples from '{split}' split...")
    
    for idx, example in enumerate(data_split):
        try:
            # Parse the info field which contains test cases
            info_str = example.get('info', '{}')
            info_dict = json.loads(info_str)
            
            # Extract tests from info
            tests_str = info_dict.get('tests', '{}')
            tests_dict = json.loads(tests_str)
            
            # Get inputs and outputs - preserve exactly as-is
            inputs = tests_dict.get('inputs', [])
            outputs = tests_dict.get('outputs', [])
            
            # Normalize to strings to prevent PyArrow type mixing errors
            # This does NOT modify content, only ensures type consistency
            normalized_inputs = [normalize_value(inp) for inp in inputs]
            normalized_outputs = [normalize_value(out) for out in outputs]
            
            # Get the question/problem description - preserve exactly as-is
            question = example.get('question', '')
            
            # Construct the transformed format
            transformed_example = {
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "reference_answer": {
                    "inputs": normalized_inputs,
                    "outputs": normalized_outputs
                }
            }
            
            transformed_data.append(transformed_example)
            
            # Progress indicator
            if (idx + 1) % 100 == 0:
                print(f"Processed {idx + 1} examples...")
                
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON for example {idx}: {e}")
            continue
        except Exception as e:
            print(f"Warning: Error processing example {idx}: {e}")
            continue
    
    total_examples = len(transformed_data)
    print(f"\nSuccessfully processed {total_examples} examples")
    
    # Shuffle if requested
    if shuffle:
        print(f"Shuffling data with seed={seed}...")
        random.seed(seed)
        random.shuffle(transformed_data)
    
    # Calculate split indices
    train_size = int(total_examples * train_ratio)
    val_size = int(total_examples * val_ratio)
    
    # Split the data
    train_data = transformed_data[:train_size]
    val_data = transformed_data[train_size:train_size + val_size]
    test_data = transformed_data[train_size + val_size:]
    
    print(f"\nSplit sizes:")
    print(f"  Train: {len(train_data)} examples ({len(train_data)/total_examples*100:.1f}%)")
    print(f"  Val:   {len(val_data)} examples ({len(val_data)/total_examples*100:.1f}%)")
    print(f"  Test:  {len(test_data)} examples ({len(test_data)/total_examples*100:.1f}%)")
    
    # Write splits to files
    output_files = {}
    splits = {
        'train': train_data,
        'val': val_data,
        'test': test_data
    }
    
    for split_name, split_data in splits.items():
        if len(split_data) == 0:
            print(f"Warning: {split_name} split is empty, skipping file creation")
            continue
            
        output_file = f"{output_prefix}_{split_name}.jsonl"
        print(f"\nWriting {len(split_data)} examples to {output_file}...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in split_data:
                json_line = json.dumps(item, ensure_ascii=False)
                f.write(json_line + '\n')
        
        output_files[split_name] = output_file
        print(f"✓ Created {output_file}")
    
    # Print sample from train split
    if train_data:
        print("\n" + "="*80)
        print("Sample from training split (first example):")
        print("="*80)
        print(json.dumps(train_data[0], indent=2, ensure_ascii=False))
        print("="*80)
    
    print(f"\n✅ Successfully created {len(output_files)} split files")
    return output_files


def main():
    """
    Main function for CLI usage.
    Note: This requires the dataset to be loaded in the Python environment.
    For direct CLI usage, you'll need to modify this to load from a file.
    """
    print("This script is designed to be imported and used with a loaded dataset.")
    print("\nExample usage in Python:")
    print("  from datasets import load_dataset")
    print("  from utils.parse_hf_to_rft import parse_hf_dataset")
    print("  ")
    print("  ds = load_dataset('your-dataset-name')")
    print("  parse_hf_dataset(ds, 'output.jsonl', split='train')")
    print("\nAlternatively, if you have a dataset loaded as 'ds', run:")
    print("  python -c \"from utils.parse_hf_to_rft import parse_hf_dataset; parse_hf_dataset(ds, 'output.jsonl')\"")


if __name__ == "__main__":
    main()
