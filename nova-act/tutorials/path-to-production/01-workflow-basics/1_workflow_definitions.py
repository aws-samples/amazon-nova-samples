#!/usr/bin/env python3
"""
Nova Act Workflow Definitions - Creating Workflow Definitions in AWS

This script creates a workflow definition in AWS using the Nova Act CLI.
The definition enables logging and tracking when running workflows with AWS authentication.

Prerequisites:
- AWS credentials configured with Nova Act permissions
- Nova Act CLI installed: pip install nova-act

What this does:
1. Creates workflow definition "getting-started-workflow" in AWS
2. Files 2 and 3 will reference this definition
3. Enables local execution with AWS logging and tracking

Important: AWS IAM authentication requires a workflow definition.
This file must be run before files 2-3.
"""

import boto3
import subprocess
import sys


def print_header(text):
    """Print formatted section header."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214m{text}\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")


def check_prerequisites():
    """Check prerequisites for creating workflow definition."""
    print_header("Prerequisites Check")
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"\n\033[93m[OK]\033[0m AWS credentials configured")
        print(f"  Account: {identity['Account']}")
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m AWS credentials not configured: {e}")
        return False
    
    # Check Nova Act CLI
    try:
        result = subprocess.run(['act', '--version'], capture_output=True, text=True)
        print(f"\n\033[93m[OK]\033[0m Nova Act CLI available")
        print(f"  {result.stdout.strip()}")
    except FileNotFoundError:
        print(f"\n\033[91m[ERROR]\033[0m Nova Act CLI not found")
        print("  Install with: pip install nova-act")
        return False
    
    return True


def explain_workflow_definitions():
    """Explain what workflow definitions are."""
    print_header("What are Workflow Definitions?")
    
    print(f"\n\033[38;5;214mWorkflow Definition:\033[0m")
    print("  • Created in AWS (not deployed code)")
    print("  • Stores configuration and logging settings")
    print("  • Enables tracking of workflow runs")
    print("  • Allows local execution with AWS logging")
    
    print(f"\n\033[38;5;214mKey Benefits:\033[0m")
    print("  • Run workflows locally, logs stored in AWS")
    print("  • Track execution history in Nova Act console")
    print("  • Centralized monitoring and observability")
    print("  • No code deployment required for local dev")


def create_workflow_definition():
    """Create workflow definition in AWS."""
    print_header("Creating Workflow Definition")
    
    workflow_name = "getting-started-workflow"
    
    print(f"\n\033[94mCreating: {workflow_name}\033[0m")
    print("  This creates the definition in AWS")
    print("  Examples 3 and 4 will reference this definition")
    
    try:
        result = subprocess.run(
            ['act', 'workflow', 'create', '--name', workflow_name],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"\n\033[92m✓ Workflow definition created!\033[0m")
        print(f"  {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr.lower():
            print(f"\n\033[93m[INFO]\033[0m Workflow definition already exists")
            return True
        print(f"\n\033[91m[ERROR]\033[0m Failed to create workflow definition:")
        print(f"  {e.stderr}")
        return False


def verify_workflow_definition():
    """Verify workflow definition exists using CLI."""
    import time
    
    print_header("Verifying Workflow Definition")
    
    try:
        # Use CLI to verify since it can see workflows
        result = subprocess.run(
            ['act', 'workflow', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if 'getting-started-workflow' in result.stdout:
            print(f"\n\033[92m✓ Workflow definition verified!\033[0m")
            print(f"  Name: getting-started-workflow")
            print(f"  Region: us-east-1")
            return True
        else:
            print(f"\n\033[91m[ERROR]\033[0m Workflow definition not found")
            return False
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Could not verify: {e}")
        return False


def main():
    """Main execution flow."""
    print_header("Nova Act Workflow Definitions")
    
    # Check prerequisites
    if not check_prerequisites():
        print(f"\n\033[91m[ERROR]\033[0m Prerequisites not met")
        sys.exit(1)
    
    # Explain workflow definitions
    explain_workflow_definitions()
    
    # Create workflow definition
    if not create_workflow_definition():
        print(f"\n\033[91m[ERROR]\033[0m Failed to create workflow definition")
        sys.exit(1)
    
    # Verify creation
    if not verify_workflow_definition():
        print(f"\n\033[93m[WARNING]\033[0m Could not verify workflow definition")
        print("  It may still exist - check Nova Act console")
    
    # Next steps
    print_header("Next Steps")
    print("\n\033[38;5;214mWorkflow definition created successfully!\033[0m")
    print("\nYou can now:")
    print("  1. Run 2_workflow_decorator.py to use Workflow context manager")
    print("  2. Run 3_workflow_context_manager.py for alternative pattern")
    print("  3. View workflow runs in Nova Act console")
    print("\nBoth examples will reference 'getting-started-workflow'")


if __name__ == "__main__":
    main()
