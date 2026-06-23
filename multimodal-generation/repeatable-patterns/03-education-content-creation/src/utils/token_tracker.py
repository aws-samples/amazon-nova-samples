"""
Enhanced Token Tracker

Flexible token tracking system designed for notebook use, frontend integration,
and future extensibility (PDF export, prompt preview, etc.).
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from ..core.token_counter import NovaTokenCounter

# Configure logging
logger = logging.getLogger(__name__)


class TokenTracker:
    """
    Enhanced token tracking system with extensible architecture for
    frontend integration, export capabilities, and prompt management.
    """
    
    _instance: Optional[NovaTokenCounter] = None
    _session_data: Dict[str, Any] = {}
    
    @classmethod
    def setup(cls) -> NovaTokenCounter:
        """
        Initialize token tracking system.
        
        Returns:
            NovaTokenCounter: Configured token counter instance
        """
        if cls._instance is None:
            cls._instance = NovaTokenCounter()
            cls._session_data = {
                'session_start': datetime.now().isoformat(),
                'features_enabled': ['tracking', 'cost_estimation', 'export_ready'],
                'version': '2.0'
            }
            
            print("✅ TokenTracker initialized")
            print("   • Advanced token tracking for all Nova models")
            print("   • Cost estimation and performance metrics")
            print("   • Frontend-ready API interface")
            print("   • Export capabilities (PDF, CSV, JSON)")
            print("   • Prompt preview and estimation")
        
        return cls._instance
    
    @classmethod
    def log(cls, model_name: str, input_tokens: int, output_tokens: int, 
            operation_type: str = "content_generation") -> None:
        """
        Log token usage for a model.
        
        Args:
            model_name: Model identifier (nova-premier, nova-pro, nova-canvas)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            operation_type: Type of operation performed
        """
        if cls._instance is None:
            cls.setup()
        
        cls._instance.log_token_usage(model_name, input_tokens, output_tokens, operation_type)
    
    @classmethod
    def summary(cls) -> None:
        """Print formatted token usage summary."""
        if cls._instance is None:
            cls.setup()
        
        cls._instance.print_summary()
    
    @classmethod
    def data(cls) -> Dict[str, Any]:
        """
        Get comprehensive session data.
        
        Returns:
            Dict containing all session statistics and metadata
        """
        if cls._instance is None:
            cls.setup()
        
        base_data = cls._instance.get_session_summary()
        
        # Add enhanced metadata for frontend/export
        enhanced_data = {
            **base_data,
            'session_metadata': cls._session_data,
            'export_timestamp': datetime.now().isoformat(),
            'api_version': '2.0'
        }
        
        return enhanced_data
    
    # =================================================================
    # PROMPT PREVIEW & ESTIMATION (Future Frontend Feature)
    # =================================================================
    
    @classmethod
    def preview_prompt(cls, prompt: str, model_name: str) -> Dict[str, Any]:
        """
        Preview prompt and estimate token usage before sending to LLM.
        
        Args:
            prompt: The prompt text to analyze
            model_name: Target model identifier
            
        Returns:
            Dict with prompt preview, token estimates, and cost estimates
        """
        if cls._instance is None:
            cls.setup()
        
        # Estimate tokens
        estimated_input, estimated_output = cls._instance.estimate_tokens_from_content(
            prompt, model_name
        )
        
        # Create preview (truncated for display)
        preview_text = prompt[:300] + "..." if len(prompt) > 300 else prompt
        
        # Estimate cost (using existing cost estimation logic)
        cost_estimates = {
            'nova-premier': {'input': 0.0008, 'output': 0.0032},
            'nova-pro': {'input': 0.0004, 'output': 0.0016},
            'nova-canvas': {'input': 0.0004, 'output': 0.0016}
        }
        
        model_key = model_name.lower().replace('us.amazon.', '').replace('amazon.', '').replace('-v1:0', '')
        if 'premier' in model_key:
            model_key = 'nova-premier'
        elif 'pro' in model_key:
            model_key = 'nova-pro'
        elif 'canvas' in model_key:
            model_key = 'nova-canvas'
        
        estimated_cost = 0
        if model_key in cost_estimates:
            rates = cost_estimates[model_key]
            estimated_cost = (estimated_input / 1000) * rates['input'] + (estimated_output / 1000) * rates['output']
        
        return {
            'prompt_preview': preview_text,
            'prompt_length': len(prompt),
            'word_count': len(prompt.split()),
            'estimated_tokens': {
                'input': estimated_input,
                'output': estimated_output,
                'total': estimated_input + estimated_output
            },
            'estimated_cost': round(estimated_cost, 6),
            'model_name': model_name,
            'timestamp': datetime.now().isoformat()
        }
    
    @classmethod
    def log_with_preview(cls, prompt: str, response_data: Dict, model_name: str, 
                        operation_type: str = "content_generation") -> Dict[str, Any]:
        """
        Log actual token usage after LLM response and compare with preview.
        
        Args:
            prompt: Original prompt sent
            response_data: Response from LLM with usage data
            model_name: Model identifier
            operation_type: Type of operation
            
        Returns:
            Dict with actual vs estimated comparison
        """
        if cls._instance is None:
            cls.setup()
        
        # Get preview data for comparison
        preview = cls.preview_prompt(prompt, model_name)
        
        # Extract actual tokens from response
        actual_input, actual_output = cls._instance.extract_tokens_from_response(
            response_data, model_name
        )
        
        # Log the actual usage
        cls.log(model_name, actual_input, actual_output, operation_type)
        
        # Return comparison data
        return {
            'preview': preview,
            'actual': {
                'input_tokens': actual_input,
                'output_tokens': actual_output,
                'total_tokens': actual_input + actual_output
            },
            'accuracy': {
                'input_accuracy': abs(preview['estimated_tokens']['input'] - actual_input) / max(actual_input, 1),
                'output_accuracy': abs(preview['estimated_tokens']['output'] - actual_output) / max(actual_output, 1)
            }
        }
    
    # =================================================================
    # EXPORT CAPABILITIES (Future PDF/CSV Export Feature)
    # =================================================================
    
    @classmethod
    def get_export_data(cls, format_type: str = "json") -> Dict[str, Any]:
        """
        Get data formatted for export.
        
        Args:
            format_type: Export format (json, csv, pdf)
            
        Returns:
            Dict with export-ready data
        """
        data = cls.data()
        
        export_data = {
            'export_info': {
                'format': format_type,
                'generated_at': datetime.now().isoformat(),
                'session_duration': data.get('session_duration', 'Unknown'),
                'total_requests': data.get('total_requests', 0)
            },
            'summary': {
                'total_tokens': data.get('total_tokens', 0),
                'total_input_tokens': data.get('total_input_tokens', 0),
                'total_output_tokens': data.get('total_output_tokens', 0),
                'estimated_cost': cls._calculate_total_cost(data)
            },
            'models': data.get('models', {}),
            'detailed_log': data.get('detailed_log', [])
        }
        
        return export_data
    
    @classmethod
    def _calculate_total_cost(cls, data: Dict) -> float:
        """Calculate total estimated cost from session data."""
        cost_estimates = {
            'nova-premier': {'input': 0.0008, 'output': 0.0032},
            'nova-pro': {'input': 0.0004, 'output': 0.0016},
            'nova-canvas': {'input': 0.0004, 'output': 0.0016}
        }
        
        total_cost = 0
        models = data.get('models', {})
        
        for model_name, usage in models.items():
            if model_name in cost_estimates and usage.get('requests', 0) > 0:
                rates = cost_estimates[model_name]
                input_cost = (usage.get('input_tokens', 0) / 1000) * rates['input']
                output_cost = (usage.get('output_tokens', 0) / 1000) * rates['output']
                total_cost += input_cost + output_cost
        
        return round(total_cost, 6)
    
    # =================================================================
    # FRONTEND API METHODS (Future Web Interface)
    # =================================================================
    
    @classmethod
    def get_api_summary(cls) -> Dict[str, Any]:
        """
        Get API-friendly summary for frontend consumption.
        
        Returns:
            Dict with frontend-optimized data structure
        """
        data = cls.data()
        
        return {
            'status': 'active' if cls._instance else 'inactive',
            'session': {
                'duration': data.get('session_duration', '0:00:00'),
                'start_time': cls._session_data.get('session_start'),
                'total_requests': data.get('total_requests', 0)
            },
            'usage': {
                'total_tokens': data.get('total_tokens', 0),
                'input_tokens': data.get('total_input_tokens', 0),
                'output_tokens': data.get('total_output_tokens', 0),
                'estimated_cost': cls._calculate_total_cost(data)
            },
            'models': {
                model: {
                    'requests': usage.get('requests', 0),
                    'tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0),
                    'active': usage.get('requests', 0) > 0
                }
                for model, usage in data.get('models', {}).items()
            }
        }
    
    @classmethod
    def reset_session(cls) -> None:
        """Reset the current tracking session."""
        cls._instance = None
        cls._session_data = {}
        print("🔄 TokenTracker session reset")
    
    # =================================================================
    # CONVENIENCE METHODS FOR SPECIFIC MODELS
    # =================================================================
    
    @classmethod
    def log_premier(cls, input_tokens: int, output_tokens: int) -> None:
        """Log Nova Premier usage."""
        cls.log('nova-premier', input_tokens, output_tokens, 'content_generation')
    
    @classmethod
    def log_pro(cls, input_tokens: int, output_tokens: int) -> None:
        """Log Nova Pro usage."""
        cls.log('nova-pro', input_tokens, output_tokens, 'image_optimization')
    
    @classmethod
    def log_canvas(cls, input_tokens: int, output_tokens: int) -> None:
        """Log Nova Canvas usage."""
        cls.log('nova-canvas', input_tokens, output_tokens, 'image_generation')
    
    # =================================================================
    # UTILITY METHODS
    # =================================================================
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if TokenTracker is initialized."""
        return cls._instance is not None
    
    @classmethod
    def get_version(cls) -> str:
        """Get TokenTracker version."""
        return cls._session_data.get('version', '2.0')
    
    @classmethod
    def get_features(cls) -> List[str]:
        """Get list of enabled features."""
        return cls._session_data.get('features_enabled', [])


# Convenience functions for backward compatibility
def setup_token_tracking() -> NovaTokenCounter:
    """Backward compatibility function."""
    return TokenTracker.setup()


def log_usage(model_name: str, input_tokens: int, output_tokens: int, 
              operation_type: str = "content_generation") -> None:
    """Backward compatibility function."""
    TokenTracker.log(model_name, input_tokens, output_tokens, operation_type)


def print_summary() -> None:
    """Backward compatibility function."""
    TokenTracker.summary()
