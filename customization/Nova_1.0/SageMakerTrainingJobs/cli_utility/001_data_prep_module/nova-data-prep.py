#!/usr/bin/env python3
"""
Nova Data Preparation Script

This script prepares data for Nova fine-tuning by:
1. Loading data from various sources (local files, S3, Hugging Face)
2. Converting to Nova converse format
3. Splitting into train/validation/test sets
4. Uploading to S3
5. Validating the output format

Supported input formats:
- CSV files with conversation columns
- JSON/JSONL files
- Hugging Face datasets
- Text files with Q&A pairs

Output format: Nova converse format (JSONL)
"""

import argparse
import json
import os
import sys
import csv
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import urlparse
import tempfile
import shutil

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    from datasets import load_dataset, Dataset
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from jinja2 import Template, Environment, meta
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

# Import the validator from the provided script
# Assuming the validator script is in the same directory or available
try:
    from nova_validator import (
        validate_converse_dataset, 
        ConverseDatasetSample, 
        NovaClientError,
        load_jsonl_data
    )
    HAS_VALIDATOR = True
except ImportError:
    print("Warning: Nova validator not found. Validation will be skipped.")
    HAS_VALIDATOR = False


class DataPrepError(Exception):
    """Custom exception for data preparation errors."""
    pass


class NovaDataPreparator:
    """Main class for preparing Nova training data."""
    
    def __init__(self, model_name: str = "lite"):
        self.model_name = model_name
        self.s3_client = None
        self.jinja_env = None
        
        if HAS_BOTO3:
            try:
                self.s3_client = boto3.client('s3')
            except NoCredentialsError:
                print("Warning: AWS credentials not found. S3 operations will fail.")
        
        if HAS_JINJA2:
            # Enable autoescape by default to prevent XSS vulnerabilities
            self.jinja_env = Environment(autoescape=True)
            # Add custom filters if needed
            self.jinja_env.filters['truncate'] = self._truncate_filter
            self.jinja_env.filters['upper'] = str.upper
            self.jinja_env.filters['lower'] = str.lower
    
    def load_data(self, 
                  data_file: Optional[str] = None, 
                  hf_dataset: Optional[str] = None,
                  hf_config: Optional[str] = None,
                  hf_split: Optional[str] = None) -> List[Dict]:
        """Load data from various sources."""
        
        if data_file and hf_dataset:
            raise DataPrepError("Cannot specify both --data_file and --hf_dataset")
        
        if not data_file and not hf_dataset:
            raise DataPrepError("Must specify either --data_file or --hf_dataset")
        
        if hf_dataset:
            return self._load_huggingface_data(hf_dataset, hf_config, hf_split)
        else:
            return self._load_file_data(data_file)
    
    def _load_huggingface_data(self, 
                              dataset_name: str, 
                              config: Optional[str] = None,
                              split: Optional[str] = None) -> List[Dict]:
        """Load data from Hugging Face datasets."""
        if not HAS_DATASETS:
            raise DataPrepError("datasets library not installed. Install with: pip install datasets")
        
        try:
            print(f"Loading Hugging Face dataset: {dataset_name}")
            dataset = load_dataset(dataset_name, config, split=split)
            
            # Convert to list of dictionaries
            if isinstance(dataset, Dataset):
                data = [dict(item) for item in dataset]
            else:
                # If multiple splits, take the first one
                split_name = list(dataset.keys())[0]
                data = [dict(item) for item in dataset[split_name]]
            
            print(f"Loaded {len(data)} samples from Hugging Face")
            return data
            
        except Exception as e:
            raise DataPrepError(f"Error loading Hugging Face dataset: {e}")
    
    def _truncate_filter(self, text: str, length: int = 100) -> str:
        """Jinja2 filter to truncate text."""
        if len(text) <= length:
            return text
        return text[:length] + "..."
    
    def load_template(self, template_path: str) -> str:
        """Load Jinja2 template from file or string."""
        if not HAS_JINJA2:
            raise DataPrepError("jinja2 library not installed. Install with: pip install jinja2")
        
        # Check if it's a file path
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Treat as template string
            return template_path
    
    def validate_template(self, template_str: str, sample_data: Dict) -> List[str]:
        """Validate template against sample data and return missing variables."""
        if not HAS_JINJA2:
            return []
        
        try:
            # Parse template to find undefined variables
            ast = self.jinja_env.parse(template_str)
            template_vars = meta.find_undeclared_variables(ast)
            
            # Check which variables are missing from sample data
            missing_vars = []
            for var in template_vars:
                if var not in sample_data:
                    missing_vars.append(var)
            
            return missing_vars
        except Exception as e:
            raise DataPrepError(f"Template validation error: {e}")
    
    def render_template(self, template_str: str, data: Dict) -> str:
        """Render Jinja2 template with data."""
        if not HAS_JINJA2:
            raise DataPrepError("jinja2 library not installed. Install with: pip install jinja2")
        
        try:
            template = self.jinja_env.from_string(template_str)
            return template.render(**data)
        except Exception as e:
            raise DataPrepError(f"Template rendering error: {e}")
    
    def convert_with_template(self, 
                             data: List[Dict], 
                             user_template: Optional[str] = None,
                             assistant_template: Optional[str] = None,
                             system_template: Optional[str] = None,
                             system_message: str = "You are a helpful assistant.") -> List[Dict]:
        """Convert data using Jinja2 templates."""
        
        if not any([user_template, assistant_template, system_template]):
            raise DataPrepError("At least one template (user, assistant, or system) must be provided")
        
        nova_samples = []
        
        # Load templates
        user_tmpl_str = self.load_template(user_template) if user_template else None
        assistant_tmpl_str = self.load_template(assistant_template) if assistant_template else None
        system_tmpl_str = self.load_template(system_template) if system_template else None
        
        # Validate templates with first sample
        if data:
            sample_data = data[0]
            if user_tmpl_str:
                missing_vars = self.validate_template(user_tmpl_str, sample_data)
                if missing_vars:
                    print(f"Warning: User template references undefined variables: {missing_vars}")
            
            if assistant_tmpl_str:
                missing_vars = self.validate_template(assistant_tmpl_str, sample_data)
                if missing_vars:
                    print(f"Warning: Assistant template references undefined variables: {missing_vars}")
            
            if system_tmpl_str:
                missing_vars = self.validate_template(system_tmpl_str, sample_data)
                if missing_vars:
                    print(f"Warning: System template references undefined variables: {missing_vars}")
        
        for idx, item in enumerate(data):
            try:
                # Create base sample
                sample = {
                    "schemaVersion": "bedrock-conversation-2024",
                    "system": [],
                    "messages": []
                }
                
                # Render system message
                if system_tmpl_str:
                    rendered_system = self.render_template(system_tmpl_str, item)
                    sample["system"] = [{"text": rendered_system}]
                else:
                    sample["system"] = [{"text": system_message}]
                
                # Render user message
                if user_tmpl_str:
                    rendered_user = self.render_template(user_tmpl_str, item)
                    sample["messages"].append({
                        "role": "user",
                        "content": [{"text": rendered_user}]
                    })
                
                # Render assistant message
                if assistant_tmpl_str:
                    rendered_assistant = self.render_template(assistant_tmpl_str, item)
                    sample["messages"].append({
                        "role": "assistant",
                        "content": [{"text": rendered_assistant}]
                    })
                
                # Only add sample if it has both user and assistant messages
                if len(sample["messages"]) == 2:
                    nova_samples.append(sample)
                else:
                    print(f"Skipping sample {idx}: Missing user or assistant message")
                    
            except Exception as e:
                print(f"Error processing sample {idx}: {e}")
                print(f"Sample data: {item}")
                continue
        
        print(f"Converted {len(nova_samples)} samples using templates")
        return nova_samples
    
    def _load_file_data(self, file_path: str) -> List[Dict]:
        """Load data from local or S3 file."""
        
        # Check if it's an S3 path
        if file_path.startswith('s3://'):
            return self._load_s3_file(file_path)
        else:
            return self._load_local_file(file_path)
    
    def _load_s3_file(self, s3_path: str) -> List[Dict]:
        """Load file from S3."""
        if not self.s3_client:
            raise DataPrepError("S3 client not available. Check AWS credentials.")
        
        parsed = urlparse(s3_path)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        
        try:
            # Download to temporary file
            with tempfile.NamedTemporaryFile(mode='w+b', delete=False) as tmp_file:
                self.s3_client.download_fileobj(bucket, key, tmp_file)
                tmp_path = tmp_file.name
            
            # Load the temporary file
            data = self._load_local_file(tmp_path)
            
            # Clean up
            os.unlink(tmp_path)
            return data
            
        except ClientError as e:
            raise DataPrepError(f"Error downloading from S3: {e}")
    
    def _load_local_file(self, file_path: str) -> List[Dict]:
        """Load data from local file."""
        if not os.path.exists(file_path):
            raise DataPrepError(f"File not found: {file_path}")
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.jsonl':
            return self._load_jsonl(file_path)
        elif file_ext == '.json':
            return self._load_json(file_path)
        elif file_ext == '.csv':
            return self._load_csv(file_path)
        elif file_ext == '.txt':
            return self._load_text(file_path)
        else:
            raise DataPrepError(f"Unsupported file format: {file_ext}")
    
    def _load_jsonl(self, file_path: str) -> List[Dict]:
        """Load JSONL file."""
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data.append(json.loads(line.strip()))
                except json.JSONDecodeError as e:
                    raise DataPrepError(f"Invalid JSON on line {line_num}: {e}")
        return data
    
    def _load_json(self, file_path: str) -> List[Dict]:
        """Load JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Ensure it's a list
        if not isinstance(data, list):
            data = [data]
        
        return data
    
    def _load_csv(self, file_path: str) -> List[Dict]:
        """Load CSV file."""
        if not HAS_PANDAS:
            # Fallback to csv module
            data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(dict(row))
            return data
        else:
            df = pd.read_csv(file_path)
            return df.to_dict('records')
    
    def _load_text(self, file_path: str) -> List[Dict]:
        """Load plain text file and convert to Q&A pairs."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Split by double newlines to separate Q&A pairs
        pairs = content.split('\n\n')
        data = []
        
        for i, pair in enumerate(pairs):
            lines = pair.strip().split('\n')
            if len(lines) >= 2:
                question = lines[0]
                answer = '\n'.join(lines[1:])
                data.append({
                    'question': question,
                    'answer': answer,
                    'id': i
                })
        
        return data
    
    def convert_to_nova_format(self, 
                              data: List[Dict], 
                              system_message: str = "You are a helpful assistant who answers the question based on the task assigned",
                              question_col: str = "question",
                              answer_col: str = "answer",
                              system_col: Optional[str] = None,
                              image_col: Optional[str] = None,
                              video_col: Optional[str] = None) -> List[Dict]:
        """Convert data to Nova converse format."""
        
        nova_samples = []
        
        for item in data:
            try:
                # Handle system message
                if system_col and system_col in item:
                    current_system = item[system_col]
                else:
                    current_system = system_message
                
                # Create base sample
                sample = {
                    "schemaVersion": "bedrock-conversation-2024",
                    "system": [{"text": current_system}],
                    "messages": []
                }
                
                # Handle user message
                user_content = []
                
                # Add text content
                if question_col in item and item[question_col]:
                    user_content.append({"text": str(item[question_col])})
                
                # Add image content
                if image_col and image_col in item and item[image_col]:
                    image_path = item[image_col]
                    image_format = self._get_image_format(image_path)
                    user_content.append({
                        "image": {
                            "format": image_format,
                            "source": {
                                "s3Location": {
                                    "uri": image_path if image_path.startswith('s3://') else f"s3://your-bucket/images/{Path(image_path).name}"
                                }
                            }
                        }
                    })
                
                # Add video content
                if video_col and video_col in item and item[video_col]:
                    video_path = item[video_col]
                    video_format = self._get_video_format(video_path)
                    user_content.append({
                        "video": {
                            "format": video_format,
                            "source": {
                                "s3Location": {
                                    "uri": video_path if video_path.startswith('s3://') else f"s3://your-bucket/videos/{Path(video_path).name}"
                                }
                            }
                        }
                    })
                
                # Add user message
                if user_content:
                    sample["messages"].append({
                        "role": "user",
                        "content": user_content
                    })
                
                # Add assistant message
                if answer_col in item and item[answer_col]:
                    sample["messages"].append({
                        "role": "assistant",
                        "content": [{"text": str(item[answer_col])}]
                    })
                
                # Only add sample if it has both messages
                if len(sample["messages"]) == 2:
                    nova_samples.append(sample)
                else:
                    print(f"Skipping sample due to missing question or answer: {item}")
                    
            except Exception as e:
                print(f"Error converting sample: {e}")
                print(f"Sample data: {item}")
                continue
        
        print(f"Converted {len(nova_samples)} samples to Nova format")
        return nova_samples
    
    def _get_image_format(self, image_path: str) -> str:
        """Extract image format from file path."""
        ext = Path(image_path).suffix.lower().lstrip('.')
        format_map = {
            'jpg': 'jpeg',
            'jpeg': 'jpeg',
            'png': 'png',
            'gif': 'gif',
            'webp': 'webp'
        }
        return format_map.get(ext, 'jpeg')
    
    def _get_video_format(self, video_path: str) -> str:
        """Extract video format from file path."""
        ext = Path(video_path).suffix.lower().lstrip('.')
        format_map = {
            'mp4': 'mp4',
            'mov': 'mov',
            'mkv': 'mkv',
            'webm': 'webm'
        }
        return format_map.get(ext, 'mp4')
    
    def split_data(self, 
                   data: List[Dict], 
                   train_ratio: float = 0.8, 
                   val_ratio: float = 0.1, 
                   test_ratio: float = 0.1,
                   seed: int = 42) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Split data into train, validation, and test sets."""
        
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            raise DataPrepError("Split ratios must sum to 1.0")
        
        # Shuffle data
        random.seed(seed)
        shuffled_data = data.copy()
        random.shuffle(shuffled_data)
        
        n_total = len(shuffled_data)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)
        
        train_data = shuffled_data[:n_train]
        val_data = shuffled_data[n_train:n_train + n_val]
        test_data = shuffled_data[n_train + n_val:]
        
        print(f"Data split: {len(train_data)} train, {len(val_data)} val, {len(test_data)} test")
        return train_data, val_data, test_data
    
    def save_jsonl(self, data: List[Dict], file_path: str):
        """Save data to JSONL file."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"Saved {len(data)} samples to {file_path}")
    
    def upload_to_s3(self, local_path: str, s3_path: str):
        """Upload file to S3."""
        if not self.s3_client:
            raise DataPrepError("S3 client not available. Check AWS credentials.")
        
        parsed = urlparse(s3_path)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        
        try:
            self.s3_client.upload_file(local_path, bucket, key)
            print(f"Uploaded {local_path} to {s3_path}")
        except ClientError as e:
            raise DataPrepError(f"Error uploading to S3: {e}")
    
    def validate_output(self, file_path: str):
        """Validate the output file using the Nova validator."""
        if not HAS_VALIDATOR:
            print("Validation skipped: Nova validator not available")
            return
        
        try:
            # Create a mock args object for the validator
            class Args:
                def __init__(self, input_file, model_name):
                    self.input_file = input_file
                    self.model_name = model_name
            
            args = Args(file_path, self.model_name)
            validate_converse_dataset(args)
            print(f"✅ Validation successful for {file_path}")
            
        except Exception as e:
            print(f"❌ Validation failed for {file_path}: {e}")
            raise DataPrepError(f"Validation failed: {e}")
    
    def prepare_data(self, 
                    data_file: Optional[str] = None,
                    hf_dataset: Optional[str] = None,
                    hf_config: Optional[str] = None,
                    hf_split: Optional[str] = None,
                    output_dir: str = "nova_data",
                    s3_output_prefix: Optional[str] = None,
                    job_name: Optional[str] = None,
                    train_ratio: float = 0.8,
                    val_ratio: float = 0.1,
                    test_ratio: float = 0.1,
                    system_message: str = "You are a helpful assistant.",
                    question_col: str = "question",
                    answer_col: str = "answer",
                    system_col: Optional[str] = None,
                    image_col: Optional[str] = None,
                    video_col: Optional[str] = None,
                    user_template: Optional[str] = None,
                    assistant_template: Optional[str] = None,
                    system_template: Optional[str] = None,
                    use_templates: bool = False,
                    seed: int = 42,
                    validate: bool = True):
        """Main method to prepare data for Nova fine-tuning."""
        
        try:
            # Load data
            print("Loading data...")
            raw_data = self.load_data(data_file, hf_dataset, hf_config, hf_split)
            
            # Convert to Nova format
            print("Converting to Nova format...")
            if use_templates:
                if not any([user_template, assistant_template]):
                    raise DataPrepError("When using templates, at least user_template or assistant_template must be provided")
                nova_data = self.convert_with_template(
                    raw_data, user_template, assistant_template, system_template, system_message
                )
            else:
                nova_data = self.convert_to_nova_format(
                    raw_data, system_message, question_col, answer_col,
                    system_col, image_col, video_col
                )
            
            if not nova_data:
                raise DataPrepError("No valid samples after conversion")
            
            # Split data
            print("Splitting data...")
            train_data, val_data, test_data = self.split_data(
                nova_data, train_ratio, val_ratio, test_ratio, seed
            )
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Save files
            train_path = os.path.join(output_dir, "train.jsonl")
            val_path = os.path.join(output_dir, "val.jsonl")
            test_path = os.path.join(output_dir, "test.jsonl")
            
            self.save_jsonl(train_data, train_path)
            self.save_jsonl(val_data, val_path)
            self.save_jsonl(test_data, test_path)
            
            # Validate files
            if validate:
                print("Validating output files...")
                self.validate_output(train_path)
                if val_data:
                    self.validate_output(val_path)
                if test_data:
                    self.validate_output(test_path)
            
            # Upload to S3 if specified
            if s3_output_prefix:
                print("Uploading to S3...")
                # Generate unique ID for the job
                unique_id = f"{int(time.time())}"
                job_partition = f"{job_name}-{unique_id}" if job_name else unique_id
                
                # Use job partition in S3 path
                s3_job_prefix = f"{s3_output_prefix}/{job_partition}"
                self.upload_to_s3(train_path, f"{s3_job_prefix}/train.jsonl")
                if val_data:
                    self.upload_to_s3(val_path, f"{s3_job_prefix}/val.jsonl")
                if test_data:
                    self.upload_to_s3(test_path, f"{s3_job_prefix}/test.jsonl")
            
            print("✅ Data preparation completed successfully!")
            
            # Print summary
            print("\nSummary:")
            print(f"  Total samples: {len(nova_data)}")
            print(f"  Train samples: {len(train_data)}")
            print(f"  Validation samples: {len(val_data)}")
            print(f"  Test samples: {len(test_data)}")
            print(f"  Output directory: {output_dir}")
            if s3_output_prefix:
                print(f"  S3 location: {s3_output_prefix}")
            if use_templates:
                print("  Template-based conversion used")
            
        except Exception as e:
            print(f"❌ Data preparation failed: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Prepare data for Nova fine-tuning",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--data_file", 
        type=str,
        help="Path to input data file (local or S3). Supports CSV, JSON, JSONL, TXT"
    )
    input_group.add_argument(
        "--hf_dataset",
        type=str,
        help="Hugging Face dataset name (e.g., 'squad', 'microsoft/DialoGPT-large')"
    )
    
    # Hugging Face specific options
    parser.add_argument(
        "--hf_config",
        type=str,
        help="Hugging Face dataset configuration name"
    )
    parser.add_argument(
        "--hf_split",
        type=str,
        help="Hugging Face dataset split name (e.g., 'train', 'test')"
    )
    
    # Output options
    parser.add_argument(
        "--output_dir",
        type=str,
        default="nova_data",
        help="Local output directory (default: nova_data)"
    )
    parser.add_argument(
        "--s3_output_prefix",
        type=str,
        help="S3 prefix for output files (e.g., 's3://my-bucket/nova-training')"
    )
    parser.add_argument(
        "--job_name",
        type=str,
        help="Job name to use as part of S3 partition (will be appended with unique ID)"
    )
    
    # Split ratios
    parser.add_argument(
        "--train_ratio",
        type=float,
        default=0.8,
        help="Training set ratio (default: 0.8)"
    )
    parser.add_argument(
        "--val_ratio",
        type=float,
        default=0.1,
        help="Validation set ratio (default: 0.1)"
    )
    parser.add_argument(
        "--test_ratio",
        type=float,
        default=0.1,
        help="Test set ratio (default: 0.1)"
    )
    
    # Data mapping options
    parser.add_argument(
        "--question_col",
        type=str,
        default="question",
        help="Column name for questions/user input (default: question)"
    )
    parser.add_argument(
        "--answer_col",
        type=str,
        default="answer",
        help="Column name for answers/assistant output (default: answer)"
    )
    parser.add_argument(
        "--system_col",
        type=str,
        help="Column name for system messages (optional)"
    )
    parser.add_argument(
        "--image_col",
        type=str,
        help="Column name for image paths/URLs (optional)"
    )
    parser.add_argument(
        "--video_col",
        type=str,
        help="Column name for video paths/URLs (optional)"
    )
    parser.add_argument(
        "--system_message",
        type=str,
        default="You are a helpful assistant.",
        help="Default system message (default: 'You are a helpful assistant.')"
    )
    
    # Template options
    parser.add_argument(
        "--use_templates",
        action="store_true",
        help="Use Jinja2 templates for data conversion"
    )
    parser.add_argument(
        "--user_template",
        type=str,
        help="Jinja2 template for user messages (file path or template string)"
    )
    parser.add_argument(
        "--assistant_template",
        type=str,
        help="Jinja2 template for assistant messages (file path or template string)"
    )
    parser.add_argument(
        "--system_template",
        type=str,
        help="Jinja2 template for system messages (file path or template string)"
    )
    
    # Model and validation options
    parser.add_argument(
        "--model_name",
        type=str,
        choices=["micro", "lite", "pro"],
        default="lite",
        help="Nova model name for validation (default: lite)"
    )
    parser.add_argument(
        "--no_validate",
        action="store_true",
        help="Skip output validation"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for data splitting (default: 42)"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    missing_deps = []
    if args.s3_output_prefix and not HAS_BOTO3:
        missing_deps.append("boto3 (for S3 operations)")
    if args.hf_dataset and not HAS_DATASETS:
        missing_deps.append("datasets (for Hugging Face datasets)")
    if args.use_templates and not HAS_JINJA2:
        missing_deps.append("jinja2 (for template processing)")
    if args.data_file and args.data_file.endswith('.csv') and not HAS_PANDAS:
        print("Warning: pandas not available. Using basic CSV parser.")
    
    if missing_deps:
        print("Missing dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("Install with: pip install boto3 datasets pandas jinja2")
        sys.exit(1)
    
    # Initialize preparator
    preparator = NovaDataPreparator(args.model_name)
    
    # Prepare data
    try:
        preparator.prepare_data(
            data_file=args.data_file,
            hf_dataset=args.hf_dataset,
            hf_config=args.hf_config,
            hf_split=args.hf_split,
            output_dir=args.output_dir,
            s3_output_prefix=args.s3_output_prefix,
            job_name=args.job_name,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            system_message=args.system_message,
            question_col=args.question_col,
            answer_col=args.answer_col,
            system_col=args.system_col,
            image_col=args.image_col,
            video_col=args.video_col,
            user_template=args.user_template,
            assistant_template=args.assistant_template,
            system_template=args.system_template,
            use_templates=args.use_templates,
            seed=args.seed,
            validate=not args.no_validate
        )
    except DataPrepError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
