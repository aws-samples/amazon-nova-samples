#!/usr/bin/env python3
"""
Nova Evaluator Class

This module provides the NovaEvaluator class for creating and running evaluation jobs
for Amazon Nova models using SageMaker Training Jobs.
"""

import os
import yaml
import datetime
from typing import Dict, List, Optional, Any
import boto3
import sagemaker
from sagemaker.estimator import Estimator
from sagemaker.pytorch import PyTorch
from sagemaker.inputs import TrainingInput

# Use direct imports instead of relative imports
try:
    from enums_and_configs import (
        ModelType,
        EvaluationTask,
        EvaluationStrategy,
        EvaluationMetric,
        RunConfig,
        EvaluationConfig,
        InferenceConfig
    )
except ImportError:
    # Fallback to relative imports if direct imports fail
    from .enums_and_configs import (
        ModelType,
        EvaluationTask,
        EvaluationStrategy,
        EvaluationMetric,
        RunConfig,
        EvaluationConfig,
        InferenceConfig
    )


class NovaEvaluator:
    """Main class for evaluating Nova models."""
    
    def __init__(
        self,
        sagemaker_session: Optional[sagemaker.Session] = None,
        role: Optional[str] = None
    ):
        """Initialize Nova evaluator.
        
        Args:
            sagemaker_session: SageMaker session
            role: IAM role for SageMaker
        """
        self.sagemaker_session = sagemaker_session
        self.role = role
        
        # Initialize task-strategy compatibility mapping
        self.task_strategy_map = {
            EvaluationTask.MMLU: [EvaluationStrategy.ZERO_SHOT_COT],
            EvaluationTask.MMLU_PRO: [EvaluationStrategy.ZERO_SHOT_COT],
            EvaluationTask.BBH: [EvaluationStrategy.FEW_SHOT_COT],
            EvaluationTask.GPQA: [EvaluationStrategy.ZERO_SHOT_COT],
            EvaluationTask.MATH: [EvaluationStrategy.ZERO_SHOT_COT],
            EvaluationTask.STRONG_REJECT: [EvaluationStrategy.ZERO_SHOT],
            EvaluationTask.IFEVAL: [EvaluationStrategy.ZERO_SHOT],
            EvaluationTask.GEN_QA: [EvaluationStrategy.GEN_QA],
            EvaluationTask.MMMU: [EvaluationStrategy.ZERO_SHOT_COT]
        }
        
        # Initialize task-metric compatibility mapping
        self.task_metric_map = {
            EvaluationTask.MMLU: [EvaluationMetric.ACCURACY],
            EvaluationTask.MMLU_PRO: [EvaluationMetric.ACCURACY],
            EvaluationTask.BBH: [EvaluationMetric.ACCURACY],
            EvaluationTask.GPQA: [EvaluationMetric.ACCURACY],
            EvaluationTask.MATH: [EvaluationMetric.EXACT_MATCH],
            EvaluationTask.STRONG_REJECT: [EvaluationMetric.DEFLECTION],
            EvaluationTask.IFEVAL: [EvaluationMetric.ACCURACY],
            EvaluationTask.GEN_QA: [EvaluationMetric.ALL],
            EvaluationTask.MMMU: [EvaluationMetric.ACCURACY]
        }
        
        # Initialize available subtasks for each task
        self.available_subtasks = {
            EvaluationTask.MMLU: [
                "abstract_algebra", "anatomy", "astronomy", "business_ethics", "clinical_knowledge",
                "college_biology", "college_chemistry", "college_computer_science", "college_mathematics",
                "college_medicine", "college_physics", "computer_security", "conceptual_physics",
                "econometrics", "electrical_engineering", "elementary_mathematics", "formal_logic",
                "global_facts", "high_school_biology", "high_school_chemistry", "high_school_computer_science",
                "high_school_european_history", "high_school_geography", "high_school_government_and_politics",
                "high_school_macroeconomics", "high_school_mathematics", "high_school_microeconomics",
                "high_school_physics", "high_school_psychology", "high_school_statistics",
                "high_school_us_history", "high_school_world_history", "human_aging", "human_sexuality",
                "international_law", "jurisprudence", "logical_fallacies", "machine_learning",
                "management", "marketing", "medical_genetics", "miscellaneous", "moral_disputes",
                "moral_scenarios", "nutrition", "philosophy", "prehistory", "professional_accounting",
                "professional_law", "professional_medicine", "professional_psychology", "public_relations",
                "security_studies", "sociology", "us_foreign_policy", "virology", "world_religions"
            ],
            EvaluationTask.BBH: [
                "boolean_expressions", "causal_judgement", "date_understanding", "disambiguation_qa",
                "dyck_languages", "formal_fallacies", "geometric_shapes", "hyperbaton",
                "logical_deduction_five_objects", "logical_deduction_seven_objects", "logical_deduction_three_objects",
                "movie_recommendation", "multistep_arithmetic_two", "navigate", "object_counting",
                "penguins_in_a_table", "reasoning_about_colored_objects", "ruin_names", "salient_translation_error_detection",
                "snarks", "sports_understanding", "temporal_sequences", "tracking_shuffled_objects_five_objects",
                "tracking_shuffled_objects_seven_objects", "tracking_shuffled_objects_three_objects", "web_of_lies",
                "word_sorting"
            ],
            EvaluationTask.MATH: [
                "algebra", "counting_and_probability", "geometry", "intermediate_algebra",
                "number_theory", "prealgebra", "precalculus"
            ],
            EvaluationTask.STRONG_REJECT: [
                "dangerous_or_sensitive_topics", "offensive_language"
            ],
            EvaluationTask.MMMU: [
                "accounting", "agriculture", "architecture_and_engineering", "art", "art_theory",
                "basic_medical_science", "biology", "chemistry", "clinical_medicine", "computer_science",
                "design", "economics", "electronics", "energy_and_power", "finance", "geography",
                "history", "literature", "manage", "marketing", "materials", "math", "mechanical_engineering",
                "music", "pharmacy", "physics", "psychology", "public_health", "sociology"
            ]
        }
    
    def get_available_subtasks(self, task: EvaluationTask) -> List[str]:
        """Get available subtasks for a given task.
        
        Args:
            task: Evaluation task
            
        Returns:
            List of available subtasks
        """
        return self.available_subtasks.get(task, [])
    
    def get_recommended_instance_type(self, model_type: ModelType) -> str:
        """Get recommended instance type for a given model type.
        
        Args:
            model_type: Type of Nova model
            
        Returns:
            Recommended instance type
        """
        instance_map = {
            ModelType.NOVA_MICRO: "ml.p5.48xlarge",
            ModelType.NOVA_LITE: "ml.p5.48xlarge",
            ModelType.NOVA_PRO: "ml.p5.48xlarge"
        }
        return instance_map.get(model_type, "ml.p5.48xlarge")
    
    def validate_custom_dataset(self, dataset_path: str) -> bool:
        """Validate custom dataset format.
        
        Args:
            dataset_path: Path to the dataset file
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(dataset_path):
                print(f"Error: File not found: {dataset_path}")
                return False
            
            # Check file extension
            if not dataset_path.endswith('.jsonl'):
                print(f"Error: File must have .jsonl extension: {dataset_path}")
                return False
            
            # Validate each line
            with open(dataset_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        import json
                        data = json.loads(line.strip())
                        
                        # Check required fields
                        if 'query' not in data:
                            print(f"Error on line {line_num}: Missing 'query' field")
                            return False
                        
                        if 'response' not in data:
                            print(f"Error on line {line_num}: Missing 'response' field")
                            return False
                        
                        # Check field types
                        if not isinstance(data['query'], str):
                            print(f"Error on line {line_num}: 'query' must be a string")
                            return False
                        
                        if not isinstance(data['response'], str):
                            print(f"Error on line {line_num}: 'response' must be a string")
                            return False
                        
                        if 'system' in data and not isinstance(data['system'], str):
                            print(f"Error on line {line_num}: 'system' must be a string")
                            return False
                        
                    except json.JSONDecodeError:
                        print(f"Error on line {line_num}: Invalid JSON")
                        return False
                    except Exception as e:
                        print(f"Error on line {line_num}: {e}")
                        return False
            
            return True
            
        except Exception as e:
            print(f"Error validating dataset: {e}")
            return False
    
    def create_text_benchmark_recipe(
        self,
        job_name: str,
        model_type: ModelType,
        model_path: str,
        task: EvaluationTask,
        subtask: Optional[str] = None,
        inference_config: Optional[InferenceConfig] = None
    ) -> Dict[str, Any]:
        """Create recipe for text benchmark evaluation.
        
        Args:
            job_name: Name for the evaluation job
            model_type: Type of Nova model
            model_path: Model path (base model name or S3 path to fine-tuned model)
            task: Evaluation task
            subtask: Specific subtask (optional)
            inference_config: Inference configuration (optional)
            
        Returns:
            Recipe dictionary
        """
        # Get default strategy and metric for task
        strategy = self.task_strategy_map[task][0]
        metric = self.task_metric_map[task][0]
        
        # Create run config
        run_config = RunConfig(
            name=job_name,
            model_type=model_type,
            model_name_or_path=model_path
        )
        
        # Create evaluation config
        eval_config = EvaluationConfig(
            task=task,
            strategy=strategy,
            metric=metric,
            subtask=subtask
        )
        
        # Create inference config if not provided
        if inference_config is None:
            inference_config = InferenceConfig()
        
        # Create recipe
        recipe = self.create_recipe(run_config, eval_config, inference_config, None)
        
        return recipe
    
    def create_multimodal_benchmark_recipe(
        self,
        job_name: str,
        model_type: ModelType,
        model_path: str,
        subtask: Optional[str] = None,
        inference_config: Optional[InferenceConfig] = None
    ) -> Dict[str, Any]:
        """Create recipe for multimodal benchmark evaluation.
        
        Args:
            job_name: Name for the evaluation job
            model_type: Type of Nova model
            model_path: Model path (base model name or S3 path to fine-tuned model)
            subtask: MMMU subtask (optional)
            inference_config: Inference configuration (optional)
            
        Returns:
            Recipe dictionary
        """
        # Create run config
        run_config = RunConfig(
            name=job_name,
            model_type=model_type,
            model_name_or_path=model_path
        )
        
        # Create evaluation config
        eval_config = EvaluationConfig(
            task=EvaluationTask.MMMU,
            strategy=EvaluationStrategy.ZERO_SHOT_COT,
            metric=EvaluationMetric.ACCURACY,
            subtask=subtask
        )
        
        # Create inference config if not provided
        if inference_config is None:
            inference_config = InferenceConfig()
        
        # Create recipe
        recipe = self.create_recipe(run_config, eval_config, inference_config, None)
        
        return recipe
    
    def create_custom_dataset_recipe(
        self,
        job_name: str,
        model_type: ModelType,
        model_path: str,
        dataset_s3_uri: Optional[str] = None,
        inference_config: Optional[InferenceConfig] = None
    ) -> Dict[str, Any]:
        """Create recipe for custom dataset evaluation.
        
        Args:
            job_name: Name for the evaluation job
            model_type: Type of Nova model
            model_path: Model path (base model name or S3 path to fine-tuned model)
            dataset_s3_uri: S3 URI for custom dataset (optional)
            inference_config: Inference configuration (optional)
            
        Returns:
            Recipe dictionary
        """
        # Create run config
        run_config = RunConfig(
            name=job_name,
            model_type=model_type,
            model_name_or_path=model_path
        )
        
        # Create evaluation config
        eval_config = EvaluationConfig(
            task=EvaluationTask.GEN_QA,
            strategy=EvaluationStrategy.GEN_QA,
            metric=EvaluationMetric.ALL
        )
        
        # Create inference config if not provided
        if inference_config is None:
            inference_config = InferenceConfig(max_new_tokens=12000)
        
        # Create recipe
        recipe = self.create_recipe(run_config, eval_config, inference_config, dataset_s3_uri)
        
        return recipe
    
    def create_recipe(
        self,
        run_config: RunConfig,
        eval_config: EvaluationConfig,
        inference_config: InferenceConfig,
        dataset_s3_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create evaluation recipe.
        
        Args:
            run_config: Run configuration
            eval_config: Evaluation configuration
            inference_config: Inference configuration
            dataset_s3_uri: S3 URI for custom dataset (optional)
            
        Returns:
            Recipe dictionary
        """
        # Map model type to the correct format
        model_type_map = {
            ModelType.NOVA_MICRO: "amazon.nova-micro-v1:0:300k",
            ModelType.NOVA_LITE: "amazon.nova-lite-v1:0:300k",
            ModelType.NOVA_PRO: "amazon.nova-pro-v1:0:300k"
        }
        
        # Get the correct model type format
        model_type_format = model_type_map.get(run_config.model_type, run_config.model_type.value)
        
        # Create recipe dictionary
        recipe = {
            "run": {
                "name": run_config.name,
                "model_type": model_type_format,
                "model_name_or_path": run_config.model_name_or_path,
                "replicas": 1,  # unmodifiable
                "data_s3_path": dataset_s3_uri or ""
            },
            "evaluation": {
                "task": eval_config.task.value,
                "strategy": eval_config.strategy.value,
                "metric": eval_config.metric.value
            },
            "inference": {
                "max_new_tokens": inference_config.max_new_tokens,
                "temperature": inference_config.temperature,
                "top_p": inference_config.top_p,
                "top_k": inference_config.top_k
            }
        }
        
        # Add subtask if provided
        if eval_config.subtask:
            recipe["evaluation"]["subtask"] = eval_config.subtask
        
        return recipe
    
    def save_recipe(self, recipe: Dict[str, Any], output_path: str):
        """Save recipe to file.
        
        Args:
            recipe: Recipe dictionary
            output_path: Output path for recipe file
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Save recipe to file
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(recipe, f, default_flow_style=False)
    
    def run_evaluation(
        self,
        recipe_path: str,
        output_s3_uri: str,
        job_name: str,
        input_s3_uri: Optional[str] = None,
        instance_type: Optional[str] = None
    ) -> Estimator:
        """Run evaluation job.
        
        Args:
            recipe_path: Path to recipe file
            output_s3_uri: S3 URI for output data
            job_name: Name for the evaluation job
            input_s3_uri: S3 URI for input data (optional)
            instance_type: Instance type (optional)
            
        Returns:
            SageMaker estimator
        """
        # Check if SageMaker session and role are available
        if not self.sagemaker_session or not self.role:
            raise ValueError("SageMaker session and role are required for running evaluation jobs")
        
        # Load recipe
        with open(recipe_path, 'r', encoding='utf-8') as f:
            recipe = yaml.safe_load(f)
        
        # Get model type from the recipe
        model_type_str = recipe["run"]["model_type"]
        
        # Map the model type string back to ModelType enum for instance type recommendation
        model_type_map = {
            "amazon.nova-micro-v1:0:300k": ModelType.NOVA_MICRO,
            "amazon.nova-lite-v1:0:300k": ModelType.NOVA_LITE,
            "amazon.nova-pro-v1:0:300k": ModelType.NOVA_PRO
        }
        
        # Get the ModelType enum or use NOVA_LITE as default
        model_type = model_type_map.get(model_type_str, ModelType.NOVA_LITE)
        
        # Get recommended instance type if not provided
        if instance_type is None:
            instance_type = self.get_recommended_instance_type(model_type)
        
        # Create the correct image URI using the SageMaker session's region
        image_uri = f"708977205387.dkr.ecr.{self.sagemaker_session.boto_region_name}.amazonaws.com/nova-evaluation-repo:SM-TJ-Eval-latest"
        
        # Define recipe overrides
        recipe_overrides = {
            "run": {
                "replicas": 1,  # Default to 1 instance
            },
        }
        
        # Create estimator using PyTorch class
        estimator = PyTorch(
            image_uri=image_uri,
            role=self.role,
            instance_count=1,
            instance_type=instance_type,
            output_path=output_s3_uri,
            base_job_name=job_name,
            disable_profiler=True,
            debugger_hook_config=False,
            sagemaker_session=self.sagemaker_session,
            training_recipe=recipe_path,
            recipe_overrides=recipe_overrides
        )
        
        # Generate a unique job name by appending a timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        unique_job_name = f"{job_name}-{timestamp}"
        
        print(f"Using unique job name: {unique_job_name}")
        
        # Start training job
        if input_s3_uri:
            # If input dataset exists, create a TrainingInput object and pass it to the fit method
            eval_input = TrainingInput(
                s3_data=input_s3_uri,
                distribution="FullyReplicated",
                s3_data_type="S3Prefix",
            )
            
            # Pass the TrainingInput object to the fit method
            estimator.fit(job_name=unique_job_name, inputs={"train": eval_input})
        else:
            # Otherwise, just use the job name
            estimator.fit(job_name=unique_job_name)
        
        return estimator
