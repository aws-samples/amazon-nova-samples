"""
Token Counter Module for Nova Models

Comprehensive token tracking and reporting for all Nova models with detailed
usage statistics, cost estimation, and performance metrics.
"""

import json
from datetime import datetime


class NovaTokenCounter:
    """
    Comprehensive token counter for Nova models with detailed tracking and reporting.
    """
    
    def __init__(self):
        self.token_usage = {
            'nova-premier': {'input_tokens': 0, 'output_tokens': 0, 'requests': 0},
            'nova-pro': {'input_tokens': 0, 'output_tokens': 0, 'requests': 0},
            'nova-canvas': {'input_tokens': 0, 'output_tokens': 0, 'requests': 0}
        }
        self.session_start = datetime.now()
        self.detailed_log = []
    
    def log_token_usage(self, model_name, input_tokens, output_tokens, operation_type="content_generation"):
        """
        Log token usage for a specific model and operation.
        
        Args:
            model_name (str): Model identifier (nova-premier, nova-pro, nova-canvas)
            input_tokens (int): Number of input tokens consumed
            output_tokens (int): Number of output tokens generated
            operation_type (str): Type of operation (content_generation, image_optimization, image_generation)
        """
        # Normalize model name
        model_key = model_name.lower().replace('us.amazon.', '').replace('amazon.', '').replace('-v1:0', '')
        if 'premier' in model_key:
            model_key = 'nova-premier'
        elif 'pro' in model_key:
            model_key = 'nova-pro'
        elif 'canvas' in model_key:
            model_key = 'nova-canvas'
        
        if model_key in self.token_usage:
            self.token_usage[model_key]['input_tokens'] += input_tokens
            self.token_usage[model_key]['output_tokens'] += output_tokens
            self.token_usage[model_key]['requests'] += 1
            
            # Log detailed entry
            self.detailed_log.append({
                'timestamp': datetime.now().isoformat(),
                'model': model_key,
                'operation': operation_type,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens
            })
            
            print(f"   📊 Token usage - {model_key}: {input_tokens} in, {output_tokens} out")
    
    def extract_tokens_from_response(self, response_body, model_name):
        """
        Extract token usage from Bedrock response metadata.
        
        Args:
            response_body (dict): Response from Bedrock model
            model_name (str): Model identifier
            
        Returns:
            tuple: (input_tokens, output_tokens)
        """
        try:
            # Check for usage metadata in response
            if 'usage' in response_body:
                usage = response_body['usage']
                input_tokens = usage.get('inputTokens', 0)
                output_tokens = usage.get('outputTokens', 0)
                return input_tokens, output_tokens
            
            # Alternative locations for token data
            if 'amazon-bedrock-invocationMetrics' in response_body:
                metrics = response_body['amazon-bedrock-invocationMetrics']
                input_tokens = metrics.get('inputTokenCount', 0)
                output_tokens = metrics.get('outputTokenCount', 0)
                return input_tokens, output_tokens
            
            # For image models, estimate tokens based on prompt length
            if 'canvas' in model_name.lower():
                # Estimate tokens for image generation (approximate)
                if 'textToImageParams' in str(response_body):
                    # Rough estimation: ~4 characters per token
                    prompt_text = str(response_body).get('text', '')
                    estimated_input = len(prompt_text) // 4
                    estimated_output = 10  # Minimal output tokens for image generation
                    return estimated_input, estimated_output
            
            # Default estimation if no metadata available
            return self.estimate_tokens_from_content(response_body, model_name)
            
        except Exception as e:
            print(f"   ⚠️ Could not extract token usage: {e}")
            return 0, 0
    
    def estimate_tokens_from_content(self, content, model_name):
        """
        Estimate token usage when metadata is not available.
        
        Args:
            content: Content to estimate tokens for
            model_name (str): Model identifier
            
        Returns:
            tuple: (estimated_input_tokens, estimated_output_tokens)
        """
        try:
            content_str = str(content)
            # Rough estimation: ~4 characters per token for text
            estimated_tokens = len(content_str) // 4
            
            if 'canvas' in model_name.lower():
                # Image generation: input is prompt, output is minimal
                return estimated_tokens, 10
            else:
                # Text generation: split between input and output
                input_estimate = estimated_tokens // 3  # Assume 1/3 input
                output_estimate = estimated_tokens - input_estimate  # Rest is output
                return input_estimate, output_estimate
                
        except Exception:
            return 0, 0
    
    def get_session_summary(self):
        """
        Get comprehensive session summary with token usage statistics.
        
        Returns:
            dict: Detailed session statistics
        """
        session_duration = datetime.now() - self.session_start
        total_input = sum(model['input_tokens'] for model in self.token_usage.values())
        total_output = sum(model['output_tokens'] for model in self.token_usage.values())
        total_requests = sum(model['requests'] for model in self.token_usage.values())
        
        return {
            'session_duration': str(session_duration).split('.')[0],  # Remove microseconds
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'total_tokens': total_input + total_output,
            'total_requests': total_requests,
            'models': self.token_usage.copy(),
            'detailed_log': self.detailed_log.copy()
        }
    
    def print_summary(self):
        """Print formatted token usage summary."""
        summary = self.get_session_summary()
        
        print(f"\n📊 TOKEN USAGE SUMMARY")
        print("=" * 60)
        print(f"Session Duration: {summary['session_duration']}")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total Input Tokens: {summary['total_input_tokens']:,}")
        print(f"Total Output Tokens: {summary['total_output_tokens']:,}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        
        print(f"\n📈 PER-MODEL BREAKDOWN:")
        print("-" * 60)
        
        for model_name, usage in summary['models'].items():
            if usage['requests'] > 0:
                total_model_tokens = usage['input_tokens'] + usage['output_tokens']
                avg_input = usage['input_tokens'] / usage['requests']
                avg_output = usage['output_tokens'] / usage['requests']
                
                print(f"\n🤖 {model_name.upper()}:")
                print(f"   Requests: {usage['requests']}")
                print(f"   Input Tokens: {usage['input_tokens']:,} (avg: {avg_input:.1f})")
                print(f"   Output Tokens: {usage['output_tokens']:,} (avg: {avg_output:.1f})")
                print(f"   Total Tokens: {total_model_tokens:,}")
        
        # Cost estimation (approximate)
        print(f"\n💰 ESTIMATED COSTS (Approximate):")
        print("-" * 60)
        
        # Rough cost estimates (these would need to be updated with actual pricing)
        cost_estimates = {
            'nova-premier': {'input': 0.0008, 'output': 0.0032},  # per 1K tokens
            'nova-pro': {'input': 0.0004, 'output': 0.0016},     # per 1K tokens  
            'nova-canvas': {'input': 0.0004, 'output': 0.0016}   # per 1K tokens
        }
        
        total_estimated_cost = 0
        for model_name, usage in summary['models'].items():
            if usage['requests'] > 0 and model_name in cost_estimates:
                rates = cost_estimates[model_name]
                input_cost = (usage['input_tokens'] / 1000) * rates['input']
                output_cost = (usage['output_tokens'] / 1000) * rates['output']
                model_cost = input_cost + output_cost
                total_estimated_cost += model_cost
                
                print(f"   {model_name}: ~${model_cost:.4f}")
        
        print(f"   TOTAL ESTIMATED: ~${total_estimated_cost:.4f}")
        print(f"\n⚠️ Note: Cost estimates are approximate and may not reflect actual pricing")


def create_token_counter():
    """Factory function to create a new token counter instance."""
    return NovaTokenCounter()
