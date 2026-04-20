# Getting Started with Amazon Nova Act

## Overview
This tutorial introduces Amazon Nova Act (research preview), a Python SDK for building agents that reliably take actions in web browsers. You'll learn basic setup, API usage, and create your first automation script.

## Learning Objectives
- Install and set up Amazon Nova Act
- Create your first automation script
- Understand basic Nova Act API concepts
- Extract structured data from web pages
- Build multi-step automation workflows

## Prerequisites
**⚠️ Complete the centralized setup first!**
- Complete setup in `../00-setup/` (see [Setup Guide](../00-setup/README.md))
- Python 3.10 or higher
- Amazon Nova Act API key
- Basic Python programming knowledge

## What You'll Build
Automation scripts that navigate websites and extract information using natural language commands.

## Quick Start
```bash
# 1. Complete setup (one-time)
cd ../00-setup && ./setup.sh

# 2. Activate environment
source ../00-setup/venv/bin/activate

# 3. Run tutorial
python 1_getting_started.py
```

## Key Concepts

### NovaAct Class
Main interface to the SDK. Creates browser sessions and handles automation.

### act() Method
Natural language interface for browser actions. Takes a prompt describing what to do and optionally a schema for structured responses.

### Structured Data Extraction
Use Pydantic models to extract specific information from web pages in a structured format.

### Best Practices
- Be prescriptive and succinct in prompts
- Break large tasks into smaller steps
- Use separate act() calls for different actions
- Don't mix actions and data extraction in one call

## What This Tutorial Covers
The `1_getting_started.py` script demonstrates:
- Installation verification
- API key validation
- Basic web automation
- Structured data extraction with schemas
- Boolean responses for yes/no questions
- Multi-step workflow patterns

## Troubleshooting
- Ensure centralized setup is complete
- Verify virtual environment is activated
- Check API key is configured
- Nova Act doesn't support Jupyter notebooks - use .py files

## Next Steps
- Explore and modify the tutorial script
- Try the Human in the Loop tutorial
- Read full documentation at https://nova.amazon.com/act
