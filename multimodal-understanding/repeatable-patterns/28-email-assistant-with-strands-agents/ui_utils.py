import streamlit as st
from datetime import datetime
import sys
import os
import uuid
import boto3
import json
import re
import time

import base64
from PIL import Image as PILImage 
import io 

from typing import Any, Dict

# Add the src directory to the path
from generate_img_streamlit import generate_img_streamlit
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve, think, editor, http_request


region_name = os.getenv('AWS_REGION')
# Create directory for saved images if it doesn't exist
SAVE_DIR = "generated_images"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

MESSAGE_TYPE_HUMAN = "human"
MESSAGE_TYPE_AI = "ai"
MESSAGE_TYPE_TOOL = "tool"
MESSAGE_TYPE_SYSTEM = "system"

def extract_text_after_thinking(text):
    """
    Extract only the text that appears after the </thinking> tag.
    If no </thinking> tag is found, return the original text.
    
    Args:
        text (str): The text that may contain thinking tags
        
    Returns:
        str: The text after the last </thinking> tag, or the original text if no tag is found
    """
    if not text:
        return text
        
    # Find the position of the last </thinking> tag
    last_thinking_end = text.rfind('</thinking>')
    
    if last_thinking_end != -1:
        # Return everything after the last </thinking> tag
        return text[last_thinking_end + len('</thinking>'):].strip()
    else:
        # If no </thinking> tag is found, return the original text
        return text

def initialize_email_assistant():
    """Initialize the email assistant with conversation history if needed"""
    if "email_conversation" not in st.session_state:
        st.session_state.email_conversation = create_initial_messages()
        email_assistant.messages = st.session_state.email_conversation

def add_message_to_history(message_type, content, metadata=None):
    """
    Add a message to the conversation history with proper typing
    
    Args:
        message_type (str): Type of message (human, ai, tool, system)
        content (str): The message content
        metadata (dict, optional): Additional metadata like image paths, etc.
    """
    if metadata is None:
        metadata = {}
    
    # Create a timestamp for ordering
    timestamp = datetime.now()
    
    # Create the message object
    message = {
        "type": message_type,
        "content": content,
        "timestamp": timestamp,
        "display_time": timestamp.strftime("%H:%M"),
        "metadata": metadata
    }
    
    # Add to session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    st.session_state.messages.append(message)
    
    return message

def add_human_message(content):
    """Add a human message to the conversation history"""
    return add_message_to_history(MESSAGE_TYPE_HUMAN, content)

def add_ai_message(content, image_path=None):
    """Add an AI message to the conversation history"""
    metadata = {}
    if image_path:
        metadata["image_path"] = image_path
    return add_message_to_history(MESSAGE_TYPE_AI, content, metadata)

def add_tool_message(tool_name, content, result=None):
    """Add a tool message to the conversation history"""
    metadata = {
        "tool_name": tool_name
    }
    if result:
        metadata["result"] = result
    return add_message_to_history(MESSAGE_TYPE_TOOL, content, metadata)

def add_system_message(content):
    """Add a system message to the conversation history"""
    return add_message_to_history(MESSAGE_TYPE_SYSTEM, content)

def extract_text_after_thinking(text):
    """
    Extract only the text that appears after the </thinking> tag.
    If no </thinking> tag is found, return the original text.
    
    Args:
        text (str): The text that may contain thinking tags
        
    Returns:
        str: The text after the last </thinking> tag, or the original text if no tag is found
    """
    if not text:
        return text
        
    # Find the position of the last </thinking> tag
    last_thinking_end = text.rfind('</thinking>')
    
    if last_thinking_end != -1:
        # Return everything after the last </thinking> tag
        return text[last_thinking_end + len('</thinking>'):].strip()
    else:
        # If no </thinking> tag is found, return the original text
        return text

