# Amazon Nova Act Tutorials - Setup Guide

## Overview
This setup guide prepares your environment for all Amazon Nova Act tutorials (01-04). Complete this setup once to run any tutorial script.

## What This Setup Includes
- Python virtual environment creation
- All required dependencies installation
- Nova Act SDK installation and verification
- API key configuration guidance
- Optional Chrome browser installation
- Environment validation

## Prerequisites
- **Operating System:** macOS Sierra+, Ubuntu 22.04+, WSL2, or Windows 10+
- **Python:** 3.10 or higher
- **Internet connection:** Required for package installation
- **Terminal access:** Command line interface

## Quick Setup

### Automated Setup (Recommended)
```bash
cd tutorials/research-preview/00-setup
./setup.sh
```

This script will:
1. ✓ Check Python version (3.10+ required)
2. ✓ Create virtual environment at `./venv`
3. ✓ Install all dependencies
4. ✓ Verify Nova Act installation
5. ✓ Guide you through API key setup
6. ✓ Optionally install Chrome browser

### Manual Setup
```bash
# 1. Navigate to setup directory
cd tutorials/research-preview/00-setup

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify installation
python3 -c "import nova_act; print(f'Nova Act version: {nova_act.__version__}')"
```

## API Key Setup

### Step 1: Get Your API Key
1. Visit [https://nova.amazon.com/act](https://nova.amazon.com/act)
2. Sign up or log in
3. Generate an API key

### Step 2: Set Environment Variable
**Current session:**
```bash
export NOVA_ACT_API_KEY="your_api_key_here"
```

**Persistent (recommended):**
```bash
# For bash
echo 'export NOVA_ACT_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc

# For zsh
echo 'export NOVA_ACT_API_KEY="your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Verify
```bash
echo $NOVA_ACT_API_KEY  # Should print your API key
```

## Dependencies Installed
- **nova-act** (>=1.0.0) - Amazon Nova Act SDK
- **playwright** (>=1.30.0) - Browser automation
- **pydantic** (>=2.0.0) - Data validation
- **pandas** (>=2.0.0) - Data analysis (Tutorial 03)
- **requests** (>=2.31.0) - HTTP library (Tutorial 03)
- **boto3** (>=1.28.0) - AWS SDK (Tutorial 04, optional)

## Verifying Setup
```bash
# Activate environment
source venv/bin/activate

# Check installations
python3 --version  # Should be 3.10+
python3 -c "import nova_act; print(nova_act.__version__)"
echo $NOVA_ACT_API_KEY  # Should print your key
```

## Running Tutorials
Once setup is complete:

```bash
# Tutorial 01 - Getting Started
cd ../01-getting-started && python 1_getting_started.py

# Tutorial 02 - Human in the Loop
cd ../02-human-in-loop && python 1_captcha_handling.py

# Tutorial 03 - Tool Use
cd ../03-tool-use && python 1_page_object_usage.py

# Tutorial 04 - Observability
cd ../04-observability && python 1_observability.py
```

**Note:** Always activate the virtual environment first:
```bash
source tutorials/research-preview/00-setup/venv/bin/activate
```

## Troubleshooting

### Python Version Issues
Install Python 3.10+ from [python.org](https://www.python.org/downloads/) or use pyenv.

### Virtual Environment Issues
```bash
# Install venv module (Ubuntu/Debian)
sudo apt-get install python3-venv
```

### Permission Issues
```bash
chmod +x setup.sh
./setup.sh
```

### Import Errors
1. Ensure virtual environment is activated
2. Reinstall dependencies: `pip install -r requirements.txt`

### API Key Issues
1. Verify it's set: `echo $NOVA_ACT_API_KEY`
2. Check for typos or extra spaces
3. Re-export if needed

### Browser Issues
```bash
# Install Chrome
playwright install chrome
# Or use default Chromium
playwright install
```

## Security Notes
- Never commit your API key - use environment variables
- Protect your virtual environment
- Follow security best practices in tutorials
- Be cautious with sensitive data

## What's Next
After setup completion:
1. Start with Tutorial 01 - Getting Started
2. Progress through tutorials in order (01-04)
3. Explore Nova Act samples
4. Build your own automations

## Additional Resources
- [Nova Act Documentation](https://nova.amazon.com/act)
- [Nova Act GitHub Repository](https://github.com/aws/nova-act)
- [Playwright Documentation](https://playwright.dev/python/)

## Getting Help
1. Check this README for common issues
2. Review tutorial-specific READMEs
3. Check Nova Act documentation
4. Report issues on GitHub
5. Email: nova-act@amazon.com
