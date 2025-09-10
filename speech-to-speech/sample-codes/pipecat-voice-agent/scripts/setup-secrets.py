#!/usr/bin/env python3
"""
Script to create AWS Secrets Manager secrets for the Pipecat ECS deployment.
This script creates the necessary secrets that will be injected into ECS tasks.
"""

import os
import json
import boto3
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_secrets():
    """Create AWS Secrets Manager secrets for the Pipecat deployment."""

    print("=" * 60)
    print("Setting up AWS Secrets Manager for Pipecat ECS Deployment")
    print("=" * 60)

    aws_region = os.getenv("AWS_REGION", "eu-north-1")
    daily_api_key = os.getenv("DAILY_API_KEY")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    # Twilio credentials
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
    twilio_api_sid = os.getenv("TWILIO_SID")
    twilio_api_secret = os.getenv("TWILIO_SECRET")

    if not daily_api_key:
        print("✗ DAILY_API_KEY not found in environment variables")
        return False

    if not aws_access_key or not aws_secret_key:
        print("✗ AWS credentials not found in environment variables")
        return False

    if not twilio_account_sid or not twilio_auth_token:
        print(
            "✗ Twilio credentials (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) not found in environment variables"
        )
        return False

    try:
        # Create Secrets Manager client
        secrets_client = boto3.client("secretsmanager", region_name=aws_region)

        print(f"Using AWS region: {aws_region}")
        print()

        # Secret 1: Daily API Key
        daily_secret_name = "pipecat/daily-api-key"
        daily_secret_value = {
            "DAILY_API_KEY": daily_api_key,
            "DAILY_API_URL": os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        }

        try:
            # Try to create the secret
            response = secrets_client.create_secret(
                Name=daily_secret_name,
                Description="Daily.co API credentials for Pipecat voice agent",
                SecretString=json.dumps(daily_secret_value),
                Tags=[
                    {"Key": "Application", "Value": "pipecat-voice-agent"},
                    {"Key": "Environment", "Value": "test"},
                ],
            )
            print(f"✓ Created secret: {daily_secret_name}")
            print(f"  ARN: {response['ARN']}")

        except secrets_client.exceptions.ResourceExistsException:
            # Secret already exists, update it
            secrets_client.update_secret(
                SecretId=daily_secret_name, SecretString=json.dumps(daily_secret_value)
            )
            print(f"✓ Updated existing secret: {daily_secret_name}")

        # Secret 2: AWS Credentials (for ECS tasks that need explicit credentials)
        aws_secret_name = "pipecat/aws-credentials"
        aws_secret_value = {
            "AWS_ACCESS_KEY_ID": aws_access_key,
            "AWS_SECRET_ACCESS_KEY": aws_secret_key,
            "AWS_REGION": aws_region,
        }

        try:
            # Try to create the secret
            response = secrets_client.create_secret(
                Name=aws_secret_name,
                Description="AWS credentials for Pipecat voice agent Bedrock access",
                SecretString=json.dumps(aws_secret_value),
                Tags=[
                    {"Key": "Application", "Value": "pipecat-voice-agent"},
                    {"Key": "Environment", "Value": "test"},
                ],
            )
            print(f"✓ Created secret: {aws_secret_name}")
            print(f"  ARN: {response['ARN']}")

        except secrets_client.exceptions.ResourceExistsException:
            # Secret already exists, update it
            secrets_client.update_secret(
                SecretId=aws_secret_name, SecretString=json.dumps(aws_secret_value)
            )
            print(f"✓ Updated existing secret: {aws_secret_name}")

        # Secret 3: Twilio Credentials
        twilio_secret_name = "pipecat/twilio-credentials"
        twilio_secret_value = {
            "TWILIO_ACCOUNT_SID": twilio_account_sid,
            "TWILIO_AUTH_TOKEN": twilio_auth_token,
            "TWILIO_PHONE_NUMBER": twilio_phone_number or "",
            "TWILIO_API_SID": twilio_api_sid or "",
            "TWILIO_API_SECRET": twilio_api_secret or "",
        }

        try:
            # Try to create the secret
            response = secrets_client.create_secret(
                Name=twilio_secret_name,
                Description="Twilio API credentials for Pipecat phone integration",
                SecretString=json.dumps(twilio_secret_value),
                Tags=[
                    {"Key": "Application", "Value": "pipecat-voice-agent"},
                    {"Key": "Environment", "Value": "test"},
                    {"Key": "Service", "Value": "twilio"},
                ],
            )
            print(f"✓ Created secret: {twilio_secret_name}")
            print(f"  ARN: {response['ARN']}")

        except secrets_client.exceptions.ResourceExistsException:
            # Secret already exists, update it
            secrets_client.update_secret(
                SecretId=twilio_secret_name,
                SecretString=json.dumps(twilio_secret_value),
            )
            print(f"✓ Updated existing secret: {twilio_secret_name}")

        print()
        print("✓ All secrets created/updated successfully!")

        # Verify secrets can be retrieved
        print("\nVerifying secret access...")

        try:
            daily_response = secrets_client.get_secret_value(SecretId=daily_secret_name)
            daily_data = json.loads(daily_response["SecretString"])
            print(f"✓ Daily API secret verified - contains {len(daily_data)} keys")

            aws_response = secrets_client.get_secret_value(SecretId=aws_secret_name)
            aws_data = json.loads(aws_response["SecretString"])
            print(f"✓ AWS credentials secret verified - contains {len(aws_data)} keys")

            twilio_response = secrets_client.get_secret_value(
                SecretId=twilio_secret_name
            )
            twilio_data = json.loads(twilio_response["SecretString"])
            print(
                f"✓ Twilio credentials secret verified - contains {len(twilio_data)} keys"
            )

        except Exception as e:
            print(f"✗ Error verifying secrets: {str(e)}")
            return False

        print()
        print("📋 Secret ARNs for CDK configuration:")
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        print(
            f"Daily API Key: arn:aws:secretsmanager:{aws_region}:{account_id}:secret:{daily_secret_name}"
        )
        print(
            f"AWS Credentials: arn:aws:secretsmanager:{aws_region}:{account_id}:secret:{aws_secret_name}"
        )
        print(
            f"Twilio Credentials: arn:aws:secretsmanager:{aws_region}:{account_id}:secret:{twilio_secret_name}"
        )

        return True

    except Exception as e:
        print(f"✗ Error creating secrets: {str(e)}")
        return False


