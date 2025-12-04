#!/bin/bash

# Environment Setup Script for Nova Act Path to Production Tutorials
# This script creates a virtual environment and installs required dependencies

set -e  # Exit on error

echo "============================================================"
echo "Nova Act Environment Setup"
echo "============================================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TUTORIAL_ROOT="$(dirname "$SCRIPT_DIR")"

# Navigate to tutorial root
cd "$TUTORIAL_ROOT"

echo "Tutorial root: $TUTORIAL_ROOT"
echo ""

# Check Python version
echo "[1/5] Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 12 ]); then
    echo "❌ Error: Python 3.12 or later is required"
    echo "   Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Create virtual environment
echo "[2/5] Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "⚠️  Virtual environment already exists at .venv"
    read -p "   Remove and recreate? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv
        python3 -m venv .venv
        echo "✓ Virtual environment recreated"
    else
        echo "✓ Using existing virtual environment"
    fi
else
    python3 -m venv .venv
    echo "✓ Virtual environment created at .venv"
fi
echo ""

# Activate virtual environment
echo "[3/5] Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "[4/5] Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "[5/5] Installing dependencies from requirements.txt..."
echo ""
pip install -r 00-setup/requirements.txt

echo ""
echo "============================================================"
echo "✓ Environment Setup Complete"
echo "============================================================"
echo ""
echo "Installed packages:"
pip list | grep -E "nova-act|boto3|strands|mcp"
echo ""
echo "Next steps:"
echo "  1. Activate the environment: source .venv/bin/activate"
echo "  2. Verify installation: python -c 'from nova_act import workflow; print(\"✓ Nova Act ready\")'"
echo "  3. Configure AWS credentials: see 00-setup/1_setup_aws_credentials.md"
echo "  4. Start tutorials: cd 01-workflow-basics"
echo ""
echo "To deactivate later: deactivate"
echo ""
