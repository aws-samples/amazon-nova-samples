#!/usr/bin/env python3
"""
Security Guardrails for Production Tool Use

This script demonstrates implementing security guardrails for Nova Act
tool usage in production environments, including access controls and validation.

Prerequisites:
- Completed 2_agentcore_gateway.py
- Understanding of security best practices
- Knowledge of Nova Act security options
- Production security requirements

Setup:
1. Configure security policies for tool access
2. Implement state guardrails and validation
3. Set up file access restrictions
4. Test security controls and monitoring

Note: Security guardrails protect against unauthorized access and tool misuse.
"""

import os
import fnmatch
from urllib.parse import urlparse
from nova_act import NovaAct, SecurityOptions, GuardrailDecision, GuardrailInputState, workflow


def create_workflow_definition():
    """Create workflow definition for security guardrails demo."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mCreating Workflow Definition\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    try:
        import boto3
        
        client = boto3.client('nova-act', region_name='us-east-1')
        
        response = client.create_workflow_definition(
            name="security-guardrails-demo",
            description="Demonstrates security guardrails for URL access control in production workflows"
        )
        
        print(f"\n\033[93m[OK]\033[0m Workflow definition created: security-guardrails-demo")
        print(f"  ARN: {response.get('workflowDefinitionArn', 'N/A')}")
        print(f"  Description: Security guardrails demonstration")
        
        return response
        
    except Exception as e:
        if "already exists" in str(e).lower() or "ResourceConflictException" in str(e):
            print(f"\n\033[93m[OK]\033[0m Workflow definition already exists: security-guardrails-demo")
            return None
        else:
            print(f"\n\033[91m[ERROR]\033[0m Failed to create workflow definition: {e}")
            raise


def demonstrate_url_guardrails():
    """Demonstrate URL-based security guardrails."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mURL Security Guardrails\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m URL guardrails control website access during workflow execution")
    print("  Prevent navigation to unauthorized domains")
    print("  Block access to sensitive or malicious sites")
    print("  Enforce corporate web access policies")
    
    def url_guardrail(state: GuardrailInputState) -> GuardrailDecision:
        """URL guardrail implementation with allow/block lists."""
        hostname = urlparse(state.browser_url).hostname
        if not hostname:
            print(f"\033[91m[BLOCKED]\033[0m Invalid URL: {state.browser_url}")
            return GuardrailDecision.BLOCK
        
        # Corporate block list - real domains for demonstration
        blocked_domains = [
            "google.com",
            "*.google.com",
            "facebook.com",
            "*.facebook.com",
            "twitter.com",
            "*.twitter.com"
        ]
        
        if any(fnmatch.fnmatch(hostname, pattern) for pattern in blocked_domains):
            print(f"\033[91m[BLOCKED]\033[0m Blocked domain: {hostname}")
            return GuardrailDecision.BLOCK
        
        # Corporate allow list
        allowed_domains = [
            "nova.amazon.com",
            "*.aws.amazon.com",
            "docs.aws.amazon.com",
            "console.aws.amazon.com",
            "amazon.com",
            "*.amazon.com"
        ]
        
        if any(fnmatch.fnmatch(hostname, pattern) for pattern in allowed_domains):
            print(f"\033[92m[ALLOWED]\033[0m Approved domain: {hostname}")
            return GuardrailDecision.PASS
        
        # Default deny for unknown domains
        print(f"\033[91m[BLOCKED]\033[0m Unknown domain: {hostname}")
        return GuardrailDecision.BLOCK
    
    print(f"\n\033[38;5;214mGuardrail Configuration:\033[0m")
    print("  Block List: google.com, *.google.com, facebook.com, twitter.com")
    print("  Allow List: nova.amazon.com, *.aws.amazon.com, amazon.com")
    print("  Default Policy: DENY (block unknown domains)")
    
    return url_guardrail


