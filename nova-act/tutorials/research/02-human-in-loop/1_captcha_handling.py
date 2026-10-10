#!/usr/bin/env python3
"""
CAPTCHA Handling with Amazon Nova Act

This script demonstrates how to detect and handle CAPTCHAs in Nova Act workflows.
CAPTCHAs are security measures designed to distinguish humans from bots, and Nova Act
cannot solve them automatically - it requires human intervention.

Prerequisites:
- Complete the centralized setup first (see ../00-setup/README.md)
- Completion of the Getting Started tutorial

Setup:
1. Run the centralized setup (one-time):
   cd ../00-setup
   ./setup.sh

2. Activate the virtual environment:
   source ../00-setup/venv/bin/activate

3. Run this tutorial:
   python captcha_handling.py
"""

import os
from nova_act import NovaAct, BOOL_SCHEMA


def check_api_key():
    """Check if the API key is set."""
    api_key = os.getenv('NOVA_ACT_API_KEY')
    if not api_key:
        print("\033[91m[ERROR]\033[0m API key not found. Please set the NOVA_ACT_API_KEY environment variable.")
        print("  Example: export NOVA_ACT_API_KEY='your_api_key_here'")
        return None
    print("\033[93m[OK]\033[0m API key found!")
    return api_key


def example_detect_captcha(api_key: str):
    """
    Example 1: Detecting a CAPTCHA on a webpage
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 1: Detecting CAPTCHAs\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Learning to detect CAPTCHAs on webpages")
    print("  CAPTCHA detection helps identify when human intervention is needed.")
    print("  You'll see Nova Act analyze a page and determine if a CAPTCHA is present.")
    print("\n\033[94m→ Next:\033[0m Navigating to a CAPTCHA demo page and testing detection capabilities")
    
    # Using nopecha.com for CAPTCHA handling demonstration
    with NovaAct(starting_page="https://nopecha.com/captcha/hcaptcha", nova_act_api_key=api_key) as nova:
        try:
            # Check if a CAPTCHA is present
            result = nova.act("Is there a captcha on the screen?", schema=BOOL_SCHEMA)
            
            if result.matches_schema and result.parsed_response:
                print("\033[93m[OK]\033[0m CAPTCHA detected!")
            else:
                print("\033[93m[OK]\033[0m No CAPTCHA found")
            
            print(f"  Raw response: {result.response}")
            
        except Exception as e:
            if "HumanValidationError" in str(e):
                print("\033[93m[OK]\033[0m CAPTCHA detected! (Nova Act correctly refused to solve it)")
                print("  This is expected behavior - Nova Act will not solve CAPTCHAs")
            else:
                print(f"\033[91m[ERROR]\033[0m Unexpected error: {e}")


def example_pause_for_captcha(api_key: str):
    """
    Example 2: Pausing automation for CAPTCHA solving
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 2: Pausing for Human Input\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Implementing human-in-the-loop workflow for CAPTCHA handling")
    print("  When CAPTCHAs are detected, automation should pause and wait for human intervention.")
    print("  You'll see Nova Act detect a CAPTCHA and demonstrate proper handling procedures.")
    print("\n\033[94m→ Next:\033[0m Checking for CAPTCHAs and implementing pause-and-wait logic")
    
    with NovaAct(starting_page="https://nopecha.com/captcha/hcaptcha", nova_act_api_key=api_key) as nova:
        # Simulate filling out a form
        print("Checking for CAPTCHA before form submission...")
        
        try:
            # Check for CAPTCHA before submitting
            result = nova.act("Is there a captcha on the screen?", schema=BOOL_SCHEMA)
            
            if result.matches_schema and result.parsed_response:
                print("\n\033[93m[WARNING]\033[0m CAPTCHA detected. Please solve it manually.")
                input("Press Enter after you have solved the CAPTCHA...")
                print("\033[93m[OK]\033[0m Continuing with automation...")
            else:
                print("\033[93m[OK]\033[0m No CAPTCHA detected, proceeding automatically")
                
        except Exception as e:
            if "HumanValidationError" in str(e):
                print("\n\033[93m[WARNING]\033[0m CAPTCHA detected! Nova Act correctly refused to interact with it.")
                print("In a real scenario, you would pause here for human intervention.")
                input("Press Enter to continue (simulating CAPTCHA solved)...")
                print("\033[93m[OK]\033[0m Continuing with automation...")
            else:
                raise e
        
        print("\033[93m[OK]\033[0m Form submission flow completed")


