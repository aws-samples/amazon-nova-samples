"""
Error Handler Module

Enhanced error handling for Amazon Bedrock interactions with detailed
logging, content analysis, and recovery suggestions.
"""

import re
import logging
from datetime import datetime

# Handle optional dependencies gracefully
try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False

try:
    import nltk
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    from IPython.display import display, HTML
    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


class EnhancedBedrockError(Exception):
    """Custom exception for enhanced Bedrock errors with detailed context."""
    
    def __init__(self, error_details):
        self.error_details = error_details
        super().__init__(error_details.get("error_message", "Unknown Bedrock error"))


class BedrockErrorHandler:
    """Enhanced error handler for Amazon Bedrock interactions."""
    
    def __init__(self):
        self.error_log = []
        self.blocked_content_log = []
        self.response_analysis_log = []
    
    def handle_bedrock_error(self, error, prompt, model_id, additional_context=None):
        """Handle and log Bedrock errors with detailed information."""
        error_details = {
            "timestamp": datetime.now().isoformat(),
            "model_id": model_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "prompt_sent": prompt,
            "prompt_length": len(prompt),
            "prompt_word_count": len(prompt.split()),
            "additional_context": additional_context or {},
            "response_received": None
        }
        
        # Enhanced content filtering detection
        if any(keyword in str(error).lower() for keyword in 
               ["content filter", "content policy", "safety", "blocked", "inappropriate"]):
            self.log_blocked_content(prompt, error, additional_context)
            error_details["content_filtered"] = True
        else:
            error_details["content_filtered"] = False
        
        # Analyze prompt for potential issues
        error_details["prompt_analysis"] = self.analyze_prompt_for_issues(prompt)
        
        self.error_log.append(error_details)
        logger.error(f"Bedrock Error: {error_details}")
        
        return error_details
    
    def log_blocked_content(self, prompt, error, additional_context):
        """Log detailed information about blocked content."""
        blocked_details = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "reason": str(error),
            "content_analysis": self.analyze_blocked_content(prompt),
            "context": additional_context or {},
            "suggested_modifications": self.suggest_prompt_modifications(prompt)
        }
        self.blocked_content_log.append(blocked_details)
        
        # Display detailed error information
        self.display_blocked_content_details(blocked_details)
    
    def analyze_blocked_content(self, prompt):
        """Analyze why content might have been blocked."""
        analysis = {
            "prompt_length": len(prompt),
            "word_count": len(prompt.split()),
            "potential_triggers": [],
            "content_categories": []
        }
        
        # Check for potential trigger words or phrases
        trigger_patterns = [
            r'\b(violence|weapon|drug|alcohol)\b',
            r'\b(personal|private|confidential)\b',
            r'\b(generate|create|make).*\b(fake|false|misleading)\b'
        ]
        
        for pattern in trigger_patterns:
            matches = re.findall(pattern, prompt.lower())
            if matches:
                analysis["potential_triggers"].extend(matches)
        
        return analysis
    
    def analyze_prompt_for_issues(self, prompt):
        """Analyze prompt for potential issues that might cause errors."""
        try:
            if TEXTSTAT_AVAILABLE:
                readability_score = textstat.flesch_reading_ease(prompt) if prompt else 0
            else:
                readability_score = 0
                
            if NLTK_AVAILABLE:
                sentence_count = len(nltk.sent_tokenize(prompt)) if prompt else 0
            else:
                # Simple sentence count fallback
                sentence_count = prompt.count('.') + prompt.count('!') + prompt.count('?') if prompt else 0
        except:
            readability_score = 0
            sentence_count = 0
            
        return {
            "length": len(prompt),
            "word_count": len(prompt.split()),
            "has_special_chars": bool(re.search(r'[^\w\s.,!?;:()-]', prompt)),
            "readability_score": readability_score,
            "sentence_count": sentence_count
        }
    
    def suggest_prompt_modifications(self, prompt):
        """Suggest modifications to potentially blocked prompts."""
        suggestions = []
        
        if len(prompt) > 5000:
            suggestions.append(f"Consider shortening the prompt (current length: {len(prompt)} chars)")
        
        if any(word in prompt.lower() for word in ['create fake', 'generate false', 'make misleading']):
            suggestions.append("Remove requests for fake or misleading content")
        
        suggestions.append("Try rephrasing with more educational/academic language")
        suggestions.append("Add explicit educational context and learning objectives")
        
        return suggestions
    
    def display_blocked_content_details(self, blocked_details):
        """Display detailed information about blocked content."""
        html_content = f"""
        <div style="border: 2px solid #ff6b6b; padding: 15px; margin: 10px 0; border-radius: 5px; background-color: #ffe0e0;">
            <h3 style="color: #d63031; margin-top: 0;">🚫 Content Blocked by Bedrock</h3>
            <p><strong>Timestamp:</strong> {blocked_details['timestamp']}</p>
            <p><strong>Reason:</strong> {blocked_details['reason']}</p>
            <details>
                <summary><strong>Prompt Sent to Model (Click to expand)</strong></summary>
                <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto;">{blocked_details['prompt']}</pre>
            </details>
            <details>
                <summary><strong>Content Analysis</strong></summary>
                <ul>
                    <li>Prompt Length: {blocked_details['content_analysis']['prompt_length']} characters</li>
                    <li>Word Count: {blocked_details['content_analysis']['word_count']} words</li>
                    <li>Potential Triggers: {', '.join(blocked_details['content_analysis']['potential_triggers']) or 'None detected'}</li>
                </ul>
            </details>
            <details>
                <summary><strong>Suggested Modifications</strong></summary>
                <ul>
                    {''.join(f'<li>{suggestion}</li>' for suggestion in blocked_details['suggested_modifications'])}
                </ul>
            </details>
        </div>
        """
        
        if IPYTHON_AVAILABLE:
            display(HTML(html_content))
        else:
            # Fallback to plain text display
            print("🚫 Content Blocked by Bedrock")
            print(f"Timestamp: {blocked_details['timestamp']}")
            print(f"Reason: {blocked_details['reason']}")
            print(f"Prompt Length: {blocked_details['content_analysis']['prompt_length']} characters")
            print(f"Potential Triggers: {', '.join(blocked_details['content_analysis']['potential_triggers']) or 'None detected'}")
            print("Suggested Modifications:")
            for suggestion in blocked_details['suggested_modifications']:
                print(f"  - {suggestion}")
    
    def get_error_summary(self):
        """Get a summary of all errors encountered."""
        return {
            "total_errors": len(self.error_log),
            "blocked_content_count": len(self.blocked_content_log),
            "error_types": [error["error_type"] for error in self.error_log],
            "models_with_errors": list(set(error["model_id"] for error in self.error_log))
        }
