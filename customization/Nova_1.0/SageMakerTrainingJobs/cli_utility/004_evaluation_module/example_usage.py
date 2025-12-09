#!/usr/bin/env python3
"""
Example Usage of Nova Evaluation Module

This script demonstrates how to use the modular structure of the Nova Evaluation Module.
"""

import os
import sys
import boto3
import sagemaker
from sagemaker.session import Session

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the current directory to sys.path if needed
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import directly from the module files
from enums_and_configs import ModelType, EvaluationTask
from nova_evaluator import NovaEvaluator
from eval_result_analyzer import EvalResultAnalyzer
from helper_functions import create_text_evaluation_job, create_custom_dataset_evaluation_job


def setup_sagemaker():
    """Set up SageMaker session and role."""
    # Get SageMaker session
    boto_session = boto3.Session()
    sagemaker_session = Session(boto_session=boto_session)
    
    # Get SageMaker execution role
    # In a real scenario, you would use your actual role ARN
    role = "arn:aws:iam::123456789012:role/SageMakerRole"
    
    return sagemaker_session, role


def run_text_benchmark_evaluation():
    """Run a text benchmark evaluation job."""
    # Set up SageMaker
    sagemaker_session, role = setup_sagemaker()
    
    # Create evaluator
    evaluator = NovaEvaluator(sagemaker_session=sagemaker_session, role=role)
    
    # Define evaluation parameters
    job_name = "nova-mmlu-eval"
    model_type = ModelType.NOVA_LITE
    model_path = "amazon.nova-lite-v1:0:300k"  # Base model
    task = EvaluationTask.MMLU
    subtask = "high_school_mathematics"
    output_s3_uri = "s3://my-bucket/output/"
    
    # Create and run evaluation job
    print(f"Running {task.value} evaluation with subtask {subtask}...")
    
    # In a real scenario, you would uncomment this code
    # estimator = create_text_evaluation_job(
    #     evaluator=evaluator,
    #     job_name=job_name,
    #     model_type=model_type,
    #     model_path=model_path,
    #     task=task,
    #     output_s3_uri=output_s3_uri,
    #     subtask=subtask
    # )
    
    print("Evaluation job submitted successfully!")
    
    # For demonstration purposes, we'll just print the job details
    print(f"Job Name: {job_name}")
    print(f"Model Type: {model_type.value}")
    print(f"Task: {task.value}")
    print(f"Subtask: {subtask}")
    print(f"Output S3 URI: {output_s3_uri}")


def run_custom_dataset_evaluation():
    """Run a custom dataset evaluation job."""
    # Set up SageMaker
    sagemaker_session, role = setup_sagemaker()
    
    # Create evaluator
    evaluator = NovaEvaluator(sagemaker_session=sagemaker_session, role=role)
    
    # Define evaluation parameters
    job_name = "nova-custom-eval"
    model_type = ModelType.NOVA_LITE
    model_path = "s3://my-bucket/models/nova-lite-finetuned/"  # Fine-tuned model
    dataset_s3_uri = "s3://my-bucket/datasets/custom_eval_dataset.jsonl"
    output_s3_uri = "s3://my-bucket/output/"
    
    # Create and run evaluation job
    print(f"Running custom dataset evaluation...")
    
    # In a real scenario, you would uncomment this code
    # estimator = create_custom_dataset_evaluation_job(
    #     evaluator=evaluator,
    #     job_name=job_name,
    #     model_type=model_type,
    #     model_path=model_path,
    #     dataset_s3_uri=dataset_s3_uri,
    #     output_s3_uri=output_s3_uri
    # )
    
    print("Evaluation job submitted successfully!")
    
    # For demonstration purposes, we'll just print the job details
    print(f"Job Name: {job_name}")
    print(f"Model Type: {model_type.value}")
    print(f"Dataset S3 URI: {dataset_s3_uri}")
    print(f"Output S3 URI: {output_s3_uri}")


def analyze_evaluation_results():
    """Analyze evaluation results."""
    # Set up SageMaker
    sagemaker_session, role = setup_sagemaker()
    
    # Create analyzer
    analyzer = EvalResultAnalyzer(sagemaker_session=sagemaker_session)
    
    # Define job name
    job_name = "nova-mmlu-eval-2025-06-25-12-34-56"
    
    # In a real scenario, you would uncomment this code
    # # Download and extract output
    # extract_dir = analyzer.download_and_extract_output(job_name)
    #
    # # Get metrics
    # metrics = analyzer.get_metrics(job_name, extract_dir)
    # print(f"Metrics: {metrics}")
    #
    # # Get raw inferences
    # raw_inferences_dir = analyzer.get_raw_inferences(job_name, extract_dir)
    # print(f"Raw inferences directory: {raw_inferences_dir}")
    #
    # # Get TensorBoard logs
    # tensorboard_dir = analyzer.get_tensorboard_logs(job_name, extract_dir)
    # print(f"TensorBoard logs directory: {tensorboard_dir}")
    #
    # # Visualize TensorBoard logs
    # analyzer.visualize_tensorboard(tensorboard_dir)
    
    print("Analysis completed successfully!")


def main():
    """Main function."""
    print("Nova Evaluation Module - Example Usage")
    print("=====================================")
    
    # Run text benchmark evaluation
    print("\n1. Running Text Benchmark Evaluation")
    print("----------------------------------")
    run_text_benchmark_evaluation()
    
    # Run custom dataset evaluation
    print("\n2. Running Custom Dataset Evaluation")
    print("----------------------------------")
    run_custom_dataset_evaluation()
    
    # Analyze evaluation results
    print("\n3. Analyzing Evaluation Results")
    print("-----------------------------")
    analyze_evaluation_results()


if __name__ == "__main__":
    main()
