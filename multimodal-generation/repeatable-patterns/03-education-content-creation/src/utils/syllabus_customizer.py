"""
Syllabus Customization Utility

Provides interactive widgets and configuration management for syllabus generation
customization. This demonstrates Nova's versatility in generating different
types of educational content based on user preferences.
"""

import logging
from typing import Dict, Any, Optional, Tuple

# Handle optional dependencies gracefully
try:
    import ipywidgets as widgets
    from IPython.display import display
    WIDGETS_AVAILABLE = True
except ImportError:
    WIDGETS_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


class SyllabusCustomizer:
    """
    Interactive syllabus customization system with widgets and configuration management.
    Demonstrates Nova's ability to generate varied educational content.
    """
    
    def __init__(self):
        if not WIDGETS_AVAILABLE:
            raise ImportError("ipywidgets not available - install with: pip install ipywidgets")
        
        self.widgets = {}
        self.config_output = None
        self._create_widgets()
        self._setup_configuration_data()
    
    def _create_widgets(self):
        """Create all customization widgets."""
        # Topics count selector
        self.widgets['topics_count'] = widgets.IntSlider(
            value=5,
            min=3,
            max=15,
            step=1,
            description='Number of Topics:',
            style={'description_width': '120px'}
        )
        
        # Syllabus focus selector
        self.widgets['focus'] = widgets.Dropdown(
            options=[
                ('Main Topics Only', 'main_topics'),
                ('Detailed Chapters', 'detailed_chapters'),
                ('Learning Objectives', 'learning_objectives'),
                ('Comprehensive Overview', 'comprehensive')
            ],
            value='main_topics',
            description='Syllabus Focus:',
            style={'description_width': '120px'}
        )
        
        # Content depth selector
        self.widgets['depth'] = widgets.Dropdown(
            options=[
                ('Overview Level', 'overview'),
                ('Standard Depth', 'standard'),
                ('Detailed Analysis', 'detailed')
            ],
            value='standard',
            description='Content Depth:',
            style={'description_width': '120px'}
        )
        
        # Custom instructions
        self.widgets['custom_instructions'] = widgets.Textarea(
            value='',
            placeholder='Enter any specific instructions for syllabus creation (optional)...',
            description='Custom Instructions:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='500px', height='80px')
        )
        
        # Configuration button and output
        self.widgets['show_config_button'] = widgets.Button(
            description='Show Current Configuration',
            button_style='info',
            icon='eye'
        )
        
        self.config_output = widgets.Output()
        
        # Connect button to function
        self.widgets['show_config_button'].on_click(self._show_configuration)
    
    def _setup_configuration_data(self):
        """Set up configuration labels and multipliers."""
        self.focus_labels = {
            'main_topics': 'Main Topics Only',
            'detailed_chapters': 'Detailed Chapters',
            'learning_objectives': 'Learning Objectives',
            'comprehensive': 'Comprehensive Overview'
        }
        
        self.depth_labels = {
            'overview': 'Overview Level',
            'standard': 'Standard Depth',
            'detailed': 'Detailed Analysis'
        }
        
        # Time estimation multipliers
        self.time_multipliers = {
            'focus': {
                'main_topics': 1.0,
                'detailed_chapters': 1.2,
                'learning_objectives': 1.1,
                'comprehensive': 1.3
            },
            'depth': {
                'overview': 0.8,
                'standard': 1.0,
                'detailed': 1.2
            }
        }
    
    def display_widgets(self):
        """Display all customization widgets."""
        print("🎯 Syllabus Customization")
        
        # Display widgets in order
        display(self.widgets['topics_count'])
        display(self.widgets['focus'])
        display(self.widgets['depth'])
        display(self.widgets['custom_instructions'])
        display(self.widgets['show_config_button'])
        display(self.config_output)
        
        print("\n✅ Syllabus customization widgets ready!")
        print("   • Adjust settings above")
        print("   • Click 'Show Current Configuration' to see current settings")
        print("   • NO automatic updates = NO repeated output spam")
        
        # Show initial configuration
        self._show_initial_configuration()
    
    def _show_configuration(self, button=None):
        """Show current configuration when button is clicked."""
        with self.config_output:
            self.config_output.clear_output()
            
            config = self.get_configuration()
            
            print("📊 Current Configuration:")
            print(f"   Topics: {config['topics_count']}")
            print(f"   Focus: {config['focus_label']}")
            print(f"   Depth: {config['depth_label']}")
            if config['custom_instructions']:
                custom_preview = config['custom_instructions'][:50]
                if len(config['custom_instructions']) > 50:
                    custom_preview += "..."
                print(f"   Custom: {custom_preview}")
            print(f"   ⏱️ Estimated Time: ~{config['estimated_time']} seconds")
            print("✅ Ready for syllabus extraction")
    
    def _show_initial_configuration(self):
        """Show initial default configuration."""
        config = self.get_configuration()
        
        print(f"\n📊 Default Configuration:")
        print(f"   Topics: {config['topics_count']}")
        print(f"   Focus: {config['focus_label']}")
        print(f"   Depth: {config['depth_label']}")
        print(f"   Custom: None")
        print(f"   ⏱️ Estimated Time: ~{config['estimated_time']} seconds")
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get current configuration values.
        
        Returns:
            Dict with all current configuration values
        """
        topics_count = self.widgets['topics_count'].value
        focus = self.widgets['focus'].value
        depth = self.widgets['depth'].value
        custom = self.widgets['custom_instructions'].value.strip()
        
        # Calculate estimated time
        base_time = 30
        focus_multiplier = self.time_multipliers['focus'].get(focus, 1.0)
        depth_multiplier = self.time_multipliers['depth'].get(depth, 1.0)
        estimated_time = int(base_time * topics_count * focus_multiplier * depth_multiplier)
        
        return {
            'topics_count': topics_count,
            'focus': focus,
            'focus_label': self.focus_labels.get(focus, focus),
            'depth': depth,
            'depth_label': self.depth_labels.get(depth, depth),
            'custom_instructions': custom,
            'estimated_time': estimated_time,
            'configuration_summary': {
                'topics_count': topics_count,
                'syllabus_focus': focus,
                'content_depth': depth,
                'has_custom_instructions': bool(custom),
                'estimated_processing_time': estimated_time
            }
        }
    
    def get_prompt_parameters(self) -> Dict[str, Any]:
        """
        Get parameters formatted for Nova prompt generation.
        
        Returns:
            Dict with parameters ready for Nova prompts
        """
        config = self.get_configuration()
        
        return {
            'topic_count': config['topics_count'],
            'focus_type': config['focus'],
            'depth_level': config['depth'],
            'custom_instructions': config['custom_instructions'],
            'focus_description': config['focus_label'],
            'depth_description': config['depth_label']
        }
    
    def create_syllabus_prompt(self, base_content: str) -> str:
        """
        Create a customized syllabus extraction prompt based on current settings.
        
        Args:
            base_content: Base content to extract syllabus from
            
        Returns:
            Formatted prompt string for Nova
        """
        params = self.get_prompt_parameters()
        
        prompt = f"""Based on this document, identify exactly {params['topic_count']} main topics and list them separated by commas.

