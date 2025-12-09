"""
AWS SageMaker/Bedrock Proxy for Synthetic Data Kit
Supports both SageMaker endpoints and Bedrock models
Uses AWS credentials from default profile, environment variables, or IAM roles
Compatible with standard AWS credential chain
"""
from flask import Flask, request, jsonify
import boto3
import json
import logging
import argparse
import subprocess
from botocore.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration defaults (can be overridden via CLI arguments)
PLATFORM = None  # 'sm' for SageMaker or 'br' for Bedrock
ENDPOINT_NAME = None  # Required for SageMaker
MODEL_ID = None  # Required for Bedrock
REGION = 'us-east-1'
PROFILE = None  # Optional - uses default if not specified

def create_sagemaker_client():
    """
    Create SageMaker client using AWS credential chain:
    1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    2. AWS CLI profile (aws configure)
    3. IAM role (if running on EC2/ECS/Lambda)
    """
    try:
        session_kwargs = {'region_name': REGION}
        if PROFILE:
            session_kwargs['profile_name'] = PROFILE
        
        session = boto3.Session(**session_kwargs)
        client = session.client('sagemaker-runtime')
        
        # Test credentials by getting caller identity
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        logger.info(f"Authenticated as: {identity['Arn']}")
        
        return client
    except Exception as e:
        logger.error(f"Failed to create SageMaker client: {e}")
        logger.error("Make sure AWS credentials are configured:")
        logger.error("  - Run 'aws configure' to set up credentials")
        logger.error("  - Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        logger.error("  - Or run on EC2/ECS with IAM role")
        raise

def create_bedrock_client():
    """
    Create Bedrock client using AWS credential chain
    """
    try:
        session_kwargs = {'region_name': REGION}
        if PROFILE:
            session_kwargs['profile_name'] = PROFILE
        
        session = boto3.Session(**session_kwargs)
        client = session.client('bedrock-runtime')
        
        # Test credentials
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        logger.info(f"Authenticated as: {identity['Arn']}")
        
        return client
    except Exception as e:
        logger.error(f"Failed to create Bedrock client: {e}")
        logger.error("Make sure AWS credentials are configured")
        raise


# Initialize runtime clients
sagemaker_runtime = None
bedrock_runtime = None

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """
    Handle chat completion requests in OpenAI format
    Support both SageMaker and Bedrock platforms
    Auto-refreshes credentials if expired
    """
    global sagemaker_runtime, bedrock_runtime
    
    try:
        data = request.json
        logger.info(f"Received request for platform: {PLATFORM}")
        
        # Extract parameters
        messages = data.get('messages', [])
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 2048)
        top_p = data.get('top_p', 0.95)
        
        if PLATFORM == 'sm':
            # SageMaker endpoint
            if sagemaker_runtime is None:
                sagemaker_runtime = create_sagemaker_client()
            
            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p
            }
            
            logger.info(f"Invoking SageMaker endpoint: {ENDPOINT_NAME}")
            logger.info(f"Payload: {payload}")
            
            try:
                response = sagemaker_runtime.invoke_endpoint(
                    EndpointName=ENDPOINT_NAME,
                    ContentType='application/json',
                    Body=json.dumps(payload)
                )
            except Exception as e:
                if 'ExpiredToken' in str(e) or 'expired' in str(e).lower():
                    logger.warning("Credentials expired, refreshing...")
                    sagemaker_runtime = create_sagemaker_client()
                    response = sagemaker_runtime.invoke_endpoint(
                        EndpointName=ENDPOINT_NAME,
                        ContentType='application/json',
                        Body=json.dumps(payload)
                    )
                else:
                    raise
            
            result = json.loads(response['Body'].read().decode())
            
        elif PLATFORM == 'br':
            # Bedrock model
            if bedrock_runtime is None:
                bedrock_runtime = create_bedrock_client()
            
            # message normalization for Nova via Converse in Bedrock 
            bedrock_messages = []
            for msg in messages:
                # 1. Force all roles to 'user' if not already
                role = msg["role"] if msg["role"] == "user" else "user"
                
                # 2. If content is string, wrap it in format
                content = msg["content"]
                if isinstance(content, str):
                    content = [{"text": content}]
                
                bedrock_messages.append({
                    "role": role,
                    "content": content
                })

            # Use in payload
            payload = {
                "modelId": MODEL_ID,
                "messages": bedrock_messages,
                "inferenceConfig": {
                    "temperature": temperature,
                    "maxTokens": max_tokens,
                    "topP": top_p
                }
            }
            
            logger.info(f"Invoking Bedrock model: {MODEL_ID}")
            logger.info(f"Payload: {payload}")
            
            try:
                response = bedrock_runtime.converse(**payload)
            except Exception as e:
                if 'ExpiredToken' in str(e) or 'expired' in str(e).lower():
                    logger.warning("Credentials expired, refreshing...")
                    bedrock_runtime = create_bedrock_client()
                    response = bedrock_runtime.converse(**payload)
                else:
                    raise
            
            # Convert Bedrock response to OpenAI format
            # Extract the text from Bedrock's response structure
            bedrock_content = response['output']['message']['content']
            response_text = bedrock_content[0]['text'] if bedrock_content else ""
            
            result = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    }
                }]
            }
        else:
            return jsonify({"error": f"Unknown platform: {PLATFORM}"}), 400
        
        logger.info("Successfully received response")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    health_info = {
        "status": "healthy",
        "platform": PLATFORM,
        "region": REGION,
        "profile": PROFILE or "default"
    }
    if PLATFORM == 'sm':
        health_info["endpoint"] = ENDPOINT_NAME
    else:
        health_info["model_id"] = MODEL_ID
    return jsonify(health_info)

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with proxy information"""
    info = {
        "service": "AWS SageMaker/Bedrock Proxy",
        "description": "OpenAI-compatible proxy for SageMaker endpoints and Bedrock models",
        "platform": PLATFORM,
        "region": REGION,
        "profile": PROFILE or "default",
        "api_endpoints": {
            "chat_completions": "/v1/chat/completions",
            "health": "/health"
        },
        "usage": {
            "sagemaker": "python aws_proxy.py --platform sm --endpoint YOUR_ENDPOINT",
            "bedrock": "python aws_proxy.py --platform br --model-id MODEL_ID",
            "test_health": "curl http://localhost:8000/health"
        }
    }
    if PLATFORM == 'sm':
        info["endpoint"] = ENDPOINT_NAME
    else:
        info["model_id"] = MODEL_ID
    return jsonify(info)

if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='AWS SageMaker/Bedrock Proxy Server for Synthetic Data Kit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # SageMaker with default AWS credentials
  python aws_proxy.py --platform sm --endpoint my-llama-endpoint
  
  # Bedrock with specific model
  python aws_proxy.py --platform br --model-id anthropic.claude-3-sonnet-20240229-v1:0
  
  # SageMaker with specific AWS profile
  python aws_proxy.py --platform sm --endpoint my-endpoint --profile myprofile
  
  # Bedrock with specific region
  python aws_proxy.py --platform br --model-id amazon.nova-lite-v1:0 --region us-west-2
  
  # Custom port
  python aws_proxy.py --platform sm --endpoint my-endpoint --port 8080

Prerequisites:
  - Configure AWS credentials: aws configure
  - Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
  - Or run on EC2/ECS with IAM role
  
  Install dependencies: pip install flask boto3
        """
    )
    
    parser.add_argument(
        '--platform',
        required=True,
        choices=['sm', 'br'],
        help='Platform: "sm" for SageMaker, "br" for Bedrock (required)'
    )
    parser.add_argument(
        '--endpoint',
        default=None,
        help='SageMaker endpoint name (required when --platform sm)'
    )
    parser.add_argument(
        '--model-id',
        default=None,
        help='Bedrock model ID (required when --platform br)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--profile',
        default=None,
        help='AWS CLI profile name (optional, uses default if not specified)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Server port (default: 8000)'
    )
    
    args = parser.parse_args()
    
    # Validate platform-specific requirements
    if args.platform == 'sm' and not args.endpoint:
        parser.error("--endpoint is required when --platform is 'sm'")
    if args.platform == 'br' and not args.model_id:
        parser.error("--model-id is required when --platform is 'br'")
    
    # Set global configuration from arguments
    PLATFORM = args.platform
    ENDPOINT_NAME = args.endpoint
    MODEL_ID = args.model_id
    REGION = args.region
    PROFILE = args.profile
    
    platform_name = "SageMaker" if PLATFORM == 'sm' else "Bedrock"
    logger.info("=" * 60)
    logger.info(f"AWS {platform_name} Proxy Server")
    logger.info("=" * 60)
    logger.info(f"  Platform: {platform_name}")
    if PLATFORM == 'sm':
        logger.info(f"  Endpoint: {ENDPOINT_NAME}")
    else:
        logger.info(f"  Model ID: {MODEL_ID}")
    logger.info(f"  Region: {REGION}")
    logger.info(f"  Profile: {PROFILE or 'default'}")
    logger.info(f"  Port: {args.port}")
    logger.info("=" * 60)
    
    # Test credentials on startup
    try:
        if PLATFORM == 'sm':
            create_sagemaker_client()
        else:
            create_bedrock_client()
        logger.info("✓ AWS credentials verified")
    except Exception as e:
        logger.error(f"✗ Failed to verify credentials: {e}")
        logger.error("Please configure AWS credentials before starting the proxy")
        exit(1)
    
    logger.info(f"Starting server on http://localhost:{args.port}")
    logger.info("Press Ctrl+C to stop")
    
    app.run(host='0.0.0.0', port=args.port, debug=False)