def example_advanced_captcha_detection(api_key: str):
    """
    Example 3: Advanced CAPTCHA detection with specific types
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 3: Advanced CAPTCHA Detection\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Advanced CAPTCHA detection with detailed analysis")
    print("  Advanced detection identifies specific CAPTCHA types and security challenges.")
    print("  You'll see Nova Act provide detailed descriptions of security elements on the page.")
    print("\n\033[94m→ Next:\033[0m Analyzing page security challenges and identifying CAPTCHA variations")
    
    with NovaAct(starting_page="https://nopecha.com/captcha/hcaptcha", nova_act_api_key=api_key) as nova:
        try:
            # Get detailed analysis of security challenges
            captcha_check = nova.act(
                "Describe any security challenges on this page (CAPTCHA, reCAPTCHA, image verification, etc.)"
            )
            
            print(f"\n\033[93mResult:\033[0m Security challenge analysis:")
            print(f"  {captcha_check.response}")
            
            # Check for specific CAPTCHA types
            print("\nChecking for specific CAPTCHA types...")
            
            recaptcha_present = nova.act("Is there a reCAPTCHA checkbox on the screen?", schema=BOOL_SCHEMA)
            if recaptcha_present.matches_schema and recaptcha_present.parsed_response:
                print("\033[93m[WARNING]\033[0m reCAPTCHA detected")
            else:
                print("\033[93m[OK]\033[0m No reCAPTCHA found")
                
        except Exception as e:
            if "HumanValidationError" in str(e):
                print("\n\033[93m[OK]\033[0m Advanced CAPTCHA detection triggered security measures")
                print("This demonstrates Nova Act's built-in CAPTCHA protection")
            else:
                print(f"\033[91m[ERROR]\033[0m Unexpected error: {e}")
        
        print("\n\033[93m[OK]\033[0m Advanced CAPTCHA detection completed")


def main():
    """Main function to run all CAPTCHA handling examples."""
    print("="*60)
    print("CAPTCHA Handling with Amazon Nova Act")
    print("="*60)
    
    # Check API key
    api_key = check_api_key()
    if not api_key:
        return
    
    print("\n\033[93m[WARNING]\033[0m Important Notes:")
    print("- Nova Act will NOT solve CAPTCHAs automatically")
    print("- Human intervention is always required for CAPTCHAs")
    print("- CAPTCHAs are security measures - respect their purpose")
    
    print("\nThis tutorial includes 3 examples. Press Enter after each to continue...")
    
    try:
        # Example 1
        example_detect_captcha(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m CAPTCHA detection using boolean schemas")
        print(f"\033[94m→ Next:\033[0m Pausing automation for human CAPTCHA solving")
        input("\n>> Press Enter to continue to Example 2...")
        
        # Example 2
        example_pause_for_captcha(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Human intervention workflow for CAPTCHA handling")
        print(f"\033[94m→ Next:\033[0m Advanced CAPTCHA type detection and analysis")
        input("\n>> Press Enter to continue to Example 3...")
        
        # Example 3
        example_advanced_captcha_detection(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Advanced CAPTCHA detection for multiple types")
        
        print("\n" + "="*60)
        print("\033[93m[OK]\033[0m All CAPTCHA handling examples completed!")
        print("="*60)
        print("\nKey Takeaways:")
        print("- Always check for CAPTCHAs before critical actions")
        print("- Use BOOL_SCHEMA for yes/no CAPTCHA detection")
        print("- Provide clear instructions to users")
        print("- Validate that CAPTCHAs were actually solved")
        
        print("\nNext Steps:")
        print("- Move on to Tool Use tutorial (03-tool-use)")
        print("- Explore the Observability tutorial (04-observability)")
        print("- Practice CAPTCHA handling with real websites")
        
    except KeyboardInterrupt:
        print("\n\n[WARNING] Tutorial interrupted by user")
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Error running examples: {e}")
        print("\nTroubleshooting:")
        print("- Ensure your API key is valid")
        print("- Check your internet connection")
        print("- Try with different websites that have CAPTCHAs")


if __name__ == "__main__":
    main()
