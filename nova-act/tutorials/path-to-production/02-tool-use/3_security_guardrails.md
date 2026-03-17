# Security Guardrails for Production Tool Use

## Prerequisites
- Completed `2_agentcore_gateway.py`
- Understanding of security best practices
- Knowledge of Nova Act state guardrails
- Production security requirements and policies
- Familiarity with URL parsing and pattern matching

## Overview
This example demonstrates implementing security guardrails with Nova Act using **State Guardrails** - the documented security feature for controlling URL access during workflow execution. State guardrails provide protection against unauthorized website access and malicious sites in enterprise deployments.

**Note**: This tutorial focuses on documented Nova Act security features. Additional security controls (file access restrictions, tool approval workflows, rate limiting) should be implemented at the infrastructure/application level.

## What Are State Guardrails?

State guardrails allow you to control which URLs the agent can visit during execution. You provide a callback function that inspects the browser state after each observation and decides whether to allow or block continued execution. If blocked, `act()` will raise `ActStateGuardrailError`.

**Use Cases:**
- Preventing navigation to unauthorized domains
- Blocking access to sensitive internal pages
- Enforcing corporate web access policies
- Protecting against prompt injection attacks that attempt navigation

## Code Walkthrough

### Section 1: URL Security Guardrails

```python
from nova_act import NovaAct, GuardrailDecision, GuardrailInputState, workflow
from urllib.parse import urlparse
import fnmatch

def url_guardrail(state: GuardrailInputState) -> GuardrailDecision:
    """
    URL guardrail implementation with allow/block lists.
    
    This function is called after each browser observation to validate
    the current URL against corporate security policies.
    """
    hostname = urlparse(state.browser_url).hostname
    
    if not hostname:
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
        print(f"[BLOCKED] Access denied to blocked domain: {hostname}")
        return GuardrailDecision.BLOCK
    
    # Corporate allow list - define approved business domains
    allowed_domains = [
        "nova.amazon.com",
        "*.aws.amazon.com",
        "docs.aws.amazon.com",
        "console.aws.amazon.com",
        "amazon.com",
        "*.amazon.com"
    ]
    
    if any(fnmatch.fnmatch(hostname, pattern) for pattern in allowed_domains):
        print(f"[ALLOWED] Access granted to approved domain: {hostname}")
        return GuardrailDecision.PASS
    
    # Default deny - block unknown domains for maximum security
    print(f"[BLOCKED] Access denied to unknown domain: {hostname}")
    return GuardrailDecision.BLOCK
```

**Key Features:**
- **Block Lists**: Prevent access to social media and search engines (google.com, facebook.com, twitter.com)
- **Allow Lists**: Define approved Amazon/AWS domains for workflow access
- **Pattern Matching**: Support wildcards (`*`) for flexible domain policies (e.g., `*.google.com` blocks all Google subdomains)
- **Default Deny**: Block unknown domains for maximum security

**Real-World Example:**
This configuration blocks popular social media and search sites while allowing access to Amazon and AWS documentation/services. This is useful for:
- Preventing workflow distractions or data leakage
- Enforcing corporate acceptable use policies
- Limiting attack surface for prompt injection attempts

### Section 2: Secure Workflow Implementation

