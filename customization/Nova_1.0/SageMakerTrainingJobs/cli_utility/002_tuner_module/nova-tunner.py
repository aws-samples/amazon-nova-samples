# -*- coding: utf-8 -*-
# #!/usr/bin/env python3
#pip install -r requirements.txt

"""SageMaker Nova Training Script Runner (Step 2 of Nova Fine-tuning Process)
Command-line interface for running Nova model training jobs on SageMaker.

This script is typically used as Step 2 in the Nova fine-tuning process:
Step 1: Prepare and validate training data (using nova-data-prep.py)
Step 2: Run the fine-tuning job (using this script)

You can skip Step 1 if you already have properly formatted training/validation files in S3.
"""


import os
import sys
import argparse
import sagemaker
import boto3
import yaml
import json
from sagemaker.pytorch import PyTorch
from sagemaker.inputs import TrainingInput
from sagemaker.debugger import TensorBoardOutputConfig

def verify_s3_file_exists(s3_path):
    """Verify that a file exists in S3"""
    try:
        s3 = boto3.client('s3')
        bucket = s3_path.replace('s3://', '').split('/')[0]
        key = '/'.join(s3_path.replace('s3://', '').split('/')[1:])
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        return False

def handle_validation_input(args):
    """Handle validation input - either file path or direct JSONL content"""
    if not args.validation_jsonl:
        print(f"ℹ️  Skipping validation as no validation path provided")
        return None
    
    if os.path.exists(args.validation_jsonl) and args.upload_data:
        print()
        val_data_path = f"s3://{args.s3_bucket}/nova-training/{args.job_name}/val_data.jsonl"
        upload_data_to_s3(args.validation_jsonl, val_data_path)
        print(f"✓ Local File Detected uploading to S3 path:", val_data_path)
        return val_data_path
    if 's3://' in args.validation_jsonl:
        val_data_path = args.validation_jsonl
        if not verify_s3_file_exists(val_data_path):
            raise ValueError(f"❌ Validation file not found in S3: {val_data_path}")
        print(f"✓ S3 File Detected and Verified; S3 path:", val_data_path)
        return val_data_path

def handle_data_input(args):
    """Handle data input - either file path or direct JSONL content"""
    if not args.data_jsonl:
        raise ValueError("❌ Training data file (--data-jsonl) is required. Please provide a path to your training data in S3 or a local file.")
    # Check if it's a file path
    if os.path.exists(args.data_jsonl) and args.upload_data:
        print()
        input_data_path = f"s3://{args.s3_bucket}/nova-training/{args.job_name}/train_data.jsonl"
        upload_data_to_s3(args.data_jsonl, input_data_path)
        print(f"✓ Local File Detected uploading to S3 path:", input_data_path)
        return input_data_path
    if 's3://' in args.data_jsonl:
        input_data_path = args.data_jsonl
        if not verify_s3_file_exists(input_data_path):
            raise ValueError(f"❌ Training data file not found in S3: {input_data_path}")
        print(f"✓ S3 File Detected and Verified; S3 path:", input_data_path)
        return input_data_path
    
    raise ValueError("❌ Training data must be provided either as a local file with --upload-data flag or as an S3 path")


def parse_recipe_override(override_str):
    """Parse recipe override string in format key1.key2=value"""
    if not override_str:
        return {}
    
    overrides = {}
    for pair in override_str.split(','):
        if '=' not in pair:
            continue
        keys, value = pair.split('=', 1)
        # Handle nested keys (e.g., "optimizer.learning_rate=0.001")
        key_parts = keys.strip().split('.')
        current = overrides
        for i, key in enumerate(key_parts):
            if i == len(key_parts) - 1:
                # Try to convert value to appropriate type
                try:
                    # Try as number first
                    if '.' in value:
                        current[key] = float(value)
                    else:
                        current[key] = int(value)
                except ValueError:
                    # If not a number, try as boolean
                    if value.lower() in ('true', 'false'):
                        current[key] = value.lower() == 'true'
                    else:
                        # Otherwise keep as string
                        current[key] = value
            else:
                current = current.setdefault(key, {})
    return overrides

