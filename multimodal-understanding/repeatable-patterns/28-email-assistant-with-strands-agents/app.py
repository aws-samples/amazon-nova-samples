import streamlit as st
from datetime import datetime
import time
import sys
import os
import uuid
import boto3
import json
import re

import base64
from PIL import Image as PILImage 
import io
from ui_utils import *

import base64
from pathlib import Path


# Add this function to app.py
def display_chat():
    """Display the chat interface"""
    # Display chat history
    display_chat_history()
    
    # Handle new user input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat history
        add_human_message(prompt)
        
        # Display the updated chat with the new user message
        st.rerun()
    
    # Process the AI's response if the last message is from the user
    if (st.session_state.messages and 
        st.session_state.messages[-1]["type"] == MESSAGE_TYPE_HUMAN):
        
        user_prompt = st.session_state.messages[-1]["content"]
        

def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded
    
def img_to_html(img_path):
    img_html = "<img src='data:image/png;base64,{}' class='img-fluid'>".format(
    img_to_bytes(img_path)
    )
    return img_html

def display_chat_history():
    """Display the chat history in a structured way"""
    chat_container = st.container()
    
    with chat_container:
        # Sort messages by timestamp to ensure correct order
        messages = sorted(st.session_state.messages, key=lambda x: x["timestamp"])
        
        for message in messages:
            
            message_type = message["type"]
            content = message["content"]
            metadata = message.get("metadata", {})
            
            if message_type == MESSAGE_TYPE_HUMAN:
                with st.chat_message("user"):
                    st.write(content)
            
            elif message_type == MESSAGE_TYPE_AI:
                with st.chat_message("assistant"):
                    st.write(content)
                    
                    # If this message has an image path, display the image
                    if "image_path" in metadata and metadata["image_path"]:
                        image_path = metadata["image_path"]
                        if os.path.exists(image_path):
                            # Display the image
                            st.image(
                                image_path,
                                caption="Generated Image",
                                use_container_width=True
                            )
                            
                            # Add a download button
                            with open(image_path, "rb") as file:
                                st.download_button(
                                    label="Download Image",
                                    data=file,
                                    file_name=os.path.basename(image_path),
                                    mime="image/png",
                                    key=f"download_btn_chat_{message['timestamp'].timestamp()}"  # Add this line
                                )
            
            elif message_type == MESSAGE_TYPE_TOOL:
                with st.chat_message("assistant", avatar="🔧"):
                    tool_name = metadata.get("tool_name", "Tool")
                    st.write(f"**{tool_name}**: {content}")
                    
                    # If there's a result, show it
                    if "result" in metadata:
                        st.code(metadata["result"])
            
            elif message_type == MESSAGE_TYPE_SYSTEM:
                st.info(content)


st.set_page_config(
    layout="wide"
    #initial_sidebar_state="collapsed"
)
st.title("\n🔍 Knowledge Base Query System\n")  # Title of the application

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add initial welcome message
    add_ai_message("How can I help you?")

# Sidebar for agent selection
st.sidebar.header("Agent Selection")

# Set default agent to "Audio RAG"
if "selected_agent" not in st.session_state:
    st.session_state.selected_agent = "Audio RAG"

# List of available agents
agents = [
    "Audio RAG",
    "Image agent",
    "Email assistant agent"
]

# Dropdown to select agent
selected_agent = st.sidebar.selectbox(
    "Choose an agent:",
    agents,
    index=agents.index(st.session_state.selected_agent)
)

# Check if agent was changed
if selected_agent != st.session_state.selected_agent:
    old_agent = st.session_state.selected_agent
    st.session_state.selected_agent = selected_agent
 
    # If switching to or from Email assistant, handle conversation reset
    if selected_agent == "Email assistant agent" or old_agent == "Email assistant agent":
        # Reset the email assistant when switching to it
        if selected_agent == "Email assistant agent":
            email_assistant.messages = create_initial_messages()
 
    add_system_message(f"Switched to {selected_agent}")

# Additional sidebar options
st.sidebar.divider()

