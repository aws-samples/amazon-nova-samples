#!/bin/bash

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Adaptive UI Testing Demo - Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.11+ is required but not installed."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js 22+ is required but not installed."
    exit 1
fi

echo "✅ Prerequisites met"
echo ""

# Setup Playwright
echo "Setting up Playwright tests..."
cd playwright-tests
npm install
npx playwright install chromium
cd ..
echo "✅ Playwright setup complete"
echo ""

# Setup Nova Act with clean venv
echo "Setting up Nova Act tests (in virtual environment)..."
cd nova-act-tests

# Remove existing venv if present
if [ -d "venv" ]; then
    echo "  Removing existing virtual environment..."
    rm -rf venv
fi

# Create fresh venv
echo "  Creating Python virtual environment..."
python3 -m venv venv

# Activate and install dependencies
echo "  Installing dependencies in venv..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
echo "  Verifying installation..."
python3 -c "from nova_act import workflow, NovaAct; print('✅ nova-act installed successfully')"

deactivate

cd ..
echo "✅ Nova Act setup complete"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Configure authentication (required):"
echo "   AWS IAM (recommended): aws configure"
echo "   API key (alternative): nano nova-act-tests/.env"
echo ""
echo "2. Start the application (Terminal 1):"
echo "   cd sample-app"
echo "   python3 -m http.server 8000"
echo ""
echo "3. Run 3-phase demo (Terminal 2, from repo root):"
echo "   ./phase1-baseline.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ℹ️  About Virtual Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Nova Act is installed in an isolated virtual environment at:"
echo "  nova-act-tests/venv/"
echo ""
echo "The demo scripts automatically activate/deactivate this environment."
echo "You don't need to manually activate it."
echo ""
echo "To manually use the virtual environment:"
echo "  cd nova-act-tests"
echo "  source venv/bin/activate"
echo "  # Your prompt will show (venv)"
echo "  deactivate  # When done"
echo ""