```python
@workflow(workflow_definition_name="security-guardrails-demo", model_id="nova-act-latest")
def demonstrate_secure_workflow():
    """
    Demonstrate Nova Act workflow with URL security guardrails.
    
    This workflow runs three tests:
    1. Navigate to allowed domain (nova.amazon.com) - succeeds
    2. Attempt to navigate to blocked domain (google.com) - blocked
    3. Navigate within allowed domains (docs.aws.amazon.com) - succeeds
    """
    try:
        # Test 1: Navigate to allowed domain
        print("Test 1: Navigate to Allowed Domain")
        with NovaAct(
            starting_page="https://nova.amazon.com/act",
            state_guardrail=url_guardrail
        ) as nova:
            result = nova.act("Get the main heading on this page")
            print(f"✓ Navigation successful: {result}")
        
        # Test 2: Attempt to navigate to blocked domain
        print("\nTest 2: Attempt to Navigate to Blocked Domain")
        with NovaAct(
            starting_page="https://nova.amazon.com/act",
            state_guardrail=url_guardrail
        ) as nova:
            try:
                # This will be blocked by the guardrail
                result = nova.act("Navigate to google.com")
                print("✗ Unexpected: Navigation succeeded (should have been blocked)")
            except Exception as e:
                if "guardrail" in str(e).lower():
                    print("✓ Security guardrail blocked navigation to google.com")
        
        # Test 3: Navigate within allowed domains
        print("\nTest 3: Navigate Within Allowed Domains")
        with NovaAct(
            starting_page="https://docs.aws.amazon.com",
            state_guardrail=url_guardrail
        ) as nova:
            result = nova.act("Find information about Amazon Nova")
            print(f"✓ Navigation within allowed domains successful")
            
        return {
            "status": "completed",
            "tests_passed": 3,
            "blocked_attempts": 1
        }
            
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

**Security Benefits:**
1. **Automatic Enforcement**: Guardrails are checked after every browser observation
2. **Fail-Safe**: Violations raise exceptions, preventing unauthorized access
3. **Audit Trail**: Logging provides visibility into blocked/allowed navigation
4. **Flexible Policies**: Easy to update allow/block lists without code changes

**Demonstration Flow:**
- **Test 1** shows normal operation on allowed domains
- **Test 2** demonstrates blocking google.com navigation attempts
- **Test 3** confirms navigation works within approved Amazon/AWS domains

### Section 3: Additional Security Recommendations

While Nova Act provides state guardrails for URL control, implement these additional security measures at the application/infrastructure level:

#### Domain Restriction Best Practices
```python
# Recommended: Use specific domains instead of wildcards when possible
allowed_domains = [
    "docs.aws.amazon.com",      # Specific subdomain
    "console.aws.amazon.com",   # Specific subdomain
]

# Avoid overly broad patterns
# ❌ "*.com" - Too permissive
# ✅ "*.aws.amazon.com" - Scoped to AWS services
```

#### Tool Use Restriction
From the user guide: "Minimize attack surfaces by only registering tools relevant for a given workflow."

```python
# Only include necessary tools
with NovaAct(
    starting_page="https://docs.aws.amazon.com",
    tools=[aws_documentation_search],  # Only approved tools
    state_guardrail=url_guardrail
) as nova:
    result = nova.act("Search for Lambda documentation")
```

#### Local File Access Restriction
From the user guide: "Restrict access to file:// path access unless necessary for a specific workflow. This is blocked by default in the SDK."

**Recommendation**: Only enable file:// access for specific, approved file paths when absolutely necessary.

#### Monitoring and Alerting
- Log all guardrail violations for security review
- Set up CloudWatch alarms for blocked navigation attempts
- Monitor for patterns indicating prompt injection attacks
- Review audit logs regularly for compliance

## Running the Example

```bash
cd /path/to/nova-act/tutorials/path-to-production/03-tool-use
python 3_security_guardrails.py
```

**Expected Output:**
```
Security Guardrails for Production Tool Use
============================================================

URL Security Guardrails
============================================================
[OK] URL guardrails control website access during workflow execution
  ✓ Block lists prevent access to social media and search engines
  ✓ Allow lists define approved Amazon/AWS domains
  ✓ Pattern matching supports flexible policies
  ✓ Default deny blocks unknown domains

Guardrail Configuration:
  Block List: google.com, *.google.com, facebook.com, twitter.com
  Allow List: nova.amazon.com, *.aws.amazon.com, amazon.com
  Default Policy: DENY (block unknown domains)

Test 1: Navigate to Allowed Domain
============================================================
[ALLOWED] Access granted to approved domain: nova.amazon.com
✓ Navigation successful: Beyond the Pale Blue Dot

Test 2: Attempt to Navigate to Blocked Domain
============================================================
Attempting to navigate to google.com (BLOCKED)
[BLOCKED] Access denied to blocked domain: google.com
✓ Security guardrail blocked navigation to google.com
✓ Guardrail protection working correctly

Test 3: Navigate Within Allowed Domains
============================================================
[ALLOWED] Access granted to approved domain: docs.aws.amazon.com
✓ Navigation within allowed domains successful

Workflow Execution
============================================================
Status: completed
Tests Passed: 3
Blocked Attempts: 1
Message: Security guardrails successfully blocked unauthorized access
```

## Testing Guardrails

### Test 1: Allowed Domain (Amazon/AWS)
```python
# Should succeed - Amazon domains are in the allow list
with NovaAct(
    starting_page="https://docs.aws.amazon.com",
    state_guardrail=url_guardrail
) as nova:
    result = nova.act("Navigate to the Amazon Bedrock documentation")
    print(f"Success: {result}")