# Display usage instructions based on selected agent
if selected_agent == "Image agent":
    st.sidebar.subheader("🎨 AI Image Generator and File Manager 🖼️")
    st.sidebar.markdown("**Commands:**")
    st.sidebar.markdown("- Generate image: describe what you want to see")
    st.sidebar.markdown("- Save image: ask to save the last generated image")
    st.sidebar.divider()
elif selected_agent == "Audio RAG":
    st.sidebar.subheader("🔍 Audio Knowledge Base")
    st.sidebar.markdown("Ask questions about audio content in the knowledge base.")
    st.sidebar.divider()
elif selected_agent == "Email assistant agent":
    st.sidebar.subheader("✉️ Enhanced Email Assistant with RAG and Image Generation ✉️")
    st.sidebar.markdown("This assistant can:")
    st.sidebar.markdown("- Search web resources")
    st.sidebar.markdown("- Retrieve relevant audio context")
    st.sidebar.markdown("- Generate appropriate images")
    st.sidebar.markdown("- Create professional emails")

    # Add a button to reset the email conversation
    if st.sidebar.button("Reset Email Conversation"):
        try:
            st.session_state.email_conversation = clean_email_conversation()
            email_assistant.messages = st.session_state.email_conversation.copy()
            add_system_message("Email conversation has been reset")
            st.rerun()
        except Exception as e:
            st.error(f"Error resetting email conversation: {str(e)}")
            st.exception(e)

# Clear chat button
if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []
    # Reset email conversation if it exists
    if "email_conversation" in st.session_state:
        st.session_state.email_conversation = create_initial_messages()
        email_assistant.messages = st.session_state.email_conversation
    # Re-add welcome message after clearing
    add_ai_message("How can I help you?")
    st.rerun()

# Display the chat interface
display_chat_history()