DOCUMENT CONTENT:
{base_content[:10000]}

INSTRUCTIONS:
- Identify exactly {params['topic_count']} main topics from this document
- Focus on: {params['focus_description']}
- Content depth: {params['depth_description']}
- Each topic should be 3-8 words maximum
- Separate each topic with a comma
- Do NOT use numbers, bullets, or dashes
- Just provide the comma-separated list"""

        if params['custom_instructions']:
            prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{params['custom_instructions']}"
        
        return prompt
    
    def get_api_data(self) -> Dict[str, Any]:
        """
        Get configuration data formatted for API/frontend use.
        
        Returns:
            Dict with API-friendly configuration data
        """
        config = self.get_configuration()
        
        return {
            'customization_active': True,
            'settings': config['configuration_summary'],
            'labels': {
                'focus': config['focus_label'],
                'depth': config['depth_label']
            },
            'estimated_time': config['estimated_time'],
            'widget_values': {
                'topics_count': config['topics_count'],
                'focus': config['focus'],
                'depth': config['depth'],
                'custom_instructions': config['custom_instructions']
            }
        }


# Global customizer instance
_global_customizer: Optional[SyllabusCustomizer] = None


def setup_syllabus_customization() -> SyllabusCustomizer:
    """
    Set up syllabus customization widgets.
    
    Returns:
        SyllabusCustomizer instance
    """
    global _global_customizer
    
    if _global_customizer is None:
        _global_customizer = SyllabusCustomizer()
    
    return _global_customizer


def get_customizer() -> SyllabusCustomizer:
    """Get the global syllabus customizer instance."""
    global _global_customizer
    
    if _global_customizer is None:
        return setup_syllabus_customization()
    
    return _global_customizer


def get_syllabus_configuration() -> Dict[str, Any]:
    """Get current syllabus configuration."""
    customizer = get_customizer()
    return customizer.get_configuration()


def get_prompt_parameters() -> Dict[str, Any]:
    """Get parameters for Nova prompt generation."""
    customizer = get_customizer()
    return customizer.get_prompt_parameters()


def create_custom_prompt(base_content: str) -> str:
    """Create customized syllabus prompt."""
    customizer = get_customizer()
    return customizer.create_syllabus_prompt(base_content)


class SyllabusTracker:
    """
    Class-based interface for syllabus customization (similar to other tracker patterns).
    """
    
    @classmethod
    def setup(cls) -> SyllabusCustomizer:
        """Set up syllabus customization."""
        return setup_syllabus_customization()
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get current configuration."""
        return get_syllabus_configuration()
    
    @classmethod
    def get_prompt_params(cls) -> Dict[str, Any]:
        """Get prompt parameters."""
        return get_prompt_parameters()
    
    @classmethod
    def create_prompt(cls, content: str) -> str:
        """Create customized prompt."""
        return create_custom_prompt(content)
    
    @classmethod
    def get_api_data(cls) -> Dict[str, Any]:
        """Get API-friendly data."""
        customizer = get_customizer()
        return customizer.get_api_data()


# Quick setup function for notebook cells
def quick_syllabus_setup():
    """
    Ultra-simple setup function for notebook cells.
    
    Returns:
        tuple: (customizer, config_function, prompt_function)
    """
    customizer = setup_syllabus_customization()
    return customizer, get_syllabus_configuration, create_custom_prompt
