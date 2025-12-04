#!/usr/bin/env python3
"""
Workflow Context Manager Pattern

This script demonstrates the Workflow context manager as an alternative
to the @workflow decorator for production deployment.

Prerequisites:
- Completed 2_workflow_decorator.py
- Workflow "getting-started-workflow" created in AWS
- Understanding of @workflow decorator pattern
- AWS credentials with Nova Act permissions

Setup:
1. Compare context manager vs decorator approaches
2. Understand when to use each pattern
3. See workflow definition creation process

Note: Context manager provides more explicit control over workflow configuration.
"""

from nova_act import NovaAct, Workflow


def demonstrate_context_manager_pattern():
    """Explain the Workflow context manager approach."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mWorkflow Context Manager Pattern\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Workflow context manager provides explicit control")
    print("  More verbose than @workflow decorator")
    print("  Better for complex workflow configurations")
    print("  Enables dynamic workflow definition names")
    print("\n\033[38;5;214m→ Next:\033[0m Implementing workflow with context manager")


def context_manager_workflow():
    """Execute workflow with multiple sessions using Workflow context manager."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMulti-Session Workflow Execution\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Use Workflow context manager to reference workflow definition
    with Workflow(
        workflow_definition_name="getting-started-workflow",
        model_id="nova-act-latest"
    ) as workflow:
        
        print(f"\n\033[93m[OK]\033[0m Workflow context manager initialized")
        print("  Workflow definition: getting-started-workflow")
        print("  Pattern: Multiple independent sessions")
        print("  Logging: All sessions tracked in one workflow run")
        
        # First session - Wikipedia
        print(f"\n\033[38;5;214mSession 1:\033[0m Wikipedia")
        with NovaAct(
            starting_page="https://en.wikipedia.org",
            workflow=workflow,
            headless=True
        ) as nova1:
            print(f"  Browser session 1 started")
            result1 = nova1.act("Find and return the main heading of the page")
            print(f"  Result: {result1}")
        
        # Second session - Nova Act site
        print(f"\n\033[38;5;214mSession 2:\033[0m Nova Act")
        with NovaAct(
            starting_page="https://nova.amazon.com/act/gym/next-dot/",
            workflow=workflow,
            headless=True
        ) as nova2:
            print(f"  Browser session 2 started")
            result2 = nova2.act("Find and return the main heading of the page")
            print(f"  Result: {result2}")
        
        print(f"\n\033[92m✓ Completed:\033[0m Both sessions executed successfully")
        print("  • Each session tracked independently")
        print("  • Both sessions logged to same workflow run")
        print("  • All traces available in Nova Act console")
        
        return {"session1": result1, "session2": result2}


def compare_patterns():
    """Compare decorator vs context manager patterns."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mPattern Comparison\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214m@workflow Decorator Pattern:\033[0m")
    print("  ✓ Concise syntax")
    print("  ✓ Function-based approach")
    print("  ✓ Good for single-session workflows")
    
    print(f"\n\033[38;5;214mWorkflow Context Manager:\033[0m")
    print("  ✓ Explicit configuration control")
    print("  ✓ Multiple sessions in one workflow")
    print("  ✓ Better for complex workflows")
    print("  ✓ Flexible session management")


def show_usage_patterns():
    """Show when to use each pattern."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mUsage Recommendations\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214mUse @workflow Decorator When:\033[0m")
    print("  • Simple, single-purpose workflows")
    print("  • Static workflow configurations")
    print("  • Function-based workflow design")
    print("  • Minimal configuration requirements")
    
    print(f"\n\033[38;5;214mUse Workflow Context Manager When:\033[0m")
    print("  • Complex workflow configurations")
    print("  • Dynamic workflow naming")
    print("  • Multiple NovaAct sessions per workflow")
    print("  • Advanced error handling requirements")
    print("  • Integration with existing context managers")


def main(payload):
    """
    Main function demonstrating Workflow context manager pattern.
    
    Args:
        payload: Input parameters for workflow execution
    """
    print("="*60)
    print("Workflow Context Manager Pattern")
    print("="*60)
    
    # Explain context manager pattern
    demonstrate_context_manager_pattern()
    
    # Execute workflow with context manager
    try:
        result = context_manager_workflow()
        print(f"\n\033[92m✓ Completed:\033[0m Context manager workflow executed successfully")
        
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Context manager workflow failed: {e}")
        return
    
    # Compare patterns
    compare_patterns()
    
    # Show usage recommendations
    show_usage_patterns()
    
    # Display completion
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mContext Manager Pattern Complete\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[92m✓ Completed:\033[0m Workflow context manager pattern demonstrated")
    print(f"\033[38;5;214m→ Next:\033[0m Learn deployment to AWS infrastructure")
    
    print(f"\n\033[38;5;214mPattern Selection Guide:\033[0m")
    print("1. Use @workflow for simple workflows")
    print("2. Use context manager for complex configurations")
    print("3. Both patterns support production deployment")
    print("4. Choose based on workflow complexity needs")
    
    print(f"\n\033[38;5;214mNext Tutorial:\033[0m")
    print("Run: python 4_deploy_workflow.py")


if __name__ == "__main__":
    # Execute with empty payload for local testing
    main({})
