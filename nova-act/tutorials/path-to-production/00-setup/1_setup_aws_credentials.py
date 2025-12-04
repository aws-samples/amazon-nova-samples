#!/usr/bin/env python3
"""
AWS Credentials Setup for Nova Act Production

This script guides you through setting up AWS credentials and configuration
required for Nova Act production deployment.

Prerequisites:
- AWS CLI installed
- AWS account with appropriate permissions
- Python 3.10 or higher

Setup:
1. Install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
2. Run this script to configure credentials
3. Verify setup with verify_permissions.py

Note: This configures AWS IAM authentication for production use, not API key authentication.
"""

import subprocess
import sys
import os
import json
from pathlib import Path


def check_aws_cli_installed():
    """Check if AWS CLI is installed and accessible."""
    try:
        result = subprocess.run(['aws', '--version'], capture_output=True, text=True)
        print(f"\033[93m[OK]\033[0m AWS CLI found: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("\033[91m[ERROR]\033[0m AWS CLI not found. Please install it first:")
        print("  https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")
        return False


def check_existing_credentials():
    """Check if AWS credentials already exist."""
    try:
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                              capture_output=True, text=True, check=True)
        identity = json.loads(result.stdout)
        print(f"\n\033[93m[OK]\033[0m Existing credentials found:")
        print(f"  Account: {identity.get('Account')}")
        print(f"  User ARN: {identity.get('Arn')}")
        return True
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return False


def configure_aws_credentials():
    """Guide user through AWS credentials configuration."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mAWS Credentials Configuration\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Check for existing credentials
    if check_existing_credentials():
        response = input("\nCredentials already configured. Reconfigure? (y/N): ").strip().lower()
        if response != 'y':
            print("Keeping existing credentials")
            return True
    
    print("\nConfiguring AWS credentials for Nova Act production deployment.")
    print("You'll need your AWS Access Key ID and Secret Access Key.")
    print("\nIf you don't have these, create them in the AWS Console:")
    print("  1. Go to IAM > Users > [Your User] > Security credentials")
    print("  2. Create access key > Command Line Interface (CLI)")
    print("  3. Download the credentials")
    
    # Run AWS configure
    try:
        print(f"\n\033[38;5;214m→ Running:\033[0m aws configure")
        subprocess.run(['aws', 'configure'], check=True)
        print(f"\n\033[93m[OK]\033[0m AWS credentials configured")
        return True
    except subprocess.CalledProcessError:
        print(f"\n\033[91m[ERROR]\033[0m Failed to configure AWS credentials")
        return False


def set_default_region():
    """Set default region for Nova Act (us-east-1 required)."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mRegion Configuration\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Check current region
    try:
        result = subprocess.run(['aws', 'configure', 'get', 'region'], 
                              capture_output=True, text=True)
        current_region = result.stdout.strip()
        if current_region == 'us-east-1':
            print(f"\n\033[93m[OK]\033[0m Region already set to us-east-1")
            return True
    except subprocess.CalledProcessError:
        pass
    
    print("\nNova Act is currently available in: us-east-1")
    print("Setting default region to us-east-1...")
    
    try:
        subprocess.run(['aws', 'configure', 'set', 'region', 'us-east-1'], check=True)
        print(f"\033[93m[OK]\033[0m Default region set to us-east-1")
        return True
    except subprocess.CalledProcessError:
        print(f"\033[91m[ERROR]\033[0m Failed to set default region")
        return False


def verify_credentials():
    """Verify AWS credentials are working."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mCredentials Verification\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    try:
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                              capture_output=True, text=True, check=True)
        
        identity = json.loads(result.stdout)
        print(f"\n\033[93m[OK]\033[0m AWS credentials verified:")
        print(f"  Account: {identity.get('Account')}")
        print(f"  User ARN: {identity.get('Arn')}")
        print(f"  User ID: {identity.get('UserId')}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n\033[91m[ERROR]\033[0m Failed to verify credentials:")
        print(f"  {e.stderr}")
        return False
    except json.JSONDecodeError:
        print(f"\n\033[91m[ERROR]\033[0m Invalid response from AWS")
        return False


def display_next_steps():
    """Display next steps after successful setup."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mSetup Complete\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[92m✓ Completed:\033[0m AWS credentials and region configuration")
    print(f"\033[38;5;214m→ Next:\033[0m Run 2_verify_permissions.py to check Nova Act service access")
    
    print(f"\n\033[38;5;214mNext Steps:\033[0m")
    print("1. Run: python 2_verify_permissions.py")
    print("2. Proceed to 01-workflow-basics tutorials")
    print("3. Begin building production Nova Act workflows")


def main():
    """Main setup function."""
    print("="*60)
    print("AWS Credentials Setup for Nova Act Production")
    print("="*60)
    
    # Check AWS CLI
    if not check_aws_cli_installed():
        sys.exit(1)
    
    # Configure credentials
    if not configure_aws_credentials():
        sys.exit(1)
    
    # Set region
    if not set_default_region():
        sys.exit(1)
    
    # Verify setup
    if not verify_credentials():
        sys.exit(1)
    
    # Show next steps
    display_next_steps()


if __name__ == "__main__":
    main()