def apply_recipe_overrides(recipe_content, overrides_json=None, override_str=None):
    """Apply overrides to YAML recipe content from either JSON or string format"""
    if not overrides_json and not override_str:
        return recipe_content
    
    try:
        # Parse the YAML recipe
        recipe_data = yaml.safe_load(recipe_content)
        
        # Handle JSON overrides
        if overrides_json:
            if isinstance(overrides_json, str):
                overrides = json.loads(overrides_json)
            else:
                overrides = overrides_json
            print(f"🔧 Applying JSON recipe overrides...")
        
        # Handle string overrides
        if override_str:
            cli_overrides = parse_recipe_override(override_str)
            if cli_overrides:
                print(f"🔧 Applying command-line recipe overrides...")
                if overrides_json:
                    # Merge with JSON overrides if both are present
                    overrides.update(cli_overrides)
                else:
                    overrides = cli_overrides
        
        # Parse the YAML recipe
        recipe_data = yaml.safe_load(recipe_content)
        
        print(f"🔧 Applying recipe overrides...")
        
        # Recursively apply overrides
        def deep_update(base_dict, update_dict):
            for key, value in update_dict.items():
                if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value
                    print(f"  ✓ Override: {key} = {value}")
        
        deep_update(recipe_data, overrides)
        
        # Convert back to YAML
        modified_recipe = yaml.dump(recipe_data, default_flow_style=False)
        print(f"✓ Successfully applied {len(overrides)} override(s)")
        
        return modified_recipe
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing recipe overrides JSON: {e}")
        raise
    except yaml.YAMLError as e:
        print(f"❌ Error parsing recipe YAML: {e}")
        raise
    except Exception as e:
        print(f"❌ Error applying recipe overrides: {e}")
        raise

def get_recipe_from_repo(model_name, training_type, recipe_repo_path=None):
    """Automatically select the appropriate recipe from the repository based on model and training type"""
    
    # Default recipe repository path
    if not recipe_repo_path:
        recipe_repo_path = "/Users/dewanup/projects/git2/NovaCustomizationSamples/NovaPrimeRecipesStaging/sagemaker_training_job_recipes/recipes"
    
    # Map training types to directory names and recipe patterns
    training_type_mapping = {
        'sft': {
            'dir': 'supervised-fine-tuning/smtj_ga/nova',
            'pattern': 'nova_{model}_p5_gpu_sft.yaml'
        },
        'lora': {
            'dir': 'supervised-fine-tuning/smtj_ga/nova', 
            'pattern': 'nova_{model}_p5_gpu_lora_sft.yaml'
        },
        'dpo': {
            'dir': 'direct-preference-ptimization/smtj_ga/nova',
            'pattern': 'nova_{model}_p5_gpu_dpo.yaml'
        },
        'dpo-sft': {
            'dir': 'direct-preference-ptimization/smtj_ga/nova',
            'pattern': 'nova_{model}_p5_gpu_lora_dpo.yaml'
        }
    }
    
    if training_type not in training_type_mapping:
        raise ValueError(f"❌ Unsupported training type: {training_type}. Supported types: {list(training_type_mapping.keys())}")
    
    # Build the recipe file path
    training_config = training_type_mapping[training_type]
    recipe_filename = training_config['pattern'].format(model=model_name)
    recipe_path = os.path.join(recipe_repo_path, training_config['dir'], recipe_filename)
    
    # Check if the recipe file exists
    if not os.path.exists(recipe_path):
        raise ValueError(f"❌ Recipe file not found: {recipe_path}")
    
    print(f"✓ Auto-selected recipe: {recipe_path}")
    print(f"  Model: {model_name}")
    print(f"  Training Type: {training_type}")
    
    return recipe_path

