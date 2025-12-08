# Environment Setup

## Overview

This guide walks you through setting up a Python virtual environment and installing the required dependencies for the Nova Act Path to Production tutorials.

## Prerequisites

- Python 3.12 or later
- pip (Python package installer)
- Terminal/command line access

## Quick Setup

Run the automated setup script with one command:

```bash
chmod +x 00-setup/0_setup_environment.sh && ./00-setup/0_setup_environment.sh
```

The script will:
1. Create a `.venv` virtual environment
2. Activate the virtual environment
3. Install all required packages from `requirements.txt`

**Note:** Run this from the `path-to-production` directory, not from inside `00-setup`.

## Manual Setup

If you prefer to set up manually or the script fails:

### Step 1: Create Virtual Environment

```bash
cd /path/to/nova-act/tutorials/path-to-production
python3 -m venv .venv
```

This creates a `.venv` directory containing an isolated Python environment.

### Step 2: Activate Virtual Environment

**macOS/Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```cmd
.venv\Scripts\activate
```

You should see `(.venv)` prefix in your terminal prompt.

### Step 3: Upgrade pip

```bash
pip install --upgrade pip
```

### Step 4: Install Dependencies

```bash
pip install -r 00-setup/requirements.txt
```

This installs:
- `nova-act[cli]` - Nova Act SDK with CLI tools
- `boto3` - AWS SDK for Python
- `strands-agents` - Strands Agents framework
- `mcp` - Model Context Protocol library

## Verify Installation

Check that Nova Act is installed correctly:

```bash
python -c "from nova_act import NovaAct, workflow; print('✓ Nova Act installed')"
```

Check the CLI is available:

```bash
act --version
```

Check boto3 is installed:

```bash
python -c "import boto3; print('✓ boto3 installed')"
```

## Troubleshooting

### Command not found: act

**Cause:** Virtual environment not activated or CLI extras not installed

**Solution:**
```bash
source .venv/bin/activate
pip install --upgrade 'nova-act[cli]'
```

### ModuleNotFoundError: No module named 'yaml'

**Cause:** CLI extras not installed

**Solution:**
```bash
pip install --upgrade 'nova-act[cli]'
```

### Permission denied: ./0_setup_environment.sh

**Cause:** Script not executable

**Solution:**
```bash
chmod +x 00-setup/0_setup_environment.sh
./00-setup/0_setup_environment.sh
```

### zsh: no matches found: nova-act[cli]

**Cause:** Zsh interprets brackets as glob patterns

**Solution:** Quote the package name:
```bash
pip install --upgrade 'nova-act[cli]'
```

## Deactivating the Environment

When you're done working with the tutorials:

```bash
deactivate
```

## Reactivating the Environment

To work on the tutorials again later:

```bash
cd /path/to/nova-act/tutorials/path-to-production
source .venv/bin/activate
```

## Next Steps

Once your environment is set up:

1. Configure AWS credentials: `1_setup_aws_credentials.md`
2. Verify permissions: `2_verify_permissions.md`
3. Start with workflow basics: `../01-workflow-basics/`

## Package Details

### nova-act[cli]
- **Purpose:** Nova Act SDK with CLI tools
- **Includes:** Browser automation, workflow management, CLI commands
- **Documentation:** [Nova Act User Guide](../../p2p-user-guide.md)

### boto3
- **Purpose:** AWS SDK for Python
- **Used for:** Lambda, IAM, AgentCore Gateway, CloudWatch
- **Documentation:** [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

### strands-agents
- **Purpose:** Agentic framework for tool integration
- **Used for:** MCP client, tool management
- **Documentation:** [Strands Agents](https://strandsagents.com/)

### mcp
- **Purpose:** Model Context Protocol implementation
- **Used for:** Remote tool integration
- **Documentation:** [MCP Specification](https://spec.modelcontextprotocol.io/)

## Environment Variables

Some tutorials may require environment variables. Set them in your shell or create a `.env` file:

```bash
# AWS Configuration (optional if using default profile)
export AWS_PROFILE=default
export AWS_REGION=us-east-1

# Nova Act Configuration (optional)
export NOVA_ACT_MODEL=nova-act-latest
```

## Updating Dependencies

To update all packages to their latest versions:

```bash
pip install --upgrade -r 00-setup/requirements.txt
```

To update a specific package:

```bash
pip install --upgrade 'nova-act[cli]'
```
