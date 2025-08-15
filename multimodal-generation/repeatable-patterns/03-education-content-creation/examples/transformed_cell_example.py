"""
TRANSFORMED NOTEBOOK CELL EXAMPLE

BEFORE: 150+ lines of token counter implementation
AFTER: Clean, simple cell with modular imports

This demonstrates how a complex cell becomes simple and maintainable.
"""

# =============================================================================
# BEFORE (Original Cell - 150+ lines):
# =============================================================================
"""
# TOKEN COUNTER IMPLEMENTATION
# Add comprehensive token tracking for all Nova models

import json
from datetime import datetime

class NovaTokenCounter:
    # ... 150+ lines of implementation ...
    
# Create global token counter
token_counter = NovaTokenCounter()
print("✅ Token Counter initialized")
# ... more complex initialization code ...
"""

# =============================================================================
# AFTER (Transformed Cell - 5 lines):
# =============================================================================

# Import the token counter module
from src.core.token_counter import create_token_counter

# Create and initialize token counter
token_counter = create_token_counter()
print("✅ Token Counter initialized with comprehensive tracking")
print("   • Tracks input/output tokens for all Nova models")
print("   • Provides detailed usage statistics")
print("   • Estimates costs and performance metrics")

# =============================================================================
# BENEFITS OF TRANSFORMATION:
# =============================================================================
"""
✅ CELL COMPLEXITY: 150+ lines → 5 lines (97% reduction)
✅ MAINTAINABILITY: Logic separated into dedicated module
✅ REUSABILITY: Token counter can be used in other projects
✅ TESTABILITY: Module can be unit tested independently
✅ READABILITY: Cell purpose is immediately clear
✅ DEBUGGING: Issues isolated to specific module
✅ COLLABORATION: Multiple developers can work on different modules
"""

# =============================================================================
# USAGE EXAMPLE:
# =============================================================================

def demonstrate_token_tracking():
    """Show how the modular token counter works."""
    
    # Log some sample token usage
    token_counter.log_token_usage('nova-premier', 150, 300, 'content_generation')
    token_counter.log_token_usage('nova-pro', 75, 25, 'image_optimization')
    token_counter.log_token_usage('nova-canvas', 50, 10, 'image_generation')
    
    # Get session summary
    summary = token_counter.get_session_summary()
    print(f"\n📊 Session Summary:")
    print(f"   Total Tokens: {summary['total_tokens']:,}")
    print(f"   Total Requests: {summary['total_requests']}")
    
    # Print detailed summary
    token_counter.print_summary()

if __name__ == "__main__":
    demonstrate_token_tracking()
