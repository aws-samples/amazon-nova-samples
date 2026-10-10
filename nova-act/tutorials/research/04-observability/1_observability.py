#!/usr/bin/env python3
"""
Observability in Amazon Nova Act

This script demonstrates Nova Act's built-in logging, tracing, and session
recording capabilities for monitoring and debugging automation workflows.

Prerequisites:
- Complete the centralized setup first (see ../00-setup/README.md)
- Completion of previous tutorials

Setup:
1. Run the centralized setup (one-time):
   cd ../00-setup
   ./setup.sh

2. Activate the virtual environment:
   source ../00-setup/venv/bin/activate

3. Run this tutorial:
   python observability.py
"""

import os
import logging
from nova_act import NovaAct, BOOL_SCHEMA
from pydantic import BaseModel


def check_api_key():
    """Check if the API key is set."""
    api_key = os.getenv('NOVA_ACT_API_KEY')
    if not api_key:
        print("\033[91m[ERROR]\033[0m API key not found. Please set the NOVA_ACT_API_KEY environment variable.")
        return None
    print("\033[93m[OK]\033[0m API key found!")
    return api_key


def example_basic_logging(api_key: str):
    """
    Example 1: Basic logging with Nova Act
    
    Nova Act automatically logs all actions at INFO level or above.
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 1: Basic Logging\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Nova Act logging is automatic")
    print("  Default log level: INFO")
    print("  Logs include: actions, decisions, errors")
    print("  Nova Act automatically logs every action it takes, including what it sees and decides.")
    print("  You'll see detailed output showing the browser automation process in real-time.")
    print("\n\033[94m→ Next:\033[0m Performing a simple navigation task with automatic logging enabled")
    
    with NovaAct(starting_page="https://nova.amazon.com/act/gym/next-dot", nova_act_api_key=api_key) as nova:
        print("\n\033[93m[OK]\033[0m Performing actions (check console for logs)...")
        result = nova.act("Navigate to the main page and describe what you see")
        
        print("\n\033[93m[OK]\033[0m Action completed")
        print("  Check the console output above for detailed execution logs")
        
        print(f"\n\033[38;5;208m📁 NAVIGATE TO VIEW ACT RUN:\033[0m")
        print(f"\033[38;5;208m   Look for the orange-colored output above showing 'View your act run here: /path/to/file.html'\033[0m")
        print(f"\033[38;5;208m   Open that HTML file in your browser to see detailed trace information\033[0m")


def example_debug_logging(api_key: str):
    """
    Example 2: Debug-level logging
    
    Set NOVA_ACT_LOG_LEVEL environment variable for more detailed logs.
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 2: Debug-Level Logging\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    # Set log level to DEBUG for more detailed output
    os.environ['NOVA_ACT_LOG_LEVEL'] = str(logging.DEBUG)
    print("\n\033[93m[OK]\033[0m Log level set to DEBUG")
    print("  This provides maximum detail about Nova Act's operations")
    print("  DEBUG level shows internal reasoning, screenshot analysis, and decision trees.")
    print("  You'll see much more verbose output including Nova Act's thought process.")
    print("\n\033[94m→ Next:\033[0m Running an action with debug-level logging to see detailed internal operations")
    
    with NovaAct(starting_page="https://nova.amazon.com/act/gym/next-dot", nova_act_api_key=api_key) as nova:
        print("\n\033[93m[OK]\033[0m Performing action with debug logging...")
        result = nova.act("Click on the first link if available")
        
        print("\n\033[93m[OK]\033[0m Action completed with debug logging")
        print("  Notice the increased detail in console output")
        
        print(f"\n\033[38;5;208m📁 NAVIGATE TO VIEW ACT RUN:\033[0m")
        print(f"\033[38;5;208m   Look for the orange-colored output above showing 'View your act run here: /path/to/file.html'\033[0m")
        print(f"\033[38;5;208m   Open that HTML file in your browser to see detailed trace with debug information\033[0m")
    
    # Reset to INFO level
    os.environ['NOVA_ACT_LOG_LEVEL'] = str(logging.INFO)


