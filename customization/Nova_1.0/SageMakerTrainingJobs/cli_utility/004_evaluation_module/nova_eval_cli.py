#!/usr/bin/env python3
"""
Nova Model Evaluation CLI Tool

Command-line interface for evaluating Amazon Nova models using various benchmarks
and custom datasets through SageMaker Training Jobs.

Usage:
    python nova_eval_cli.py text-benchmark --help
    python nova_eval_cli.py multimodal --help
    python nova_eval_cli.py custom-dataset --help
    python nova_eval_cli.py validate-dataset --help
    python nova_eval_cli.py list-subtasks --help
    python nova_eval_cli.py create-recipe --help
    python nova_eval_cli.py analyze-results --help
"""

import argparse
import json
import sys
import os
import tempfile
import boto3
from pathlib import Path
import sagemaker

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the current directory to sys.path if needed
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import directly from files
try:
    from enums_and_configs import (
        ModelType, 
        EvaluationTask, 
        EvaluationStrategy,
        EvaluationMetric,
        InferenceConfig
    )
    from nova_evaluator import NovaEvaluator
    from eval_result_analyzer import EvalResultAnalyzer
    from helper_functions import (
        create_text_evaluation_job,
        create_custom_dataset_evaluation_job
    )
    
    # Import the format converter
    try:
        from format_converter import convert_file
        HAS_FORMAT_CONVERTER = True
    except ImportError:
        HAS_FORMAT_CONVERTER = False
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running the script from the correct directory.")
    sys.exit(1)


def setup_sagemaker(role=None):
    """Initialize SageMaker session and role
    
    Args:
        role (str, optional): IAM role ARN for SageMaker. If not provided, will attempt to auto-detect.
    
    Returns:
        tuple: (sagemaker_session, role)
    """
    try:
        sagemaker_session = sagemaker.Session()
        if not role:
            role = sagemaker.get_execution_role()
        return sagemaker_session, role
    except Exception as e:
        print(f"Error setting up SageMaker: {e}")
        print("Make sure you're running in a SageMaker environment or have proper AWS credentials configured.")
        sys.exit(1)


def get_model_type(model_name: str) -> ModelType:
    """Convert string model name to ModelType enum"""
    model_mapping = {
        'micro': ModelType.NOVA_MICRO,
        'lite': ModelType.NOVA_LITE,
        'pro': ModelType.NOVA_PRO
    }
    
    if model_name.lower() not in model_mapping:
        print(f"Error: Invalid model type '{model_name}'. Choose from: {list(model_mapping.keys())}")
        sys.exit(1)
    
    return model_mapping[model_name.lower()]


def get_evaluation_task(task_name: str) -> EvaluationTask:
    """Convert string task name to EvaluationTask enum"""
    task_mapping = {
        'mmlu': EvaluationTask.MMLU,
        'mmlu_pro': EvaluationTask.MMLU_PRO,
        'bbh': EvaluationTask.BBH,
        'gpqa': EvaluationTask.GPQA,
        'math': EvaluationTask.MATH,
        'strong_reject': EvaluationTask.STRONG_REJECT,
        'ifeval': EvaluationTask.IFEVAL,
        'gen_qa': EvaluationTask.GEN_QA,
        'mmmu': EvaluationTask.MMMU
    }
    
    if task_name.lower() not in task_mapping:
        print(f"Error: Invalid task '{task_name}'. Choose from: {list(task_mapping.keys())}")
        sys.exit(1)
    
    return task_mapping[task_name.lower()]


