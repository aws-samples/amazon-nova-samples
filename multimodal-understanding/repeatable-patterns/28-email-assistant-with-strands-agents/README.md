# Email assistant with Strands Agents SDK 

## Overview

This notebook demonstrates how to create an email assistant using the Strands Agents SDK, featuring a user-friendly Streamlit interface. The system comprises multiple specialized agents working together to deliver comprehensive email assistance.

## Available Agents

### 1. Image Agent
- AI-powered image generation
- File management capabilities 
- Creates images based on user descriptions

### 2. Audio RAG (Retrieval-Augmented Generation)
- Specialized knowledge base for audio content, created using Bedrock Data Automation (BDA) as parser
- Sources information from Amazon earnings call recordings
- Answers queries about audio content

### 3. Email Assistant Agent
- Creates professional emails using multiple tools and agent integrations
- Features:
  - Web resource search
  - Audio context retrieval (via Audio RAG)
  - Image generation integration
  - Professional email composition

### 4. Report Writing Agent
- Handles systematic planning and writing of reports

## Project Structure

The implementation consists of three main files:
- `app.py`: Main Streamlit user interface
- `generate_img_streamlit.py`: Image generation tool using Nova Canvas model
- `ui_utils.py`: Contains core functionality including:
  - Strands tools
  - Agent definitions
  - Helper functions

This multi-agent system is designed to provide comprehensive, context-aware responses by leveraging the strengths of each specialized agent.

## Pre-requisite

**Important:** Before running this notebook, you need to create a Bedrock knowledge base for audio files. Please complete the setup by running notebooks 1-2 in the `audio-video-rag` folder.