def handle_recipe_input(recipe_arg, model_name=None, training_type=None, recipe_repo_path=None):
    """Handle recipe input - either file path, direct YAML content, or auto-select from repo"""
    
    # If training type is specified, auto-select recipe from repo
    if training_type and model_name:
        return get_recipe_from_repo(model_name, training_type, recipe_repo_path)
    
    if not recipe_arg:
        # Create default recipe
        default_recipe = """# Nova LoRA Training Recipe
model_name: nova-micro
training_type: lora
lora_config:
  rank: 8
  alpha: 16
  dropout: 0.1
optimizer:
  name: adamw
  learning_rate: 1e-4
training:
  epochs: 3
  batch_size: 1
  gradient_accumulation_steps: 8"""
        with open("quickstart_recipe.yaml", "w") as f:
            f.write(default_recipe)
        print("✓ Created default quickstart_recipe.yaml")
        return "quickstart_recipe.yaml"
    
    # Check if it's a file path
    if os.path.exists(recipe_arg):
        print(f"✓ Using existing recipe file: {recipe_arg}")
        return recipe_arg
    elif recipe_arg.startswith("fine-tuning/nova") and 'github' in recipe_arg:
        return recipe_arg
    else:
        # Treat as direct YAML content
        with open("quickstart_recipe.yaml", "w") as f:
            f.write(recipe_arg)
        print("✓ Created quickstart_recipe.yaml from provided content")
        return "quickstart_recipe.yaml"


def upload_data_to_s3(local_file, s3_path):
    print("""Upload data file to S3""")
    try:
        # Use AWS CLI if available, otherwise use boto3
        os.system(f"aws s3 cp {local_file} {s3_path}")
        print(f"✓ Uploaded {local_file} to {s3_path}")
    except Exception as e:
        print(f"⚠ Warning: Could not upload to S3: {e}")
        print("Please ensure AWS CLI is configured and you have S3 permissions")


def run_training_job(args):
    """Execute the SageMaker training job"""
    
    print("""
🔍 Step 2: Nova Fine-tuning Job Configuration
   Note: This is typically the second step after preparing your training data.
   If you haven't validated your data format yet, consider using nova-data-prep.py first.
""")
    
    # Initialize SageMaker session
    sagemaker_session = sagemaker.Session()
    role = args.role or sagemaker.get_execution_role()
    
    # Configure paths
    args.s3_bucket = args.s3_bucket or sagemaker_session.default_bucket()
    output_path = f"s3://{args.s3_bucket}/nova-training/output/{args.job_name}/output"
    
    # Handle data and recipe files
    input_data_path = handle_data_input(args if hasattr(args, 'data_jsonl') else None)
    val_data_path = handle_validation_input(args if hasattr(args, 'validation_jsonl') else None)
    
    # Handle recipe and overrides
    recipe_file = handle_recipe_input(
        args.recipe_yaml if hasattr(args, 'recipe_yaml') else None,
        model_name=args.model_name,
        training_type=getattr(args, 'training_type', None),
        recipe_repo_path=getattr(args, 'recipe_repo_path', None)
    )
    if hasattr(args, 'recipe_override') and args.recipe_override:
        # Read the recipe file
        with open(recipe_file, 'r') as f:
            recipe_content = f.read()
        # Apply overrides
        modified_recipe = apply_recipe_overrides(recipe_content, override_str=args.recipe_override)
        # Write back to file
        with open(recipe_file, 'w') as f:
            f.write(modified_recipe)
        print("✓ Applied recipe overrides")

    print(f"📁 S3 Bucket: {args.s3_bucket}")
    print(f"📥 Input Data: {input_data_path}")
    if val_data_path:
        print(f"📊 Validation Data: {val_data_path}")
    print(f"📤 Output Path: {output_path}")

    tensorboard_output_config = TensorBoardOutputConfig(
        s3_output_path=os.path.join(f"s3://{args.s3_bucket}/nova-training/{args.job_name}", 'tensorboard'),
    )
    # Configure training estimator
    print("⚙️  Configuring PyTorch estimator...")
    
    estimator_config = {
        "output_path": output_path,
        "base_job_name": args.job_name,
        "role": role,
        "instance_count": args.instance_count,
        "instance_type": args.instance_type,
        "training_recipe": recipe_file,
        "max_run": args.max_run,
        "sagemaker_session": sagemaker_session,
        "image_uri": args.image_uri,
        "disable_profiler":True,
        "debugger_hook_config":False,
        "tensorboard_output_config":tensorboard_output_config
    }
    
    # Add optional parameters
    if args.hyperparameters:
        estimator_config["hyperparameters"] = args.hyperparameters
    
    estimator = PyTorch(**estimator_config)
    # Configure training input
    training_input = TrainingInput(
        s3_data=input_data_path,
        distribution='FullyReplicated',
        s3_data_type='Converse'
    )
    # Configure validation input if provided
    inputs = {"train": training_input}
    if args.validation_jsonl:
        validation_input = TrainingInput(
            s3_data=val_data_path,
            distribution='FullyReplicated',
            s3_data_type='Converse'
        )
        inputs["validation"] = validation_input
        print("✓ Validation data configured")
    
    # Execute training job
    if not args.dry_run:
        print("🔥 Starting training job...")
        estimator.fit(inputs=inputs)
        print(f"✅ Training job completed!")
        print(f"📋 Check model manifest at: {output_path}/manifest.json")
    else:
        print("🔍 Dry run mode - configuration validated but job not started")
        print("Configuration summary:")
        for key, value in estimator_config.items():
            print(f"  {key}: {value}")
        print(f"Training inputs: {list(inputs.keys())}")