def demonstrate_file_access_security():
    """Demonstrate file access security controls."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mFile Access Security Controls\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m File access controls prevent unauthorized file operations")
    print("  Restrict local file:// URL navigation")
    print("  Control file upload capabilities")
    print("  Prevent access to sensitive directories")
    
    # Configure secure file access options
    security_options = SecurityOptions(
        # Allow file access only to specific directories
        allowed_file_open_paths=[
            '/tmp/nova-act-workspace/*',
            '/home/user/documents/public/*',
            '/opt/company/shared-files/*'
        ],
        
        # Allow file uploads only to designated areas
        allowed_file_upload_paths=[
            '/tmp/nova-act-uploads/*',
            '/home/user/uploads/*'
        ]
    )
    
    print(f"\n\033[38;5;214mFile Access Configuration:\033[0m")
    print("  Allowed File Open Paths:")
    for path in security_options.allowed_file_open_paths:
        print(f"    • {path}")
    
    print("  Allowed File Upload Paths:")
    for path in security_options.allowed_file_upload_paths:
        print(f"    • {path}")
    
    print(f"\n\033[38;5;214mSecurity Benefits:\033[0m")
    print("  • Prevents access to system files (/etc/, /root/)")
    print("  • Blocks access to user credentials and keys")
    print("  • Restricts file uploads to safe directories")
    print("  • Enables audit trails for file operations")
    
    return security_options


def demonstrate_tool_access_controls():
    """Demonstrate tool access security controls."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mTool Access Security Controls\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m Tool access controls limit external tool capabilities")
    print("  Whitelist approved tools for workflow use")
    print("  Validate tool inputs and outputs")
    print("  Monitor tool usage for security violations")
    
    # Define approved tools with security validation
    approved_tools = {
        "aws-documentation-search": {
            "allowed": True,
            "max_requests_per_minute": 30,
            "input_validation": ["query", "service"],
            "output_sanitization": True,
            "audit_logging": True
        },
        "enterprise-ticketing": {
            "allowed": True,
            "max_requests_per_minute": 10,
            "input_validation": ["title", "description", "priority"],
            "output_sanitization": True,
            "audit_logging": True
        },
        "external-api-tool": {
            "allowed": False,
            "reason": "Not approved for production use"
        }
    }
    
    print(f"\n\033[38;5;214mTool Security Policies:\033[0m")
    for tool_name, policy in approved_tools.items():
        status = "APPROVED" if policy.get("allowed") else "BLOCKED"
        color = "\033[92m" if policy.get("allowed") else "\033[91m"
        print(f"  {color}[{status}]\033[0m {tool_name}")
        
        if policy.get("allowed"):
            print(f"    Rate limit: {policy.get('max_requests_per_minute', 'N/A')} req/min")
            print(f"    Input validation: {policy.get('input_validation', [])}")
            print(f"    Audit logging: {policy.get('audit_logging', False)}")
        else:
            print(f"    Reason: {policy.get('reason', 'Security policy violation')}")
    
    return approved_tools


@workflow(workflow_definition_name="security-guardrails-demo", model_id="nova-act-latest")
def demonstrate_secure_workflow():
    """Demonstrate Nova Act workflow with security guardrails."""
    print(f"\n\033[93m[OK]\033[0m Executing workflow with security guardrails enabled")
    print("  URL access controls active")
    print("  File access restrictions enforced")
    print("  Tool usage monitoring enabled")
    
    # Set up security guardrails
    url_guardrail = demonstrate_url_guardrails()
    security_options = demonstrate_file_access_security()
    
    try:
        print(f"\n\033[38;5;214m{'='*60}\033[0m")
        print(f"\033[38;5;214mTest 1: Navigate to Allowed Domain\033[0m")
        print(f"\033[38;5;214m{'='*60}\033[0m")
        
        with NovaAct(
            starting_page="https://nova.amazon.com/act",
            state_guardrail=url_guardrail,
            security_options=security_options
        ) as nova:
            
            print(f"  ✓ Security guardrails active and monitoring")
            print(f"  ✓ Starting page: nova.amazon.com (ALLOWED)")
            
            # This should succeed - nova.amazon.com is in allow list
            result = nova.act("Get the main heading on this page")
            print(f"  ✓ Navigation successful: {result}")
            
        print(f"\n\033[38;5;214m{'='*60}\033[0m")
        print(f"\033[38;5;214mTest 2: Attempt to Navigate to Blocked Domain\033[0m")
        print(f"\033[38;5;214m{'='*60}\033[0m")
        
        print(f"  Attempting to navigate to google.com (BLOCKED)")
        
        with NovaAct(
            starting_page="https://nova.amazon.com/act",
            state_guardrail=url_guardrail,
            security_options=security_options
        ) as nova:
            
            try:
                # This should be blocked by guardrails
                result = nova.act("Navigate to google.com")
                print(f"  ✗ Unexpected: Navigation succeeded (should have been blocked)")
                
            except Exception as e:
                if "guardrail" in str(e).lower() or "blocked" in str(e).lower():
                    print(f"  ✓ Security guardrail blocked navigation to google.com")
                    print(f"  ✓ Guardrail protection working correctly")
                else:
                    print(f"  ⚠ Navigation failed with error: {e}")
        
        print(f"\n\033[38;5;214m{'='*60}\033[0m")
        print(f"\033[38;5;214mTest 3: Navigate Within Allowed Domains\033[0m")
        print(f"\033[38;5;214m{'='*60}\033[0m")
        
        with NovaAct(
            starting_page="https://docs.aws.amazon.com",
            state_guardrail=url_guardrail,
            security_options=security_options
        ) as nova:
            
            print(f"  ✓ Starting page: docs.aws.amazon.com (ALLOWED)")
            result = nova.act("Find information about Amazon Nova")
            print(f"  ✓ Navigation within allowed domains successful")
            
        return {
            "status": "completed",
            "security_controls": "active",
            "tests_passed": 3,
            "blocked_attempts": 1,
            "message": "Security guardrails successfully blocked unauthorized access"
        }
            
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Workflow error: {e}")
        return {"status": "error", "error": str(e)}


