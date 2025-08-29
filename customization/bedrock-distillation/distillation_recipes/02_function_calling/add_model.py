#!/usr/bin/env python3
"""
Berkeley Function Call Leaderboard Model Automation Script

This script automates the process of adding model configurations to the Berkeley
Function Call Leaderboard system. It supports three input types:
1. Regular model IDs (e.g., "gpt-4")
2. Custom model deployment ARNs (e.g., "arn:aws:bedrock:us-west-2:123456789012:custom-model-deployment/my-model")
3. Provisioned throughput endpoint ARNs (e.g., "arn:aws:bedrock:us-west-2:123456789012:provisioned-model-throughput/my-endpoint")

This script is based on v1.3 of the Berkeley Function Call Leaderboard (BFCL):
https://github.com/ShishirPatil/gorilla/releases/tag/v1.3

Additional Features:
- Automatically replaces the contents of api_inference/nova.py with the provided nova.py file at startup

Usage:
    python add_model.py [MODEL_ID_OR_ARN] [OPTIONS]

Example:
    python add_model.py gpt-4-turbo --handler OpenAIResponsesHandler --org OpenAI
    python add_model.py "arn:aws:bedrock:us-east-1:123456789012:custom-model-deployment/my-model" --base-model nova-lite-v1.0
    python add_model.py --interactive
"""

import argparse
import sys
import os
import re
import json
import logging
import shutil
import tempfile
import ast
import yaml
import urllib.parse
import inspect
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import asdict
import importlib.util

# ASCII Art and Color Support
try:
    import pyfiglet
    PYFIGLET_AVAILABLE = True
except ImportError:
    PYFIGLET_AVAILABLE = False

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)  # Automatically reset colors after each print
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback color definitions (no-op)
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        DIM = NORMAL = BRIGHT = RESET_ALL = ""

# Global path variables (will be initialized based on working directory)
SCRIPT_DIR = None
BFCL_EVAL_DIR = None
MODEL_CONFIG_FILE = None
SUPPORTED_MODELS_FILE = None
BACKUP_DIR = None

def initialize_paths(working_dir: Optional[Path] = None):
    """Initialize global path constants based on working directory."""
    global SCRIPT_DIR, BFCL_EVAL_DIR, MODEL_CONFIG_FILE, SUPPORTED_MODELS_FILE, BACKUP_DIR
    
    if working_dir is None:
        working_dir = Path(__file__).parent
    else:
        working_dir = Path(working_dir).resolve()
    
    SCRIPT_DIR = working_dir
    BFCL_EVAL_DIR = SCRIPT_DIR / "bfcl_eval"
    MODEL_CONFIG_FILE = BFCL_EVAL_DIR / "constants" / "model_config.py"
    SUPPORTED_MODELS_FILE = BFCL_EVAL_DIR / "constants" / "supported_models.py"
    BACKUP_DIR = SCRIPT_DIR / "backups"
    
    # Add the bfcl_eval directory to Python path for imports
    sys.path.insert(0, str(SCRIPT_DIR))

# Initialize with default paths (will be overridden if --working-dir is specified)
initialize_paths()

# Import ModelConfig for template generation
from bfcl_eval.constants.model_config import ModelConfig

# ARN Patterns
CUSTOM_DEPLOYMENT_ARN_PATTERN = re.compile(
    r"^arn:aws:bedrock:[\w-]+:\d+:custom-model-deployment/[\w-]+$"
)
PROVISIONED_THROUGHPUT_ARN_PATTERN = re.compile(
    r"^arn:aws:bedrock:[\w-]+:\d+:provisioned-model-throughput/[\w-]+$"
)


class ASCIIArtGenerator:
    """Generates ASCII art banners and visual elements for the CLI interface."""
    
    def __init__(self):
        self.pyfiglet_available = PYFIGLET_AVAILABLE
        self.colorama_available = COLORAMA_AVAILABLE
        
        # Define color themes
        self.colors = {
            'primary': Fore.CYAN,
            'secondary': Fore.MAGENTA,
            'success': Fore.GREEN,
            'warning': Fore.YELLOW,
            'error': Fore.RED,
            'info': Fore.BLUE,
            'highlight': Fore.WHITE + Style.BRIGHT,
            'dim': Style.DIM,
            'reset': Style.RESET_ALL
        }
        
        # Fallback ASCII art patterns
        self.fallback_patterns = {
            'large_border': '█' * 80,
            'medium_border': '▄' * 60,
            'small_border': '─' * 40,
            'corner_tl': '╔', 'corner_tr': '╗',
            'corner_bl': '╚', 'corner_br': '╝',
            'horizontal': '═', 'vertical': '║'
        }
    
    def create_banner(self, text: str, font: str = 'slant', width: int = 80) -> str:
        """Create an ASCII art banner for the given text."""
        if self.pyfiglet_available:
            try:
                ascii_art = pyfiglet.figlet_format(text, font=font, width=width)
                return ascii_art.rstrip()
            except Exception:
                # Fallback to default font if specific font fails
                try:
                    ascii_art = pyfiglet.figlet_format(text, width=width)
                    return ascii_art.rstrip()
                except Exception:
                    pass
        
        # Manual fallback banner
        return self._create_fallback_banner(text)
    
    def _create_fallback_banner(self, text: str) -> str:
        """Create a fallback banner when pyfiglet is not available."""
        lines = []
        border = '█' * (len(text) + 8)
        
        lines.append(border)
        lines.append(f"█   {text.upper()}   █")
        lines.append(border)
        
        return '\n'.join(lines)
    
    def create_progress_bar(self, current: int, total: int, width: int = 40) -> str:
        """Create an ASCII progress bar."""
        if total == 0:
            percentage = 0
        else:
            percentage = current / total
        
        filled = int(width * percentage)
        bar = '█' * filled + '░' * (width - filled)
        
        return f"[{bar}] {current}/{total} ({percentage:.0%})"
    
    def create_step_indicator(self, current_step: int, total_steps: int, step_name: str) -> str:
        """Create a visual step indicator."""
        # Create step circles
        circles = []
        for i in range(1, total_steps + 1):
            if i < current_step:
                circles.append('●')  # Completed
            elif i == current_step:
                circles.append('◉')  # Current
            else:
                circles.append('○')  # Pending
        
        circle_line = ' '.join(circles)
        
        lines = [
            f"Step {current_step} of {total_steps}: {step_name}",
            circle_line,
            ""
        ]
        
        return '\n'.join(lines)
    
    def create_section_header(self, title: str, width: int = 60) -> str:
        """Create a formatted section header."""
        if len(title) > width - 4:
            title = title[:width-7] + "..."
        
        padding = (width - len(title) - 2) // 2
        border = '═' * width
        
        lines = [
            f"╔{border}╗",
            f"║{' ' * padding}{title}{' ' * (width - len(title) - padding)}║",
            f"╚{border}╝"
        ]
        
        return '\n'.join(lines)
    
    def create_info_box(self, title: str, content: List[str], width: int = 60) -> str:
        """Create an information box with border."""
        lines = []
        
        # Top border
        lines.append('┌' + '─' * (width - 2) + '┐')
        
        # Title
        if title:
            title_line = f"│ {title}" + ' ' * (width - len(title) - 3) + '│'
            lines.append(title_line)
            lines.append('├' + '─' * (width - 2) + '┤')
        
        # Content
        for line in content:
            if len(line) > width - 4:
                # Wrap long lines
                wrapped = [line[i:i+width-4] for i in range(0, len(line), width-4)]
                for wrapped_line in wrapped:
                    padded = f"│ {wrapped_line}" + ' ' * (width - len(wrapped_line) - 3) + '│'
                    lines.append(padded)
            else:
                padded = f"│ {line}" + ' ' * (width - len(line) - 3) + '│'
                lines.append(padded)
        
        # Bottom border
        lines.append('└' + '─' * (width - 2) + '┘')
        
        return '\n'.join(lines)
    
    def colorize(self, text: str, color: str = 'primary') -> str:
        """Apply color to text if colorama is available."""
        if not self.colorama_available:
            return text
        
        color_code = self.colors.get(color, '')
        return f"{color_code}{text}{self.colors['reset']}"
    
    def create_welcome_banner(self) -> str:
        """Create the main welcome banner for the wizard."""
        title_art = self.create_banner("BFCL", font='slant')
        subtitle = "Berkeley Function Call Leaderboard"
        wizard_text = "🧙‍♂️ Model Addition Wizard"
        
        lines = []
        lines.append(self.colorize(title_art, 'primary'))
        lines.append("")
        lines.append(self.colorize(f"{'=' * 60}", 'secondary'))
        lines.append(self.colorize(f"  {subtitle.center(56)}", 'highlight'))
        lines.append(self.colorize(f"  {wizard_text.center(56)}", 'info'))
        lines.append(self.colorize(f"{'=' * 60}", 'secondary'))
        lines.append("")
        
        return '\n'.join(lines)
    
    def create_completion_banner(self) -> str:
        """Create a completion banner."""
        success_art = self.create_banner("SUCCESS!", font='slant')
        
        lines = []
        lines.append(self.colorize(success_art, 'success'))
        lines.append("")
        lines.append(self.colorize("🎉 Model configuration completed successfully! 🎉", 'success'))
        lines.append("")
        
        return '\n'.join(lines)


class ModelAutomationError(Exception):
    """Base exception for model automation errors."""
    pass

class ValidationError(ModelAutomationError):
    """Raised when input validation fails."""
    pass

class BackupError(ModelAutomationError):
    """Raised when backup operations fail."""
    pass

class FileUpdateError(ModelAutomationError):
    """Raised when file update operations fail."""
    pass

class SecurityValidator:
    """Handles input sanitization and security validation."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
        # Define valid AWS regions for ARN validation
        self.valid_aws_regions = {
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2',
            'eu-west-3', 'eu-north-1', 'eu-south-1', 'ap-northeast-1',
            'ap-northeast-2', 'ap-northeast-3', 'ap-southeast-1',
            'ap-southeast-2', 'ap-south-1', 'sa-east-1', 'af-south-1',
            'me-south-1', 'ap-east-1'
        }
        
        # Known license identifiers
        self.valid_licenses = {
            'MIT', 'Apache-2.0', 'apache-2.0', 'GPL-3.0', 'GPL-2.0',
            'BSD-3-Clause', 'BSD-2-Clause', 'LGPL-2.1', 'LGPL-3.0',
            'CC-BY-4.0', 'CC-BY-SA-4.0', 'cc-by-nc-4.0', 'Proprietary',
            'Meta Llama 3 Community', 'gemma-terms-of-use', 'Varies', 'Unknown'
        }
    
    def sanitize_input(self, input_str: str, input_type: str = "general") -> str:
        """Sanitize user input to prevent injection attacks."""
        if not isinstance(input_str, str):
            raise ValidationError(f"Input must be string, got {type(input_str)}")
        
        # Remove null bytes
        sanitized = input_str.replace('\x00', '')
        
        # Input length limits
        max_lengths = {
            'model_name': 200,
            'display_name': 150,
            'org': 100,
            'url': 500,
            'license': 100,
            'general': 500
        }
        
        max_length = max_lengths.get(input_type, max_lengths['general'])
        if len(sanitized) > max_length:
            raise ValidationError(f"Input too long: {len(sanitized)} chars (max {max_length})")
        
        # Character set validation for model names
        if input_type == 'model_name' and not sanitized.startswith('arn:'):
            # Allow alphanumeric, hyphens, underscores, dots, forward slashes
            allowed_chars = re.compile(r'^[a-zA-Z0-9\-_.:/]+$')
            if not allowed_chars.match(sanitized):
                raise ValidationError("Model name contains invalid characters")
        
        # Path traversal protection
        if '..' in sanitized or sanitized.startswith('/') or '\\' in sanitized:
            raise ValidationError("Input contains potential path traversal sequences")
        
        # Code injection prevention - check for suspicious patterns
        suspicious_patterns = [
            r'import\s+os', r'import\s+sys', r'import\s+subprocess',
            r'eval\s*\(', r'exec\s*\(', r'__import__',
            r'open\s*\(', r'file\s*\(', r'input\s*\(',
            r'raw_input\s*\(', r'compile\s*\('
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValidationError(f"Input contains suspicious code pattern: {pattern}")
        
        return sanitized
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format and safety."""
        if not url:
            return True  # Optional field
        
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Only allow HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Basic domain validation
            domain = parsed.netloc.lower()
            if any(char in domain for char in ['<', '>', '"', "'"]):
                return False
            
            return True
            
        except Exception:
            return False
    
    def validate_license(self, license_str: str) -> bool:
        """Validate license identifier."""
        if not license_str:
            return False
        
        return license_str in self.valid_licenses
    
    def validate_aws_region(self, region: str) -> bool:
        """Validate AWS region name."""
        return region in self.valid_aws_regions
    
    def validate_account_id(self, account_id: str) -> bool:
        """Validate AWS account ID format (12-digit number)."""
        return bool(re.match(r'^\d{12}$', account_id))


