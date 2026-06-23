"""
Enhanced Bedrock Client Manager with Modular Architecture
Provides comprehensive client initialization, validation, and testing.
"""

import importlib
import time
from typing import Any, Dict, Optional, Tuple

class ClientManager:
    """Manages Enhanced Bedrock Client initialization and validation."""
    
    def __init__(self):
        self.client = None
        self.region = None
        self.credentials = None
        self.last_validation_results = {}
        self.last_test_results = {}
        
        # Will be set by import methods
        self.EnhancedBedrockClient = None
        self.BedrockErrorHandler = None
        self.ContentAnalyzer = None
        self.StandardsDatabase = None
        self.GRADE_LEVEL_CONFIGS = None
        self.get_grade_level_category = None
    
    def setup_client(self, region: str, credentials: Dict[str, str], force_reload: bool = True) -> Any:
        """
        Set up Enhanced Bedrock Client with comprehensive validation.
        
        Args:
            region: AWS region
            credentials: AWS credentials dictionary
            force_reload: Whether to force reload the modular components
            
        Returns:
            Validated Enhanced Bedrock Client instance
        """
        print("🔄 Setting up Enhanced Bedrock Client...")
        
        self.region = region
        self.credentials = credentials
        
        try:
            # Step 1: Load/reload modular components
            if force_reload:
                self._reload_modular_components()
            else:
                self._import_modular_components()
            
            # Step 2: Initialize client
            client = self._initialize_client()
            
            # Step 3: Validate client methods
            validation_results = self._validate_client_methods(client)
            
            # Step 4: Test client functionality
            test_results = self._test_client_functionality(client)
            
            # Step 5: Store results
            self.client = client
            self.last_validation_results = {
                'timestamp': time.time(),
                'validation': validation_results,
                'tests': test_results
            }
            
            print("🔧 Client initialization complete!")
            return client
            
        except Exception as e:
            print(f"❌ Error during client initialization: {e}")
            print("⚠️ Will attempt to use existing client with fallback methods")
            raise
    
    def _reload_modular_components(self) -> None:
        """Reload the modular components to get latest changes."""
        try:
            import importlib
            from src.core import bedrock_client
            from src.utils import error_handler, config, standards
            from src.content import analyzer
            
            importlib.reload(bedrock_client)
            importlib.reload(error_handler)
            importlib.reload(config)
            importlib.reload(standards)
            importlib.reload(analyzer)
            
            # Import the classes after reload
            self._import_modular_components()
            
            print("✅ Modular components reloaded successfully")
            
        except Exception as e:
            print(f"❌ Error reloading modular components: {e}")
            print("⚠️ Please check that src/ modules are available")
            raise
    
    def _import_modular_components(self) -> None:
        """Import modular components without reloading."""
        try:
            from src.core.bedrock_client import EnhancedBedrockClient
            from src.utils.error_handler import BedrockErrorHandler
            from src.content.analyzer import ContentAnalyzer
            from src.utils.standards import StandardsDatabase
            from src.utils.config import GRADE_LEVEL_CONFIGS, get_grade_level_category
            
            # Store references for later use
            self.EnhancedBedrockClient = EnhancedBedrockClient
            self.BedrockErrorHandler = BedrockErrorHandler
            self.ContentAnalyzer = ContentAnalyzer
            self.StandardsDatabase = StandardsDatabase
            self.GRADE_LEVEL_CONFIGS = GRADE_LEVEL_CONFIGS
            self.get_grade_level_category = get_grade_level_category
            
            print("✅ Modular components imported successfully")
            
        except Exception as e:
            print(f"❌ Error importing modular components: {e}")
            raise
    
    def _initialize_client(self) -> Any:
        """Initialize the Enhanced Bedrock Client."""
        try:
            # Check if we have the stored reference, if not import directly
            if not hasattr(self, 'EnhancedBedrockClient') or self.EnhancedBedrockClient is None:
                from src.core.bedrock_client import EnhancedBedrockClient
                self.EnhancedBedrockClient = EnhancedBedrockClient
            
            # Use the stored reference from modular imports
            client = self.EnhancedBedrockClient(self.region, self.credentials)
            print("✅ Enhanced Bedrock client initialized")
            
            return client
            
        except Exception as e:
            print(f"❌ Error initializing client: {e}")
            raise
    
    def _validate_client_methods(self, client: Any) -> Dict[str, bool]:
        """Validate that all required methods are available on the client."""
        required_methods = [
            'sanitize_text_content',
            'sanitize_content_list', 
            'sanitize_image_prompt',
            'create_optimized_canvas_prompt',
            'generate_image_with_optimized_prompt',
            'generate_content',
            'generate_image'
        ]
        
        validation_results = {}
        print("\n📋 Method Availability Check:")
        
        for method_name in required_methods:
            has_method = hasattr(client, method_name) and callable(getattr(client, method_name))
            validation_results[method_name] = has_method
            status = "✅" if has_method else "❌"
            print(f"   {status} {method_name}")
        
        all_methods_available = all(validation_results.values())
        if all_methods_available:
            print("\n🎉 All enhanced methods are available!")
        else:
            print("\n⚠️ Some enhanced methods are missing!")
        
        return validation_results
    
    def _test_client_functionality(self, client: Any) -> Dict[str, Any]:
        """Test basic client functionality."""
        test_results = {}
        
        try:
            # Test text sanitization
            if hasattr(client, 'sanitize_text_content'):
                test_input = "**Bold text** with *italic* formatting and `code`"
                sanitized = client.sanitize_text_content(test_input)
                
                print(f"\n🧪 Sanitization Test:")
                print(f"   Input: '{test_input}'")
                print(f"   Output: '{sanitized}'")
                print("   ✅ Text sanitization working correctly")
                
                test_results['sanitization'] = {
                    'success': True,
                    'input': test_input,
                    'output': sanitized
                }
            
            print("\n✅ Enhanced Bedrock client is ready for optimized generation!")
            print("💡 You can now use all enhanced features including:")
            print("   - Text sanitization (removes markdown formatting)")
            print("   - Nova Pro → Nova Canvas optimization")
            print("   - Context-aware image generation")
            
        except Exception as e:
            print(f"⚠️ Some functionality tests failed: {e}")
            test_results['error'] = str(e)
        
        return test_results

# Global client manager instance
_global_client_manager: Optional[ClientManager] = None

def setup_bedrock_client(region: str, credentials: Dict[str, str], force_reload: bool = True) -> Any:
    """
    Set up Enhanced Bedrock Client with comprehensive validation.
    
    Args:
        region: AWS region
        credentials: AWS credentials dictionary
        force_reload: Whether to force reload modular components
        
    Returns:
        Validated Enhanced Bedrock Client instance
    """
    global _global_client_manager
    
    if _global_client_manager is None:
        _global_client_manager = ClientManager()
    
    return _global_client_manager.setup_client(region, credentials, force_reload)

def get_client_manager() -> Optional[ClientManager]:
    """Get the global client manager instance."""
    return _global_client_manager
