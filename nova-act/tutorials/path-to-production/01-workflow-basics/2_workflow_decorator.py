#!/usr/bin/env python3
"""
Workflow Context Manager Pattern for Production Deployment

This script demonstrates using the Workflow context manager to reference
workflow definitions created in AWS.

Prerequisites:
- Completed 1_workflow_definitions.py
- Workflow "getting-started-workflow" created in AWS
- AWS credentials configured with Nova Act permissions

Setup:
1. Ensure AWS authentication is working
2. Run this script to see Workflow context manager usage
3. Workflow runs locally but logs stored in AWS

Note: Workflow context manager references existing workflow definitions.
"""

from nova_act import NovaAct, workflow
import os


def demonstrate_workflow_decorator():
    """Show how @workflow decorator works."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mWorkflow Decorator Pattern\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m The @workflow decorator enables production deployment")
    print("  Automatically references workflow definition in AWS")
    print("  Enables deployment to AWS infrastructure")
    print("  Provides AWS logging for local execution")
    print("\n\033[38;5;214m→ Next:\033[0m Defining a workflow function with @workflow decorator")


@workflow(workflow_definition_name="getting-started-workflow", model_id="nova-act-latest")
def search_documentation_workflow():
    """
    References the workflow definition from 1_workflow_definitions.py.
    
    This workflow demonstrates:
    - @workflow decorator usage
    - Referencing workflow definitions
    - Local execution with AWS logging
    """
    print(f"\n\033[93m[OK]\033[0m Executing workflow: getting-started-workflow")
    print("  Model: nova-act-latest")
    print("  Execution: Local with AWS logging")
    
    with NovaAct(starting_page="https://nova.amazon.com/act/gym/next-dot/") as nova:
        # Execute simple navigation task
        print(f"\nExecuting workflow with AWS logging...")
        result = nova.act("Return the main heading on this page")
        
        print(f"\n\033[93mWorkflow Result:\033[0m {result}")
        return result


def explain_decorator_parameters():
    """Explain @workflow decorator parameters."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mDecorator Parameters Explained\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214m@workflow Parameters:\033[0m")
    print("  • workflow_definition_name: References the AWS workflow definition")
    print("  • model_id: Specifies the Nova Act model version")
    
    print(f"\n\033[38;5;214mWorkflow Definition:\033[0m")
    print("  • References the definition created in file 1")
    print("  • Enables AWS logging for local execution")
    print("  • Provides deployment readiness")


def demonstrate_main_function():
    """Show the required main function pattern."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMain Function Pattern\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Production workflows require a main() function")
    print("  • main() must accept a payload parameter")
    print("  • Enables parameterized workflow execution")
    print("  • Required for AWS deployment compatibility")
    print("  Required for AWS deployment compatibility")
    print("\n\033[38;5;214m→ Next:\033[0m Executing workflow through main() function")


def main(payload):
    """
    Main function required for production workflow deployment.
    
    Args:
        payload: Input parameters for workflow execution
    """
    print("="*60)
    print("Workflow Decorator Pattern for Production Deployment")
    print("="*60)
    
    # Explain workflow decorator
    demonstrate_workflow_decorator()
    
    # Execute the workflow
    try:
        result = search_documentation_workflow()
        print(f"\n\033[92m✓ Completed:\033[0m Workflow executed successfully")
        print(f"\n\033[38;5;214mExecution Details:\033[0m")
        print("  • Workflow ran locally on your machine")
        print("  • Logs automatically stored in AWS S3")
        print("  • Execution tracked in Nova Act console")
        
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Workflow execution failed: {e}")
        return
    
    # Show where to find logs
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mView Your Workflow Logs\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[93m[INFO]\033[0m Your workflow execution has been logged to AWS")
    print("\n\033[38;5;214mTo view logs and execution details:\033[0m")
    print("  1. Open Nova Act Console:")
    print("     https://us-east-1.console.aws.amazon.com/nova-act/home")
    print("  2. Click on 'getting-started-workflow'")
    print("  3. View the latest workflow run")
    print("  4. Explore execution traces, logs, and artifacts")
    
    print(f"\n\033[38;5;214mWhat you'll see in the console:\033[0m")
    print("  • Workflow run status and duration")
    print("  • Step-by-step execution trace")
    print("  • S3 location of detailed logs")
    print("  • Session and act-level metrics")
    
    # Explain decorator parameters
    explain_decorator_parameters()
    
    # Show main function pattern
    demonstrate_main_function()
    
    # Display next steps
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mWorkflow Decorator Complete\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[92m✓ Completed:\033[0m @workflow decorator pattern demonstrated")
    print(f"\033[38;5;214m→ Next:\033[0m Learn Workflow context manager alternative")
    
    print(f"\n\033[38;5;214mKey Takeaways:\033[0m")
    print("1. @workflow decorator enables AWS logging for local execution")
    print("2. Logs stored in S3, viewable in Nova Act console")
    print("3. Workflow definition enables deployment readiness")
    print("4. Local execution with AWS tracking and monitoring")
    
    print(f"\n\033[38;5;214mNext Tutorial:\033[0m")
    print("Run: python 3_workflow_context_manager.py")


if __name__ == "__main__":
    # Execute with empty payload for local testing
    main({})
