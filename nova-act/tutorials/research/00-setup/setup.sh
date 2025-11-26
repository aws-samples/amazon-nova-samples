#!/bin/bash
# Amazon Nova Act Tutorials - Setup Script
# This script sets up your environment for all Nova Act tutorials (01-04)

set -e  # Exit on error

echo "======================================================================"
echo "Amazon Nova Act Tutorials - Environment Setup"
echo "======================================================================"

# Check Python version
echo ""
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $python_version"

# Check if Python 3.10+
required_version="3.10"
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "✗ Python 3.10 or higher is required"
    echo "  Current version: $python_version"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists at ./venv"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo "✓ Virtual environment recreated"
    else
        echo "✓ Using existing virtual environment"
    fi
else
    python3 -m venv venv
    echo "✓ Virtual environment created at ./venv"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ All dependencies installed"

# Verify Nova Act installation
echo ""
echo "Verifying Nova Act installation..."
python3 -c "import nova_act; print(f'✓ Nova Act version: {nova_act.__version__}')"

# Check for API key
echo ""
echo "======================================================================"
echo "API Key Setup"
echo "======================================================================"
if [ -z "$NOVA_ACT_API_KEY" ]; then
    echo "⚠️  NOVA_ACT_API_KEY environment variable is not set"
    echo ""
    echo "To get an API key:"
    echo "  1. Visit https://nova.amazon.com/act"
    echo "  2. Sign up and generate an API key"
    echo "  3. Set it as an environment variable:"
    echo ""
    echo "     export NOVA_ACT_API_KEY=\"your_api_key_here\""
    echo ""
    echo "  4. Add to your shell profile (~/.bashrc or ~/.zshrc) to persist:"
    echo ""
    echo "     echo 'export NOVA_ACT_API_KEY=\"your_api_key_here\"' >> ~/.zshrc"
    echo ""
else
    echo "✓ NOVA_ACT_API_KEY is set"
fi

# Optional: Install Chrome
echo ""
echo "======================================================================"
echo "Browser Setup (Optional)"
echo "======================================================================"
echo "Nova Act works best with Google Chrome."
echo "Playwright will use Chromium by default, but you can install Chrome:"
echo ""
echo "  playwright install chrome"
echo ""
read -p "Install Chrome now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    playwright install chrome
    echo "✓ Chrome installed"
else
    echo "✓ Skipping Chrome installation (will use Chromium)"
fi

# Summary
echo ""
echo "======================================================================"
echo "Setup Complete!"
echo "======================================================================"
echo ""
echo "✓ Virtual environment created at: ./venv"
echo "✓ All dependencies installed"
echo "✓ Nova Act verified"
echo ""
echo "Next steps:"
echo "  1. Set your API key (if not already set):"
echo "     export NOVA_ACT_API_KEY=\"your_api_key_here\""
echo ""
echo "  2. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  3. Run any tutorial script:"
echo "     python ../01-getting-started/getting_started.py"
echo "     python ../02-human-in-loop/captcha_handling.py"
echo "     python ../03-tool-use/page_object_usage.py"
echo "     python ../04-observability/observability.py"
echo ""
echo "  4. Read the README in each tutorial directory for details"
echo ""
echo "Happy automating with Nova Act!"
echo "======================================================================"
