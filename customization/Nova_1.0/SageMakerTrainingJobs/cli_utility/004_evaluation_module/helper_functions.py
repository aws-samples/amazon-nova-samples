#!/usr/bin/env python3
"""
Helper Functions for Nova Evaluation

This module provides helper functions for creating and running evaluation jobs
for Amazon Nova models using SageMaker Training Jobs.
"""

from typing import Optional
from sagemaker.estimator import Estimator

# Use direct imports instead of relative imports
try:
    from enums_and_configs import ModelType, EvaluationTask
    from nova_evaluator import NovaEvaluator
except ImportError:
    # Fallback to relative imports if direct imports fail
    from .enums_and_configs import ModelType, EvaluationTask
    from .nova_evaluator import NovaEvaluator


def create_text_evaluation_job(
    evaluator: NovaEvaluator,
    job_name: str,
    model_type: ModelType,
    model_path: str,
    task: EvaluationTask,
    output_s3_uri: str,
    subtask: Optional[str] = None,
    recipe_save_path: Optional[str] = None
) -> Estimator:
    """Create and run text benchmark evaluation job.
    
    Args:
        evaluator: Nova evaluator
        job_name: Name for the evaluation job
        model_type: Type of Nova model
        model_path: Model path (base model name or S3 path to fine-tuned model)
        task: Evaluation task
        output_s3_uri: S3 URI for output data
        subtask: Specific subtask (optional)
        recipe_save_path: Path to save the recipe file (optional)
        
    Returns:
        SageMaker estimator
    """
    # Create recipe
    recipe = evaluator.create_text_benchmark_recipe(
        job_name=job_name,
        model_type=model_type,
        model_path=model_path,
        task=task,
        subtask=subtask
    )
    
    # Save recipe
    recipe_path = recipe_save_path or f"{job_name}_recipe.yaml"
    evaluator.save_recipe(recipe, recipe_path)
    
    # Get recommended instance type
    instance_type = evaluator.get_recommended_instance_type(model_type)
    
    # Run evaluation
    estimator = evaluator.run_evaluation(
        recipe_path=recipe_path,
        output_s3_uri=output_s3_uri,
        job_name=job_name,
        instance_type=instance_type
    )
    
    return estimator


def create_custom_dataset_evaluation_job(
    evaluator: NovaEvaluator,
    job_name: str,
    model_type: ModelType,
    model_path: str,
    dataset_s3_uri: str,
    output_s3_uri: str,
    recipe_save_path: Optional[str] = None
) -> Estimator:
    """Create and run custom dataset evaluation job.
    
    Args:
        evaluator: Nova evaluator
        job_name: Name for the evaluation job
        model_type: Type of Nova model
        model_path: Model path (base model name or S3 path to fine-tuned model)
        dataset_s3_uri: S3 URI for custom dataset
        output_s3_uri: S3 URI for output data
        recipe_save_path: Path to save the recipe file (optional)
        
    Returns:
        SageMaker estimator
    """
    # Create recipe
    recipe = evaluator.create_custom_dataset_recipe(
        job_name=job_name,
        model_type=model_type,
        model_path=model_path,
        dataset_s3_uri=dataset_s3_uri
    )
    
    # Save recipe
    recipe_path = recipe_save_path or f"{job_name}_recipe.yaml"
    evaluator.save_recipe(recipe, recipe_path)
    
    # Get recommended instance type
    instance_type = evaluator.get_recommended_instance_type(model_type)
    
    # Run evaluation
    estimator = evaluator.run_evaluation(
        recipe_path=recipe_path,
        output_s3_uri=output_s3_uri,
        job_name=job_name,
        input_s3_uri=dataset_s3_uri,
        instance_type=instance_type
    )
    
    return estimator