def cmd_text_benchmark(args):
    """Run text benchmark evaluation"""
    print(f"Starting text benchmark evaluation...")
    print(f"Job Name: {args.job_name}")
    print(f"Model: {args.model_type}")
    print(f"Task: {args.task}")
    print(f"Subtask: {args.subtask or 'None'}")
    
    # Setup SageMaker
    sagemaker_session, role = setup_sagemaker(args.role)
    evaluator = NovaEvaluator(sagemaker_session=sagemaker_session, role=role)
    
    # Convert arguments
    model_type = get_model_type(args.model_type)
    task = get_evaluation_task(args.task)
    
    # Validate subtask if provided
    if args.subtask:
        available_subtasks = evaluator.get_available_subtasks(task)
        if available_subtasks and args.subtask not in available_subtasks:
            print(f"Error: Invalid subtask '{args.subtask}' for task '{args.task}'")
            print(f"Available subtasks: {available_subtasks[:10]}...")  # Show first 10
            sys.exit(1)
    
    # Create inference config if parameters provided
    inference_config = None
    if any([args.max_tokens, args.temperature is not None, args.top_p is not None, args.top_k is not None]):
        inference_config = InferenceConfig(
            max_new_tokens=args.max_tokens or 8196,
            temperature=args.temperature if args.temperature is not None else 0.0,
            top_p=args.top_p if args.top_p is not None else 1.0,
            top_k=args.top_k if args.top_k is not None else -1
        )
    
    try:
        # Run evaluation
        estimator = create_text_evaluation_job(
            evaluator=evaluator,
            job_name=args.job_name,
            model_type=model_type,
            model_path=args.model_path,
            task=task,
            output_s3_uri=args.output_s3_uri,
            subtask=args.subtask,
            recipe_save_path=args.recipe_path
        )
        
        print(f"✅ Evaluation job started successfully!")
        print(f"Job Name: {estimator.latest_training_job.name}")
        print(f"Job ARN: {estimator.latest_training_job.job_arn}")
        print(f"Output will be saved to: {args.output_s3_uri}")
        
        if args.wait:
            print("Waiting for job to complete...")
            estimator.latest_training_job.wait()
            status = estimator.latest_training_job.describe()['TrainingJobStatus']
            print(f"Job completed with status: {status}")
            
    except Exception as e:
        print(f"❌ Error running evaluation: {e}")
        sys.exit(1)


def cmd_custom_dataset(args):
    """Run custom dataset evaluation"""
    print(f"Starting custom dataset evaluation...")
    print(f"Job Name: {args.job_name}")
    print(f"Model: {args.model_type}")
    print(f"Dataset: {args.dataset_s3_uri}")
    
    # Setup SageMaker
    sagemaker_session, role = setup_sagemaker(args.role)
    evaluator = NovaEvaluator(sagemaker_session=sagemaker_session, role=role)
    
    # Convert arguments
    model_type = get_model_type(args.model_type)
    
    # Create inference config if parameters provided
    inference_config = None
    if any([args.max_tokens, args.temperature is not None, args.top_p is not None, args.top_k is not None]):
        inference_config = InferenceConfig(
            max_new_tokens=args.max_tokens or 12000,
            temperature=args.temperature if args.temperature is not None else 0.0,
            top_p=args.top_p if args.top_p is not None else 1.0,
            top_k=args.top_k if args.top_k is not None else -1
        )
    
    # Handle Bedrock format conversion if needed
    dataset_s3_uri = args.dataset_s3_uri
    if args.is_bedrock_format:
        if not HAS_FORMAT_CONVERTER:
            print("❌ Error: format_converter module not found. Cannot convert Bedrock format.")
            sys.exit(1)
            
        print(f"Converting dataset from Bedrock Conversation Format to gen_qa format...")
        
        # Download the dataset from S3
        local_dataset_path = download_from_s3(args.dataset_s3_uri)
        
        # Create a temporary file for the converted dataset
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as tmp_file:
            converted_path = tmp_file.name
        
        # Convert the file
        try:
            converted_count = convert_file(local_dataset_path, converted_path, True)
            if converted_count > 0:
                print(f"✅ Successfully converted {converted_count} entries")
                
                # Upload the converted file back to S3 with the name gen_qa.jsonl
                s3_client = boto3.client('s3')
                
                # Parse the original S3 URI to get the bucket and prefix
                from urllib.parse import urlparse
                parsed = urlparse(args.dataset_s3_uri)
                bucket = parsed.netloc
                key_parts = parsed.path.lstrip('/').split('/')
                
                # Create a new key with the same prefix but with gen_qa.jsonl as the filename
                if len(key_parts) > 1:
                    # If there's a prefix, use it
                    prefix = '/'.join(key_parts[:-1])
                    new_key = f"{prefix}/gen_qa.jsonl"
                else:
                    # If there's no prefix, just use gen_qa.jsonl
                    new_key = "gen_qa.jsonl"
                
                print(f"Uploading converted file to s3://{bucket}/{new_key}...")
                s3_client.upload_file(converted_path, bucket, new_key)
                
                # Update the dataset S3 URI to point to the converted file
                dataset_s3_uri = f"s3://{bucket}/{new_key}"
                print(f"Using converted dataset: {dataset_s3_uri}")
                
                # Clean up temporary files
                os.unlink(local_dataset_path)
                os.unlink(converted_path)
            else:
                print("❌ No entries were converted")
                os.unlink(local_dataset_path)
                os.unlink(converted_path)
                sys.exit(1)
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            if os.path.exists(local_dataset_path):
                os.unlink(local_dataset_path)
            if os.path.exists(converted_path):
                os.unlink(converted_path)
            sys.exit(1)
    
    try:
        # Run evaluation
        estimator = create_custom_dataset_evaluation_job(
            evaluator=evaluator,
            job_name=args.job_name,
            model_type=model_type,
            model_path=args.model_path,
            dataset_s3_uri=dataset_s3_uri,
            output_s3_uri=args.output_s3_uri,
            recipe_save_path=args.recipe_path
        )
        
        print(f"✅ Custom dataset evaluation job started successfully!")
        print(f"Job Name: {estimator.latest_training_job.name}")
        print(f"Job ARN: {estimator.latest_training_job.job_arn}")
        print(f"Output will be saved to: {args.output_s3_uri}")
        
        if args.wait:
            print("Waiting for job to complete...")
            estimator.latest_training_job.wait()
            status = estimator.latest_training_job.describe()['TrainingJobStatus']
            print(f"Job completed with status: {status}")
            
    except Exception as e:
        print(f"❌ Error running custom dataset evaluation: {e}")
        sys.exit(1)