def parse_hyperparameters(hp_string):
    """Parse hyperparameters from string format key1=value1,key2=value2"""
    if not hp_string:
        return None
    
    hyperparams = {}
    for pair in hp_string.split(','):
        if '=' in pair:
            key, value = pair.split('=', 1)
            hyperparams[key.strip()] = value.strip()
    return hyperparams

def get_image_uri():
    return {
       "train": "708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-fine-tune-repo:SM-TJ-SFT-latest",
        "eval": "708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-evaluation-repo:SM-TJ-Eval-latest",
        "dpo":"708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-fine-tune-repo:SM-TJ-DPO-latest",
    }

def get_default_instance_type():
    return {
    "train":{
        "micro": "ml.p5.48xlarge",
        "lite": "ml.p5.48xlarge",
        "pro": "ml.p5.48xlarge"
    },
    "eval":{
        "micro": "ml.g5.12xlarge",
        "lite": "ml.g5.12xlarge",
        "pro": "ml.p5.48xlarge"
        },
    "dpo":{
        "micro": "ml.p5.48xlarge",
        "lite": "ml.p5.48xlarge",
        "pro": "ml.p5.48xlarge"
        }
    }

def get_default_instance_count():
    return {
    "train":{
        "micro":2,
        "lite":4,
        "pro":6
    },
    "eval":{
        "micro":1,
        "lite": 1,
        "pro": 1
        },
    "dpo":{
        "micro":2,
        "lite":4,
        "pro":6
        }
    }