def list_secrets():
    """List existing Pipecat-related secrets."""

    print("\n" + "=" * 60)
    print("Existing Pipecat Secrets")
    print("=" * 60)

    aws_region = os.getenv("AWS_REGION", "eu-north-1")

    try:
        secrets_client = boto3.client("secretsmanager", region_name=aws_region)

        # List all secrets
        response = secrets_client.list_secrets()

        pipecat_secrets = [
            secret
            for secret in response.get("SecretList", [])
            if secret["Name"].startswith("pipecat/")
        ]

        if not pipecat_secrets:
            print("No Pipecat secrets found.")
            return

        for secret in pipecat_secrets:
            print(f"Name: {secret['Name']}")
            print(f"  ARN: {secret['ARN']}")
            print(f"  Description: {secret.get('Description', 'N/A')}")
            print(f"  Created: {secret.get('CreatedDate', 'N/A')}")
            print(f"  Last Changed: {secret.get('LastChangedDate', 'N/A')}")
            print()

    except Exception as e:
        print(f"✗ Error listing secrets: {str(e)}")


def main():
    """Main function."""

    print(f"AWS Secrets Manager Setup - {datetime.now().isoformat()}")

    # Create secrets
    success = create_secrets()

    # List existing secrets
    list_secrets()

    if success:
        print("\n🎉 Secrets setup completed successfully!")
        print("\nNext steps:")
        print("1. Update your CDK infrastructure to reference these secrets")
        print("2. Deploy the updated infrastructure")
        print("3. Test the ECS deployment with secrets injection")
    else:
        print("\n⚠️  Secrets setup failed. Please check the errors above.")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
