# Human in the Loop with Amazon Nova Act

## Overview
This tutorial covers incorporating human input into automation workflows for tasks requiring human judgment, security challenges, or sensitive data handling.

## Learning Objectives
- Understand when human intervention is needed in automation
- Detect and handle CAPTCHAs with human assistance
- Learn proper error handling for security challenges
- Understand Nova Act's built-in CAPTCHA protection

## Prerequisites
**⚠️ Complete the centralized setup first!**
- Complete setup in `../00-setup/`
- Completion of Tutorial 01 - Getting Started
- Basic understanding of web security concepts

## When Human Intervention is Needed
- CAPTCHAs and security measures
- Complex decision-making requiring judgment
- Sensitive data entry (passwords, credit cards)
- Authentication flows (2FA, SSO)
- Exception handling for unusual situations

## Tutorial Script

### CAPTCHA Handling (`1_captcha_handling.py`)
Learn to detect and handle CAPTCHAs in automation workflows.

**What you'll learn:**
- Detecting CAPTCHAs using Nova Act's analysis
- Handling `HumanValidationError` exceptions
- Pausing automation for human CAPTCHA solving
- Advanced detection for different CAPTCHA types

**Key concepts:**
- Nova Act will NOT solve CAPTCHAs automatically
- `HumanValidationError` is expected and correct behavior
- Use `BOOL_SCHEMA` for yes/no CAPTCHA detection
- Always handle CAPTCHA exceptions gracefully

## Security Notes

### Critical Security Notice
⚠️ **Nova Act correctly refuses to solve CAPTCHAs** - this is intentional security behavior that should be respected.

## Best Practices

### CAPTCHA Handling
- Always check before critical actions
- Handle `HumanValidationError` exceptions properly
- Provide clear instructions to users
- Use try-catch blocks for CAPTCHA detection
- Validate completion after human intervention

## Quick Start
```bash
# Activate environment
source ../00-setup/venv/bin/activate

# Run the tutorial
python 1_captcha_handling.py
```

## Next Steps
- Practice with real websites using CAPTCHAs
- Understand Nova Act's security protections
- Move on to Tool Use tutorial (03-tool-use)
