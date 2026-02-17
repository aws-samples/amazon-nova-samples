"""
Text Sanitization Utility

Comprehensive text sanitization for educational content with markdown removal,
special character handling, and PowerPoint compatibility.
"""

import re
import logging
from typing import Optional, List, Union

# Configure logging
logger = logging.getLogger(__name__)


class TextSanitizer:
    """
    Advanced text sanitization system for educational content processing.
    Handles markdown removal, special characters, and format compatibility.
    """
    
    def __init__(self):
        self.sanitization_stats = {
            'total_processed': 0,
            'markdown_removed': 0,
            'special_chars_cleaned': 0,
            'empty_inputs': 0
        }
    
    def sanitize(self, text: Union[str, None], mode: str = 'comprehensive') -> str:
        """
        Sanitize text content with various cleaning modes.
        
        Args:
            text: Text to sanitize
            mode: Sanitization mode ('basic', 'comprehensive', 'powerpoint')
            
        Returns:
            Sanitized text string
        """
        if not text or not isinstance(text, str):
            self.sanitization_stats['empty_inputs'] += 1
            return text if text is not None else ""
        
        self.sanitization_stats['total_processed'] += 1
        
        if mode == 'basic':
            return self._basic_sanitization(text)
        elif mode == 'comprehensive':
            return self._comprehensive_sanitization(text)
        elif mode == 'powerpoint':
            return self._powerpoint_sanitization(text)
        else:
            return self._comprehensive_sanitization(text)
    
    def _basic_sanitization(self, text: str) -> str:
        """Basic sanitization - removes common markdown and cleans spaces."""
        sanitized = text
        
        # Remove basic markdown formatting
        sanitized = re.sub(r'\*\*(.*?)\*\*', r'\1', sanitized)  # Bold
        sanitized = re.sub(r'\*(.*?)\*', r'\1', sanitized)      # Italic
        sanitized = re.sub(r'`([^`]+)`', r'\1', sanitized)      # Code
        
        # Clean up spaces
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    def _comprehensive_sanitization(self, text: str) -> str:
        """Comprehensive sanitization - removes all markdown and formatting."""
        sanitized = text
        has_markdown = False
        
        # Remove markdown headers (# ## ###)
        if re.search(r'^#+\s*', sanitized, flags=re.MULTILINE):
            sanitized = re.sub(r'^#+\s*', '', sanitized, flags=re.MULTILINE)
            has_markdown = True
        
        # Remove markdown bold (**text** or __text__)
        if re.search(r'\*\*(.*?)\*\*|__(.*?)__', sanitized):
            sanitized = re.sub(r'\*\*(.*?)\*\*', r'\1', sanitized)
            sanitized = re.sub(r'__(.*?)__', r'\1', sanitized)
            has_markdown = True
        
        # Remove markdown italic (*text* or _text_)
        if re.search(r'\*(.*?)\*|_(.*?)_', sanitized):
            sanitized = re.sub(r'\*(.*?)\*', r'\1', sanitized)
            sanitized = re.sub(r'_(.*?)_', r'\1', sanitized)
            has_markdown = True
        
        # Remove markdown links [text](url)
        if re.search(r'\[([^\]]+)\]\([^\)]+\)', sanitized):
            sanitized = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', sanitized)
            has_markdown = True
        
        # Remove markdown code blocks (```code```)
        if re.search(r'```.*?```', sanitized, flags=re.DOTALL):
            sanitized = re.sub(r'```.*?```', '', sanitized, flags=re.DOTALL)
            has_markdown = True
        
        # Remove inline code (`code`)
        if re.search(r'`([^`]+)`', sanitized):
            sanitized = re.sub(r'`([^`]+)`', r'\1', sanitized)
            has_markdown = True
        
        # Remove bullet points and list markers
        if re.search(r'^[\s]*[-*+•]\s*|^\s*\d+\.\s*', sanitized, flags=re.MULTILINE):
            sanitized = re.sub(r'^[\s]*[-*+•]\s*', '', sanitized, flags=re.MULTILINE)
            sanitized = re.sub(r'^\s*\d+\.\s*', '', sanitized, flags=re.MULTILINE)
            has_markdown = True
        
        # Clean up multiple spaces and newlines
        sanitized = re.sub(r'\s+', ' ', sanitized)
        sanitized = sanitized.strip()
        
        if has_markdown:
            self.sanitization_stats['markdown_removed'] += 1
        
        return sanitized
    
    def _powerpoint_sanitization(self, text: str) -> str:
        """PowerPoint-specific sanitization - ensures compatibility with PPT."""
        # Start with comprehensive sanitization
        sanitized = self._comprehensive_sanitization(text)
        
        # Remove special characters that cause issues in PowerPoint
        original_length = len(sanitized)
        sanitized = re.sub(r'[^\w\s.,!?;:()\-\'\\"&%$@#+=/\\\\]+', ' ', sanitized)
        
        if len(sanitized) != original_length:
            self.sanitization_stats['special_chars_cleaned'] += 1
        
        # Final cleanup
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    def sanitize_list(self, text_list: List[str], mode: str = 'comprehensive') -> List[str]:
        """
        Sanitize a list of text strings.
        
        Args:
            text_list: List of strings to sanitize
            mode: Sanitization mode
            
        Returns:
            List of sanitized strings
        """
        if not text_list:
            return []
        
        return [self.sanitize(text, mode) for text in text_list if text]
    
    def get_stats(self) -> dict:
        """Get sanitization statistics."""
        return self.sanitization_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset sanitization statistics."""
        self.sanitization_stats = {
            'total_processed': 0,
            'markdown_removed': 0,
            'special_chars_cleaned': 0,
            'empty_inputs': 0
        }


# Global sanitizer instance
_global_sanitizer: Optional[TextSanitizer] = None


def get_sanitizer() -> TextSanitizer:
    """Get the global text sanitizer instance."""
    global _global_sanitizer
    
    if _global_sanitizer is None:
        _global_sanitizer = TextSanitizer()
    
    return _global_sanitizer


def sanitize_text(text: Union[str, None], mode: str = 'comprehensive') -> str:
    """
    Quick function to sanitize text.
    
    Args:
        text: Text to sanitize
        mode: Sanitization mode ('basic', 'comprehensive', 'powerpoint')
        
    Returns:
        Sanitized text
    """
    sanitizer = get_sanitizer()
    return sanitizer.sanitize(text, mode)


def sanitize_for_powerpoint(text: Union[str, None]) -> str:
    """
    Sanitize text specifically for PowerPoint compatibility.
    
    Args:
        text: Text to sanitize
        
    Returns:
        PowerPoint-compatible sanitized text
    """
    return sanitize_text(text, mode='powerpoint')


def sanitize_for_topics(text: Union[str, None]) -> str:
    """
    Sanitize text for topic extraction (comprehensive mode).
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text suitable for topic extraction
    """
    return sanitize_text(text, mode='comprehensive')


def sanitize_list(text_list: List[str], mode: str = 'comprehensive') -> List[str]:
    """
    Sanitize a list of text strings.
    
    Args:
        text_list: List of strings to sanitize
        mode: Sanitization mode
        
    Returns:
        List of sanitized strings
    """
    sanitizer = get_sanitizer()
    return sanitizer.sanitize_list(text_list, mode)


def get_sanitization_stats() -> dict:
    """Get sanitization statistics."""
    sanitizer = get_sanitizer()
    return sanitizer.get_stats()


class SanitizerTracker:
    """
    Class-based interface for text sanitization (similar to other tracker patterns).
    """
    
    @classmethod
    def sanitize(cls, text: Union[str, None], mode: str = 'comprehensive') -> str:
        """Sanitize text."""
        return sanitize_text(text, mode)
    
    @classmethod
    def sanitize_list(cls, text_list: List[str], mode: str = 'comprehensive') -> List[str]:
        """Sanitize list of texts."""
        return sanitize_list(text_list, mode)
    
    @classmethod
    def for_powerpoint(cls, text: Union[str, None]) -> str:
        """Sanitize for PowerPoint."""
        return sanitize_for_powerpoint(text)
    
    @classmethod
    def for_topics(cls, text: Union[str, None]) -> str:
        """Sanitize for topic extraction."""
        return sanitize_for_topics(text)
    
    @classmethod
    def stats(cls) -> dict:
        """Get sanitization statistics."""
        return get_sanitization_stats()
    
    @classmethod
    def reset_stats(cls) -> None:
        """Reset statistics."""
        sanitizer = get_sanitizer()
        sanitizer.reset_stats()


# Backward compatibility functions (matching the original function names)
def safe_sanitize_text(text: Union[str, None]) -> str:
    """
    Backward compatibility function matching the original safe_sanitize_text.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text
    """
    return sanitize_text(text, mode='comprehensive')


# Quick setup function for notebook cells
def setup_text_sanitization():
    """
    Set up text sanitization utilities.
    
    Returns:
        tuple: (sanitize_function, sanitize_list_function, stats_function)
    """
    return sanitize_text, sanitize_list, get_sanitization_stats
