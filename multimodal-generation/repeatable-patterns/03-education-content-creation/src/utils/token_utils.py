"""
Token Utility Functions

Simplified token tracking utilities for notebook cells.
Provides easy-to-use functions that replace complex code blocks.
"""

from ..core.token_counter import NovaTokenCounter
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Global token counter instance
_global_token_counter = None


def setup_token_tracking():
    """
    Set up token tracking with a single function call.
    
    Returns:
        NovaTokenCounter: Configured token counter instance
    """
    global _global_token_counter
    
    if _global_token_counter is None:
        _global_token_counter = NovaTokenCounter()
        print("✅ Token Counter initialized")
        print("   • Tracks input/output tokens for all Nova models")
        print("   • Provides detailed usage statistics")
        print("   • Estimates costs and performance metrics")
    
    return _global_token_counter


def get_token_counter():
    """
    Get the global token counter instance.
    
    Returns:
        NovaTokenCounter: The global token counter
    """
    global _global_token_counter
    
    if _global_token_counter is None:
        return setup_token_tracking()
    
    return _global_token_counter


def log_usage(model_name, input_tokens, output_tokens, operation_type="content_generation"):
    """
    Quick function to log token usage.
    
    Args:
        model_name (str): Model identifier
        input_tokens (int): Input tokens used
        output_tokens (int): Output tokens generated
        operation_type (str): Type of operation
    """
    counter = get_token_counter()
    counter.log_token_usage(model_name, input_tokens, output_tokens, operation_type)


def print_summary():
    """Quick function to print token usage summary."""
    counter = get_token_counter()
    counter.print_summary()


def get_session_data():
    """
    Get session summary data.
    
    Returns:
        dict: Session statistics
    """
    counter = get_token_counter()
    return counter.get_session_summary()


class TokenTracker:
    """
    Simplified token tracker class for easy notebook usage.
    """
    
    @classmethod
    def setup(cls):
        """
        Class method to set up token tracking.
        
        Returns:
            NovaTokenCounter: Configured token counter
        """
        return setup_token_tracking()
    
    @classmethod
    def log(cls, model_name, input_tokens, output_tokens, operation_type="content_generation"):
        """
        Class method to log token usage.
        
        Args:
            model_name (str): Model identifier
            input_tokens (int): Input tokens used
            output_tokens (int): Output tokens generated
            operation_type (str): Type of operation
        """
        log_usage(model_name, input_tokens, output_tokens, operation_type)
    
    @classmethod
    def summary(cls):
        """Class method to print usage summary."""
        print_summary()
    
    @classmethod
    def data(cls):
        """
        Class method to get session data.
        
        Returns:
            dict: Session statistics
        """
        return get_session_data()


# Convenience functions for common operations
def track_nova_premier(input_tokens, output_tokens):
    """Track Nova Premier usage."""
    log_usage('nova-premier', input_tokens, output_tokens, 'content_generation')


def track_nova_pro(input_tokens, output_tokens):
    """Track Nova Pro usage."""
    log_usage('nova-pro', input_tokens, output_tokens, 'image_optimization')


def track_nova_canvas(input_tokens, output_tokens):
    """Track Nova Canvas usage."""
    log_usage('nova-canvas', input_tokens, output_tokens, 'image_generation')


# Quick setup function for notebook cells
def quick_setup():
    """
    Ultra-simple setup function for notebook cells.
    
    Returns:
        tuple: (token_counter, log_function, summary_function)
    """
    counter = setup_token_tracking()
    return counter, log_usage, print_summary