def cmd_multimodal(args):
    """Run multimodal benchmark evaluation"""
    print(f"Starting multimodal benchmark evaluation...")
    print(f"Job Name: {args.job_name}")
    print(f"Model: {args.model_type}")
    print(f"Subtask: {args.subtask or 'None'}")
    
    # Setup SageMaker
    sagemaker_session, role = setup_sagemaker(args.role)
    evaluator = NovaEvaluator(sagemaker_session=sagemaker_session, role=role)
    
    # Convert arguments
    model_type = get_model_type(args.model_type)
    
    # Validate model type for multimodal
    if model_type == ModelType.NOVA_MICRO:
        print("❌ Error: Multimodal evaluation is not supported for Nova Micro model")
        print("Please use Nova Lite or Nova Pro")
        sys.exit(1)
    
    # Validate subtask if provided
    if args.subtask:
        available_subtasks = evaluator.get_available_subtasks(EvaluationTask.MMMU)
        if args.subtask not in available_subtasks:
            print(f"Error: Invalid subtask '{args.subtask}' for MMMU")
            print(f"Available subtasks: {available_subtasks[:10]}...")  # Show first 10
            sys.exit(1)
    
    # Create inference config if parameters provided
    inference_config = None
    if any([args.max_tokens, args.temperature is not None, args.top_p is not None, args.top_k is not None]):
        inference_config = InferenceConfig(
            max_new_tokens=args.max_tokens or 8196,
            temperature=args.temperature if args.temperature is not None else 0.0,
            top_p=args.top_p if args.top_p is not None else 1.0,
            top_k=args.top_k if args.top_k is not None else -1
        )
    
    try:
        # Create recipe
        recipe = evaluator.create_multimodal_benchmark_recipe(
            job_name=args.job_name,
            model_type=model_type,
            model_path=args.model_path,
            subtask=args.subtask,
            inference_config=inference_config
        )
        
        # Update data_s3_path in the recipe if dataset_s3_uri is provided
        if args.dataset_s3_uri:
            recipe["run"]["data_s3_path"] = args.dataset_s3_uri
        
        # Save recipe
        recipe_path = args.recipe_path or f"{args.job_name}_recipe.yaml"
        evaluator.save_recipe(recipe, recipe_path)
        print(f"Recipe saved to: {recipe_path}")
        
        # Get recommended instance type
        instance_type = evaluator.get_recommended_instance_type(model_type)
        
        # Run evaluation
        estimator = evaluator.run_evaluation(
            recipe_path=recipe_path,
            output_s3_uri=args.output_s3_uri,
            job_name=args.job_name,
            input_s3_uri=args.dataset_s3_uri,
            instance_type=instance_type
        )
        
        print(f"✅ Multimodal evaluation job started successfully!")
        print(f"Job Name: {estimator.latest_training_job.name}")
        print(f"Job ARN: {estimator.latest_training_job.job_arn}")
        print(f"Output will be saved to: {args.output_s3_uri}")
        
        if args.wait:
            print("Waiting for job to complete...")
            estimator.latest_training_job.wait()
            status = estimator.latest_training_job.describe()['TrainingJobStatus']
            print(f"Job completed with status: {status}")
            
    except Exception as e:
        print(f"❌ Error running multimodal evaluation: {e}")
        sys.exit(1)