def example_trace_files(api_key: str):
    """
    Example 3: HTML trace files
    
    Nova Act generates HTML trace files after each act() call.
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 3: HTML Trace Files\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    # Specify a custom logs directory
    logs_dir = "/tmp/nova-act-traces"
    os.makedirs(logs_dir, exist_ok=True)
    
    print(f"\n\033[93m[OK]\033[0m Logs directory: {logs_dir}")
    print("  Nova Act will save HTML trace files here")
    print("  HTML trace files contain screenshots, actions, and decision timelines.")
    print("  Each trace file is a complete visual record of what Nova Act saw and did.")
    print("\n\033[94m→ Next:\033[0m Running an action that generates an HTML trace file for detailed inspection")
    
    with NovaAct(
        starting_page="https://nova.amazon.com/act/gym/next-dot",
        nova_act_api_key=api_key,
        logs_directory=logs_dir
    ) as nova:
        print("\n\033[93m[OK]\033[0m Performing actions...")
        result = nova.act("Look for a 'Why Go' page on this website")
        
        print("\n\033[93m[OK]\033[0m Action completed")
        print(f"  Trace files saved to: {logs_dir}")
        print("  Open the HTML files in a browser to view detailed traces")
        print("  Traces include: screenshots, actions, decisions, timing")
        
        print(f"\n\033[38;5;208m📁 NAVIGATE TO VIEW ACT RUN:\033[0m")
        print(f"\033[38;5;208m   1. Look for the orange-colored output above: 'View your act run here: /path/to/file.html'\033[0m")
        print(f"\033[38;5;208m   2. Copy that file path and open it in your web browser\033[0m")
        print(f"\033[38;5;208m   3. Or navigate to {logs_dir} and open any .html file\033[0m")
        print(f"\033[38;5;208m   4. The trace shows screenshots, actions, and Nova Act's decision process\033[0m")


def example_session_recording(api_key: str):
    """
    Example 4: Session video recording
    
    Record the entire browser session as a video.
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 4: Session Video Recording\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    logs_dir = "/tmp/nova-act-videos"
    os.makedirs(logs_dir, exist_ok=True)
    
    print(f"\n\033[93m[OK]\033[0m Video directory: {logs_dir}")
    print("  Nova Act will record the browser session")
    print("  Session recording captures the entire browser window as a video file.")
    print("  This creates a movie of exactly what Nova Act did, perfect for debugging or demos.")
    print("\n\033[94m→ Next:\033[0m Running an action while recording the browser session to video")
    
    with NovaAct(
        starting_page="https://nova.amazon.com/act/gym/next-dot",
        nova_act_api_key=api_key,
        logs_directory=logs_dir,
        record_video=True  # Enable video recording
    ) as nova:
        print("\n\033[93m[OK]\033[0m Recording session...")
        nova.act("Scroll down the page")
        nova.act("Scroll back to the top")
        
        print("\n\033[93m[OK]\033[0m Session recorded")
        print(f"  Video saved to: {logs_dir}")
        print("  Look for .webm video files")


def example_error_debugging(api_key: str):
    """
    Example 5: Debugging failed automations
    
    Demonstrates how to use observability features to debug issues.
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 5: Error Debugging\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    logs_dir = "/tmp/nova-act-debug"
    os.makedirs(logs_dir, exist_ok=True)
    
    print(f"\n\033[93m[OK]\033[0m Debug logs directory: {logs_dir}")
    print("  Enabling debug logging and trace files")
    print("  Error debugging shows how Nova Act handles failures and provides diagnostic information.")
    print("  You'll see detailed error logs and trace files that help identify what went wrong.")
    print("\n\033[94m→ Next:\033[0m Attempting an impossible action to demonstrate error logging and recovery")
    
    # Enable debug logging
    os.environ['NOVA_ACT_LOG_LEVEL'] = str(logging.DEBUG)
    
    try:
        with NovaAct(
            starting_page="https://nova.amazon.com/act/gym/next-dot",
            nova_act_api_key=api_key,
            logs_directory=logs_dir
        ) as nova:
            print("\n\033[93m[OK]\033[0m Attempting action that might fail...")
            
            # Try an action that might not work
            result = nova.act("Click on the non-existent button labeled 'XYZ123'")
            
            print("\n\033[93m[OK]\033[0m Action completed (or failed gracefully)")
            
    except Exception as e:
        print(f"\n[WARNING] Action failed: {e}")
        print("\n\033[93m[OK]\033[0m Debugging information available:")
        print(f"  1. Console logs (above) show detailed error")
        print(f"  2. Trace files in {logs_dir} show what Nova Act saw")
        print(f"  3. Screenshots in trace files show page state")
        print("\n  Use these to understand why the action failed")
    
    # Reset log level
    os.environ['NOVA_ACT_LOG_LEVEL'] = str(logging.INFO)


def example_custom_logging(api_key: str):
    """
    Example 6: Custom logging in your automation
    
    Add your own logging alongside Nova Act's logs.
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 6: Custom Logging\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    # Set up custom logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Add console handler if not already present
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    print("\n\033[93m[OK]\033[0m Custom logger configured")
    print("  A custom logger lets you add your own timestamped messages alongside Nova Act's logs.")
    print("  This logger is configured to show INFO-level messages with timestamps and module names.")
    print("  You'll see both your custom messages and Nova Act's internal logging in the output.")
    print("\n\033[94m→ Next:\033[0m Running a multi-step workflow with custom logging at each stage")
    
    with NovaAct(starting_page="https://nova.amazon.com/act/gym/next-dot", nova_act_api_key=api_key) as nova:
        logger.info("Starting custom automation workflow")
        
        logger.info("Step 1: Navigating to page")
        result = nova.act("Go to the main content area", schema=BOOL_SCHEMA)
        
        logger.info(f"Step 1 completed: {result.response[:50] if result.response else 'No response'}...")
        
        logger.info("Step 2: Extracting information")
        
        class PageTitle(BaseModel):
            title: str
        
        result = nova.act("What is the page title?", schema=PageTitle.model_json_schema())
        
        logger.info(f"Step 2 completed: {result.response}")
        
        logger.info("Automation workflow completed successfully")
    
    print("\n\033[93m[OK]\033[0m Custom logging integrated with Nova Act logs")