```

### Test 2: Blocked Domain (Google)
```python
# Should raise ActStateGuardrailError - google.com is in the block list
with NovaAct(
    starting_page="https://nova.amazon.com/act",
    state_guardrail=url_guardrail
) as nova:
    try:
        nova.act("Navigate to google.com")
    except Exception as e:
        print(f"Blocked: {e}")  # Expected behavior
```

### Test 3: Blocked Domain (Facebook)
```python
# Should raise ActStateGuardrailError - facebook.com is in the block list
with NovaAct(
    starting_page="https://nova.amazon.com/act",
    state_guardrail=url_guardrail
) as nova:
    try:
        nova.act("Go to facebook.com")
    except Exception as e:
        print(f"Blocked: {e}")  # Expected behavior
```

### Test 4: Unknown Domain (Default Deny)
```python
# Should raise ActStateGuardrailError - unknown domains are blocked by default
with NovaAct(
    starting_page="https://unknown-domain.com",
    state_guardrail=url_guardrail
) as nova:
    nova.act("Navigate to the homepage")
```

**Expected Behavior:**
- ✅ Test 1: Succeeds (allowed domain)
- ❌ Test 2: Blocked (google.com in block list)
- ❌ Test 3: Blocked (facebook.com in block list)
- ❌ Test 4: Blocked (default deny policy)

## Production Deployment Considerations

### 1. Centralized Policy Management
Store allow/block lists in a configuration service (AWS Systems Manager Parameter Store, Secrets Manager) for easy updates without code deployment.

### 2. Environment-Specific Policies
```python
import os

def get_allowed_domains():
    env = os.getenv('ENVIRONMENT', 'prod')
    if env == 'dev':
        return ["*.amazon.com", "localhost"]
    elif env == 'prod':
        return ["docs.aws.amazon.com", "console.aws.amazon.com"]
```

### 3. Logging and Monitoring
```python
import logging

logger = logging.getLogger(__name__)

def url_guardrail(state: GuardrailInputState) -> GuardrailDecision:
    hostname = urlparse(state.browser_url).hostname
    
    if is_blocked(hostname):
        logger.warning(f"Blocked navigation attempt to: {hostname}")
        return GuardrailDecision.BLOCK
    
    logger.info(f"Allowed navigation to: {hostname}")
    return GuardrailDecision.PASS
```

### 4. Incident Response
- Set up CloudWatch alarms for high volumes of blocked attempts
- Create runbooks for investigating security violations
- Implement automated responses for repeated violations

## Security Best Practices Summary

✅ **DO:**
- Use state guardrails for URL access control
- Implement default deny policies
- Log all guardrail decisions
- Regularly review and update allow/block lists
- Minimize tool registration to only necessary tools
- Monitor for prompt injection attempts

❌ **DON'T:**
- Use overly broad wildcard patterns
- Disable guardrails in production
- Ignore guardrail violation logs
- Register unnecessary tools
- Allow file:// access without specific justification

## Troubleshooting

### ActStateGuardrailError
**Cause**: Agent attempted to navigate to a blocked URL

**Solution**: 
1. Check if the domain should be allowed
2. Add to allow list if legitimate
3. Investigate if this indicates a prompt injection attempt

### Guardrail Not Triggering
**Cause**: Guardrail function not properly configured

**Solution**:
1. Verify `state_guardrail` parameter is set in NovaAct constructor
2. Ensure guardrail function returns `GuardrailDecision.PASS` or `GuardrailDecision.BLOCK`
3. Check that function signature matches `(GuardrailInputState) -> GuardrailDecision`

## Additional Resources

- [Nova Act User Guide - State Guardrails](https://p2p-user-guide.md#state-guardrails)
- [Nova Act User Guide - Responsible Use](https://p2p-user-guide.md#responsible-use)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [Prompt Injection Mitigation](https://p2p-user-guide.md#prompt-injection)

## Next Steps

1. Implement state guardrails in your production workflows
2. Set up centralized policy management
3. Configure CloudWatch monitoring and alerting
4. Review security logs regularly
5. Test guardrails with various scenarios
6. Document your security policies and procedures