def main():
    DEFAULT_RECIPE_PATH = "/Users/dewanup/projects/git2/NovaCustomizationSamples/NovaPrimeRecipesStaging/sagemaker_training_job_recipes/recipes/supervised-fine-tuning/smtj_ga/nova"
    parser = argparse.ArgumentParser(
        description="SageMaker Nova Training Script Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script is Step 2 of the Nova fine-tuning process. You should have your training and validation
data ready in S3 before running this script. You can prepare your data using nova-data-prep.py (Step 1)
or use your own properly formatted data files directly in S3.

Examples:
  # Basic training job with S3 data using custom recipe
  python nova-tunner.py --job-name my-nova-job --model-name lite \\
    --data-jsonl s3://my-bucket/train.jsonl \\
    --validation-jsonl s3://my-bucket/val.jsonl \\
    --recipe-yaml recipes/my_recipe.yaml

  # Auto-select recipe for SFT training
  python nova-tunner.py --job-name my-sft-job --model-name lite \\
    --training-type sft \\
    --data-jsonl s3://my-bucket/train.jsonl \\
    --validation-jsonl s3://my-bucket/val.jsonl

  # Auto-select recipe for LoRA training
  python nova-tunner.py --job-name my-lora-job --model-name micro \\
    --training-type lora \\
    --data-jsonl s3://my-bucket/train.jsonl \\
    --validation-jsonl s3://my-bucket/val.jsonl

  # Auto-select recipe for DPO training
  python nova-tunner.py --job-name my-dpo-job --model-name pro \\
    --training-type dpo \\
    --data-jsonl s3://my-bucket/train.jsonl \\
    --validation-jsonl s3://my-bucket/val.jsonl

  # Auto-select recipe for DPO+SFT (LoRA DPO) training
  python nova-tunner.py --job-name my-dpo-sft-job --model-name lite \\
    --training-type dpo-sft \\
    --data-jsonl s3://my-bucket/train.jsonl \\
    --validation-jsonl s3://my-bucket/val.jsonl

  # Upload local files to S3 and train with auto-selected recipe
  python nova-tunner.py --job-name my-nova-job --model-name lite \\
    --training-type sft \\
    --data-jsonl local_train.jsonl \\
    --validation-jsonl local_val.jsonl \\
    --upload-data

  # Use custom recipe repository path
  python nova-tunner.py --job-name my-job --model-name micro \\
    --training-type lora \\
    --recipe-repo-path /path/to/custom/recipes \\
    --data-jsonl s3://my-bucket/train.jsonl

  # Dry run to validate configuration
  python nova-tunner.py --job-name test-job --model-name lite \\
    --training-type sft \\
    --data-jsonl s3://my-bucket/train.jsonl \\
    --dry-run
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--job-name", 
        required=True,
        help="Name for the SageMaker training job"
    )
    parser.add_argument(
        "--model-name", 
        required=True,
        help="Model Name(micro, lite, pro)"
    )
    
    # Optional configuration
    parser.add_argument(
        "--role",
        help="IAM role ARN for SageMaker (auto-detected if not provided)"
    )
    
    parser.add_argument(
        "--s3-bucket",
        help="S3 bucket for data and outputs (uses default if not provided)"
    )
    
    parser.add_argument(
        "--max-run",
        type=int,
        default=432000,
        help="Maximum runtime in seconds (default: 432000 = 5 days)"
    )
    
    # Data and recipe options
    parser.add_argument(
        "--data-jsonl",
        help="Path to existing JSONL training data file, or JSONL content as string"
    )

    parser.add_argument(
        "--validation-jsonl",
        help="Path to existing JSONL validation data file, or JSONL content as string (optional)"
    )
    
    parser.add_argument(
        "--recipe-yaml",
        help="Path to existing recipe YAML file, or YAML content as string"
    )
    
    parser.add_argument(
        "--training-type",
        choices=['sft', 'lora', 'dpo', 'dpo-sft'],
        help="Training type to auto-select recipe from repository (sft, lora, dpo, dpo-sft). "
             "When specified, automatically selects the appropriate recipe based on model-name and training-type."
    )
    
    parser.add_argument(
        "--recipe-repo-path",
        help="Path to the recipe repository directory. If not specified, uses the default path."
    )
    
    parser.add_argument(
        "--upload-data",
        action="store_true",
        help="Upload sample data to S3"
    )
    
    # Advanced options
    parser.add_argument(
        "--hyperparameters",
        help="Additional hyperparameters (format: key1=value1,key2=value2)"
    )
    
    parser.add_argument(
        "--recipe-override",
        help="Override specific recipe values (format: key1.key2=value1,key3.key4=value2). "
             "Example: optimizer.learning_rate=0.001,training.epochs=5"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without starting training job"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Determine training mode based on training type
    training_mode = "train"  # default
    if hasattr(args, 'training_type') and args.training_type:
        if args.training_type in ['dpo', 'dpo-sft']:
            training_mode = "dpo"
    
    args.instance_count = get_default_instance_count()[training_mode][args.model_name]
    args.instance_type = get_default_instance_type()[training_mode][args.model_name]
    args.image_uri = get_image_uri()[training_mode]

    # Parse hyperparameters
    args.hyperparameters = parse_hyperparameters(args.hyperparameters)
    
    # Set log level
    if args.verbose:
        os.environ['SAGEMAKER_SUBMIT_DIRECTORY'] = '.'
    
    try:
        run_training_job(args)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