def main():
    """Main function to demonstrate observability features."""
    print("="*60)
    print("Observability in Amazon Nova Act")
    print("="*60)
    
    # Check API key
    api_key = check_api_key()
    if not api_key:
        return
    
    print("\n[DATA] Observability Features:")
    print("  1. Automatic logging (INFO level by default)")
    print("  2. Debug logging (set NOVA_ACT_LOG_LEVEL)")
    print("  3. HTML trace files (generated after each act())")
    print("  4. Session video recording (record_video=True)")
    print("  5. Custom logs directory (logs_directory parameter)")
    
    print("\nThis tutorial includes 6 examples. Press Enter after each to continue...")
    
    try:
        # Example 1
        example_basic_logging(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Basic logging and console output")
        print(f"\033[94m→ Next:\033[0m Debug-level logging for detailed troubleshooting")
        input("\n>> Press Enter to continue to Example 2...")
        
        # Example 2
        example_debug_logging(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Debug logging with detailed information")
        print(f"\033[94m→ Next:\033[0m HTML trace file generation and analysis")
        input("\n>> Press Enter to continue to Example 3...")
        
        # Example 3
        example_trace_files(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m HTML trace file generation")
        print(f"\033[94m→ Next:\033[0m Session video recording for visual debugging")
        input("\n>> Press Enter to continue to Example 4...")
        
        # Example 4
        example_session_recording(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Session video recording")
        print(f"\033[94m→ Next:\033[0m Error debugging using observability tools")
        input("\n>> Press Enter to continue to Example 5...")
        
        # Example 5
        example_error_debugging(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Error debugging with trace analysis")
        print(f"\033[94m→ Next:\033[0m Custom logging integration patterns")
        input("\n>> Press Enter to continue to Example 6...")
        
        # Example 6
        example_custom_logging(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Custom logging integration with Nova Act")
        
        print("\n" + "="*60)
        print("\033[93m[OK]\033[0m All observability examples completed!")
        print("="*60)
        
        print("\nKey Takeaways:")
        print("- Nova Act automatically logs all actions")
        print("- Use NOVA_ACT_LOG_LEVEL for debug output")
        print("- HTML trace files provide visual debugging")
        print("- Video recording captures entire sessions")
        print("- Custom logging integrates with Nova Act logs")
        
        print("\nBest Practices:")
        print("- Always specify logs_directory in production")
        print("- Use debug logging when troubleshooting")
        print("- Review trace files when actions fail")
        print("- Record videos for complex workflows")
        print("- Add custom logging for business logic")
        
        print("\nNext Steps:")
        print("- Review the generated trace files and videos")
        print("- Practice debugging with intentional failures")
        print("- Integrate observability into your workflows")
        print("- Explore S3 integration for log storage (see README)")
        
    except KeyboardInterrupt:
        print("\n\n[WARNING] Tutorial interrupted by user")
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Error running examples: {e}")
        print("\nTroubleshooting:")
        print("- Check your API key is valid")
        print("- Ensure logs directories are writable")
        print("- Verify internet connection")


if __name__ == "__main__":
    main()
