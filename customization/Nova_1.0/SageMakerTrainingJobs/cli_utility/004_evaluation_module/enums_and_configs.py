#!/usr/bin/env python3
"""
Enums and Configuration Classes for Nova Evaluation

This module defines the enums and configuration classes used in the Nova evaluation process.
"""

import enum
from typing import Optional


class ModelType(enum.Enum):
    """Enum for Nova model types."""
    NOVA_MICRO = "nova-micro"
    NOVA_LITE = "nova-lite"
    NOVA_PRO = "nova-pro"


class EvaluationTask(enum.Enum):
    """Enum for evaluation tasks."""
    MMLU = "mmlu"
    MMLU_PRO = "mmlu_pro"
    BBH = "bbh"
    GPQA = "gpqa"
    MATH = "math"
    STRONG_REJECT = "strong_reject"
    IFEVAL = "ifeval"
    GEN_QA = "gen_qa"
    MMMU = "mmmu"


class EvaluationStrategy(enum.Enum):
    """Enum for evaluation strategies."""
    ZERO_SHOT = "zs"
    ZERO_SHOT_COT = "zs_cot"
    FEW_SHOT = "fs"
    FEW_SHOT_COT = "fs_cot"
    GEN_QA = "gen_qa"


class EvaluationMetric(enum.Enum):
    """Enum for evaluation metrics."""
    ACCURACY = "accuracy"
    EXACT_MATCH = "exact_match"
    DEFLECTION = "deflection"
    ALL = "all"


class RunConfig:
    """Configuration for evaluation run."""
    
    def __init__(
        self,
        name: str,
        model_type: ModelType,
        model_name_or_path: str
    ):
        """Initialize run configuration.
        
        Args:
            name: Name for the evaluation job
            model_type: Type of Nova model
            model_name_or_path: Model name or S3 path to fine-tuned model
        """
        self.name = name
        self.model_type = model_type
        self.model_name_or_path = model_name_or_path


class EvaluationConfig:
    """Configuration for evaluation task."""
    
    def __init__(
        self,
        task: EvaluationTask,
        strategy: EvaluationStrategy,
        metric: EvaluationMetric,
        subtask: Optional[str] = None
    ):
        """Initialize evaluation configuration.
        
        Args:
            task: Evaluation task
            strategy: Evaluation strategy
            metric: Evaluation metric
            subtask: Specific subtask (optional)
        """
        self.task = task
        self.strategy = strategy
        self.metric = metric
        self.subtask = subtask


class InferenceConfig:
    """Configuration for model inference."""
    
    def __init__(
        self,
        max_new_tokens: int = 8196,
        temperature: float = 0.0,
        top_p: float = 1.0,
        top_k: int = -1
    ):
        """Initialize inference configuration.
        
        Args:
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
        """
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
