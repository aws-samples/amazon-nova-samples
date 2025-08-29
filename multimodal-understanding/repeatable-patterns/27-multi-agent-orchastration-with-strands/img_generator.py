from IPython.display import Image, display
import io
import os
import re
import base64
import json
import boto3
import sagemaker
from datetime import datetime
from typing import Any, Union, Dict, Set, List, TypedDict, Annotated
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve, editor, http_request

# Create directory for saved images if it doesn't exist
SAVE_DIR = "generated_images"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()["Account"]
session = sagemaker.Session()

aws_region = boto3.session.Session().region_name

@tool
def img_creator(prompt: str, img_model: str = "amazon.nova-canvas-v1:0", number_of_images: int = 1) -> str:
    """Generates an image using Amazon Bedrock Nova Canvas model based on a given prompt and saves it to a file
    
    Args:
        prompt: The text prompt for image generation
        model_id: Model id for image model, default is amazon.nova-canvas-v1:0
        number_of_images: Number of images to generate (default: 1)
    """
    try:
        # Create a Bedrock Runtime client
        client = boto3.client("bedrock-runtime", region_name=aws_region)

        # Enhanced prompt
        enhanced_prompt = f"Generate a high resolution, photo realistic picture of {prompt} with vivid color and attending to details."

        # Format the request payload
        request_payload = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": enhanced_prompt
            },
            "imageGenerationConfig": {
                "numberOfImages": number_of_images
            }
        }

        # Invoke the model
        response = client.invoke_model(
            body=json.dumps(request_payload),
            modelId=img_model,
            accept="application/json",
            contentType="application/json"
        )

        # Parse the response
        response_body = json.loads(response["body"].read())
        base64_image = response_body.get("images")[0]
        
        # Decode the image
        image_bytes = base64.b64decode(base64_image.encode('ascii'))
        
        # Create filename with timestamp and sanitized prompt
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize prompt for filename
        safe_prompt = re.sub(r'[^a-zA-Z0-9]', '_', prompt[:30])  # Take first 30 chars
        filename = f"{SAVE_DIR}/nova_{safe_prompt}_{timestamp}.png"
        
        # Save the image
        with open(filename, "wb") as f:
            f.write(image_bytes)
        return f"✨ Generated image for prompt: '{prompt}'\nImage saved to: {filename}"
       
    except Exception as e:
        return f"❌ Error generating image: {str(e)}"
