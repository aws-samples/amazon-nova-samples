#!/usr/bin/env python3
"""
Getting Started with Amazon Nova Act

This tutorial demonstrates the basics of using Amazon Nova Act to automate
web browser tasks.

Prerequisites:
- Complete the centralized setup first (see ../00-setup/README.md)
- Python 3.10 or higher
- Amazon Nova Act API key

Setup:
1. Run the centralized setup (one-time):
   cd ../00-setup
   ./setup.sh

2. Activate the virtual environment:
   source ../00-setup/venv/bin/activate  # On macOS/Linux
   # OR
   ..\00-setup\venv\Scripts\activate  # On Windows

3. Run this tutorial:
   python getting_started.py

Note: The setup script handles all dependencies and API key configuration.
"""

import os
from nova_act import NovaAct, BOOL_SCHEMA
from pydantic import BaseModel


def verify_installation():
    """Verify that Nova Act is installed correctly."""
    try:
        import nova_act
        print("\033[93m[OK]\033[0m Amazon Nova Act successfully imported!")
        print(f"  Version: {nova_act.__version__}")
        return True
    except ImportError:
        print("\033[91m[ERROR]\033[0m Failed to import Amazon Nova Act. Please check your installation.")
        return False


def check_api_key():
    """Check if the API key is set."""
    api_key = os.getenv('NOVA_ACT_API_KEY')
    if api_key:
        print("\033[93m[OK]\033[0m API key found!")
        return api_key
    else:
        print("\033[91m[ERROR]\033[0m API key not found. Please set the NOVA_ACT_API_KEY environment variable.")
        print("  Example: export NOVA_ACT_API_KEY='your_api_key_here'")
        return None


def example_basic_automation(api_key: str):
    """
    Example 1: Basic automation
    Navigate to a website and extract information.
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 1: Basic Automation\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Starting basic automation with natural language commands")
    print("  Nova Act can understand plain English instructions like 'click' and 'return information'.")
    print("  You'll see Nova Act navigate the page, click elements, and extract the requested data.")
    print("\n\033[94m→ Next:\033[0m Executing a multi-step task: clicking a button and extracting blog information")
    
    with NovaAct(starting_page="https://nova.amazon.com/act", nova_act_api_key=api_key) as nova:
        result = nova.act("Click learn more. Then, return the title and publication date of the blog.")
        print(f"\n\033[93mResult:\033[0m {result}")


def example_extract_structured_data(api_key: str):
    """
    Example 2: Extract structured data using Pydantic schemas
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 2: Extract Structured Data\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Using Pydantic schemas for structured data extraction")
    print("  Schemas ensure Nova Act returns data in exactly the format you specify.")
    print("  You'll see Nova Act extract specific fields and validate them against the schema.")
    print("\n\033[94m→ Next:\033[0m Defining a schema and extracting page title, search bar presence, and main heading")
    
    class PageInfo(BaseModel):
        title: str
        has_search_bar: bool
        main_heading: str
    
    with NovaAct(starting_page="https://nova.amazon.com/act", nova_act_api_key=api_key) as nova:
        result = nova.act(
            "Extract the page title, whether there's a search bar, and the main heading",
            schema=PageInfo.model_json_schema()
        )
        
        if result.matches_schema:
            page_info = PageInfo.model_validate(result.parsed_response)
            print(f"\n\033[93m[OK]\033[0m Successfully extracted structured data:")
            print(f"  Title: {page_info.title}")
            print(f"  Has search bar: {page_info.has_search_bar}")
            print(f"  Main heading: {page_info.main_heading}")
        else:
            print(f"\n\033[91m[ERROR]\033[0m Response did not match schema: {result}")


def example_boolean_response(api_key: str):
    """
    Example 3: Navigate and find specific page
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 3: Navigate and Find Page\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Using boolean responses for simple yes/no questions")
    print("  Boolean schemas are perfect for existence checks and simple decision-making.")
    print("  You'll see Nova Act search the website and return a true/false answer.")
    print("\n\033[94m→ Next:\033[0m Navigating to Amazon and searching for Black Friday Deals page")
    
    with NovaAct(starting_page="https://amazon.com", nova_act_api_key=api_key) as nova:
        result = nova.act("Look for a 'Black Friday Deals' page on this website", schema=BOOL_SCHEMA)
        
        if result.matches_schema:
            if result.parsed_response:
                print("\n\033[92m[OK]\033[0m Found a 'Black Friday Deals' page")
            else:
                print("\n\033[93m[OK]\033[0m No 'Black Friday Deals' page found")
        else:
            print(f"\n\033[91m[ERROR]\033[0m Invalid result: {result}")


def example_multi_step_workflow(api_key: str):
    """
    Example 4: Multi-step workflow
    Break down complex tasks into smaller, reliable steps.
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 4: Multi-Step Workflow\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Breaking complex tasks into smaller, reliable steps")
    print("  Multi-step workflows are more reliable than single complex commands.")
    print("  You'll see Nova Act execute each step sequentially with clear progress updates.")
    print("\n\033[94m→ Next:\033[0m Executing a two-step process: navigation followed by information extraction")
    
    with NovaAct(starting_page="https://nova.amazon.com/act", nova_act_api_key=api_key) as nova:
        # Step 1: Navigate to a section
        print("\nStep 1: Clicking 'Learn More'...")
        nova.act("Click the 'Learn More' button")
        
        # Step 2: Extract information
        print("Step 2: Extracting blog information...")
        result = nova.act("Return the title and publication date of the blog")
        print(f"\nBlog info: {result}")


def main():
    """Main function to run all examples."""
    print("="*60)
    print("Getting Started with Amazon Nova Act")
    print("="*60)
    
    # Step 1: Verify installation
    if not verify_installation():
        return
    
    # Step 2: Check API key
    api_key = check_api_key()
    if not api_key:
        return
    
    print("\nThis tutorial includes 4 examples. Press Enter after each to continue...")
    
    # Run examples
    try:
        # Example 1
        example_basic_automation(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Basic automation with natural language commands")
        print(f"\033[94m→ Next:\033[0m Learn to extract structured data using schemas")
        input("\n>> Press Enter to continue to Example 2...")
        
        # Example 2
        example_extract_structured_data(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Structured data extraction with Pydantic models")
        print(f"\033[94m→ Next:\033[0m Simple yes/no questions using boolean responses")
        input("\n>> Press Enter to continue to Example 3...")
        
        # Example 3
        example_boolean_response(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Navigation and page search functionality")
        print(f"\033[94m→ Next:\033[0m Breaking complex tasks into multiple steps")
        input("\n>> Press Enter to continue to Example 4...")
        
        # Example 4
        example_multi_step_workflow(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Multi-step workflow with sequential actions")
        
        print(f"\n\033[94m{'='*60}\033[0m")
        print(f"\033[94m[OK] All examples completed successfully!\033[0m")
        print(f"\033[94m{'='*60}\033[0m")
        print("\nNext Steps:")
        print("- Explore the other tutorials in this series")
        print("- Check out the samples in the Nova Act repository")
        print("- Read the full documentation at https://nova.amazon.com/act")
        
    except KeyboardInterrupt:
        print("\n\nTutorial interrupted by user")
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Error running examples: {e}")
        print("\nTroubleshooting:")
        print("- Make sure your API key is valid")
        print("- Check your internet connection")
        print("- Ensure Chrome/Chromium is installed")


if __name__ == "__main__":
    main()
