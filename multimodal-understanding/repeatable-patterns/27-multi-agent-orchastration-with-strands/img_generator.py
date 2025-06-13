from IPython.display import Image, display
import io
import os
import re
import base64
import json
import boto3
import sagemaker
from datetime import datetime
from typing import Any, Dict
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve, think, editor, http_request

# Create directory for saved images if it doesn't exist
SAVE_DIR = "generated_images"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)


sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()["Account"]
session = sagemaker.Session()

aws_region = boto3.session.Session().region_name



def img_creator(tool: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """
    Generate an image using Nova Canvas model and save it to a file
    """
    try:
        tool_use_id = tool["toolUseId"]
        tool_input = tool["input"]
        filename = None

        # Extract input parameters
        prompt = tool_input.get("prompt", "A high resolution, photo realistic picture")
        model_id = tool_input.get("model_id", "amazon.nova-canvas-v1:0")
        number_of_images = tool_input.get("number_of_images", 1)

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
            modelId=model_id,
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
        try:
            with open(filename, "wb") as f:
                f.write(image_bytes)
            save_message = f"✨ Generated image for prompt: '{prompt}'\nImage saved to: {filename}"
       
        except Exception as save_error:
            save_message = f"✨ Generated image for prompt: '{prompt}'\nFailed to save image: {str(save_error)}"
                
        

        # Return the result in the correct format
        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [
                {
                    "text": save_message
                }
            ]
        }


    except Exception as e:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [
                {
                    "text": f"❌ Error generating image: {str(e)}"
                }
            ]
        }




img_creator.TOOL_SPEC = {
    "name": "img_creator",
    "description": "Generates an image using Amazon Bedrock Nova Canvas model based on a given prompt and saves it to a file",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The text prompt for image generation",
                },
                "model_id": {
                    "type": "string",
                    "description": "Model id for image model, amazon.nova-canvas-v1:0",
                },
                "number_of_images": {
                    "type": "integer",
                    "description": "Optional: Number of images to generate (default: 1)",
                }
            },
            "required": ["prompt"],
        }
    },
}