def download_from_s3(s3_uri, local_path=None, force_gen_qa_name=False):
    """Download a file from S3 to a local path"""
    try:
        # Parse S3 URI
        from urllib.parse import urlparse
        parsed = urlparse(s3_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        
        # Create a temporary file if no local path provided
        if not local_path:
            # If force_gen_qa_name is True, use gen_qa.jsonl as the filename
            if force_gen_qa_name:
                temp_dir = tempfile.mkdtemp()
                local_path = os.path.join(temp_dir, 'gen_qa.jsonl')
            else:
                with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as tmp_file:
                    local_path = tmp_file.name
        
        # Download the file
        print(f"Downloading {s3_uri} to {local_path}...")
        s3_client = boto3.client('s3')
        s3_client.download_file(bucket, key, local_path)
        print(f"✅ Download successful")
        
        return local_path
    except Exception as e:
        print(f"❌ Error downloading from S3: {e}")
        if local_path and os.path.exists(local_path):
            os.unlink(local_path)
        sys.exit(1)


def cmd_validate_dataset(args):
    """Validate custom dataset format"""
    print(f"Validating dataset: {args.dataset_path}")
    
    # Check if the dataset path is an S3 URI
    is_s3_path = args.dataset_path.startswith('s3://')
    local_files_to_cleanup = []
    
    # Download from S3 if needed
    dataset_path = args.dataset_path
    if is_s3_path:
        # For gen_qa format, ensure the file is named gen_qa.jsonl
        force_gen_qa_name = not args.is_bedrock_format
        dataset_path = download_from_s3(args.dataset_path, force_gen_qa_name=force_gen_qa_name)
        local_files_to_cleanup.append(dataset_path)
    
    # Handle format conversion if needed
    if args.is_bedrock_format:
        if not HAS_FORMAT_CONVERTER:
            print("❌ Error: format_converter module not found. Cannot convert Bedrock format.")
            sys.exit(1)
            
        print(f"Converting dataset from Bedrock Conversation Format to gen_qa format...")
        # Create a temporary file for the converted dataset
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as tmp_file:
            converted_path = tmp_file.name
            local_files_to_cleanup.append(converted_path)
        
        # Convert the file
        try:
            converted_count = convert_file(dataset_path, converted_path, True)
            if converted_count > 0:
                print(f"✅ Successfully converted {converted_count} entries")
                # Use the converted file for validation
                dataset_path = converted_path
            else:
                print("❌ No entries were converted")
                for file_path in local_files_to_cleanup:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                sys.exit(1)
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            for file_path in local_files_to_cleanup:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            sys.exit(1)
    
    evaluator = NovaEvaluator()
    
    try:
        if evaluator.validate_custom_dataset(dataset_path):
            print("✅ Dataset validation passed!")
            
            # Show dataset statistics
            try:
                with open(dataset_path, 'r') as f:
                    lines = f.readlines()
                    total_lines = len(lines)
                    
                    # Count entries with system prompts
                    system_count = 0
                    for line in lines:
                        try:
                            data = json.loads(line.strip())
                            if 'system' in data:
                                system_count += 1
                        except:
                            continue
                    
                    print(f"📊 Dataset Statistics:")
                    print(f"   Total entries: {total_lines}")
                    print(f"   Entries with system prompts: {system_count}")
                    print(f"   Entries without system prompts: {total_lines - system_count}")
                    
            except Exception as e:
                print(f"Warning: Could not read dataset statistics: {e}")
        else:
            print("❌ Dataset validation failed!")
            sys.exit(1)
    finally:
        # Clean up temporary files
        for file_path in local_files_to_cleanup:
            if os.path.exists(file_path):
                os.unlink(file_path)
                print(f"Cleaned up temporary file: {file_path}")


def cmd_list_subtasks(args):
    """List available subtasks for a given task"""
    evaluator = NovaEvaluator()
    task = get_evaluation_task(args.task)
    
    subtasks = evaluator.get_available_subtasks(task)
    
    if subtasks:
        print(f"Available subtasks for {args.task}:")
        for i, subtask in enumerate(subtasks, 1):
            print(f"  {i:2d}. {subtask}")
        print(f"\nTotal: {len(subtasks)} subtasks")
    else:
        print(f"No subtasks available for {args.task}")


def cmd_create_recipe(args):
    """Create evaluation recipe without running the job"""
    print(f"Creating evaluation recipe...")
    
    # Setup evaluator
    evaluator = NovaEvaluator()
    
    # Convert arguments
    model_type = get_model_type(args.model_type)
    task = get_evaluation_task(args.task)
    
    # Create inference config
    inference_config = InferenceConfig(
        max_new_tokens=args.max_tokens or 8196,
        temperature=args.temperature if args.temperature is not None else 0.0,
        top_p=args.top_p if args.top_p is not None else 1.0,
        top_k=args.top_k if args.top_k is not None else -1
    )
    
    try:
        if task == EvaluationTask.MMMU:
            recipe = evaluator.create_multimodal_benchmark_recipe(
                job_name=args.job_name,
                model_type=model_type,
                model_path=args.model_path,
                subtask=args.subtask,
                inference_config=inference_config
            )
        elif task == EvaluationTask.GEN_QA:
            recipe = evaluator.create_custom_dataset_recipe(
                job_name=args.job_name,
                model_type=model_type,
                model_path=args.model_path,
                inference_config=inference_config
            )
        else:
            recipe = evaluator.create_text_benchmark_recipe(
                job_name=args.job_name,
                model_type=model_type,
                model_path=args.model_path,
                task=task,
                subtask=args.subtask,
                inference_config=inference_config
            )
        
        # Save recipe
        output_path = args.output or f"{args.job_name}_recipe.yaml"
        evaluator.save_recipe(recipe, output_path)
        
        print(f"✅ Recipe created successfully!")
        print(f"Saved to: {output_path}")
        
        if args.show:
            print(f"\nRecipe content:")
            print("=" * 50)
            with open(output_path, 'r') as f:
                print(f.read())
                
    except Exception as e:
        print(f"❌ Error creating recipe: {e}")
        sys.exit(1)


def cmd_analyze_results(args):
    """Analyze evaluation results after job completion"""
    print(f"Analyzing evaluation results for job: {args.job_name}")
    
    # Setup SageMaker session
    sagemaker_session = None
    try:
        sagemaker_session = sagemaker.Session()
        print("✅ SageMaker session initialized")
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize SageMaker session: {e}")
        if not args.output_uri:
            print("Either provide --output-uri or ensure AWS credentials are configured")
            sys.exit(1)
    
    # Initialize analyzer
    analyzer = EvalResultAnalyzer(
        sagemaker_session=sagemaker_session,
        output_dir=args.output_dir
    )
    
    try:
        # Get output URI if not provided
        output_uri = args.output_uri
        if not output_uri:
            try:
                output_uri = analyzer.get_job_output_uri(args.job_name)
                print(f"Found output URI: {output_uri}")
            except Exception as e:
                print(f"❌ Error getting output URI from job name: {e}")
                sys.exit(1)
        
        # Download and extract output
        extract_dir = analyzer.download_and_extract_output(args.job_name, output_uri)
        
        # Get metrics if requested
        if args.metrics:
            metrics = analyzer.get_metrics(args.job_name, extract_dir)
            print("\n📊 Evaluation Metrics:")
            print("=" * 50)
            print(json.dumps(metrics, indent=2))
            
            # Save metrics to file if requested
            if args.save_metrics:
                metrics_file = args.save_metrics
                with open(metrics_file, 'w') as f:
                    json.dump(metrics, f, indent=2)
                print(f"✅ Metrics saved to: {metrics_file}")
        
        # Get raw inferences if requested
        if args.raw_inferences:
            inferences_dir = analyzer.get_raw_inferences(args.job_name, extract_dir)
            print(f"\n📝 Raw inferences available at: {inferences_dir}")
            
            # Convert parquet to JSONL if requested
            if args.convert_parquet:
                try:
                    # Find the first directory with parquet files
                    parquet_dir = None
                    for root, dirs, files in os.walk(inferences_dir):
                        if any(f.endswith('.parquet') for f in files):
                            parquet_dir = root
                            break
                    
                    if parquet_dir:
                        output_file = args.output_jsonl or os.path.join(inferences_dir, "raw_inferences.jsonl")
                        jsonl_path = analyzer.convert_parquet_to_jsonl(parquet_dir, output_file)
                        print(f"✅ Converted parquet files to JSONL: {jsonl_path}")
                    else:
                        print("❌ No parquet directory found for conversion")
                except Exception as e:
                    print(f"❌ Error converting parquet to JSONL: {e}")
            
            # Create visual failure analysis UI if requested
            if args.visual_failure_analysis:
                try:
                    # Look for JSONL files in the inferences directory
                    jsonl_files = [f for f in os.listdir(inferences_dir) if f.endswith('.jsonl')]
                    jsonl_path = None
                    
                    if jsonl_files:
                        # Use the first JSONL file found
                        jsonl_path = os.path.join(inferences_dir, jsonl_files[0])
                        print(f"Using existing JSONL file for visual failure analysis: {jsonl_path}")
                    elif args.convert_parquet:
                        # If we converted parquet to JSONL, use that file
                        jsonl_path = output_file
                        print(f"Using converted JSONL file for visual failure analysis: {jsonl_path}")
                    else:
                        print("No JSONL files found. Use --convert-parquet to convert parquet files.")
                        sys.exit(1)
                    
                    # Create the visual failure analysis UI
                    output_dir = os.path.join(args.output_dir, args.job_name, "visual_analysis")
                    analyzer.create_visual_failure_analysis(jsonl_path, output_dir, args.ui_port)
                except Exception as e:
                    print(f"❌ Error creating visual failure analysis UI: {e}")
        
        # Get TensorBoard logs if requested
        if args.tensorboard:
            try:
                tensorboard_dir = analyzer.get_tensorboard_logs(args.job_name, extract_dir)
                print(f"\n📈 TensorBoard logs available at: {tensorboard_dir}")
                
                # Visualize TensorBoard if requested
                if args.visualize:
                    try:
                        tensorboard_process, port = analyzer.visualize_tensorboard(
                            tensorboard_dir, 
                            port=args.port
                        )
                        
                        # Keep the process running until user interrupts
                        try:
                            print("\nTensorBoard is running. Press Ctrl+C to stop...")
                            tensorboard_process.wait()
                        except KeyboardInterrupt:
                            print("\nStopping TensorBoard...")
                            tensorboard_process.terminate()
                            print("TensorBoard stopped")
                    except Exception as e:
                        print(f"❌ Error visualizing TensorBoard: {e}")
            except Exception as e:
                print(f"❌ Error getting TensorBoard logs: {e}")
        
        print("\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error analyzing evaluation results: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Nova Model Evaluation CLI Tool (Modular Version)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Text benchmark command
    text_parser = subparsers.add_parser('text-benchmark', help='Run text benchmark evaluation')
    text_parser.add_argument('--job-name', required=True, help='Name for the evaluation job')
    text_parser.add_argument('--model-type', required=True, choices=['micro', 'lite', 'pro'], 
                           help='Nova model type')
    text_parser.add_argument('--model-path', required=True, 
                           help='Model path (base model name or S3 path to fine-tuned model)')
    text_parser.add_argument('--task', required=True, 
                           choices=['mmlu', 'mmlu_pro', 'bbh', 'gpqa', 'math', 'strong_reject', 'ifeval'],
                           help='Evaluation task')
    text_parser.add_argument('--subtask', help='Specific subtask (optional)')
    text_parser.add_argument('--output-s3-uri', required=True, help='S3 URI for output data')
    text_parser.add_argument('--recipe-path', help='Path to save the recipe file')
    text_parser.add_argument('--max-tokens', type=int, help='Maximum tokens to generate')
    text_parser.add_argument('--temperature', type=float, help='Sampling temperature')
    text_parser.add_argument('--top-p', type=float, help='Top-p sampling parameter')
    text_parser.add_argument('--top-k', type=int, help='Top-k sampling parameter')
    text_parser.add_argument('--wait', action='store_true', help='Wait for job completion')
    text_parser.add_argument('--role', help='IAM role ARN for SageMaker (auto-detected if not provided)')
    text_parser.set_defaults(func=cmd_text_benchmark)
    
    # Multimodal command
    multimodal_parser = subparsers.add_parser('multimodal', help='Run multimodal benchmark evaluation')
    multimodal_parser.add_argument('--job-name', required=True, help='Name for the evaluation job')
    multimodal_parser.add_argument('--model-type', required=True, choices=['lite', 'pro'], 
                                 help='Nova model type (Micro not supported)')
    multimodal_parser.add_argument('--model-path', required=True, 
                                 help='Model path (base model name or S3 path to fine-tuned model)')
    multimodal_parser.add_argument('--subtask', help='MMMU subtask (optional)')
    multimodal_parser.add_argument('--dataset-s3-uri', required=True, help='S3 URI for MMMU dataset')
    multimodal_parser.add_argument('--output-s3-uri', required=True, help='S3 URI for output data')
    multimodal_parser.add_argument('--recipe-path', help='Path to save the recipe file')
    multimodal_parser.add_argument('--max-tokens', type=int, help='Maximum tokens to generate')
    multimodal_parser.add_argument('--temperature', type=float, help='Sampling temperature')
    multimodal_parser.add_argument('--top-p', type=float, help='Top-p sampling parameter')
    multimodal_parser.add_argument('--top-k', type=int, help='Top-k sampling parameter')
    multimodal_parser.add_argument('--wait', action='store_true', help='Wait for job completion')
    multimodal_parser.add_argument('--role', help='IAM role ARN for SageMaker (auto-detected if not provided)')
    multimodal_parser.set_defaults(func=cmd_multimodal)
    
    # Custom dataset command
    custom_parser = subparsers.add_parser('custom-dataset', help='Run custom dataset evaluation')
    custom_parser.add_argument('--job-name', required=True, help='Name for the evaluation job')
    custom_parser.add_argument('--model-type', required=True, choices=['micro', 'lite', 'pro'], 
                             help='Nova model type')
    custom_parser.add_argument('--model-path', required=True, 
                             help='Model path (base model name or S3 path to fine-tuned model)')
    custom_parser.add_argument('--dataset-s3-uri', required=True, help='S3 URI for custom dataset')
    custom_parser.add_argument('--output-s3-uri', required=True, help='S3 URI for output data')
    custom_parser.add_argument('--recipe-path', help='Path to save the recipe file')
    custom_parser.add_argument('--max-tokens', type=int, help='Maximum tokens to generate')
    custom_parser.add_argument('--temperature', type=float, help='Sampling temperature')
    custom_parser.add_argument('--top-p', type=float, help='Top-p sampling parameter')
    custom_parser.add_argument('--top-k', type=int, help='Top-k sampling parameter')
    custom_parser.add_argument('--wait', action='store_true', help='Wait for job completion')
    custom_parser.add_argument('--is-bedrock-format', action='store_true',
                             help='Flag indicating the dataset is in Bedrock Conversation Format')
    custom_parser.add_argument('--role', help='IAM role ARN for SageMaker (auto-detected if not provided)')
    custom_parser.set_defaults(func=cmd_custom_dataset)
    
    # Validate dataset command
    validate_parser = subparsers.add_parser('validate-dataset', help='Validate custom dataset format')
    validate_parser.add_argument('--dataset-path', required=True, 
                               help='Path to the dataset file (local path or S3 URI)')
    validate_parser.add_argument('--is-bedrock-format', action='store_true',
                               help='Flag indicating the dataset is in Bedrock Conversation Format')
    validate_parser.set_defaults(func=cmd_validate_dataset)
    
    # List subtasks command
    subtasks_parser = subparsers.add_parser('list-subtasks', help='List available subtasks for a task')
    subtasks_parser.add_argument('--task', required=True, 
                               choices=['mmlu', 'mmlu_pro', 'bbh', 'gpqa', 'math', 'strong_reject', 'ifeval', 'mmmu'],
                               help='Evaluation task')
    subtasks_parser.set_defaults(func=cmd_list_subtasks)
    
    # Create recipe command
    recipe_parser = subparsers.add_parser('create-recipe', help='Create evaluation recipe without running job')
    recipe_parser.add_argument('--job-name', required=True, help='Name for the evaluation job')
    recipe_parser.add_argument('--model-type', required=True, choices=['micro', 'lite', 'pro'], 
                             help='Nova model type')
    recipe_parser.add_argument('--model-path', required=True, 
                             help='Model path (base model name or S3 path to fine-tuned model)')
    recipe_parser.add_argument('--task', required=True, 
                             choices=['mmlu', 'mmlu_pro', 'bbh', 'gpqa', 'math', 'strong_reject', 'ifeval', 'gen_qa', 'mmmu'],
                             help='Evaluation task')
    recipe_parser.add_argument('--subtask', help='Specific subtask (optional)')
    recipe_parser.add_argument('--output', help='Output path for recipe file')
    recipe_parser.add_argument('--show', action='store_true', help='Show recipe content after creation')
    recipe_parser.add_argument('--max-tokens', type=int, help='Maximum tokens to generate')
    recipe_parser.add_argument('--temperature', type=float, help='Sampling temperature')
    recipe_parser.add_argument('--top-p', type=float, help='Top-p sampling parameter')
    recipe_parser.add_argument('--top-k', type=int, help='Top-k sampling parameter')
    recipe_parser.set_defaults(func=cmd_create_recipe)
    
    # Analyze results command
    analyze_parser = subparsers.add_parser('analyze-results', help='Analyze evaluation results')
    analyze_parser.add_argument('--job-name', required=True, help='Name of the completed training job')
    analyze_parser.add_argument('--output-uri', help='S3 URI for the job output (optional if using SageMaker)')
    
    # Use the module directory by default
    module_dir = os.path.dirname(os.path.abspath(__file__))
    default_output_dir = os.path.join(module_dir, "eval_results")
    analyze_parser.add_argument('--output-dir', default=default_output_dir, help='Directory to store extracted results')
    analyze_parser.add_argument('--metrics', action='store_true', help='Get evaluation metrics')
    analyze_parser.add_argument('--save-metrics', help='Save metrics to file')
    analyze_parser.add_argument('--raw-inferences', action='store_true', help='Get raw inference results')
    analyze_parser.add_argument('--convert-parquet', action='store_true', help='Convert parquet files to JSONL format')
    analyze_parser.add_argument('--output-jsonl', help='Path to save the converted JSONL file')
    analyze_parser.add_argument('--visual-failure-analysis', action='store_true', help='Create a visual UI for analyzing failures')
    analyze_parser.add_argument('--tensorboard', action='store_true', help='Get TensorBoard logs')
    analyze_parser.add_argument('--visualize', action='store_true', help='Visualize TensorBoard logs')
    analyze_parser.add_argument('--port', type=int, default=6006, help='Port for TensorBoard server')
    analyze_parser.add_argument('--ui-port', type=int, default=8000, help='Port for visual failure analysis UI server')
    analyze_parser.set_defaults(func=cmd_analyze_results)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    args.func(args)


if __name__ == '__main__':
    main()