# Handle new user input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    add_human_message(prompt)
    
    # Display the updated chat with the new user message
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["type"] == MESSAGE_TYPE_HUMAN:
    user_prompt = st.session_state.messages[-1]["content"]
    
    # Process the AI's response
    with st.chat_message("assistant"):
        try:
            # Create a container for the streaming response
            response_container = st.container()
            
            with response_container:
                # Show loading spinner while processing
                with st.spinner("Thinking..."):
                    # Process the user's message
                    s3_info, img_response, retrieve_response, agent_response, email_agent_response, metrics = call_agent(user_prompt, selected_agent)
                    
                if selected_agent == "Email assistant agent":

                    email_response = email_agent_response.message

                    if email_response and "content" in email_response and len(email_response["content"]) > 0:
                        if isinstance(email_response["content"][0], dict) and "text" in email_response["content"][0]:
                            email_text = email_response["content"][0]["text"]
                                   
                            # Clean the response text to remove thinking tags
                            clean_email_text = extract_text_after_thinking(email_text)
                              
                            # Create a pattern that matches both markdown images and direct image paths
                            pattern = r'(!\[(.*?)\]\((generated_images.+?\.png)\))|(generated_images\S+\.png)'
                            
                            # Find all matches (both markdown images and direct paths)
                            matches = re.finditer(pattern, clean_email_text)
                            
                            # If no matches, just display the text
                            if not re.search(pattern, clean_email_text):
                                st.markdown(clean_email_text, unsafe_allow_html=True)
                            else:
                                # Split the text by all image references and process each part
                                last_end = 0
                                for match in matches:
                                    # Display text before the image
                                    if match.start() > last_end:
                                        st.markdown(clean_email_text[last_end:match.start()], unsafe_allow_html=True)
                                    
                                    # Determine the image path
                                    if match.group(1):  # Markdown image
                                        image_path = match.group(3)
                                    else:  # Direct path
                                        image_path = match.group(0)
                                    
                                    # Display the image if it exists
                                    if os.path.exists(image_path):
                                        img = PILImage.open(image_path)
                                        st.image(img, width=400)
                                    
                                    # Update the last position
                                    last_end = match.end()
                                
                                # Display any remaining text after the last image
                                if last_end < len(clean_email_text):
                                    st.markdown(clean_email_text[last_end:], unsafe_allow_html=True)

                # Handle image response
                elif (img_response and selected_agent == "Image agent"):

                    # st.write("img_response")
                    # st.write(img_response)
                    # st.write("agent_response.message")
                    # st.write(agent_response.message)
                    

                    #img_response = agent_response.message
                   
                    if img_response and "content" in img_response and len(img_response["content"]) > 0:
                        if isinstance(img_response["content"][0], dict) and "text" in img_response["content"][0]:
                            txt_msg = img_response["content"][0]["text"]
                    
                    with st.container():
                        st.write(txt_msg)
                    
                    # First try to extract tool output from metrics
                    tool_output = extract_tool_output_from_metrics(img_response)
                    
                    image_displayed = False
                    image_path = None
                    
                    if tool_output and isinstance(tool_output, dict) and "file_path" in tool_output:
                        # Get the file path from tool output
                        image_path = tool_output["file_path"]

                        st.write(image_path)
                        
                        if os.path.exists(image_path):
                            # Display the image
                            st.image(
                                image_path,
                                caption="Generated Image",
                                use_container_width=True
                            )
                            
                            # Add a download button
                            with open(image_path, "rb") as file:
                                st.download_button(
                                    label="Download Image",
                                    data=file,
                                    file_name=os.path.basename(image_path),
                                    mime="image/png",
                                    key=f"download_btn_response_1" 
                                )
                            
                            # Show the file path
                            st.success(f"Image saved to: {image_path}")
                            image_displayed = True
                    
                    # If we couldn't get the image from tool output, try to find the most recent image
                    if not image_displayed:
                        recent_image_path = find_most_recent_image()
                        
                        if recent_image_path:
                            image_path = recent_image_path
                            # Display the image
                            st.image(
                                recent_image_path,
                                caption="Generated Image",
                                use_container_width=True
                            )

                            # Add a download button
                            with open(recent_image_path, "rb") as file:
                                st.download_button(
                                    label="Download Image",
                                    data=file,
                                    file_name=os.path.basename(recent_image_path),
                                    mime="image/png"
                                )
                            
                            image_displayed = True
                    
                    # If we still couldn't display an image, show an error
                    if not image_displayed:
                        st.warning("Could not find the generated image. The image may have been generated but couldn't be displayed.")
                    
                    # Add the response to the conversation history with the image path
                    add_ai_message(txt_msg, image_path)
                    
                    # Add a tool message for the image generation
                    add_tool_message(
                        "Image Generator", 
                        f"Generated image for prompt: '{user_prompt}'",
                        f"Image saved to: {image_path}" if image_path else "Image generation completed"
                    )
                
                # Display audio player if S3 info is available
                elif selected_agent == "Audio RAG":
                    
                    agent_message = agent_response.message
                   
                    if agent_message and "content" in agent_message and len(agent_message["content"]) > 0:
                        if isinstance(agent_message["content"][0], dict) and "text" in agent_message["content"][0]:
                            txt_msg = agent_message["content"][0]["text"]
                            with st.container():
                                st.write(txt_msg)

                        if s3_info:
                            # Streamlit native audio player
                            try:
                                st.subheader("Play audio file")
                                s3_client = boto3.client('s3')
                                url = s3_client.generate_presigned_url(
                                    'get_object',
                                    Params={
                                        'Bucket': s3_info['bucket'],
                                        'Key': s3_info['key']
                                    },
                                    ExpiresIn=3600
                                )
        
                                st.audio(url)
        
                                # Add a tool message for the audio retrieval
                                add_tool_message(
                                    "Audio Player", 
                                    f"Retrieved audio file from knowledge base",
                                    f"Bucket: {s3_info['bucket']}, Key: {s3_info['key']}"
                                )
                                
                            except Exception as e:
                                st.error(f"Error with fallback player: {str(e)}")
                                st.exception(e)
                
                # Display expanders if we have responses
                with st.expander("Retrieved Details", expanded=False):
                    if retrieve_response is not None and retrieve_response != "":
                        st.write(retrieve_response)
    
                with st.expander("Agent Response Details", expanded=False):
                    if agent_response is not None and agent_response != "":
                        st.write(agent_response)
    
                with st.expander("Metrics", expanded=False):
                    if metrics is not None and metrics != "":
                        st.write(metrics)
               
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.exception(e)
            add_system_message(f"Error: {str(e)}")
    
    