class ARNValidator:
    """Enhanced ARN validation with comprehensive checks."""
    
    def __init__(self, logger: logging.Logger, security_validator: SecurityValidator):
        self.logger = logger
        self.security_validator = security_validator
        
        # Enhanced ARN patterns with more strict validation
        self.custom_deployment_pattern = re.compile(
            r'^arn:aws:bedrock:([a-z0-9\-]+):(\d{12}):custom-model-deployment/([a-zA-Z0-9\-_]+)$'
        )
        self.provisioned_throughput_pattern = re.compile(
            r'^arn:aws:bedrock:([a-z0-9\-]+):(\d{12}):provisioned-model-throughput/([a-zA-Z0-9\-_]+)$'
        )
    
    def validate_arn_format(self, arn: str) -> Tuple[bool, str, Dict[str, str]]:
        """
        Validate ARN format and extract components.
        Returns (is_valid, arn_type, components_dict)
        """
        if not arn or not isinstance(arn, str):
            return False, "", {}
        
        try:
            # Sanitize input first
            arn = self.security_validator.sanitize_input(arn, "general")
        except ValidationError as e:
            return False, "", {}
        
        # Check custom deployment ARN
        custom_match = self.custom_deployment_pattern.match(arn)
        if custom_match:
            region, account_id, deployment_id = custom_match.groups()
            components = {
                'service': 'bedrock',
                'region': region,
                'account_id': account_id,
                'resource_type': 'custom-model-deployment',
                'resource_id': deployment_id
            }
            return True, "custom_deployment", components
        
        # Check provisioned throughput ARN
        provisioned_match = self.provisioned_throughput_pattern.match(arn)
        if provisioned_match:
            region, account_id, endpoint_id = provisioned_match.groups()
            components = {
                'service': 'bedrock',
                'region': region,
                'account_id': account_id,
                'resource_type': 'provisioned-model-throughput',
                'resource_id': endpoint_id
            }
            return True, "provisioned_throughput", components
        
        return False, "", {}
    
    def validate_arn_components(self, components: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate individual ARN components."""
        errors = []
        
        # Validate region
        if not self.security_validator.validate_aws_region(components.get('region', '')):
            errors.append(f"Invalid AWS region: {components.get('region', 'missing')}")
        
        # Validate account ID
        if not self.security_validator.validate_account_id(components.get('account_id', '')):
            errors.append(f"Invalid AWS account ID format: {components.get('account_id', 'missing')}")
        
        # Validate resource ID format
        resource_id = components.get('resource_id', '')
        if not resource_id:
            errors.append("Missing resource ID")
        elif len(resource_id) > 63:  # AWS resource name limits
            errors.append("Resource ID too long (max 63 characters)")
        elif not re.match(r'^[a-zA-Z0-9\-_]+$', resource_id):
            errors.append("Resource ID contains invalid characters")
        
        return len(errors) == 0, errors
    
    def validate_resource_type_compatibility(self, arn_type: str, base_model: Optional[str]) -> Tuple[bool, str]:
        """Validate that resource type is compatible with base model requirements."""
        if arn_type in ["custom_deployment", "provisioned_throughput"]:
            if not base_model:
                return False, f"Base model is required for {arn_type.replace('_', ' ')} ARNs"
            
            # Additional validation could check if base_model exists in supported models
            # For now, just check it's not empty and reasonable length
            if len(base_model.strip()) == 0:
                return False, "Base model cannot be empty"
            if len(base_model) > 100:
                return False, "Base model name too long"
        
        return True, ""


class HandlerValidator:
    """Advanced handler class validation."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.handler_base_dir = BFCL_EVAL_DIR / "model_handler"
        self._handler_cache = {}
    
    def validate_handler_exists(self, handler_name: str) -> bool:
        """Check if handler class exists via import."""
        try:
            # Try to import from model_config module first
            spec = importlib.util.spec_from_file_location("model_config", MODEL_CONFIG_FILE)
            model_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(model_config)
            
            return hasattr(model_config, handler_name)
        except Exception as e:
            self.logger.debug(f"Error checking handler existence: {e}")
            return False
    
    def validate_handler_inheritance(self, handler_name: str) -> Tuple[bool, str]:
        """Validate that handler inherits from BaseHandler or appropriate subclass."""
        try:
            # Import the handler class dynamically
            handler_class = self._import_handler_class(handler_name)
            if not handler_class:
                return False, f"Handler class {handler_name} not found"
            
            # Check if it inherits from BaseHandler
            from bfcl_eval.model_handler.base_handler import BaseHandler
            
            if not issubclass(handler_class, BaseHandler):
                return False, f"Handler {handler_name} does not inherit from BaseHandler"
            
            # Check for required methods
            required_methods = ['inference', '_query_FC', '_query_prompting']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(handler_class, method):
                    missing_methods.append(method)
            
            if missing_methods:
                return False, f"Handler {handler_name} missing required methods: {', '.join(missing_methods)}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error validating handler inheritance: {str(e)}"
    
    def _import_handler_class(self, handler_name: str):
        """Dynamically import handler class."""
        if handler_name in self._handler_cache:
            return self._handler_cache[handler_name]
        
        # Try common handler import patterns
        handler_import_patterns = [
            ("api_inference", [
                "openai_response", "claude", "nova", "mistral", "gemini",
                "qwen", "deepseek", "cohere", "grok", "fireworks", "databricks"
            ]),
            ("local_inference", [
                "llama", "llama_3_1", "qwen", "qwen_fc", "phi", "phi_fc",
                "gemma", "deepseek", "glm"
            ])
        ]
        
        for inference_type, modules in handler_import_patterns:
            for module_name in modules:
                try:
                    module_path = self.handler_base_dir / inference_type / f"{module_name}.py"
                    if module_path.exists():
                        spec = importlib.util.spec_from_file_location(module_name, module_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        if hasattr(module, handler_name):
                            handler_class = getattr(module, handler_name)
                            self._handler_cache[handler_name] = handler_class
                            return handler_class
                            
                except Exception as e:
                    self.logger.debug(f"Failed to import from {module_path}: {e}")
                    continue
        
        return None
    
    def validate_handler_compatibility(self, handler_name: str, model_type: str) -> Tuple[bool, str]:
        """Validate handler is compatible with model type (FC vs Prompting)."""
        try:
            handler_class = self._import_handler_class(handler_name)
            if not handler_class:
                return False, f"Handler {handler_name} not found"
            
            # Check if handler supports the required inference type
            has_fc_methods = all(hasattr(handler_class, method) for method in [
                '_query_FC', '_parse_query_response_FC', 'add_first_turn_message_FC'
            ])
            
            has_prompting_methods = all(hasattr(handler_class, method) for method in [
                '_query_prompting', '_parse_query_response_prompting', 'add_first_turn_message_prompting'
            ])
            
            if model_type == "FC" and not has_fc_methods:
                return False, f"Handler {handler_name} does not support function calling"
            
            if model_type == "prompting" and not has_prompting_methods:
                return False, f"Handler {handler_name} does not support prompting mode"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error validating handler compatibility: {str(e)}"
    
    def validate_handler_file_structure(self, handler_name: str) -> Tuple[bool, str]:
        """Validate handler file location and structure."""
        try:
            # Find the handler file
            handler_file = None
            for inference_type in ["api_inference", "local_inference"]:
                inference_dir = self.handler_base_dir / inference_type
                if inference_dir.exists():
                    for py_file in inference_dir.glob("*.py"):
                        if py_file.name.startswith("__"):
                            continue
                        
                        try:
                            with open(py_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            if f"class {handler_name}" in content:
                                handler_file = py_file
                                break
                        except Exception:
                            continue
                
                if handler_file:
                    break
            
            if not handler_file:
                return False, f"Handler file for {handler_name} not found"
            
            # Validate file structure
            try:
                with open(handler_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file is syntactically valid
                ast.parse(content)
                
                # Check for class definition
                if f"class {handler_name}" not in content:
                    return False, f"Class {handler_name} not found in {handler_file}"
                
                return True, f"Handler file validated: {handler_file.relative_to(SCRIPT_DIR)}"
                
            except SyntaxError as e:
                return False, f"Syntax error in handler file {handler_file}: {e}"
            
        except Exception as e:
            return False, f"Error validating handler file structure: {str(e)}"


class ValidationEngine:
    """Coordinates multi-layer validation pipeline."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.security_validator = SecurityValidator(logger)
        self.arn_validator = ARNValidator(logger, self.security_validator)
        self.handler_validator = HandlerValidator(logger)
        
        # Track validation results for reporting
        self.validation_results = {
            'input_validation': [],
            'system_validation': [],
            'semantic_validation': [],
            'security_validation': []
        }
    
    def validate_complete_input(self, args: argparse.Namespace) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Run complete multi-layer validation pipeline.
        Returns (is_valid, detailed_results)
        """
        self.validation_results = {
            'input_validation': [],
            'system_validation': [],
            'semantic_validation': [],
            'security_validation': []
        }
        
        # Layer 1: Input Validation
        input_valid = self._validate_input_layer(args)
        
        # Layer 2: System Validation
        system_valid = self._validate_system_layer(args)
        
        # Layer 3: Semantic Validation
        semantic_valid = self._validate_semantic_layer(args)
        
        # Layer 4: Security Validation
        security_valid = self._validate_security_layer(args)
        
        overall_valid = all([input_valid, system_valid, semantic_valid, security_valid])
        
        return overall_valid, self.validation_results
    
    def _validate_input_layer(self, args: argparse.Namespace) -> bool:
        """Layer 1: Input validation with enhanced format and syntax checks."""
        valid = True
        
        try:
            # Enhanced model ID validation
            model_id = getattr(args, 'model_id', None)
            if model_id:
                # Sanitize input
                try:
                    sanitized_model_id = self.security_validator.sanitize_input(model_id, 'model_name')
                    
                    # Check for ARN format if it looks like ARN
                    if model_id.startswith('arn:'):
                        arn_valid, arn_type, components = self.arn_validator.validate_arn_format(model_id)
                        if not arn_valid:
                            valid = False
                            self.validation_results['input_validation'].append("Invalid ARN format")
                        else:
                            # Validate ARN components
                            components_valid, component_errors = self.arn_validator.validate_arn_components(components)
                            if not components_valid:
                                valid = False
                                self.validation_results['input_validation'].extend(component_errors)
                            else:
                                self.validation_results['input_validation'].append(f"✓ Valid {arn_type} ARN format")
                    else:
                        # Regular model ID validation
                        if len(model_id) < 1:
                            valid = False
                            self.validation_results['input_validation'].append("Model ID cannot be empty")
                        elif len(model_id) > 200:
                            valid = False
                            self.validation_results['input_validation'].append("Model ID too long (max 200 chars)")
                        else:
                            self.validation_results['input_validation'].append("✓ Valid model ID format")
                            
                except ValidationError as e:
                    valid = False
                    self.validation_results['input_validation'].append(f"Model ID validation failed: {str(e)}")
            
            # Enhanced URL validation
            url = getattr(args, 'url', None)
            if url:
                if not self.security_validator.validate_url(url):
                    valid = False
                    self.validation_results['input_validation'].append("Invalid URL format")
                else:
                    self.validation_results['input_validation'].append("✓ Valid URL format")
            
            # Enhanced license validation
            license_str = getattr(args, 'license', None)
            if license_str:
                if not self.security_validator.validate_license(license_str):
                    self.validation_results['input_validation'].append(f"⚠ Unknown license identifier: {license_str}")
                else:
                    self.validation_results['input_validation'].append("✓ Valid license identifier")
            
            # Enhanced pricing validation
            input_price = getattr(args, 'input_price', None)
            output_price = getattr(args, 'output_price', None)
            
            if input_price is not None or output_price is not None:
                if input_price is not None and (input_price < 0 or input_price > 1000):
                    valid = False
                    self.validation_results['input_validation'].append("Input price out of reasonable range (0-1000)")
                
                if output_price is not None and (output_price < 0 or output_price > 1000):
                    valid = False
                    self.validation_results['input_validation'].append("Output price out of reasonable range (0-1000)")
                
                if valid and (input_price is not None or output_price is not None):
                    self.validation_results['input_validation'].append("✓ Valid pricing parameters")
        
        except Exception as e:
            valid = False
            self.validation_results['input_validation'].append(f"Input validation error: {str(e)}")
        
        return valid
    
    def _validate_system_layer(self, args: argparse.Namespace) -> bool:
        """Layer 2: System validation with enhanced handler and file checks."""
        valid = True
        
        try:
            # Enhanced handler validation
            handler = getattr(args, 'handler', None)
            model_id = getattr(args, 'model_id', None)
            
            # Determine if this is an ARN input (which uses NovaHandler automatically)
            if model_id and model_id.startswith('arn:'):
                handler = 'NovaHandler'  # ARN inputs always use NovaHandler
            
            if handler:
                # Check handler exists
                if not self.handler_validator.validate_handler_exists(handler):
                    valid = False
                    self.validation_results['system_validation'].append(f"Handler class {handler} not found")
                else:
                    self.validation_results['system_validation'].append(f"✓ Handler {handler} exists")
                
                # Validate handler inheritance
                inheritance_valid, inheritance_msg = self.handler_validator.validate_handler_inheritance(handler)
                if not inheritance_valid:
                    valid = False
                    self.validation_results['system_validation'].append(inheritance_msg)
                else:
                    self.validation_results['system_validation'].append(f"✓ Handler inheritance validated")
                
                # Validate handler file structure
                file_valid, file_msg = self.handler_validator.validate_handler_file_structure(handler)
                if not file_valid:
                    valid = False
                    self.validation_results['system_validation'].append(file_msg)
                else:
                    self.validation_results['system_validation'].append(f"✓ Handler file structure validated")
            
            # File accessibility checks
            files_to_check = [MODEL_CONFIG_FILE, SUPPORTED_MODELS_FILE]
            for file_path in files_to_check:
                if not file_path.exists():
                    valid = False
                    self.validation_results['system_validation'].append(f"Required file missing: {file_path}")
                elif not os.access(file_path, os.R_OK | os.W_OK):
                    valid = False
                    self.validation_results['system_validation'].append(f"No read/write access: {file_path}")
                else:
                    self.validation_results['system_validation'].append(f"✓ File accessible: {file_path.name}")
        
        except Exception as e:
            valid = False
            self.validation_results['system_validation'].append(f"System validation error: {str(e)}")
        
        return valid
    
    def _validate_semantic_layer(self, args: argparse.Namespace) -> bool:
        """Layer 3: Semantic validation with enhanced duplicate detection and dependency checks."""
        valid = True
        
        try:
            model_id = getattr(args, 'model_id', None)
            
            if model_id:
                # Enhanced duplicate detection
                try:
                    spec = importlib.util.spec_from_file_location("model_config", MODEL_CONFIG_FILE)
                    model_config = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(model_config)
                    
                    if hasattr(model_config, 'MODEL_CONFIG_MAPPING'):
                        if model_id in model_config.MODEL_CONFIG_MAPPING:
                            valid = False
                            self.validation_results['semantic_validation'].append(f"Duplicate model: {model_id} already exists")
                        else:
                            self.validation_results['semantic_validation'].append("✓ No duplicate model found")
                except Exception as e:
                    valid = False
                    self.validation_results['semantic_validation'].append(f"Error checking duplicates: {str(e)}")
                
                # Enhanced dependency checks for ARN inputs
                if model_id.startswith('arn:'):
                    base_model = getattr(args, 'base_model', None)
                    if not base_model:
                        valid = False
                        self.validation_results['semantic_validation'].append("Base model required for ARN inputs")
                    else:
                        # Check if base model exists
                        try:
                            if hasattr(model_config, 'MODEL_CONFIG_MAPPING'):
                                if base_model not in model_config.MODEL_CONFIG_MAPPING:
                                    self.validation_results['semantic_validation'].append(f"⚠ Base model {base_model} not found in current configuration")
                                else:
                                    self.validation_results['semantic_validation'].append(f"✓ Base model {base_model} exists")
                        except Exception:
                            self.validation_results['semantic_validation'].append(f"⚠ Could not verify base model {base_model}")
                
                # Model type compatibility checks
                handler = getattr(args, 'handler', None)
                if model_id.startswith('arn:'):
                    handler = 'NovaHandler'
                
                is_fc_model = getattr(args, 'is_fc_model', None)
                if is_fc_model is None:
                    # Auto-detect from model ID
                    is_fc_model = any(model_id.endswith(suffix) for suffix in ["-FC", "-fc", "_FC", "_fc", "FC"])
                
                if handler and is_fc_model is not None:
                    model_type = "FC" if is_fc_model else "prompting"
                    compat_valid, compat_msg = self.handler_validator.validate_handler_compatibility(handler, model_type)
                    if not compat_valid:
                        valid = False
                        self.validation_results['semantic_validation'].append(compat_msg)
                    else:
                        self.validation_results['semantic_validation'].append(f"✓ Handler compatible with {model_type} mode")
        
        except Exception as e:
            valid = False
            self.validation_results['semantic_validation'].append(f"Semantic validation error: {str(e)}")
        
        return valid
    
    def _validate_security_layer(self, args: argparse.Namespace) -> bool:
        """Layer 4: Security validation with comprehensive input sanitization."""
        valid = True
        
        try:
            # Sanitize all text inputs
            text_fields = ['model_id', 'display_name', 'org', 'url', 'license', 'base_model']
            
            for field in text_fields:
                value = getattr(args, field, None)
                if value:
                    try:
                        field_type = field if field in ['model_name', 'display_name', 'org', 'url', 'license'] else 'general'
                        sanitized = self.security_validator.sanitize_input(value, field_type)
                        self.validation_results['security_validation'].append(f"✓ {field} sanitized and validated")
                    except ValidationError as e:
                        valid = False
                        self.validation_results['security_validation'].append(f"{field} security validation failed: {str(e)}")
            
            # Additional ARN-specific security checks
            model_id = getattr(args, 'model_id', None)
            if model_id and model_id.startswith('arn:'):
                arn_valid, arn_type, components = self.arn_validator.validate_arn_format(model_id)
                if arn_valid:
                    # Validate resource type compatibility
                    base_model = getattr(args, 'base_model', None)
                    resource_valid, resource_msg = self.arn_validator.validate_resource_type_compatibility(arn_type, base_model)
                    if not resource_valid:
                        valid = False
                        self.validation_results['security_validation'].append(resource_msg)
                    else:
                        self.validation_results['security_validation'].append("✓ ARN resource type validated")
        
        except Exception as e:
            valid = False
            self.validation_results['security_validation'].append(f"Security validation error: {str(e)}")
        
        return valid
    
    def generate_validation_report(self) -> str:
        """Generate a detailed validation report."""
        lines = [
            "Enhanced Validation Report",
            "=" * 50,
            ""
        ]
        
        layer_names = {
            'input_validation': 'Layer 1: Input Validation',
            'system_validation': 'Layer 2: System Validation',
            'semantic_validation': 'Layer 3: Semantic Validation',
            'security_validation': 'Layer 4: Security Validation'
        }
        
        for layer_key, layer_name in layer_names.items():
            results = self.validation_results.get(layer_key, [])
            if results:
                lines.append(f"{layer_name}:")
                lines.append("-" * len(layer_name))
                for result in results:
                    lines.append(f"  {result}")
                lines.append("")
        
        return "\n".join(lines)
    
    def get_validation_suggestions(self, args: argparse.Namespace) -> List[str]:
        """Provide enhanced validation suggestions with specific fixes."""
        suggestions = []
        
        # Check validation results for common issues and provide suggestions
        all_results = []
        for results in self.validation_results.values():
            all_results.extend(results)
        
        error_results = [r for r in all_results if not r.startswith('✓') and not r.startswith('⚠')]
        
        if any('Handler' in r for r in error_results):
            suggestions.append("Use --list-handlers to see all available model handlers")
        
        if any('ARN' in r for r in error_results):
            suggestions.append("Ensure ARN format is: arn:aws:bedrock:region:account:resource-type/resource-id")
            suggestions.append("Use valid AWS regions (e.g., us-east-1, us-west-2)")
        
        if any('Base model' in r for r in error_results):
            suggestions.append("Specify --base-model for ARN inputs (e.g., nova-pro-v1.0)")
        
        if any('duplicate' in r.lower() for r in error_results):
            suggestions.append("Check existing models with current configuration before adding")
        
        if any('URL' in r for r in error_results):
            suggestions.append("Ensure URL uses http:// or https:// protocol")
        
        if any('license' in r.lower() for r in error_results):
            suggestions.append("Use standard license identifiers: MIT, Apache-2.0, Proprietary, etc.")
        
        # Add general suggestions
        if not getattr(args, 'dry_run', False):
            suggestions.append("Use --dry-run to preview changes before applying")
        
        return suggestions


class ConfigTemplateManager:
    """Manages ModelConfig template generation with intelligent defaults."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        # Initialize the required attributes
        self._handler_defaults = self._build_handler_defaults()
        self._organization_mapping = self._build_organization_mapping()
        self._license_mapping = self._build_license_mapping()
        self._inference_map_routing = self._build_inference_map_routing()
        
    def generate_clean_model_key(self, model_id: str, base_model: Optional[str] = None) -> str:
        """Generate a clean dictionary key for ARNs and regular model IDs."""
        # If it's not an ARN, use the model_id as-is
        if not model_id.startswith("arn:"):
            return model_id
            
        # For ARNs, generate a clean key based on the deployment name and base model
        try:
            # Extract the resource ID from the ARN (last part after the last /)
            resource_id = model_id.split("/")[-1]
            
            # If we have a base_model, use it to create a meaningful name
            if base_model:
                # Convert base model to clean format (e.g., "nova-pro-v1.0" -> "custom-nova-pro")
                base_clean = base_model.replace("-v1.0", "").replace("-", "-")
                if base_clean.startswith("nova-"):
                    return f"custom-{base_clean}"
                else:
                    return f"custom-{base_clean}"
            else:
                # Fallback: use resource_id with custom prefix
                return f"custom-{resource_id}"
                
        except Exception as e:
            self.logger.warning(f"Failed to generate clean key from ARN {model_id}: {e}")
            # Fallback to using just the resource ID
            return model_id.split("/")[-1] if "/" in model_id else model_id
        self._handler_defaults = self._build_handler_defaults()
        self._organization_mapping = self._build_organization_mapping()
        self._license_mapping = self._build_license_mapping()
        self._inference_map_routing = self._build_inference_map_routing()
    
    def _build_handler_defaults(self) -> Dict[str, Dict[str, Any]]:
        """Build handler-specific default configurations."""
        return {
            # API Inference Handlers
            "OpenAIResponsesHandler": {
                "org": "OpenAI",
                "license": "Proprietary",
                "underscore_to_dot": True,
                "inference_map": "api",
                "url_template": "https://openai.com/",
                "pricing_required": True
            },
            "ClaudeHandler": {
                "org": "Anthropic",
                "license": "Proprietary",
                "underscore_to_dot": True,
                "inference_map": "api",
                "url_template": "https://www.anthropic.com/",
                "pricing_required": True
            },
            "NovaHandler": {
                "org": "Amazon",
                "license": "Proprietary",
                "underscore_to_dot": True,
                "inference_map": "api",
                "url_template": "https://aws.amazon.com/ai/generative-ai/nova/",
                "pricing_required": True
            },
            "MistralHandler": {
                "org": "Mistral AI",
                "license": "Proprietary",
                "underscore_to_dot": True,
                "inference_map": "api",
                "url_template": "https://docs.mistral.ai/",
                "pricing_required": True
            },
            "GeminiHandler": {
                "org": "Google",
                "license": "Proprietary",
                "underscore_to_dot": True,
                "inference_map": "api",
                "url_template": "https://deepmind.google/technologies/gemini/",
                "pricing_required": True
            },
            "QwenAPIHandler": {
                "org": "Qwen",
                "license": "apache-2.0",
                "underscore_to_dot": True,
                "inference_map": "api",
                "url_template": "https://huggingface.co/Qwen/",
                "pricing_required": False
            },
            "DeepSeekAPIHandler": {
                "org": "DeepSeek",
                "license": "MIT",
                "underscore_to_dot": True,
                "inference_map": "api",
                "url_template": "https://api-docs.deepseek.com/",
                "pricing_required": False
            },
            "CohereHandler": {
                "org": "Cohere",
                "license": "cc-by-nc-4.0",
                "underscore_to_dot": True,
                "inference_map": "api",
                "url_template": "https://cohere.com/",
                "pricing_required": True
            },
            "GrokHandler": {
                "org": "xAI",
                "license": "Proprietary",
                "underscore_to_dot": True,
                "inference_map": "api",
                "url_template": "https://docs.x.ai/",
                "pricing_required": True
            },
            # Local Inference Handlers
            "LlamaHandler": {
                "org": "Meta",
                "license": "Meta Llama 3 Community",
                "underscore_to_dot": False,
                "inference_map": "local",
                "url_template": "https://llama.meta.com/llama3",
                "pricing_required": False
            },
            "LlamaHandler_3_1": {
                "org": "Meta",
                "license": "Meta Llama 3 Community",
                "underscore_to_dot": False,
                "inference_map": "local",
                "url_template": "https://llama.meta.com/llama3",
                "pricing_required": False
            },
            "QwenHandler": {
                "org": "Qwen",
                "license": "apache-2.0",
                "underscore_to_dot": False,
                "inference_map": "local",
                "url_template": "https://huggingface.co/Qwen/",
                "pricing_required": False
            },
            "QwenFCHandler": {
                "org": "Qwen",
                "license": "apache-2.0",
                "underscore_to_dot": False,
                "inference_map": "local",
                "url_template": "https://huggingface.co/Qwen/",
                "pricing_required": False
            },
            "PhiHandler": {
                "org": "Microsoft",
                "license": "MIT",
                "underscore_to_dot": False,
                "inference_map": "local",
                "url_template": "https://huggingface.co/microsoft/",
                "pricing_required": False
            },
            "PhiFCHandler": {
                "org": "Microsoft",
                "license": "MIT",
                "underscore_to_dot": False,
                "inference_map": "local",
                "url_template": "https://huggingface.co/microsoft/",
                "pricing_required": False
            },
            "GemmaHandler": {
                "org": "Google",
                "license": "gemma-terms-of-use",
                "underscore_to_dot": False,
                "inference_map": "local",
                "url_template": "https://blog.google/technology/developers/gemma/",
                "pricing_required": False
            },
            # Third-party Inference Handlers
            "NovitaHandler": {
                "org": "Novita",
                "license": "Varies",
                "underscore_to_dot": True,
                "inference_map": "third_party",
                "url_template": "https://novita.ai/",
                "pricing_required": True
            }
        }
    
    def _build_organization_mapping(self) -> Dict[str, str]:
        """Build mapping from handlers to common organizations."""
        return {
            "OpenAIResponsesHandler": "OpenAI",
            "ClaudeHandler": "Anthropic",
            "NovaHandler": "Amazon",
            "MistralHandler": "Mistral AI",
            "GeminiHandler": "Google",
            "QwenAPIHandler": "Qwen",
            "QwenHandler": "Qwen",
            "QwenFCHandler": "Qwen",
            "DeepSeekAPIHandler": "DeepSeek",
            "LlamaHandler": "Meta",
            "LlamaHandler_3_1": "Meta",
            "PhiHandler": "Microsoft",
            "PhiFCHandler": "Microsoft",
            "GemmaHandler": "Google",
            "CohereHandler": "Cohere",
            "GrokHandler": "xAI"
        }
    
    def _build_license_mapping(self) -> Dict[str, str]:
        """Build mapping from organizations to common licenses."""
        return {
            "OpenAI": "Proprietary",
            "Anthropic": "Proprietary",
            "Amazon": "Proprietary",
            "Mistral AI": "Proprietary",
            "Google": "Proprietary",
            "Qwen": "apache-2.0",
            "DeepSeek": "MIT",
            "Meta": "Meta Llama 3 Community",
            "Microsoft": "MIT",
            "Cohere": "cc-by-nc-4.0",
            "xAI": "Proprietary"
        }
    
    def _build_inference_map_routing(self) -> Dict[str, str]:
        """Build mapping from handlers to inference map types."""
        return {
            # API handlers -> api inference map
            "OpenAIResponsesHandler": "api",
            "ClaudeHandler": "api",
            "NovaHandler": "api",
            "MistralHandler": "api",
            "GeminiHandler": "api",
            "QwenAPIHandler": "api",
            "DeepSeekAPIHandler": "api",
            "CohereHandler": "api",
            "GrokHandler": "api",
            "FireworksHandler": "api",
            "FunctionaryHandler": "api",
            "DatabricksHandler": "api",
            "NexusHandler": "api",
            "GoGoAgentHandler": "api",
            "WriterHandler": "api",
            "NemotronHandler": "api",
            "NvidiaHandler": "api",
            "YiHandler": "api",
            "GLMAPIHandler": "api",
            "KimiHandler": "api",
            "MiningHandler": "api",
            "DMCitoHandler": "api",
            "LingAPIHandler": "api",
            
            # Local handlers -> local inference map
            "LlamaHandler": "local",
            "LlamaHandler_3_1": "local",
            "QwenHandler": "local",
            "QwenFCHandler": "local",
            "PhiHandler": "local",
            "PhiFCHandler": "local",
            "GemmaHandler": "local",
            "DeepseekHandler": "local",
            "DeepseekCoderHandler": "local",
            "DeepseekReasoningHandler": "local",
            "GLMHandler": "local",
            "Granite3FCHandler": "local",
            "GraniteFunctionCallingHandler": "local",
            "HammerHandler": "local",
            "MiniCPMHandler": "local",
            "MiniCPMFCHandler": "local",
            "MistralFCHandler": "local",
            "Falcon3FCHandler": "local",
            "BielikHandler": "local",
            "BitAgentHandler": "local",
            "ThinkAgentHandler": "local",
            "ArchHandler": "local",
            "SalesforceLlamaHandler": "local",
            "SalesforceQwenHandler": "local",
            "GlaiveHandler": "local",
            "HermesHandler": "local",
            "QuickTestingOSSHandler": "local",
            
            # Third-party handlers -> third_party inference map
            "NovitaHandler": "third_party",
            "QwenAgentThinkHandler": "third_party",
            "QwenAgentNoThinkHandler": "third_party"
        }
    
    def detect_is_fc_model(self, model_id: str, user_specified: Optional[bool] = None) -> bool:
        """Detect if model is function-calling based on suffix or user input."""
        if user_specified is not None:
            return user_specified
        
        # Auto-detect based on common FC suffixes
        fc_suffixes = ["-FC", "-fc", "_FC", "_fc", "FC"]
        return any(model_id.endswith(suffix) for suffix in fc_suffixes)
    
    def generate_display_name(self, model_id: str, user_specified: Optional[str] = None,
                            is_fc_model: bool = True) -> str:
        """Generate display name from model ID or use user-specified name."""
        if user_specified:
            return user_specified
        
        # Clean up model ID for display name
        display_name = model_id
        
        # Remove ARN prefix if present
        if display_name.startswith("arn:aws:bedrock:"):
            # Extract just the model name from ARN
            parts = display_name.split('/')
            if len(parts) > 1:
                display_name = parts[-1]
        
        # Remove FC suffixes for clean display name
        fc_suffixes = ["-FC", "-fc", "_FC", "_fc"]
        for suffix in fc_suffixes:
            if display_name.endswith(suffix):
                display_name = display_name[:-len(suffix)]
                break
        
        # Add mode suffix
        mode_suffix = " (FC)" if is_fc_model else " (Prompt)"
        if not display_name.endswith(mode_suffix):
            display_name += mode_suffix
        
        return display_name
    
    def determine_pricing(self, handler_name: str, org: str,
                         user_input_price: Optional[float] = None,
                         user_output_price: Optional[float] = None) -> Tuple[Optional[float], Optional[float]]:
        """Determine pricing based on handler defaults and user input."""
        # User input takes precedence
        if user_input_price is not None or user_output_price is not None:
            return user_input_price, user_output_price
        
        # Check if handler requires pricing
        handler_defaults = self._handler_defaults.get(handler_name, {})
        if handler_defaults.get("pricing_required", False):
            # For proprietary models, return None to indicate pricing should be specified
            return None, None
        
        # For open source models, return None (free)
        return None, None
    
    def get_inference_map_type(self, handler_name: str, user_specified: Optional[str] = None) -> str:
        """Determine which inference map to use based on handler type."""
        if user_specified:
            return user_specified
        
        return self._inference_map_routing.get(handler_name, "api")  # Default to api
    
    def generate_base_template(self, model_id: str, handler_name: str,
                             input_type: str, user_args: Dict[str, Any]) -> ModelConfig:
        """Generate base ModelConfig template with intelligent defaults."""
        
        # Get handler defaults
        handler_defaults = self._handler_defaults.get(handler_name, {})
        
        # Determine organization
        org = user_args.get("org") or handler_defaults.get("org", "Unknown")
        
        # Determine license
        license_type = user_args.get("license") or self._license_mapping.get(org, "Unknown")
        
        # Detect FC model
        is_fc_model = self.detect_is_fc_model(model_id, user_args.get("is_fc_model"))
        
        # Generate display name
        display_name = self.generate_display_name(model_id, user_args.get("display_name"), is_fc_model)
        
        # Determine URL
        url = user_args.get("url")
        if not url and "url_template" in handler_defaults:
            url = handler_defaults["url_template"]
        
        # Determine pricing
        input_price, output_price = self.determine_pricing(
            handler_name, org,
            user_args.get("input_price"),
            user_args.get("output_price")
        )
        
        # Determine underscore_to_dot
        underscore_to_dot = user_args.get("underscore_to_dot")
        if underscore_to_dot is None:
            underscore_to_dot = handler_defaults.get("underscore_to_dot", False)
        
        # Determine base_model (only for ARN inputs)
        base_model = None
        if input_type in ["custom_deployment", "provisioned_throughput"]:
            base_model = user_args.get("base_model")
        
        # Check if ModelConfig supports base_model parameter before passing it
        import inspect
        modelconfig_params = inspect.signature(ModelConfig).parameters
        
        # Build ModelConfig kwargs dynamically based on what's supported
        config_kwargs = {
            'model_name': model_id,
            'display_name': display_name,
            'url': url or "https://example.com",  # Fallback URL
            'org': org,
            'license': license_type,
            'model_handler': handler_name,  # Will be converted to actual handler class later
            'input_price': input_price,
            'output_price': output_price,
            'is_fc_model': is_fc_model,
            'underscore_to_dot': underscore_to_dot,
        }
        
        # Always add base_model now that ModelConfig supports it
        if base_model is not None:
            config_kwargs['base_model'] = base_model
            self.logger.debug(f"Added base_model={base_model} to ModelConfig")
        
        return ModelConfig(**config_kwargs)
    
    def generate_regular_model_template(self, model_id: str, handler_name: str,
                                      user_args: Dict[str, Any]) -> ModelConfig:
        """Generate ModelConfig template for regular model IDs."""
        return self.generate_base_template(model_id, handler_name, "regular", user_args)
    
    def generate_custom_deployment_template(self, arn: str, base_model: str,
                                          user_args: Dict[str, Any]) -> ModelConfig:
        """Generate ModelConfig template for custom model deployment ARNs."""
        # Always use NovaHandler for AWS Bedrock custom deployments
        handler_name = "NovaHandler"
        user_args["base_model"] = base_model
        
        return self.generate_base_template(arn, handler_name, "custom_deployment", user_args)
    
    def generate_provisioned_throughput_template(self, arn: str, base_model: str,
                                               user_args: Dict[str, Any]) -> ModelConfig:
        """Generate ModelConfig template for provisioned throughput endpoint ARNs."""
        # Always use NovaHandler for AWS Bedrock provisioned throughput
        handler_name = "NovaHandler"
        user_args["base_model"] = base_model
        
        return self.generate_base_template(arn, handler_name, "provisioned_throughput", user_args)
    
    def preview_config(self, config: ModelConfig) -> str:
        """Generate a preview string of the ModelConfig for dry-run functionality."""
        lines = [
            "Generated ModelConfig Preview:",
            "=" * 40,
            f"Model Name: {config.model_name}",
            f"Display Name: {config.display_name}",
            f"URL: {config.url}",
            f"Organization: {config.org}",
            f"License: {config.license}",
            f"Handler: {config.model_handler}",
            f"Input Price: {config.input_price}",
            f"Output Price: {config.output_price}",
            f"Is FC Model: {config.is_fc_model}",
            f"Underscore to Dot: {config.underscore_to_dot}",
            f"Base Model: {getattr(config, 'base_model', 'Not applicable')}",
            "=" * 40
        ]
        return "\n".join(lines)
    
    def get_inference_map_name(self, handler_name: str, user_specified: Optional[str] = None) -> str:
        """Get the inference map name for file insertion."""
        map_type = self.get_inference_map_type(handler_name, user_specified)
        
        if map_type == "api":
            return "api_inference_model_map"
        elif map_type == "local":
            return "local_inference_model_map"
        elif map_type == "third_party":
            return "third_party_inference_model_map"
        else:
            return "api_inference_model_map"  # Default fallback

class HandlerDiscovery:
    """Discovers and categorizes available model handlers."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.handler_base_dir = BFCL_EVAL_DIR / "model_handler"
        self._handler_cache = None
    
    def discover_handlers(self) -> Dict[str, List[Dict[str, Any]]]:
        """Discover all available handlers and categorize them."""
        if self._handler_cache is not None:
            return self._handler_cache
        
        handlers = {
            "api": [],
            "local": [],
            "third_party": []
        }
        
        # Scan API inference handlers
        api_dir = self.handler_base_dir / "api_inference"
        if api_dir.exists():
            handlers["api"] = self._scan_handler_directory(api_dir, "api")
        
        # Scan local inference handlers
        local_dir = self.handler_base_dir / "local_inference"
        if local_dir.exists():
            handlers["local"] = self._scan_handler_directory(local_dir, "local")
        
        # Third-party handlers are typically in api_inference but marked as third-party
        # We'll identify them by known patterns or from the ConfigTemplateManager mappings
        handlers["third_party"] = self._identify_third_party_handlers(handlers["api"])
        
        # Remove third-party handlers from api list
        third_party_names = {h["handler_name"] for h in handlers["third_party"]}
        handlers["api"] = [h for h in handlers["api"] if h["handler_name"] not in third_party_names]
        
        self._handler_cache = handlers
        return handlers
    
    def _scan_handler_directory(self, directory: Path, category: str) -> List[Dict[str, Any]]:
        """Scan a directory for handler Python files."""
        handlers = []
        
        for file_path in directory.glob("*.py"):
            if file_path.name in ["__init__.py", "base_handler.py", "base_oss_handler.py", "utils.py"]:
                continue
            
            handler_info = self._extract_handler_info(file_path, category)
            if handler_info:
                handlers.append(handler_info)
        
        return sorted(handlers, key=lambda x: x["handler_name"])
    
    def _extract_handler_info(self, file_path: Path, category: str) -> Optional[Dict[str, Any]]:
        """Extract handler information from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST to find class definitions
            tree = ast.parse(content)
            handler_classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Look for classes that likely are handlers
                    class_name = node.name
                    if "Handler" in class_name and not class_name.startswith("Base"):
                        handler_classes.append(class_name)
            
            if not handler_classes:
                return None
            
            # For files with multiple handlers, use the main one (usually the one matching filename)
            file_base = file_path.stem
            main_handler = None
            
            # Try to find handler that matches filename pattern
            for handler_class in handler_classes:
                handler_lower = handler_class.lower()
                if file_base.replace('_', '').lower() in handler_lower:
                    main_handler = handler_class
                    break
            
            # If no match found, use the first handler
            if not main_handler:
                main_handler = handler_classes[0]
            
            # Extract docstring if available
            docstring = ast.get_docstring(tree) or ""
            description = docstring.split('\n')[0] if docstring else f"Handler for {file_base.replace('_', ' ').title()}"
            
            return {
                "handler_name": main_handler,
                "file_path": str(file_path.relative_to(SCRIPT_DIR)),
                "category": category,
                "description": description[:100] + "..." if len(description) > 100 else description,
                "all_classes": handler_classes
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to parse {file_path}: {e}")
            return None
    
    def _identify_third_party_handlers(self, api_handlers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify third-party handlers from the API handlers list."""
        # Get third-party handler names from ConfigTemplateManager
        config_manager = ConfigTemplateManager(self.logger)
        third_party_mapping = config_manager._inference_map_routing
        
        third_party_names = {
            name for name, map_type in third_party_mapping.items()
            if map_type == "third_party"
        }
        
        third_party_handlers = []
        for handler in api_handlers:
            if handler["handler_name"] in third_party_names:
                handler_copy = handler.copy()
                handler_copy["category"] = "third_party"
                third_party_handlers.append(handler_copy)
        
        return third_party_handlers
    
    def format_handlers_list(self) -> str:
        """Format the handlers list for display."""
        handlers = self.discover_handlers()
        
        lines = ["Available Model Handlers:", "=" * 50]
        
        for category, handler_list in handlers.items():
            if not handler_list:
                continue
                
            category_title = {
                "api": "API Inference Handlers",
                "local": "Local Inference Handlers",
                "third_party": "Third-Party Inference Handlers"
            }[category]
            
            lines.append(f"\n{category_title} ({len(handler_list)} handlers):")
            lines.append("-" * len(category_title))
            
            for handler in handler_list:
                lines.append(f"  • {handler['handler_name']}")
                if handler["description"]:
                    lines.append(f"    {handler['description']}")
                lines.append(f"    File: {handler['file_path']}")
                if len(handler["all_classes"]) > 1:
                    other_classes = [c for c in handler["all_classes"] if c != handler["handler_name"]]
                    lines.append(f"    Other classes: {', '.join(other_classes)}")
                lines.append("")
        
        total_handlers = sum(len(handler_list) for handler_list in handlers.values())
        lines.append(f"Total handlers found: {total_handlers}")
        
        return "\n".join(lines)

class InteractiveWizard:
    """Interactive configuration wizard for step-by-step model setup."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.config_manager = ConfigTemplateManager(logger)
        self.handler_discovery = HandlerDiscovery(logger)
        self.input_validator = InputValidator(logger)
        self.ascii_art = ASCIIArtGenerator()
        self.current_step = 1
        self.total_steps = 9
        self.config_data = {}
        self._available_handlers = None
    
    def _get_available_handlers(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get and cache available handlers."""
        if self._available_handlers is None:
            self._available_handlers = self.handler_discovery.discover_handlers()
        return self._available_handlers
    
    def _print_step_header(self, step_title: str):
        """Print formatted step header with ASCII art."""
        print("\n")
        
        # Create step indicator
        step_indicator = self.ascii_art.create_step_indicator(
            self.current_step, self.total_steps, step_title
        )
        print(self.ascii_art.colorize(step_indicator, 'info'))
        
        # Create section header
        section_header = self.ascii_art.create_section_header(
            f"🚀 {step_title}", width=70
        )
        print(self.ascii_art.colorize(section_header, 'primary'))
        print()
    
    def _get_input_with_default(self, prompt: str, default: Optional[str] = None,
                               validator: Optional[callable] = None) -> str:
        """Get user input with optional default and validation."""
        while True:
            if default:
                formatted_prompt = self.ascii_art.colorize(f"📝 {prompt}", 'info') + f" [default: {self.ascii_art.colorize(default, 'dim')}]: "
                user_input = input(formatted_prompt).strip()
                if not user_input:
                    user_input = default
            else:
                formatted_prompt = self.ascii_art.colorize(f"📝 {prompt}", 'info') + ": "
                user_input = input(formatted_prompt).strip()
            
            if validator:
                is_valid, error_msg = validator(user_input)
                if not is_valid:
                    error_display = self.ascii_art.colorize(f"❌ {error_msg}", 'error')
                    print(error_display)
                    continue
            
            return user_input
    
    def _get_yes_no_input(self, prompt: str, default: bool = True) -> bool:
        """Get yes/no input from user."""
        default_text = self.ascii_art.colorize("Y", 'highlight') + "/n" if default else "y/" + self.ascii_art.colorize("N", 'highlight')
        while True:
            formatted_prompt = self.ascii_art.colorize(f"❓ {prompt}", 'info') + f" ({default_text}): "
            response = input(formatted_prompt).strip().lower()
            if not response:
                return default
            if response in ['y', 'yes', 'true', '1']:
                return True
            elif response in ['n', 'no', 'false', '0']:
                return False
            else:
                error_msg = self.ascii_art.colorize("❌ Please enter 'y' for yes or 'n' for no.", 'error')
                print(error_msg)
    
    def _format_handlers_for_selection(self) -> str:
        """Format handlers for interactive selection."""
        handlers = self._get_available_handlers()
        lines = []
        
        handler_index = 1
        self._handler_lookup = {}  # Map numbers to handler info
        
        for category, handler_list in handlers.items():
            if not handler_list:
                continue
                
            category_title = {
                "api": "🌐 API Inference Handlers",
                "local": "💻 Local Inference Handlers",
                "third_party": "🔗 Third-Party Inference Handlers"
            }[category]
            
            lines.append(f"\n{category_title}:")
            
            for handler in handler_list:
                lines.append(f"  {handler_index:2d}. {handler['handler_name']}")
                if handler["description"]:
                    lines.append(f"      {handler['description']}")
                self._handler_lookup[handler_index] = handler
                handler_index += 1
        
        return "\n".join(lines)
    
    def step1_model_identifier(self) -> bool:
        """Step 1: Get model ID or ARN."""
        self._print_step_header("Model Identifier")
        
        # Create info box with examples
        examples_content = [
            "Enter the model identifier. This can be:",
            "",
            "🔹 Regular model ID:",
            "   • gpt-4-turbo",
            "   • claude-3-sonnet",
            "   • llama-3.1-70b",
            "",
            "🔹 Custom deployment ARN:",
            "   • arn:aws:bedrock:us-east-1:123456789012:custom-model-deployment/my-model",
            "",
            "🔹 Provisioned throughput ARN:",
            "   • arn:aws:bedrock:us-east-1:123456789012:provisioned-model-throughput/my-endpoint"
        ]
        
        examples_box = self.ascii_art.create_info_box(
            "📝 Model Identifier Examples", examples_content, width=80
        )
        print(self.ascii_art.colorize(examples_box, 'info'))
        
        def validate_model_id(model_id: str) -> Tuple[bool, str]:
            if not model_id:
                return False, "Model ID cannot be empty"
            
            # Check for duplicates
            if self.input_validator.check_duplicate_model(model_id):
                return False, f"Model '{model_id}' already exists in configuration"
            
            # Validate format
            if not self.input_validator.validate_model_id(model_id):
                return False, "Invalid model ID format"
            
            return True, ""
        
        print(self.ascii_art.colorize("\n🎯 Enter your model identifier:", 'highlight'))
        self.config_data['model_id'] = self._get_input_with_default(
            "Model ID or ARN",
            validator=validate_model_id
        )
        
        # Detect input type
        self.config_data['input_type'] = self.input_validator.detect_input_type(self.config_data['model_id'])
        
        input_type_desc = {
            "regular": "Regular model ID",
            "custom_deployment": "Custom deployment ARN",
            "provisioned_throughput": "Provisioned throughput ARN"
        }
        
        success_msg = f"✅ Detected input type: {input_type_desc[self.config_data['input_type']]}"
        print(self.ascii_art.colorize(success_msg, 'success'))
        
        self.current_step += 1
        return True
    
    def step2_handler_selection(self) -> bool:
        """Step 2: Select model handler."""
        self._print_step_header("Handler Selection")
        
        # For ARN inputs, handler is predetermined
        if self.config_data['input_type'] in ['custom_deployment', 'provisioned_throughput']:
            self.config_data['handler'] = 'NovaHandler'
            
            # Create info box for ARN handler selection
            arn_info = [
                "AWS Bedrock ARN inputs automatically use NovaHandler.",
                "This handler is specifically designed for:",
                "• Custom model deployments",
                "• Provisioned throughput endpoints",
                "• AWS Bedrock model integration"
            ]
            
            arn_box = self.ascii_art.create_info_box(
                "🤖 Handler Auto-Selected", arn_info, width=60
            )
            print(self.ascii_art.colorize(arn_box, 'success'))
            
            success_msg = "✅ Using NovaHandler (required for AWS Bedrock ARN inputs)"
            print(self.ascii_art.colorize(success_msg, 'success'))
            self.current_step += 1
            return True
        
        # Show available handlers
        print("Available handlers:")
        handlers_text = self._format_handlers_for_selection()
        print(handlers_text)
        
        def validate_handler_selection(selection: str) -> Tuple[bool, str]:
            try:
                handler_num = int(selection)
                if handler_num not in self._handler_lookup:
                    return False, f"Invalid selection. Please choose a number between 1 and {len(self._handler_lookup)}"
                return True, ""
            except ValueError:
                return False, "Please enter a valid number"
        
        while True:
            selection = self._get_input_with_default(
                f"\nSelect handler (1-{len(self._handler_lookup)})",
                validator=validate_handler_selection
            )
            
            handler_num = int(selection)
            selected_handler = self._handler_lookup[handler_num]
            self.config_data['handler'] = selected_handler['handler_name']
            
            print(f"✅ Selected: {selected_handler['handler_name']} ({selected_handler['category']})")
            break
        
        self.current_step += 1
        return True
    
    def step3_display_name(self) -> bool:
        """Step 3: Configure display name."""
        self._print_step_header("Display Name")
        
        # Generate intelligent default
        is_fc = self.config_manager.detect_is_fc_model(self.config_data['model_id'])
        default_display_name = self.config_manager.generate_display_name(
            self.config_data['model_id'], is_fc_model=is_fc
        )
        
        print(f"The display name will be shown in the leaderboard.")
        print(f"Generated default: '{default_display_name}'")
        
        display_name = self._get_input_with_default(
            "\nEnter display name (press Enter for default)",
            default=default_display_name
        )
        
        self.config_data['display_name'] = display_name
        self.config_data['is_fc_model'] = is_fc
        
        print(f"✅ Display name: {display_name}")
        self.current_step += 1
        return True
    
    def step4_organization(self) -> bool:
        """Step 4: Configure organization."""
        self._print_step_header("Organization")
        
        # Get default from handler
        handler_defaults = self.config_manager._handler_defaults.get(self.config_data['handler'], {})
        default_org = handler_defaults.get('org', 'Unknown')
        
        print(f"Organization that created/maintains this model.")
        print(f"Common organizations: OpenAI, Anthropic, Google, Meta, Microsoft, Amazon")
        
        org = self._get_input_with_default(
            "\nOrganization name",
            default=default_org
        )
        
        self.config_data['org'] = org
        print(f"✅ Organization: {org}")
        self.current_step += 1
        return True
    
    def step5_license(self) -> bool:
        """Step 5: Configure license."""
        self._print_step_header("License")
        
        # Get default from organization mapping
        default_license = self.config_manager._license_mapping.get(self.config_data['org'], 'Unknown')
        
        print(f"License under which the model is released.")
        print(f"Common licenses: Proprietary, MIT, apache-2.0, cc-by-nc-4.0")
        
        license_type = self._get_input_with_default(
            "\nLicense type",
            default=default_license
        )
        
        self.config_data['license'] = license_type
        print(f"✅ License: {license_type}")
        self.current_step += 1
        return True
    
    def step6_url_configuration(self) -> bool:
        """Step 6: Configure URL."""
        self._print_step_header("URL Configuration")
        
        # Get default from handler
        handler_defaults = self.config_manager._handler_defaults.get(self.config_data['handler'], {})
        default_url = handler_defaults.get('url_template', '')
        
        print(f"Reference URL for model documentation or information.")
        print(f"This is optional but recommended for users to learn more about the model.")
        
        if default_url:
            url = self._get_input_with_default(
                "\nReference URL (press Enter for default)",
                default=default_url
            )
        else:
            url = input("\nReference URL (optional, press Enter to skip): ").strip()
            if not url:
                url = "https://example.com"  # Fallback
        
        self.config_data['url'] = url
        print(f"✅ URL: {url}")
        self.current_step += 1
        return True
    
    def step7_pricing_configuration(self) -> bool:
        """Step 7: Configure pricing."""
        self._print_step_header("Pricing Configuration")
        
        # Check if pricing is required for this handler
        handler_defaults = self.config_manager._handler_defaults.get(self.config_data['handler'], {})
        pricing_required = handler_defaults.get('pricing_required', False)
        
        if pricing_required:
            print(f"This handler typically requires pricing information.")
            print(f"Prices should be in USD per million tokens.")
            print(f"If you don't know the exact prices, you can enter estimates.")
            
            def validate_price(price_str: str) -> Tuple[bool, str]:
                if not price_str:
                    return True, ""  # Optional
                try:
                    price = float(price_str)
                    if price < 0:
                        return False, "Price cannot be negative"
                    return True, ""
                except ValueError:
                    return False, "Please enter a valid number"
            
            input_price_str = self._get_input_with_default(
                "\nInput price per million tokens (optional)",
                validator=validate_price
            )
            output_price_str = self._get_input_with_default(
                "Output price per million tokens (optional)",
                validator=validate_price
            )
            
            self.config_data['input_price'] = float(input_price_str) if input_price_str else None
            self.config_data['output_price'] = float(output_price_str) if output_price_str else None
        else:
            print(f"This handler typically doesn't require pricing (likely open-source).")
            skip_pricing = self._get_yes_no_input("Skip pricing configuration?", default=True)
            
            if skip_pricing:
                self.config_data['input_price'] = None
                self.config_data['output_price'] = None
            else:
                # Allow manual pricing entry
                def validate_price(price_str: str) -> Tuple[bool, str]:
                    if not price_str:
                        return True, ""
                    try:
                        price = float(price_str)
                        if price < 0:
                            return False, "Price cannot be negative"
                        return True, ""
                    except ValueError:
                        return False, "Please enter a valid number"
                
                input_price_str = self._get_input_with_default(
                    "Input price per million tokens (optional)",
                    validator=validate_price
                )
                output_price_str = self._get_input_with_default(
                    "Output price per million tokens (optional)",
                    validator=validate_price
                )
                
                self.config_data['input_price'] = float(input_price_str) if input_price_str else None
                self.config_data['output_price'] = float(output_price_str) if output_price_str else None
        
        pricing_info = []
        if self.config_data['input_price'] is not None:
            pricing_info.append(f"Input: ${self.config_data['input_price']}/M tokens")
        if self.config_data['output_price'] is not None:
            pricing_info.append(f"Output: ${self.config_data['output_price']}/M tokens")
        
        if pricing_info:
            print(f"✅ Pricing: {', '.join(pricing_info)}")
        else:
            print(f"✅ Pricing: Not specified (likely free/open-source)")
        
        self.current_step += 1
        return True
    
    def step8_base_model_configuration(self) -> bool:
        """Step 8: Configure base model (ARN inputs only)."""
        if self.config_data['input_type'] not in ['custom_deployment', 'provisioned_throughput']:
            # Skip this step for regular models
            self.current_step += 1
            return True
        
        self._print_step_header("Base Model Configuration")
        
        print(f"For ARN inputs, you need to specify the base model that this deployment/endpoint uses.")
        print(f"This should be an existing model ID from the leaderboard (e.g., 'nova-pro-v1.0').")
        print(f"The base model is used for evaluation and comparison purposes.")
        
        def validate_base_model(base_model: str) -> Tuple[bool, str]:
            if not base_model:
                return False, "Base model is required for ARN inputs"
            return True, ""
        
        base_model = self._get_input_with_default(
            "\nBase model ID",
            validator=validate_base_model
        )
        
        self.config_data['base_model'] = base_model
        print(f"✅ Base model: {base_model}")
        self.current_step += 1
        return True
    
    def step9_final_preview_confirmation(self) -> bool:
        """Step 9: Show preview and get final confirmation."""
        self._print_step_header("Review Configuration")
        
        print("Please review your configuration:")
        print("\n" + "="*50)
        print(f"Model ID/ARN: {self.config_data['model_id']}")
        print(f"Input Type: {self.config_data['input_type']}")
        print(f"Handler: {self.config_data['handler']}")
        print(f"Display Name: {self.config_data['display_name']}")
        print(f"Organization: {self.config_data['org']}")
        print(f"License: {self.config_data['license']}")
        print(f"URL: {self.config_data['url']}")
        
        if self.config_data.get('input_price') or self.config_data.get('output_price'):
            pricing_parts = []
            if self.config_data.get('input_price'):
                pricing_parts.append(f"Input: ${self.config_data['input_price']}/M")
            if self.config_data.get('output_price'):
                pricing_parts.append(f"Output: ${self.config_data['output_price']}/M")
            print(f"Pricing: {', '.join(pricing_parts)}")
        else:
            print(f"Pricing: Not specified")
        
        print(f"Function Calling: {self.config_data['is_fc_model']}")
        
        if self.config_data.get('base_model'):
            print(f"Base Model: {self.config_data['base_model']}")
        
        print("="*50)
        
        proceed = self._get_yes_no_input("\nProceed with adding this model?", default=True)
        
        if proceed:
            print("✅ Configuration confirmed!")
            self.current_step += 1
            return True
        else:
            print("❌ Configuration cancelled.")
            return False
    
    def run_wizard(self) -> Optional[argparse.Namespace]:
        """Run the complete interactive wizard and return configured arguments."""
        # Display welcome banner
        welcome_banner = self.ascii_art.create_welcome_banner()
        print(welcome_banner)
        
        # Display introduction
        intro_content = [
            "Welcome to the interactive model configuration wizard!",
            "",
            "This wizard will guide you through:",
            "• Model identification and validation",
            "• Handler selection and configuration",
            "• Metadata and pricing setup",
            "• Final review and confirmation",
            "",
            "You can press Ctrl+C at any time to cancel."
        ]
        
        intro_box = self.ascii_art.create_info_box(
            "🎯 Getting Started", intro_content, width=70
        )
        print(self.ascii_art.colorize(intro_box, 'info'))
        print()
        
        try:
            # Execute all steps
            steps = [
                self.step1_model_identifier,
                self.step2_handler_selection,
                self.step3_display_name,
                self.step4_organization,
                self.step5_license,
                self.step6_url_configuration,
                self.step7_pricing_configuration,
                self.step8_base_model_configuration,
                self.step9_final_preview_confirmation
            ]
            
            for step_func in steps:
                if not step_func():
                    # User cancelled or error occurred
                    return None
            
            # Show completion banner
            completion_banner = self.ascii_art.create_completion_banner()
            print(completion_banner)
            
            # Convert wizard data to argparse.Namespace
            args = argparse.Namespace()
            args.model_id = self.config_data['model_id']
            args.handler = self.config_data.get('handler')
            args.display_name = self.config_data.get('display_name')
            args.org = self.config_data.get('org')
            args.url = self.config_data.get('url')
            args.license = self.config_data.get('license')
            args.input_price = self.config_data.get('input_price')
            args.output_price = self.config_data.get('output_price')
            args.is_fc_model = self.config_data.get('is_fc_model')
            args.base_model = self.config_data.get('base_model')
            
            # Set defaults for other required attributes
            args.underscore_to_dot = None  # Will be determined by ConfigTemplateManager
            args.inference_type = None  # Will be determined by ConfigTemplateManager
            args.dry_run = False
            args.force = True  # Skip confirmation since wizard already confirmed
            args.no_backup = False
            args.interactive = False  # Prevent recursive wizard calls
            
            return args
            
        except KeyboardInterrupt:
            cancel_msg = "\n\n🛑 Wizard cancelled by user (Ctrl+C)"
            print(self.ascii_art.colorize(cancel_msg, 'warning'))
            
            farewell_box = self.ascii_art.create_info_box(
                "👋 Thanks for trying BFCL Model Wizard",
                ["Feel free to run the wizard again anytime!", "Your input is always appreciated."],
                width=50
            )
            print(self.ascii_art.colorize(farewell_box, 'info'))
            return None
        except Exception as e:
            self.logger.error(f"Error in interactive wizard: {e}")
            
            error_msg = f"\n💥 An unexpected error occurred: {e}"
            print(self.ascii_art.colorize(error_msg, 'error'))
            
            error_box = self.ascii_art.create_info_box(
                "🚨 Error Details",
                [
                    "The wizard encountered an unexpected error.",
                    "Please check the logs for more details.",
                    "You can try running the wizard again or",
                    "use the command-line arguments directly."
                ],
                width=60
            )
            print(self.ascii_art.colorize(error_box, 'error'))
            return None


class YAMLConfigManager:
    """Manages YAML configuration file loading and parsing."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.default_config_file = SCRIPT_DIR / "bfcl_model_config.yaml"
    
    def load_config(self, config_file: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """Load configuration from YAML file."""
        config_path = config_file or self.default_config_file
        
        if not config_path.exists():
            if config_file:  # Explicitly specified file doesn't exist
                self.logger.error(f"Configuration file not found: {config_path}")
                return None
            else:  # Default file doesn't exist, which is fine
                self.logger.debug(f"Default config file not found: {config_path}")
                return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.logger.info(f"Loaded configuration from: {config_path}")
            return config
            
        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in {config_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load config file {config_path}: {e}")
            return None
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the structure of the YAML configuration."""
        if not isinstance(config, dict):
            self.logger.error("Configuration must be a dictionary")
            return False
        
        if "models" not in config:
            self.logger.error("Configuration must contain a 'models' key")
            return False
        
        models = config["models"]
        if not isinstance(models, list):
            self.logger.error("'models' must be a list")
            return False
        
        for i, model in enumerate(models):
            if not isinstance(model, dict):
                self.logger.error(f"Model entry {i} must be a dictionary")
                return False
            
            if "model_id" not in model:
                self.logger.error(f"Model entry {i} missing required 'model_id' field")
                return False
        
        return True
    
    def get_example_config(self) -> str:
        """Return an example YAML configuration."""
        return """# BFCL Model Configuration
# This file allows you to define multiple models to be added in batch
models:
  - model_id: "gpt-4-turbo"
    handler: "OpenAIResponsesHandler"
    display_name: "GPT-4 Turbo"
    org: "OpenAI"
    url: "https://openai.com/"
    license: "Proprietary"
    input_price: 10.0
    output_price: 30.0
    is_fc_model: true
    underscore_to_dot: true

  - model_id: "claude-3-5-sonnet-20241022"
    handler: "ClaudeHandler"
    display_name: "Claude 3.5 Sonnet"
    org: "Anthropic"
    url: "https://www.anthropic.com/"
    license: "Proprietary"
    input_price: 3.0
    output_price: 15.0
    is_fc_model: true
    underscore_to_dot: true

  - model_id: "arn:aws:bedrock:us-east-1:123456789012:custom-model-deployment/my-model"
    base_model: "nova-pro-v1.0"
    display_name: "My Custom Nova Model"
    org: "Amazon"
    url: "https://aws.amazon.com/ai/generative-ai/nova/"
    license: "Proprietary"
    input_price: 2.0
    output_price: 8.0
    is_fc_model: true
    underscore_to_dot: true
"""

class BackupManager:
    """Manages file backups and rollback operations."""
    
    def __init__(self, logger: logging.Logger, backup_dir: Path = BACKUP_DIR):
        self.logger = logger
        self.backup_dir = backup_dir
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_files = {}
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, file_path: Path) -> Path:
        """Create a timestamped backup of the specified file."""
        if not file_path.exists():
            raise BackupError(f"Cannot backup non-existent file: {file_path}")
        
        # Generate backup filename with timestamp
        backup_filename = f"{file_path.stem}_{self.backup_timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_filename
        
        try:
            shutil.copy2(file_path, backup_path)
            self.backup_files[file_path] = backup_path
            self.logger.info(f"Created backup: {file_path} -> {backup_path}")
            return backup_path
        except Exception as e:
            raise BackupError(f"Failed to create backup for {file_path}: {e}")
    
    def create_all_backups(self, files: List[Path]) -> Dict[Path, Path]:
        """Create backups for all specified files."""
        backups = {}
        
        try:
            for file_path in files:
                backup_path = self.create_backup(file_path)
                backups[file_path] = backup_path
            
            self.logger.info(f"Successfully created {len(backups)} backup files")
            return backups
        
        except Exception as e:
            # If any backup fails, clean up partial backups
            self.cleanup_backups(list(backups.values()))
            raise BackupError(f"Backup creation failed: {e}")
    
    def verify_backup(self, original_path: Path, backup_path: Path) -> bool:
        """Verify that backup file matches the original."""
        if not backup_path.exists():
            return False
        
        try:
            # Compare file sizes first (quick check)
            if original_path.stat().st_size != backup_path.stat().st_size:
                return False
            
            # Compare file contents
            with open(original_path, 'rb') as orig, open(backup_path, 'rb') as backup:
                return orig.read() == backup.read()
        
        except Exception as e:
            self.logger.error(f"Error verifying backup: {e}")
            return False
    
    def rollback_file(self, original_path: Path) -> bool:
        """Restore a single file from its backup."""
        backup_path = self.backup_files.get(original_path)
        
        if not backup_path or not backup_path.exists():
            self.logger.error(f"No valid backup found for {original_path}")
            return False
        
        try:
            shutil.copy2(backup_path, original_path)
            self.logger.info(f"Rolled back: {backup_path} -> {original_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to rollback {original_path}: {e}")
            return False
    
    def rollback_all(self) -> bool:
        """Restore all files from their backups."""
        success = True
        
        for original_path in self.backup_files:
            if not self.rollback_file(original_path):
                success = False
        
        if success:
            self.logger.info("Successfully rolled back all files")
        else:
            self.logger.error("Some files failed to rollback")
        
        return success
    
    def cleanup_backups(self, backup_paths: Optional[List[Path]] = None) -> None:
        """Clean up backup files."""
        if backup_paths is None:
            backup_paths = list(self.backup_files.values())
        
        for backup_path in backup_paths:
            try:
                if backup_path.exists():
                    backup_path.unlink()
                    self.logger.debug(f"Cleaned up backup: {backup_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup backup {backup_path}: {e}")


class AtomicFileUpdater:
    """Handles atomic file updates using temporary files and atomic renames."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def write_atomically(self, file_path: Path, content: str) -> bool:
        """Write content to file atomically using temporary file + rename."""
        try:
            # Create temporary file in the same directory as target file
            temp_dir = file_path.parent
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=temp_dir,
                suffix='.tmp',
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(content)
                temp_file.flush()
                os.fsync(temp_file.fileno())  # Force write to disk
            
            # Atomic rename
            temp_path.replace(file_path)
            self.logger.debug(f"Atomically wrote {len(content)} characters to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write atomically to {file_path}: {e}")
            # Clean up temp file if it exists
            try:
                if 'temp_path' in locals() and temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            return False


class SyntaxValidator:
    """Validates Python syntax correctness using AST parsing."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def validate_python_syntax(self, content: str, file_path: Optional[Path] = None) -> bool:
        """Validate that content is syntactically correct Python."""
        try:
            ast.parse(content)
            self.logger.debug(f"Syntax validation passed for {file_path or 'content'}")
            return True
        except SyntaxError as e:
            self.logger.error(f"Syntax error in {file_path or 'content'}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error validating syntax: {e}")
            return False
    
    def validate_file_syntax(self, file_path: Path) -> bool:
        """Validate syntax of an existing file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.validate_python_syntax(content, file_path)
        except Exception as e:
            self.logger.error(f"Failed to read file for syntax validation: {e}")
            return False


class FileParser:
    """Parses and analyzes Python source files for modification."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def read_file_content(self, file_path: Path) -> Optional[str]:
        """Read file content safely."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return None
    
    def parse_imports(self, content: str) -> List[str]:
        """Extract import statements from Python content."""
        try:
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    names = ", ".join([alias.name for alias in node.names])
                    imports.append(f"from {module} import {names}")
            
            return imports
        except Exception as e:
            self.logger.error(f"Failed to parse imports: {e}")
            return []
    
    def find_import_section_end(self, lines: List[str]) -> int:
        """Find the line number where imports end."""
        import_end = 0
        in_docstring = False
        docstring_delim = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Handle docstrings
            if '"""' in stripped or "'''" in stripped:
                if not in_docstring:
                    in_docstring = True
                    docstring_delim = '"""' if '"""' in stripped else "'''"
                elif docstring_delim in stripped:
                    in_docstring = False
                    docstring_delim = None
                continue
            
            if in_docstring:
                continue
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue
                
            # Check for import statements
            if (stripped.startswith('import ') or
                stripped.startswith('from ') or
                '= importlib.' in stripped):
                import_end = i + 1
            elif stripped and import_end > 0:
                # First non-import statement after imports
                break
        
        return import_end
    
    def find_dict_insertion_point(self, content: str, dict_name: str, key: str) -> Optional[int]:
        """Find the line number where to insert a new dictionary entry in alphabetical order."""
        lines = content.split('\n')
        
        # Find the dictionary definition
        dict_start = None
        brace_count = 0
        in_dict = False
        
        for i, line in enumerate(lines):
            if f"{dict_name} = {{" in line:
                dict_start = i
                in_dict = True
                brace_count = line.count('{') - line.count('}')
                continue
            
            if in_dict:
                brace_count += line.count('{') - line.count('}')
                
                # Check if this line contains a dictionary key
                stripped = line.strip()
                if stripped.startswith('"') and '":' in stripped:
                    # Extract the key from the line
                    key_match = re.match(r'^\s*"([^"]+)":', stripped)
                    if key_match:
                        existing_key = key_match.group(1)
                        if key > existing_key:
                            continue  # Keep looking for insertion point
                        else:
                            # Found insertion point
                            return i
                
                # End of dictionary
                if brace_count == 0:
                    return i  # Insert before closing brace
        
        return None


class InsertionPointFinder:
    """Finds appropriate insertion points for maintaining alphabetical order."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def find_alphabetical_insertion_point(self, items: List[str], new_item: str) -> int:
        """Find where to insert new_item to maintain alphabetical order."""
        for i, item in enumerate(items):
            if new_item < item:
                return i
        return len(items)  # Insert at end
    
    def find_model_config_insertion_point(self, content: str, inference_map: str, model_key: str) -> Optional[int]:
        """Find insertion point in model config file for new ModelConfig entry."""
        lines = content.split('\n')
        
        # Find the inference map definition
        map_pattern = f"{inference_map} = {{"
        map_start = None
        
        for i, line in enumerate(lines):
            if map_pattern in line:
                map_start = i
                break
        
        if map_start is None:
            self.logger.error(f"Could not find {inference_map} definition")
            return None
        
        # Find alphabetical insertion point within the map
        brace_count = 0
        in_map = False
        keys_found = []
        
        for i in range(map_start, len(lines)):
            line = lines[i]
            
            if i == map_start:
                in_map = True
                brace_count = line.count('{') - line.count('}')
                continue
            
            if in_map:
                brace_count += line.count('{') - line.count('}')
                
                # Check for model key
                stripped = line.strip()
                if stripped.startswith('"') and '":' in stripped:
                    key_match = re.match(r'^\s*"([^"]+)":', stripped)
                    if key_match:
                        existing_key = key_match.group(1)
                        if model_key < existing_key:
                            return i  # Insert before this entry
                        keys_found.append(existing_key)
                
                # End of map
                if brace_count == 0:
                    # Insert before closing brace
                    return i
        
        return None
    
    def find_supported_models_insertion_point(self, content: str, model_key: str) -> Optional[int]:
        """Find insertion point in supported_models.py for new model."""
        lines = content.split('\n')
        
        # Find SUPPORTED_MODELS list
        list_start = None
        for i, line in enumerate(lines):
            if "SUPPORTED_MODELS = [" in line:
                list_start = i
                break
        
        if list_start is None:
            self.logger.error("Could not find SUPPORTED_MODELS list")
            return None
        
        # Find alphabetical insertion point
        for i in range(list_start + 1, len(lines)):
            line = lines[i]
            stripped = line.strip()
            
            # Check for list entry
            if stripped.startswith('"') and stripped.endswith('",'):
                existing_key = stripped[1:-2]  # Remove quotes and comma
                if model_key < existing_key:
                    return i  # Insert before this entry
            elif stripped == "]":
                return i  # Insert before closing bracket
        
        return None


class ImportManager:
    """Manages import statements in Python files."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def check_import_exists(self, content: str, import_statement: str) -> bool:
        """Check if an import statement already exists in the content."""
        lines = content.split('\n')
        for line in lines:
            if line.strip() == import_statement.strip():
                return True
        return False
    
    def generate_handler_import(self, handler_name: str) -> Optional[str]:
        """Generate the appropriate import statement for a handler."""
        # Map handler names to their import paths
        handler_imports = {
            # API handlers
            "OpenAIResponsesHandler": "from bfcl_eval.model_handler.api_inference.openai_response import OpenAIResponsesHandler",
            "ClaudeHandler": "from bfcl_eval.model_handler.api_inference.claude import ClaudeHandler",
            "NovaHandler": "from bfcl_eval.model_handler.api_inference.nova import NovaHandler",
            "MistralHandler": "from bfcl_eval.model_handler.api_inference.mistral import MistralHandler",
            "GeminiHandler": "from bfcl_eval.model_handler.api_inference.gemini import GeminiHandler",
            "QwenAPIHandler": "from bfcl_eval.model_handler.api_inference.qwen import QwenAPIHandler",
            "DeepSeekAPIHandler": "from bfcl_eval.model_handler.api_inference.deepseek import DeepSeekAPIHandler",
            "CohereHandler": "from bfcl_eval.model_handler.api_inference.cohere import CohereHandler",
            "GrokHandler": "from bfcl_eval.model_handler.api_inference.grok import GrokHandler",
            
            # Local handlers
            "LlamaHandler": "from bfcl_eval.model_handler.local_inference.llama import LlamaHandler",
            "LlamaHandler_3_1": "from bfcl_eval.model_handler.local_inference.llama_3_1 import LlamaHandler_3_1",
            "QwenHandler": "from bfcl_eval.model_handler.local_inference.qwen import QwenHandler",
            "QwenFCHandler": "from bfcl_eval.model_handler.local_inference.qwen_fc import QwenFCHandler",
            "PhiHandler": "from bfcl_eval.model_handler.local_inference.phi import PhiHandler",
            "PhiFCHandler": "from bfcl_eval.model_handler.local_inference.phi_fc import PhiFCHandler",
            "GemmaHandler": "from bfcl_eval.model_handler.local_inference.gemma import GemmaHandler",
            
            # Third-party handlers
            "NovitaHandler": "from bfcl_eval.model_handler.api_inference.novita import NovitaHandler",
        }
        
        return handler_imports.get(handler_name)
    
    def add_import_if_needed(self, content: str, handler_name: str) -> str:
        """Add import statement for handler if it doesn't already exist."""
        import_statement = self.generate_handler_import(handler_name)
        if not import_statement:
            self.logger.warning(f"No import mapping found for handler: {handler_name}")
            return content
        
        if self.check_import_exists(content, import_statement):
            self.logger.debug(f"Import already exists: {handler_name}")
            return content
        
        # Add import in alphabetical order
        lines = content.split('\n')
        parser = FileParser(self.logger)
        import_end = parser.find_import_section_end(lines)
        
        # Find alphabetical insertion point within imports
        insertion_point = import_end
        for i in range(import_end):
            line = lines[i].strip()
            if line.startswith('from ') and line > import_statement:
                insertion_point = i
                break
        
        lines.insert(insertion_point, import_statement)
        self.logger.info(f"Added import: {import_statement}")
        return '\n'.join(lines)


class ModificationEngine:
    """Handles modification of Python source files for ModelConfig insertion."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.file_parser = FileParser(logger)
        self.insertion_finder = InsertionPointFinder(logger)
        self.import_manager = ImportManager(logger)
        self.syntax_validator = SyntaxValidator(logger)
    
    def ensure_base_model_parameter_exists(self, file_path: Path) -> Tuple[bool, str]:
        """Insert base_model parameter at line 112 of model_config.py."""
        content = self.file_parser.read_file_content(file_path)
        if not content:
            return False, "Failed to read file content"
        
        self.logger.info(f"Checking if base_model parameter exists in {file_path}")
        
        # Check if base_model parameter already exists
        if 'base_model: Optional[str]' in content:
            self.logger.info("base_model parameter already exists")
            return True, "base_model parameter already exists"
        
        lines = content.split('\n')
        
        # Insert at line 112 (index 111 since lines are 0-based)
        insert_line = 111
        
        if len(lines) < insert_line:
            return False, f"File has only {len(lines)} lines, cannot insert at line 112"
        
        # Insert the base_model parameter at line 112
        lines.insert(insert_line, "    # Base model for ARN-based deployments (e.g., \"nova-pro-v1.0\")")
        lines.insert(insert_line + 1, "    base_model: Optional[str] = None")
        
        modified_content = '\n'.join(lines)
        
        self.logger.info("Added base_model parameter at line 112 of ModelConfig class")
        
        # Validate syntax
        if not self.syntax_validator.validate_python_syntax(modified_content, file_path):
            return False, "Modified content has syntax errors"
        
        return True, modified_content
    
    def generate_model_config_entry(self, config: ModelConfig, handler_name: str, model_key: str) -> str:
        """Generate ModelConfig entry string for insertion into model_config.py."""
        # Convert handler string to actual handler class reference
        handler_class_name = handler_name
        
        # Check if this is an ARN (starts with "arn:")
        is_arn = config.model_name.startswith("arn:")
        
        lines = [
            f'    "{model_key}": ModelConfig(',
        ]
        
        # Add model_name with comment if it's an ARN
        if is_arn:
            lines.append(f'        model_name="{config.model_name}",  # {config.model_name}')
        else:
            lines.append(f'        model_name="{config.model_name}",')
        
        lines.extend([
            f'        display_name="{config.display_name}",',
            f'        url="{config.url}",',
            f'        org="{config.org}",',
            f'        license="{config.license}",',
            f'        model_handler={handler_class_name},',
        ])
        
        # Add optional pricing fields
        if config.input_price is not None:
            lines.append(f'        input_price={config.input_price},')
        else:
            lines.append('        input_price=None,')
            
        if config.output_price is not None:
            lines.append(f'        output_price={config.output_price},')
        else:
            lines.append('        output_price=None,')
        
        lines.extend([
            f'        is_fc_model={config.is_fc_model},',
            f'        underscore_to_dot={config.underscore_to_dot},',
        ])
        
        # Add base_model if present with comment
        if hasattr(config, 'base_model') and config.base_model:
            lines.append(f'        base_model="{config.base_model}",  # Specify the base model this custom model is derived from')
        
        lines.append('    ),')
        
        return '\n'.join(lines)
    
    def generate_supported_models_entry(self, model_key: str) -> str:
        """Generate entry for supported_models.py."""
        return f'    "{model_key}",'
    
    def modify_model_config_file(self, file_path: Path, config: ModelConfig,
                                handler_name: str, inference_map: str, model_key: str, dry_run: bool = False) -> Tuple[bool, str]:
        """Modify model_config.py to add new ModelConfig entry."""
        content = self.file_parser.read_file_content(file_path)
        if not content:
            return False, "Failed to read file content"
        
        # Add import if needed
        content = self.import_manager.add_import_if_needed(content, handler_name)
        
        # Generate the new entry
        new_entry = self.generate_model_config_entry(config, handler_name, model_key)
        
        # Find insertion point
        insertion_line = self.insertion_finder.find_model_config_insertion_point(
            content, inference_map, config.model_name
        )
        
        if insertion_line is None:
            return False, f"Could not find insertion point in {inference_map}"
        
        # Insert the new entry
        lines = content.split('\n')
        lines.insert(insertion_line, new_entry)
        modified_content = '\n'.join(lines)
        
        if dry_run:
            return True, f"Would insert ModelConfig at line {insertion_line + 1}"
        
        # Validate syntax
        if not self.syntax_validator.validate_python_syntax(modified_content, file_path):
            return False, "Modified content has syntax errors"
        
        return True, modified_content
    
    def modify_supported_models_file(self, file_path: Path, model_key: str, dry_run: bool = False) -> Tuple[bool, str]:
        """Modify supported_models.py to add new model key."""
        content = self.file_parser.read_file_content(file_path)
        if not content:
            return False, "Failed to read file content"
        
        # Generate the new entry
        new_entry = self.generate_supported_models_entry(model_key)
        
        # Find insertion point
        insertion_line = self.insertion_finder.find_supported_models_insertion_point(content, model_key)
        
        if insertion_line is None:
            return False, "Could not find insertion point in SUPPORTED_MODELS list"
        
        # Insert the new entry
        lines = content.split('\n')
        lines.insert(insertion_line, new_entry)
        modified_content = '\n'.join(lines)
        
        if dry_run:
            return True, f"Would insert model key at line {insertion_line + 1}"
        
        # Validate syntax
        if not self.syntax_validator.validate_python_syntax(modified_content, file_path):
            return False, "Modified content has syntax errors"
        
        return True, modified_content


class NovaFileManager:
    """Manages replacement of nova.py file contents."""
    
    def __init__(self, logger: logging.Logger, original_script_dir: Path = None):
        self.logger = logger
        self.backup_manager = BackupManager(logger)
        self.atomic_updater = AtomicFileUpdater(logger)
        # Store the original script directory to find the source nova.py file
        self.original_script_dir = original_script_dir or Path(__file__).parent
        
    def replace_nova_file_contents(self, nova_content_file: Path = None) -> bool:
        """Replace the contents of api_inference/nova.py with provided nova.py content."""
        try:
            # Determine the target nova.py file path (check both possible locations)
            target_nova_file = BFCL_EVAL_DIR / "model_handler" / "api_inference" / "nova.py"
            if not target_nova_file.exists():
                # Try the berkeley-function-call-leaderboard subdirectory
                target_nova_file = SCRIPT_DIR / "bfcl" / "berkeley-function-call-leaderboard" / "bfcl_eval" / "model_handler" / "api_inference" / "nova.py"
            
            # Determine the source nova.py file path - always look in the original script directory
            if nova_content_file is None:
                source_nova_file = self.original_script_dir / "nova.py"
            else:
                source_nova_file = nova_content_file
            
            # Check if source file exists
            if not source_nova_file.exists():
                self.logger.warning(f"Source nova.py file not found at {source_nova_file}")
                return False
            
            # Check if target file exists
            if not target_nova_file.exists():
                self.logger.error(f"Target nova.py file not found at {target_nova_file}")
                return False
            
            # Create backup of the target file
            self.logger.info(f"Creating backup of {target_nova_file}")
            backup_path = self.backup_manager.create_backup(target_nova_file)
            if not backup_path:
                self.logger.error("Failed to create backup of nova.py file")
                return False
            
            # Read content from source file
            try:
                with open(source_nova_file, 'r', encoding='utf-8') as f:
                    nova_content = f.read()
                self.logger.info(f"Read {len(nova_content)} characters from {source_nova_file}")
            except Exception as e:
                self.logger.error(f"Failed to read source nova.py file: {e}")
                return False
            
            # Write content to target file atomically
            self.logger.info(f"Replacing contents of {target_nova_file}")
            success = self.atomic_updater.write_atomically(target_nova_file, nova_content)
            
            if success:
                self.logger.info("Successfully replaced nova.py file contents")
                return True
            else:
                self.logger.error("Failed to write nova.py file atomically")
                # Try to restore from backup
                self.logger.info("Attempting to restore from backup")
                if not self.backup_manager.rollback_file(target_nova_file):
                    self.logger.error("Failed to restore nova.py from backup")
                return False
                
        except Exception as e:
            self.logger.error(f"Error replacing nova.py file contents: {e}")
            return False


class TransactionCoordinator:
    """Coordinates atomic transactions across multiple file updates."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.backup_manager = BackupManager(logger)
        self.atomic_updater = AtomicFileUpdater(logger)
        self.modification_engine = ModificationEngine(logger)
        self.syntax_validator = SyntaxValidator(logger)
    
    def execute_model_addition_transaction(self, config: ModelConfig, handler_name: str,
                                         inference_map: str, model_key: str, dry_run: bool = False) -> bool:
        """Execute the complete model addition transaction."""
        files_to_modify = [MODEL_CONFIG_FILE, SUPPORTED_MODELS_FILE]
        
        try:
            # Step 1: Create backups (unless in dry-run mode or --no-backup)
            if not dry_run:
                self.logger.info("Creating backups...")
                backup_paths = self.backup_manager.create_all_backups(files_to_modify)
                self.logger.info(f"Created {len(backup_paths)} backup files")
            
            # Step 2: Ensure ModelConfig class has base_model parameter
            self.logger.info("Ensuring ModelConfig class has base_model parameter...")
            success, result = self.modification_engine.ensure_base_model_parameter_exists(MODEL_CONFIG_FILE)
            
            if not success:
                self.logger.error(f"Failed to ensure base_model parameter: {result}")
                if not dry_run:
                    self.backup_manager.rollback_all()
                return False
            
            # If we have modified content, write it back to the file
            if result != "base_model parameter already exists" and not dry_run:
                if not self.atomic_updater.write_atomically(MODEL_CONFIG_FILE, result):
                    self.logger.error("Failed to write updated ModelConfig class")
                    self.backup_manager.rollback_all()
                    return False
                self.logger.info("Successfully updated ModelConfig class with base_model parameter")
                
                # CRITICAL: Reload the module to get the updated ModelConfig class
                import importlib
                import sys
                module_name = 'bfcl_eval.constants.model_config'
                if module_name in sys.modules:
                    self.logger.info("Reloading model_config module to get updated ModelConfig class")
                    importlib.reload(sys.modules[module_name])
                    
                    # Update the global ModelConfig reference
                    global ModelConfig
                    from bfcl_eval.constants.model_config import ModelConfig
                    self.logger.info("Successfully reloaded ModelConfig class")
                
            elif result == "base_model parameter already exists":
                self.logger.debug("ModelConfig class already has base_model parameter")
            
            # Step 3: Modify model_config.py (add new model entry)
            self.logger.info("Adding new model entry to model_config.py...")
            success, result = self.modification_engine.modify_model_config_file(
                MODEL_CONFIG_FILE, config, handler_name, inference_map, model_key, dry_run
            )
            
            if not success:
                self.logger.error(f"Failed to modify model_config.py: {result}")
                if not dry_run:
                    self.backup_manager.rollback_all()
                return False
            
            if dry_run:
                self.logger.info(f"model_config.py: {result}")
            else:
                model_config_content = result
            
            # Step 4: Modify supported_models.py
            self.logger.info("Modifying supported_models.py...")
            success, result = self.modification_engine.modify_supported_models_file(
                SUPPORTED_MODELS_FILE, model_key, dry_run
            )
            
            if not success:
                self.logger.error(f"Failed to modify supported_models.py: {result}")
                if not dry_run:
                    self.backup_manager.rollback_all()
                return False
            
            if dry_run:
                self.logger.info(f"supported_models.py: {result}")
                return True
            else:
                supported_models_content = result
            
            # Step 4: Write files atomically
            self.logger.info("Writing modified files...")
            
            # Write model_config.py
            if not self.atomic_updater.write_atomically(MODEL_CONFIG_FILE, model_config_content):
                self.logger.error("Failed to write model_config.py atomically")
                self.backup_manager.rollback_all()
                return False
            
            # Write supported_models.py
            if not self.atomic_updater.write_atomically(SUPPORTED_MODELS_FILE, supported_models_content):
                self.logger.error("Failed to write supported_models.py atomically")
                self.backup_manager.rollback_all()
                return False
            
            # Step 5: Verify files can be imported
            self.logger.info("Verifying modified files...")
            if not self._verify_modified_files():
                self.logger.error("Modified files failed verification")
                self.backup_manager.rollback_all()
                return False
            
            # Step 6: Success - cleanup backups
            self.logger.info("Transaction completed successfully")
            self.backup_manager.cleanup_backups()
            return True
            
        except Exception as e:
            self.logger.error(f"Transaction failed with exception: {e}")
            if not dry_run:
                self.backup_manager.rollback_all()
            return False
    
    def _verify_modified_files(self) -> bool:
        """Verify that modified files can be imported successfully."""
        try:
            # Test import model_config
            spec = importlib.util.spec_from_file_location("model_config", MODEL_CONFIG_FILE)
            model_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(model_config)
            
            # Test import supported_models
            spec = importlib.util.spec_from_file_location("supported_models", SUPPORTED_MODELS_FILE)
            supported_models = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(supported_models)
            
            self.logger.info("File verification passed")
            return True
            
        except Exception as e:
            self.logger.error(f"File verification failed: {e}")
            return False
    
    def preview_changes(self, config: ModelConfig, handler_name: str, inference_map: str, model_key: str) -> str:
        """Generate a preview of changes that would be made."""
        preview_lines = [
            "Dry Run Preview - Changes that would be made:",
            "=" * 50,
            "",
            f"Model Configuration:",
            f"  Model Key: {model_key}",
            f"  Model Name: {config.model_name}",
            f"  Display Name: {config.display_name}",
            f"  Handler: {handler_name}",
            f"  Inference Map: {inference_map}",
            f"  Organization: {config.org}",
            f"  License: {config.license}",
            f"  URL: {config.url}",
            f"  Input Price: {config.input_price}",
            f"  Output Price: {config.output_price}",
            f"  Is FC Model: {config.is_fc_model}",
            f"  Underscore to Dot: {config.underscore_to_dot}",
            f"  Base Model: {getattr(config, 'base_model', 'Not applicable')}",
            "",
            "Files to be modified:",
            f"  • {MODEL_CONFIG_FILE}",
            f"  • {SUPPORTED_MODELS_FILE}",
            "",
        ]
        
        # Run dry-run to get specific insertion information
        success = self.execute_model_addition_transaction(config, handler_name, inference_map, model_key, dry_run=True)
        
        if success:
            preview_lines.append("✓ All modifications validated successfully")
        else:
            preview_lines.append("✗ Validation failed - see error messages above")
        
        return "\n".join(preview_lines)


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.FileHandler('model_automation.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Automate adding model configurations to Berkeley Function Call Leaderboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available handlers
  %(prog)s --list-handlers
  
  # Regular model with handler
  %(prog)s gpt-4-turbo --handler OpenAIResponsesHandler --org OpenAI
  
  # Custom Nova model ARN (automatically uses NovaHandler)
  %(prog)s "arn:aws:bedrock:us-east-1:123456789012:custom-model-deployment/my-model" --base-model nova-pro-v1.0
  
  # Provisioned throughput ARN (automatically uses NovaHandler)
  %(prog)s "arn:aws:bedrock:us-east-1:123456789012:provisioned-model-throughput/my-endpoint" --base-model nova-lite-v1.0
  
  # Interactive mode
  %(prog)s --interactive
  
  # Batch processing from YAML configuration
  %(prog)s --config-file my_models.yaml
  
  # Dry run to preview changes
  %(prog)s mistral-large-2411 --handler MistralHandler --dry-run
  
  # Force addition without confirmation prompts
  %(prog)s claude-3-sonnet --handler ClaudeHandler --force
  
  # Use a custom working directory
  %(prog)s gpt-4 --handler OpenAIResponsesHandler --working-dir /path/to/bfcl

YAML Configuration Format:
  The script looks for 'bfcl_model_config.yaml' by default, or you can specify
  a custom file with --config-file. Example YAML structure:
  
  models:
    - model_id: "gpt-4-turbo"
      handler: "OpenAIResponsesHandler"
      display_name: "GPT-4 Turbo"
      org: "OpenAI"
      # ... other optional parameters
    - model_id: "arn:aws:bedrock:us-east-1:123:custom-model-deployment/my-model"
      base_model: "nova-pro-v1.0"
      display_name: "My Custom Nova Model"
      # ... other optional parameters

For ARN inputs, the script automatically:
  • Uses NovaHandler (no need to specify --handler)
  • Requires --base-model parameter
  • Validates ARN format and structure
        """
    )
    
    # Main argument (model ID or ARN)
    parser.add_argument(
        "model_id",
        nargs="?",
        help="Model identifier or ARN (required unless using --interactive, --list-handlers, or --config-file)"
    )
    
    # Information commands
    info_group = parser.add_argument_group("Information Commands")
    info_group.add_argument(
        "--list-handlers",
        action="store_true",
        help="List all available model handlers, categorized by type (API, Local, Third-party)"
    )
    info_group.add_argument(
        "--config-file",
        type=Path,
        help="Load model configurations from YAML file (default: bfcl_model_config.yaml if it exists)"
    )
    
    # Configuration arguments
    config_group = parser.add_argument_group("Model Configuration")
    config_group.add_argument(
        "--handler",
        help="Handler class name (required for non-ARN inputs)"
    )
    config_group.add_argument(
        "--display-name",
        help="Custom display name for the model"
    )
    config_group.add_argument(
        "--org",
        help="Organization name"
    )
    config_group.add_argument(
        "--url",
        help="Reference URL for the model"
    )
    config_group.add_argument(
        "--license",
        help="License type"
    )
    config_group.add_argument(
        "--input-price",
        type=float,
        help="Input price per million tokens"
    )
    config_group.add_argument(
        "--output-price",
        type=float,
        help="Output price per million tokens"
    )
    config_group.add_argument(
        "--inference-type",
        choices=["api", "local", "third-party"],
        help="Force specific inference map type"
    )
    config_group.add_argument(
        "--base-model",
        help="Base model for custom models (required for ARN inputs)"
    )
    config_group.add_argument(
        "--is-fc-model",
        type=bool,
        help="Whether this is a function-calling model (auto-detected from suffix if not specified)"
    )
    config_group.add_argument(
        "--underscore-to-dot",
        type=bool,
        help="Whether to replace dots with underscores in function names"
    )
    
    # Control options
    control_group = parser.add_argument_group("Control Options")
    control_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    control_group.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive configuration wizard"
    )
    control_group.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup creation (not recommended)"
    )
    control_group.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )
    control_group.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging"
    )
    control_group.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error output"
    )
    control_group.add_argument(
        "--working-dir",
        type=Path,
        help="Specify the working directory containing the bfcl_eval structure (default: script directory)"
    )
    
    return parser

class InputValidator:
    """Enhanced input validator using the new ValidationEngine."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.validation_engine = ValidationEngine(logger)
    
    def detect_input_type(self, model_id: str) -> str:
        """Detect the type of input: regular, custom_deployment, or provisioned_throughput."""
        if CUSTOM_DEPLOYMENT_ARN_PATTERN.match(model_id):
            return "custom_deployment"
        elif PROVISIONED_THROUGHPUT_ARN_PATTERN.match(model_id):
            return "provisioned_throughput"
        else:
            return "regular"
    
    def validate_arn_format(self, arn: str) -> bool:
        """Validate ARN format using enhanced validator."""
        is_valid, _, _ = self.validation_engine.arn_validator.validate_arn_format(arn)
        return is_valid
    
    def validate_model_id(self, model_id: str) -> bool:
        """Validate model ID format using enhanced security validator."""
        try:
            self.validation_engine.security_validator.sanitize_input(model_id, 'model_name')
            return True
        except ValidationError:
            return False
    
    def validate_handler_class(self, handler_name: str) -> bool:
        """Validate that the handler class exists using enhanced validator."""
        return self.validation_engine.handler_validator.validate_handler_exists(handler_name)
    
    def check_duplicate_model(self, model_key: str) -> bool:
        """Check if model key already exists in configuration."""
        try:
            # Import the model_config module
            spec = importlib.util.spec_from_file_location("model_config", MODEL_CONFIG_FILE)
            model_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(model_config)
            
            # Check if model key exists in any of the inference maps
            return model_key in model_config.MODEL_CONFIG_MAPPING
        except Exception as e:
            self.logger.error(f"Error checking for duplicate model: {e}")
            return False
    
    def validate_file_permissions(self) -> bool:
        """Validate that we have write permissions to the required files."""
        files_to_check = [MODEL_CONFIG_FILE, SUPPORTED_MODELS_FILE]
        
        for file_path in files_to_check:
            if not file_path.exists():
                self.logger.error(f"Required file does not exist: {file_path}")
                return False
            
            if not os.access(file_path, os.R_OK | os.W_OK):
                self.logger.error(f"No read/write permission for file: {file_path}")
                return False
        
        return True
    
    def validate_pricing_parameters(self, input_price: Optional[float], output_price: Optional[float]) -> Tuple[bool, str]:
        """Validate pricing parameters."""
        error_messages = []
        
        if input_price is not None:
            if input_price < 0:
                error_messages.append("Input price cannot be negative")
            if input_price > 1000:  # Reasonable upper bound
                error_messages.append("Input price seems unreasonably high (>$1000/M tokens)")
        
        if output_price is not None:
            if output_price < 0:
                error_messages.append("Output price cannot be negative")
            if output_price > 1000:  # Reasonable upper bound
                error_messages.append("Output price seems unreasonably high (>$1000/M tokens)")
        
        # If only one price is specified, warn the user
        if (input_price is None) != (output_price is None):
            error_messages.append("Both input_price and output_price should be specified together, or neither")
        
        return len(error_messages) == 0, "; ".join(error_messages)
    
    def validate_argument_interdependencies(self, args: argparse.Namespace) -> Tuple[bool, List[str]]:
        """Enhanced validation using ValidationEngine with fallback to legacy checks."""
        # Use the new enhanced validation system
        try:
            is_valid, detailed_results = self.validation_engine.validate_complete_input(args)
            
            if is_valid:
                return True, []
            else:
                # Collect all error messages from detailed results
                errors = []
                for layer_results in detailed_results.values():
                    for result in layer_results:
                        if not result.startswith('✓') and not result.startswith('⚠'):
                            errors.append(result)
                
                return False, errors if errors else ["Enhanced validation failed"]
                
        except Exception as e:
            self.logger.error(f"Enhanced validation failed, falling back to legacy validation: {e}")
            
            # Fallback to legacy validation
            errors = []
            
            # Check mutually exclusive options
            if getattr(args, 'quiet', False) and getattr(args, 'verbose', False):
                errors.append("--quiet and --verbose cannot be used together")
            
            # Validate model_id requirement
            if not any([
                getattr(args, 'model_id', None),
                getattr(args, 'interactive', False),
                getattr(args, 'list_handlers', False),
                getattr(args, 'config_file', None)
            ]):
                errors.append("model_id is required unless using --interactive, --list-handlers, or --config-file")
            
            # Only validate these if we have a model_id
            if getattr(args, 'model_id', None):
                input_type = self.detect_input_type(args.model_id)
                
                # Validate handler requirements for regular models
                if input_type == "regular":
                    if not getattr(args, 'handler', None):
                        errors.append("--handler is required for regular model IDs (non-ARN inputs)")
                    elif not self.validate_handler_class(args.handler):
                        errors.append(f"Handler class '{args.handler}' not found in codebase. Use --list-handlers to see available handlers")
                
                # Validate base-model requirements for ARN inputs
                elif input_type in ["custom_deployment", "provisioned_throughput"]:
                    if not getattr(args, 'base_model', None):
                        errors.append(f"--base-model is required for {input_type.replace('_', ' ')} ARNs")
                    
                    # Warn if handler is specified for ARN inputs (it will be ignored)
                    if getattr(args, 'handler', None):
                        self.logger.warning("--handler is ignored for ARN inputs; NovaHandler will be used automatically")
            
            # Validate pricing parameters
            input_price = getattr(args, 'input_price', None)
            output_price = getattr(args, 'output_price', None)
            if input_price is not None or output_price is not None:
                valid_pricing, pricing_error = self.validate_pricing_parameters(input_price, output_price)
                if not valid_pricing:
                    errors.append(f"Pricing validation failed: {pricing_error}")
            
            # Validate inference type
            inference_type = getattr(args, 'inference_type', None)
            if inference_type and inference_type not in ["api", "local", "third_party"]:
                errors.append("--inference-type must be one of: api, local, third_party")
            
            # Validate boolean parameters (Python argparse doesn't handle boolean well)
            for bool_param in ['is_fc_model', 'underscore_to_dot']:
                value = getattr(args, bool_param.replace('-', '_'), None)
                if value is not None and not isinstance(value, bool):
                    try:
                        # Try to interpret string values
                        if isinstance(value, str):
                            if value.lower() in ['true', '1', 'yes', 'on']:
                                setattr(args, bool_param.replace('-', '_'), True)
                            elif value.lower() in ['false', '0', 'no', 'off']:
                                setattr(args, bool_param.replace('-', '_'), False)
                            else:
                                errors.append(f"--{bool_param} must be a boolean value (true/false)")
                    except (ValueError, AttributeError):
                        errors.append(f"--{bool_param} must be a boolean value (true/false)")
            
            return len(errors) == 0, errors
    
    def validate_model_name_constraints(self, model_id: str) -> Tuple[bool, str]:
        """Validate model name against naming constraints using enhanced validation."""
        try:
            # Use enhanced validation
            sanitized = self.validation_engine.security_validator.sanitize_input(model_id, 'model_name')
            
            # Additional checks for regular models
            input_type = self.detect_input_type(model_id)
            if input_type == "regular":
                # Check for reasonable model naming patterns
                if model_id.startswith('-') or model_id.endswith('-'):
                    return False, "Model ID cannot start or end with hyphen"
                
                # Check for consecutive special characters
                if '--' in model_id or '__' in model_id:
                    return False, "Model ID cannot contain consecutive hyphens or underscores"
                
                # Warn about unusual patterns
                if model_id.count('/') > 1:
                    self.logger.warning("Model ID contains multiple forward slashes, which may cause issues")
            
            return True, ""
            
        except ValidationError as e:
            return False, str(e)
    
    def get_validation_suggestions(self, args: argparse.Namespace) -> List[str]:
        """Provide enhanced suggestions using ValidationEngine."""
        try:
            # Get suggestions from enhanced validator
            suggestions = self.validation_engine.get_validation_suggestions(args)
            
            # Add legacy suggestions as fallback
            legacy_suggestions = []
            
            # Suggest using --list-handlers if handler is missing
            if getattr(args, 'model_id', None) and not getattr(args, 'handler', None):
                input_type = self.detect_input_type(args.model_id)
                if input_type == "regular":
                    legacy_suggestions.append("Use --list-handlers to see all available model handlers")
            
            # Suggest pricing information for commercial models
            handler = getattr(args, 'handler', None)
            if handler and handler in ['OpenAIResponsesHandler', 'ClaudeHandler', 'NovaHandler']:
                if not getattr(args, 'input_price', None) and not getattr(args, 'output_price', None):
                    legacy_suggestions.append("Consider adding --input-price and --output-price for commercial models")
            
            # Suggest dry-run for first-time users
            if not getattr(args, 'dry_run', False) and not getattr(args, 'force', False):
                legacy_suggestions.append("Use --dry-run to preview changes before applying them")
            
            # Suggest YAML config for multiple models
            model_id = getattr(args, 'model_id', None)
            if model_id and not getattr(args, 'config_file', None):
                legacy_suggestions.append("For adding multiple models, consider using --config-file with a YAML configuration")
            
            # Combine suggestions, removing duplicates
            all_suggestions = suggestions + legacy_suggestions
            return list(dict.fromkeys(all_suggestions))  # Remove duplicates while preserving order
            
        except Exception as e:
            self.logger.error(f"Error getting enhanced validation suggestions: {e}")
            return ["Use --dry-run to preview changes before applying them"]
    
    def get_enhanced_validation_report(self, args: argparse.Namespace) -> str:
        """Get detailed validation report from ValidationEngine."""
        try:
            # Run validation to populate results
            self.validation_engine.validate_complete_input(args)
            return self.validation_engine.generate_validation_report()
        except Exception as e:
            return f"Enhanced validation report unavailable: {str(e)}"

def process_single_model(args: argparse.Namespace, logger: logging.Logger) -> bool:
    """Process a single model addition with enhanced validation. Returns True on success, False on failure."""
    try:
        # CRITICAL: Ensure ModelConfig class has base_model parameter BEFORE any processing
        logger.info("Ensuring ModelConfig class has required base_model parameter...")
        modification_engine = ModificationEngine(logger)
        success, result = modification_engine.ensure_base_model_parameter_exists(MODEL_CONFIG_FILE)
        
        if not success:
            logger.error(f"Failed to ensure base_model parameter: {result}")
            return False
        
        # If we modified the file, reload the module to get the updated class
        if result != "base_model parameter already exists":
            # Write the updated content
            atomic_updater = AtomicFileUpdater(logger)
            if not atomic_updater.write_atomically(MODEL_CONFIG_FILE, result):
                logger.error("Failed to write updated ModelConfig class")
                return False
            
            # Reload the module
            import importlib
            import sys
            module_name = 'bfcl_eval.constants.model_config'
            if module_name in sys.modules:
                logger.info("Reloading model_config module to get updated ModelConfig class")
                importlib.reload(sys.modules[module_name])
                
                # Update the global ModelConfig reference
                global ModelConfig
                from bfcl_eval.constants.model_config import ModelConfig
                logger.info("Successfully reloaded ModelConfig class with base_model parameter")
        
        # Initialize enhanced validator
        validator = InputValidator(logger)
        
        # Enhanced validation with detailed reporting
        logger.info("Running enhanced validation...")
        
        # File permission check (legacy for compatibility)
        if not validator.validate_file_permissions():
            logger.error("File permission validation failed")
            return False
        
        # Use enhanced validation system
        valid_args, validation_errors = validator.validate_argument_interdependencies(args)
        
        # Show detailed validation report in verbose mode
        if getattr(args, 'verbose', False):
            try:
                validation_report = validator.get_enhanced_validation_report(args)
                logger.info("Enhanced Validation Report:")
                for line in validation_report.split('\n'):
                    if line.strip():
                        logger.info(line)
            except Exception as e:
                logger.debug(f"Could not generate enhanced validation report: {e}")
        
        # Handle validation results
        if not valid_args:
            logger.error("Enhanced validation failed:")
            for error in validation_errors:
                logger.error(f"  • {error}")
            
            # Show helpful suggestions
            try:
                suggestions = validator.get_validation_suggestions(args)
                if suggestions:
                    logger.info("Suggestions:")
                    for suggestion in suggestions:
                        logger.info(f"  • {suggestion}")
            except Exception as e:
                logger.debug(f"Could not generate validation suggestions: {e}")
            
            return False
        
        logger.info("✓ Enhanced validation passed")
        
        # Validate model name constraints (additional legacy check)
        valid_name, name_error = validator.validate_model_name_constraints(args.model_id)
        if not valid_name:
            logger.error(f"Model name validation failed: {name_error}")
            return False
        
        # Detect input type
        input_type = validator.detect_input_type(args.model_id)
        logger.debug(f"Detected input type: {input_type}")
        
        # Enhanced format validation (using new validators)
        if input_type == "regular":
            if not validator.validate_model_id(args.model_id):
                logger.error("Invalid model ID format")
                return False
        else:  # ARN inputs
            if not validator.validate_arn_format(args.model_id):
                logger.error("Invalid ARN format")
                return False
        
        # Generate clean model key for dictionary entry
        config_manager = ConfigTemplateManager(logger)
        model_key = config_manager.generate_clean_model_key(args.model_id, getattr(args, 'base_model', None))
        logger.debug(f"Generated model key: '{model_key}' for model_id: '{args.model_id}'")
        
        # Check for duplicates
        if validator.check_duplicate_model(model_key):
            logger.error(f"Model '{model_key}' already exists in configuration")
            return False
        
        logger.debug(f"Validation passed for model: {args.model_id}")
        
        # Show validation suggestions if in verbose mode
        suggestions = validator.get_validation_suggestions(args)
        for suggestion in suggestions:
            logger.info(f"Suggestion: {suggestion}")
        
        # Initialize ConfigTemplateManager
        config_manager = ConfigTemplateManager(logger)
        
        # Prepare user arguments dictionary
        user_args = {
            "display_name": getattr(args, 'display_name', None),
            "org": getattr(args, 'org', None),
            "url": getattr(args, 'url', None),
            "license": getattr(args, 'license', None),
            "input_price": getattr(args, 'input_price', None),
            "output_price": getattr(args, 'output_price', None),
            "is_fc_model": getattr(args, 'is_fc_model', None),
            "underscore_to_dot": getattr(args, 'underscore_to_dot', None),
            "base_model": getattr(args, 'base_model', None)
        }
        
        # Generate ModelConfig based on input type
        if input_type == "regular":
            model_config = config_manager.generate_regular_model_template(
                args.model_id, args.handler, user_args
            )
        elif input_type == "custom_deployment":
            model_config = config_manager.generate_custom_deployment_template(
                args.model_id, args.base_model, user_args
            )
        elif input_type == "provisioned_throughput":
            model_config = config_manager.generate_provisioned_throughput_template(
                args.model_id, args.base_model, user_args
            )
        else:
            logger.error(f"Unknown input type: {input_type}")
            return False
        
        # Get inference map name for logging
        inference_map_name = config_manager.get_inference_map_name(
            args.handler if input_type == "regular" else "NovaHandler",
            getattr(args, 'inference_type', None)
        )
        
        logger.debug(f"Generated ModelConfig for {input_type} input")
        logger.debug(f"Target inference map: {inference_map_name}")
        
        # Initialize the transaction coordinator
        transaction_coordinator = TransactionCoordinator(logger)
        
        # Determine the handler name to use for the actual class reference
        handler_name = args.handler if input_type == "regular" else "NovaHandler"
        
        if getattr(args, 'dry_run', False):
            logger.info("Dry run mode - no changes will be made")
            print("\n" + config_manager.preview_config(model_config))
            print("\n" + transaction_coordinator.preview_changes(model_config, handler_name, inference_map_name, model_key))
            logger.info("Dry run completed successfully")
            return True
        else:
            logger.debug("Ready to proceed with model addition")
            
            # For batch processing, don't show preview or ask for confirmation
            # For single model processing, these will be handled in main()
            
            # Execute the atomic transaction
            logger.debug("Executing model addition transaction...")
            success = transaction_coordinator.execute_model_addition_transaction(
                model_config, handler_name, inference_map_name, model_key, dry_run=False
            )
            
            if success:
                logger.info(f"✓ Successfully added model '{args.model_id}' to the leaderboard configuration")
                return True
            else:
                logger.error(f"✗ Failed to add model '{args.model_id}'")
                return False
                
    except Exception as e:
        logger.error(f"Error processing model {getattr(args, 'model_id', 'Unknown')}: {e}")
        return False

def main():
    """Main entry point for the script."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Initialize paths based on working directory argument
    if hasattr(args, 'working_dir') and args.working_dir:
        if not args.working_dir.exists():
            print(f"Error: Working directory {args.working_dir} does not exist", file=sys.stderr)
            sys.exit(1)
        if not (args.working_dir / "bfcl_eval").exists():
            print(f"Error: Working directory {args.working_dir} does not contain bfcl_eval structure", file=sys.stderr)
            sys.exit(1)
        initialize_paths(args.working_dir)
    
    # Set up logging
    if args.quiet and args.verbose:
        parser.error("--quiet and --verbose cannot be used together")
    
    logger = setup_logging(args.verbose)
    
    # Log the working directory for debugging
    logger.debug(f"Using working directory: {SCRIPT_DIR}")
    logger.debug(f"BFCL_EVAL_DIR: {BFCL_EVAL_DIR}")
    
    # Replace nova.py file contents at the beginning
    logger.info("Replacing nova.py file contents...")
    original_script_dir = Path(__file__).parent  # Store the original script directory
    nova_manager = NovaFileManager(logger, original_script_dir)
    nova_replacement_success = nova_manager.replace_nova_file_contents()
    if nova_replacement_success:
        logger.info("✓ Successfully replaced nova.py file contents")
    else:
        logger.warning("⚠ Could not replace nova.py file contents (source file may be empty or missing)")
    
    # Handle --list-handlers command
    if args.list_handlers:
        handler_discovery = HandlerDiscovery(logger)
        print(handler_discovery.format_handlers_list())
        sys.exit(0)
    
    # Handle YAML configuration file
    yaml_config = None
    if args.config_file or (not args.model_id and not args.interactive):
        yaml_manager = YAMLConfigManager(logger)
        yaml_config = yaml_manager.load_config(args.config_file)
        
        if args.config_file and yaml_config is None:
            # Explicitly specified config file failed to load
            sys.exit(1)
        elif yaml_config is not None:
            # Successfully loaded config
            if not yaml_manager.validate_config(yaml_config):
                sys.exit(1)
            
            # Process models from YAML
            models = yaml_config.get("models", [])
            if not models:
                logger.error("No models found in configuration file")
                sys.exit(1)
            
            logger.info(f"Processing {len(models)} models from configuration file")
            
            # Process each model in the YAML
            success_count = 0
            for i, model_config in enumerate(models):
                logger.info(f"Processing model {i+1}/{len(models)}: {model_config.get('model_id', 'Unknown')}")
                
                try:
                    # Create a mock args object for this model
                    model_args = argparse.Namespace()
                    model_args.model_id = model_config.get("model_id")
                    model_args.handler = model_config.get("handler")
                    model_args.display_name = model_config.get("display_name")
                    model_args.org = model_config.get("org")
                    model_args.url = model_config.get("url")
                    model_args.license = model_config.get("license")
                    model_args.input_price = model_config.get("input_price")
                    model_args.output_price = model_config.get("output_price")
                    model_args.inference_type = model_config.get("inference_type")
                    model_args.base_model = model_config.get("base_model")
                    model_args.is_fc_model = model_config.get("is_fc_model")
                    model_args.underscore_to_dot = model_config.get("underscore_to_dot")
                    model_args.dry_run = args.dry_run  # Use global dry_run setting
                    model_args.force = args.force      # Use global force setting
                    model_args.no_backup = args.no_backup  # Use global backup setting
                    
                    # Process this single model
                    if process_single_model(model_args, logger):
                        success_count += 1
                    else:
                        logger.error(f"Failed to process model: {model_config.get('model_id', 'Unknown')}")
                        
                except Exception as e:
                    logger.error(f"Error processing model {model_config.get('model_id', 'Unknown')}: {e}")
            
            logger.info(f"Batch processing completed: {success_count}/{len(models)} models processed successfully")
            if success_count == len(models):
                print(f"\n✓ Successfully processed all {success_count} models from configuration file!")
            else:
                print(f"\n⚠ Processed {success_count}/{len(models)} models. Check logs for errors.")
                sys.exit(1)
            sys.exit(0)
    
    # Handle interactive mode
    if args.interactive:
        logger.info("Starting interactive configuration wizard...")
        try:
            wizard = InteractiveWizard(logger)
            wizard_args = wizard.run_wizard()
            
            if wizard_args is None:
                logger.info("Interactive wizard cancelled by user")
                sys.exit(0)
            
            # Process the configured model using the wizard results
            logger.info("Processing model configuration from wizard...")
            if process_single_model(wizard_args, logger):
                print(f"\n✅ Model '{wizard_args.model_id}' has been successfully added via interactive wizard!")
                print(f"  • Check the configuration files for the new entries")
                sys.exit(0)
            else:
                print(f"\n❌ Model addition failed. Check the log for details.")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Error in interactive wizard: {e}")
            print(f"\n❌ Interactive wizard failed: {e}")
            sys.exit(1)
    
    # Validate required arguments for non-interactive mode
    if not args.model_id:
        parser.error("model_id is required unless using --interactive, --list-handlers, or --config-file")
    
    # For single model processing, show preview and ask for confirmation
    # First, do a dry run to show what would happen
    args_copy = argparse.Namespace(**vars(args))
    args_copy.dry_run = True
    
    logger.info("Previewing changes...")
    if not process_single_model(args_copy, logger):
        sys.exit(1)
    
    # If not in dry run mode, ask for confirmation and proceed
    if not args.dry_run:
        # Confirm with user unless --force is used
        if not args.force:
            response = input("\nProceed with adding this model? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                logger.info("Model addition cancelled by user")
                sys.exit(0)
        
        # Now do the actual processing
        logger.info("Executing model addition...")
        if process_single_model(args, logger):
            print(f"\n✓ Model '{args.model_id}' has been successfully added!")
            print(f"  • Check the configuration files for the new entries")
        else:
            print(f"\n✗ Model addition failed. Check the log for details.")
            sys.exit(1)

if __name__ == "__main__":
    main()