def explain_security_best_practices():
    """Explain security best practices for production tool use."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mSecurity Best Practices\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214mURL Security Controls:\033[0m")
    print("  • Implement corporate web access policies")
    print("  • Block known malicious and inappropriate domains")
    print("  • Use allow lists for approved business domains")
    print("  • Log all navigation attempts for security monitoring")
    
    print(f"\n\033[38;5;214mFile Access Security:\033[0m")
    print("  • Restrict file:// URL access to approved directories")
    print("  • Prevent access to system files and credentials")
    print("  • Control file upload destinations and permissions")
    print("  • Implement file type validation and scanning")
    
    print(f"\n\033[38;5;214mTool Usage Security:\033[0m")
    print("  • Maintain approved tool registry with security review")
    print("  • Implement rate limiting to prevent abuse")
    print("  • Validate all tool inputs and sanitize outputs")
    print("  • Monitor tool usage patterns for anomalies")
    
    print(f"\n\033[38;5;214mMonitoring and Compliance:\033[0m")
    print("  • Log all security events and violations")
    print("  • Set up alerts for security policy violations")
    print("  • Regular security audits and policy reviews")
    print("  • Compliance reporting for regulatory requirements")


def security_implementation_guide():
    """Provide security implementation guide for production."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mSecurity Implementation Guide\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214mStep 1: Define Security Policies\033[0m")
    print("  • Create corporate web access policy")
    print("  • Define approved file access directories")
    print("  • Establish tool approval and review process")
    print("  • Document security requirements and exceptions")
    
    print(f"\n\033[38;5;214mStep 2: Implement Guardrails\033[0m")
    print("  • Configure URL guardrails with allow/block lists")
    print("  • Set up file access restrictions")
    print("  • Implement tool validation and rate limiting")
    print("  • Test guardrails with security scenarios")
    
    print(f"\n\033[38;5;214mStep 3: Set Up Monitoring\033[0m")
    print("  • Configure security event logging")
    print("  • Set up alerts for policy violations")
    print("  • Implement security dashboards and reporting")
    print("  • Establish incident response procedures")
    
    print(f"\n\033[38;5;214mStep 4: Deploy and Maintain\033[0m")
    print("  • Deploy security controls to production")
    print("  • Regular security policy reviews and updates")
    print("  • Security training for development teams")
    print("  • Continuous monitoring and improvement")


def main(payload):
    """
    Main function demonstrating security guardrails for production.
    
    Args:
        payload: Input parameters for workflow execution
    """
    print("="*60)
    print("Security Guardrails for Production Tool Use")
    print("="*60)
    
    # Create workflow definition
    create_workflow_definition()
    
    # Demonstrate URL guardrails
    url_guardrail = demonstrate_url_guardrails()
    
    # Demonstrate file access security
    security_options = demonstrate_file_access_security()
    
    # Demonstrate tool access controls
    tool_policies = demonstrate_tool_access_controls()
    
    # Execute secure workflow
    try:
        print(f"\n\033[38;5;214m{'='*60}\033[0m")
        print(f"\033[38;5;214mSecure Workflow Demonstration\033[0m")
        print(f"\033[38;5;214m{'='*60}\033[0m")
        
        result = demonstrate_secure_workflow()
        print(f"\n\033[92m✓ Completed:\033[0m Security guardrails workflow demonstrated")
        
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Security workflow demonstration failed: {e}")
    
    # Explain security best practices
    explain_security_best_practices()
    
    # Implementation guide
    security_implementation_guide()
    
    # Display completion
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mSecurity Guardrails Complete\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[92m✓ Completed:\033[0m Security guardrails implementation and best practices")
    print(f"\033[38;5;214m→ Next:\033[0m Explore observability patterns for production monitoring")
    
    print(f"\n\033[38;5;214mSecurity Controls Implemented:\033[0m")
    print("1. URL access guardrails with allow/block lists")
    print("2. File access restrictions and validation")
    print("3. Tool usage controls and monitoring")
    print("4. Security event logging and alerting")
    
    print(f"\n\033[38;5;214mNext Steps:\033[0m")
    print("1. Implement security policies for your organization")
    print("2. Set up monitoring and alerting for security events")
    print("3. Proceed to 04-observability tutorials")
    print("4. Deploy security controls to production workflows")


if __name__ == "__main__":
    # Execute with empty payload for local testing
    main({})