def extract_tool_output_from_metrics(response):
    """
    Extract tool output from the metrics in the response or from the response text
    
    Args:
        response (dict): The response from the agent
    
    Returns:
        dict or None: The tool output if found, None otherwise
    """
    try:
        # First try to extract from metrics
        if "metrics" in response:
            # Parse metrics if it's a string
            metrics = response["metrics"]
            if isinstance(metrics, str):
                metrics = json.loads(metrics)
            
            # Look for generate_img_streamlit tool metrics
            if "tool_metrics" in metrics and "generate_img_streamlit" in metrics["tool_metrics"]:
                tool_metric = metrics["tool_metrics"]["generate_img_streamlit"]
                
                # The tool might store output in its response
                if "tool" in tool_metric and "content" in tool_metric["tool"]:
                    content = tool_metric["tool"]["content"]
                    if isinstance(content, list) and len(content) > 0 and "text" in content[0]:
                        text = content[0]["text"]
                        info = extract_info_from_tool_response(text)
                        if "image_path" in info:
                            return {"file_path": info["image_path"]}
        
        # If we couldn't extract from metrics, try to extract from the response text
        if "message" in response and "content" in response["message"]:
            content = response["message"]["content"]
            if content and isinstance(content[0], dict) and "text" in content[0]:
                text = content[0]["text"]
                info = extract_info_from_tool_response(text)
                if "image_path" in info:
                    return {"file_path": info["image_path"]}
        
        return None
    except Exception as e:
        print(f"Error extracting tool output: {str(e)}")
        return None

        
