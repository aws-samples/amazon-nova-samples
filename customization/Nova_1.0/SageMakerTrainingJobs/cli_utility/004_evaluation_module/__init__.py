"""
Nova Evaluation Module

This package provides functionality for evaluating Amazon Nova models
using various benchmarks and custom datasets through SageMaker Training Jobs.
"""

# Use direct imports instead of relative imports to avoid folder structure dependencies
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

    from nova_evaluator import NovaEvaluator
    from eval_result_analyzer import EvalResultAnalyzer
    from helper_functions import (
        create_text_evaluation_job,
        create_custom_dataset_evaluation_job
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

    from .nova_evaluator import NovaEvaluator
    from .eval_result_analyzer import EvalResultAnalyzer
    from .helper_functions import (
        create_text_evaluation_job,
        create_custom_dataset_evaluation_job
    )

__all__ = [
    'ModelType',
    'EvaluationTask',
    'EvaluationStrategy',
    'EvaluationMetric',
    'RunConfig',
    'EvaluationConfig',
    'InferenceConfig',
    'NovaEvaluator',
    'EvalResultAnalyzer',
    'create_text_evaluation_job',
    'create_custom_dataset_evaluation_job'
]
