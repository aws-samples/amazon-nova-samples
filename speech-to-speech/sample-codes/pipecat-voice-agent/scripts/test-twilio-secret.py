#!/usr/bin/env python3
"""
Test script to verify Twilio credentials can be retrieved from AWS Secrets Manager.
"""

import os
import json
import boto3
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_twilio_secret_access():
    """Test that Twilio credentials can be retrieved from AWS Secrets Manager."""

    print("=" * 60)
    print("Testing Twilio Credentials Access from AWS Secrets Manager")
    print("=" * 60)

    aws_region = os.getenv("AWS_REGION", "eu-north-1")
    twilio_secret_name = "pipecat/twilio-credentials"

    try:
        # Create Secrets Manager client
        secrets_client = boto3.client("secretsmanager", region_name=aws_region)

        print(f"Using AWS region: {aws_region}")
        print(f"Testing secret: {twilio_secret_name}")
        print()

        # Retrieve the secret
        response = secrets_client.get_secret_value(SecretId=twilio_secret_name)
        secret_data = json.loads(response["SecretString"])

        print("✓ Successfully retrieved Twilio credentials from Secrets Manager")
        print(f"✓ Secret contains {len(secret_data)} keys")
        print()

        # Verify expected keys are present
        expected_keys = [
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_PHONE_NUMBER",
            "TWILIO_API_SID",
            "TWILIO_API_SECRET",
        ]

        print("Verifying credential keys:")
        for key in expected_keys:
            if key in secret_data:
                value = secret_data[key]
                if value:
                    # Mask sensitive values for display
                    if "TOKEN" in key or "SECRET" in key:
                        masked_value = (
                            value[:4] + "*" * (len(value) - 8) + value[-4:]
                            if len(value) > 8
                            else "*" * len(value)
                        )
                        print(f"  ✓ {key}: {masked_value}")
                    else:
                        print(f"  ✓ {key}: {value}")
                else:
                    print(f"  ⚠ {key}: (empty)")
            else:
                print(f"  ✗ {key}: (missing)")

        print()

        # Test basic validation
        account_sid = secret_data.get("TWILIO_ACCOUNT_SID", "")
        auth_token = secret_data.get("TWILIO_AUTH_TOKEN", "")
        phone_number = secret_data.get("TWILIO_PHONE_NUMBER", "")

        if account_sid.startswith("AC") and len(account_sid) == 34:
            print("✓ TWILIO_ACCOUNT_SID format looks valid")
        else:
            print("⚠ TWILIO_ACCOUNT_SID format may be invalid")

        if len(auth_token) == 32:
            print("✓ TWILIO_AUTH_TOKEN length looks valid")
        else:
            print("⚠ TWILIO_AUTH_TOKEN length may be invalid")

        if phone_number.startswith("+") and len(phone_number) > 10:
            print("✓ TWILIO_PHONE_NUMBER format looks valid")
        else:
            print("⚠ TWILIO_PHONE_NUMBER format may be invalid")

        print()
        print("🎉 Twilio credentials secret test completed successfully!")
        print()
        print("Next steps:")
        print("1. Deploy updated CDK infrastructure with Twilio secret integration")
        print("2. Test ECS task can access Twilio credentials")
        print("3. Verify phone service can initialize with these credentials")

        return True

    except Exception as e:
        print(f"✗ Error testing Twilio secret access: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_twilio_secret_access()
    exit(0 if success else 1)