def find_most_recent_image():
    """
    Find the most recently created image in the SAVE_DIR
    
    Returns:
        str or None: Path to the most recent image, or None if no images found
    """
    try:
        SAVE_DIR = "generated_images"  # Make sure this matches your tool's SAVE_DIR
        
        if os.path.exists(SAVE_DIR):
            image_files = [f for f in os.listdir(SAVE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            if image_files:
                # Sort by creation time, newest first
                image_files.sort(key=lambda x: os.path.getctime(os.path.join(SAVE_DIR, x)), reverse=True)
                newest_image = os.path.join(SAVE_DIR, image_files[0])
                
                # Check if the file was created in the last minute
                if time.time() - os.path.getctime(newest_image) < 60:
                    return newest_image
        
        return None
    except Exception as e:
        print(f"Error finding recent images: {str(e)}")
        return None
        

def create_initial_messages():
    return [{
        "role": "user",
        "content": [{"text": "Hello, I need help writing an email."}]
    }, {
        "role": "assistant",
        "content": [{"text": "I'm ready to help you write a professional email using web research, audio context, and images as needed. Please describe what kind of email you'd like to create."}]
    }]


# Create Image generation agent
image_agent_instance = Agent(
    system_prompt= """You are an AI assistant that can generate images and save them to files.
    You can:
    1. Generate images using the generate_img_streamlit tool
    2. Save files using the generate_img_streamlit tool
    
    When users want to:
    - Generate an image: Use generate_img_streamlit
    - Save the generated image: Use file_write to save it
    - Both: First generate, then save the image
    
    Always confirm actions and provide clear feedback about what was done.""",
    tools=[generate_img_streamlit]
)            

@tool
def handle_img_generation_request(user_message):
    return image_agent_instance(user_message)

@tool
def handle_RAG_request(user_query):

    # Create agent with Nova Pro model configuration
    agent_config = {
        "system_prompt": """You are a knowledgeable AI assistant. Analyze the retrieved information and provide comprehensive answers.
        Focus on accuracy and clarity in your responses.""",
        "model": BedrockModel(
            model_id="us.amazon.nova-pro-v1:0",
            region=region_name
        ),
        "tools": [retrieve, think]
    }
            
    try:
        # Direct call to retrieve.retrieve method
        retrieve_tool_response = retrieve.retrieve({
            "toolUseId": str(uuid.uuid4()),
            "input": {
                "text": user_query,
                "score": 0.4,
                "numberOfResults": 5
            }
        })
        
        retrieve_response = retrieve_tool_response
    
        if retrieve_tool_response["status"] == "success":
            
            retrieved_text = retrieve_tool_response["content"][0]["text"]
            
            # Extract just the S3 information
            s3_info = extract_s3_info(retrieved_text)
            
            # Create and invoke agent with the messages
            RAG_agent = Agent(
                messages=[{
                    "role": "user",
                    "content": [{"text": agent_config["system_prompt"]+f"""Here is the retrieved information:{retrieved_text}, Please analyze this information and provide insights about: {user_query}"""}]
                }],
                model=agent_config["model"],
                tools=agent_config["tools"]
            )
            
            # Get agent response
            agent_response = RAG_agent(user_query)                
        else:
            add_system_message("No relevant information found in the knowledge base.")

        return retrieve_response, agent_response, s3_info
            
    except Exception as e:
        error_msg = f"Error with Audio RAG: {str(e)}"
        print(error_msg)
        add_system_message(error_msg)
        return None, None, None





# Create the email assistant agent with Nova Pro model
email_assistant = Agent(
    system_prompt="""You are a professional email writing assistant that can leverage audio RAG and image generation capabilities. 
    You have access to two main tools:

    IMPORTANT: Only generate and add an image if you asked to do so.
    
    1. Research tools:
       - handle_RAG_request for retrieving relevant audio context and general web search
       
    2. Creative tools:
       - handle_img_generation_request for generating relevant images
       - editor for writing and formatting
    
    Follow these steps for each email request:
    
    STEP 1 - ANALYZE REQUEST:
    - Determine if audio context is needed -> Use handle_RAG_request
    - Determine if images are needed -> Use handle_img_generation_request
    - Plan web research needs -> Use handle_RAG_request
    
    STEP 2 - GATHER ALL RESOURCES:
    - Execute RAG queries if audio context needed
    - Request image generation if visuals needed
    - Perform web research for additional context
    
    STEP 3 - CONTENT CREATION:
    - Synthesize all gathered information
    - Use editor to draft email incorporating:
        * Audio context from RAG
        * Generated images
        * Web research findings
    
    STEP 4 - FORMATTING AND REVIEW:
    - Format email with proper structure
    - Include references to multimedia content
    - Ensure professional tone and accuracy""",
    model=BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region=region_name
    ),
    tools=[
        editor, 
     #   http_request, 
        handle_RAG_request,  # Your existing RAG agent
        handle_img_generation_request     # Your existing image generation agent
        #web_researcher
    ]
)

# Initialize messages
email_assistant.messages = create_initial_messages()
    
def call_agent(query, selected_agent):
    """
    Process user query using the selected agent
    
    Returns:
        tuple: (s3_info, img_response, retrieve_response, agent_response, metrics_data)
            - s3_info: S3 bucket and key information if available
            - img_response: Image generation response if available
            - retrieve_response: Knowledge retrieval response if available
            - agent_response: The main agent response (RAG, Image, or Email)
            - metrics_data: Metrics data for debugging
    """
    s3_info = None
    img_response = None
    retrieve_response = None
    agent_response = None
    metrics_data = None
    email_agent_response = None

    # Handle Email Assistant Agent
    if selected_agent == 'Email assistant agent':
        
        try:
            # Create the user message with proper Nova format
            user_message = {
                "role": "user",
                "content": [{"text": query}]
            }

            # Add message to conversation
            email_assistant.messages.append(user_message)

            #st.write(user_message)
            #st.write(handle_RAG_request)
            
            # Get response
            email_agent_response = email_assistant(user_message["content"][0]["text"])
            print(f"\nEmail Generated:\n{email_agent_response}\n")

            # Store metrics for the expander
            if isinstance(email_agent_response, dict) and "metrics" in email_agent_response:
                metrics_data = email_agent_response["metrics"]

            # Print response

            email_response = email_agent_response.message
                   
            if email_response and "content" in email_response and len(email_response["content"]) > 0:
                if isinstance(email_response["content"][0], dict) and "text" in email_response["content"][0]:
                    ai_response_text = email_response["content"][0]["text"]

                    # Clean the response text to remove thinking tags
                    ai_response_text = extract_text_after_thinking(ai_response_text)

                    # Add the assistant's response to the conversation history
                    assistant_message = {
                        "role": "assistant",
                        "content": [{"text": ai_response_text}]
                    }
                    # Update the conversation history
                    email_assistant.messages.append(assistant_message)
                
                    # Add to the UI message history
                    add_ai_message(ai_response_text)
                else:
                    add_system_message(f"Unexpected response format: {email_agent_response}")

        except Exception as e:
            error_msg = f"Error email agent: {str(e)}\n"
            print(error_msg)
            add_system_message(error_msg)


    # Handle Image Agent
    elif selected_agent == 'Image agent':
        try:
            img_response = handle_img_generation_request(query)
            agent_response = img_response  # Set agent_response to img_response

            # Store metrics for the expander
            if isinstance(img_response, dict) and "metrics" in img_response:
                metrics_data = img_response["metrics"]
                           
        except Exception as e:
            error_msg = f"Error with Image Agent: {str(e)}"
            print(error_msg)
            add_system_message(error_msg)


    # Handle Audio RAG Agent
    elif selected_agent == 'Audio RAG':  
        
        retrieve_response, agent_response, s3_info = handle_RAG_request(query)
    
        # Store metrics for the expander
        if isinstance(agent_response, dict) and "metrics" in agent_response:
            metrics_data = agent_response["metrics"]

        # Print response
        if isinstance(agent_response, dict) and "message" in agent_response:
            ai_response_text = agent_response["message"]["content"][0]["text"]
           
            # Add tool message for retrieval
            add_tool_message(
                "Knowledge Retrieval", 
                f"Retrieved information related to: '{user_query}'",
                f"Found {len(retrieve_tool_response['content'])} relevant documents"
            )
            add_ai_message(ai_response_text)
        else:
            # Don't display error message to user when switching agents
            print(f"Debug: Unexpected response format: {agent_response}")
            
    # Default case if agent not recognized
    else:
        add_system_message(f"Agent '{selected_agent}' not recognized.")
        
    return s3_info, img_response, retrieve_response, agent_response, email_agent_response, metrics_data

def extract_info_from_tool_response(response_text):
    """
    Extract image paths and S3 info from tool response text
    
    Args:
        response_text (str): The response text from a tool
        
    Returns:
        dict: Dictionary with extracted information
    """
    result = {}
    
    # Extract image path
    image_match = re.search(r"Image (?:saved to|path): (.+\.png)", response_text)
    if image_match:
        result["image_path"] = image_match.group(1)
    
    # Extract S3 info
    s3_match = re.search(r"Audio source: Bucket: ([^,]+), Key: (.+)", response_text)
    if s3_match:
        result["s3_info"] = {
            "bucket": s3_match.group(1),
            "key": s3_match.group(2)
        }
    
    return result

def clean_email_conversation():
    """
    Create a clean initial conversation for the email assistant
    """
    return [
        {
            "role": "user",
            "content": [{"text": "Hello, I need help writing an email."}]
        },
        {
            "role": "assistant",
            "content": [{"text": "I'm ready to help you write a professional email using web research, audio context, and images as needed. Please describe what kind of email you'd like to create."}]
        }
    ]


def extract_s3_info(retrieved_text):
    """
    Extract just the S3 bucket and key information from the retrieved text
    """
    try:
        # Look for metadata section containing s3_bucket and s3_key
        metadata_pattern = re.compile(r'"metadata":\s*{[^}]*"s3_bucket":\s*"([^"]+)",[^}]*"s3_key":\s*"([^"]+)"')
        
        # Find the match in the text
        match = metadata_pattern.search(retrieved_text)
        
        if match:
            s3_bucket = match.group(1)
            s3_key = match.group(2)
            
            print("\nExtracted S3 Info:")
            print(f"Bucket: {s3_bucket}")
            print(f"Key: {s3_key}")
            
            return {
                'bucket': s3_bucket,
                'key': s3_key
            }
            
        else:
            print("Could not find S3 bucket and key information in the text")
            return None
            
    except Exception as e:
        print(f"Error extracting S3 info: {str(e)}")
        return None

