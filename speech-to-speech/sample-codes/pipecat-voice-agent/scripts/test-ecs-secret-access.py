#!/usr/bin/env python3
"""
Test script to simulate ECS task access to all secrets (Daily, AWS, Twilio).
This simulates what the containerized application would do when accessing secrets.
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


def test_all_secrets_access():
    """Test that all secrets can be retrieved as an ECS task would."""

    print("=" * 70)
    print("Testing All Pipecat Secrets Access (ECS Task Simulation)")
    print("=" * 70)

    aws_region = os.getenv("AWS_REGION", "eu-north-1")

    secrets_to_test = [
        {
            "name": "pipecat/daily-api-key",
            "description": "Daily.co API credentials",
            "expected_keys": ["DAILY_API_KEY", "DAILY_API_URL"],
        },
        {
            "name": "pipecat/aws-credentials",
            "description": "AWS credentials for Bedrock",
            "expected_keys": [
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_REGION",
            ],
        },
        {
            "name": "pipecat/twilio-credentials",
            "description": "Twilio API credentials",
            "expected_keys": [
                "TWILIO_ACCOUNT_SID",
                "TWILIO_AUTH_TOKEN",
                "TWILIO_PHONE_NUMBER",
                "TWILIO_API_SID",
                "TWILIO_API_SECRET",
            ],
        },
    ]

    try:
        # Create Secrets Manager client
        secrets_client = boto3.client("secretsmanager", region_name=aws_region)

        print(f"Using AWS region: {aws_region}")
        print(f"Testing {len(secrets_to_test)} secrets...")
        print()

        all_secrets_data = {}

        for secret_info in secrets_to_test:
            secret_name = secret_info["name"]
            description = secret_info["description"]
            expected_keys = secret_info["expected_keys"]

            print(f"Testing: {secret_name} ({description})")

            try:
                # Retrieve the secret
                response = secrets_client.get_secret_value(SecretId=secret_name)
                secret_data = json.loads(response["SecretString"])

                print(f"  ✓ Successfully retrieved secret")
                print(f"  ✓ Contains {len(secret_data)} keys")

                # Verify expected keys
                missing_keys = []
                for key in expected_keys:
                    if key in secret_data and secret_data[key]:
                        print(f"    ✓ {key}: present")
                    else:
                        missing_keys.append(key)
                        print(f"    ✗ {key}: missing or empty")

                if missing_keys:
                    print(f"  ⚠ Missing keys: {missing_keys}")
                else:
                    print(f"  ✓ All expected keys present")

                all_secrets_data[secret_name] = secret_data

            except Exception as e:
                print(f"  ✗ Error retrieving secret: {str(e)}")
                return False

            print()

        # Test that we can create environment variables as ECS would
        print("Simulating ECS environment variable injection:")
        env_vars = {}

        # Daily.co credentials
        daily_data = all_secrets_data.get("pipecat/daily-api-key", {})
        env_vars.update(daily_data)

        # AWS credentials
        aws_data = all_secrets_data.get("pipecat/aws-credentials", {})
        env_vars.update(aws_data)

        # Twilio credentials
        twilio_data = all_secrets_data.get("pipecat/twilio-credentials", {})
        env_vars.update(twilio_data)

        print(f"  ✓ Would inject {len(env_vars)} environment variables")

        # Verify critical variables for phone service
        critical_vars = [
            "DAILY_API_KEY",
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_PHONE_NUMBER",
        ]

        missing_critical = []
        for var in critical_vars:
            if var in env_vars and env_vars[var]:
                print(f"    ✓ {var}: available")
            else:
                missing_critical.append(var)
                print(f"    ✗ {var}: missing")

        if missing_critical:
            print(f"  ⚠ Missing critical variables: {missing_critical}")
            return False

        print()
        print("🎉 All secrets access test completed successfully!")
        print()
        print("✅ Ready for ECS deployment with Twilio integration")
        print("✅ Phone service will have access to all required credentials")
        print("✅ Both WebRTC and phone calling modes will be supported")

        return True

    except Exception as e:
        print(f"✗ Error testing secrets access: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_all_secrets_access()
    exit(0 if success else 1)
