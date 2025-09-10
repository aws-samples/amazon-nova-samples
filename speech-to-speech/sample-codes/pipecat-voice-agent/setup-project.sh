#!/bin/bash

# Pipecat Voice AI Agent - Project Setup Script
# This script prepares the project for GitHub upload and local development

set -e

echo "🚀 Setting up Pipecat Voice AI Agent project..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    print_error "This is not a git repository. Please run 'git init' first."
    exit 1
fi

# Remove any existing .env file (security)
if [ -f ".env" ]; then
    print_warning "Removing .env file with sensitive credentials..."
    rm -f .env
    print_status "Removed .env file"
fi

# Create .env.example if it doesn't exist
if [ ! -f ".env.example" ]; then
    print_info "Creating .env.example template..."
    cat > .env.example << 'EOF'
# Daily.co API Configuration
DAILY_API_KEY=your_daily_api_key_here
DAILY_API_URL=https://api.daily.co/v1

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1

# Twilio Configuration (for phone service)
TWILIO_RECOVERY_CODE=your_twilio_recovery_code
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_SID=your_twilio_sid
TWILIO_SECRET=your_twilio_secret
TWILIO_AUTH_LIVE=your_twilio_auth_live

# Optional Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
HOST=0.0.0.0
FAST_API_PORT=7860
MAX_BOTS_PER_ROOM=1
MAX_CONCURRENT_ROOMS=10
EOF
    print_status "Created .env.example template"
fi

# Make scripts executable
print_info "Making scripts executable..."
find scripts/ -name "*.sh" -type f -exec chmod +x {} \;
if [ -f "infrastructure/deploy.sh" ]; then
    chmod +x infrastructure/deploy.sh
fi
if [ -f "setup-project.sh" ]; then
    chmod +x setup-project.sh
fi
print_status "Scripts are now executable"

# Check for required tools
print_info "Checking required tools..."

check_tool() {
    if command -v $1 &> /dev/null; then
        print_status "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

MISSING_TOOLS=0

# Check essential tools
if ! check_tool "aws"; then
    print_warning "Install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    MISSING_TOOLS=1
fi

if ! check_tool "docker"; then
    print_warning "Install Docker: https://docs.docker.com/get-docker/"
    MISSING_TOOLS=1
fi

if ! check_tool "node"; then
    print_warning "Install Node.js: https://nodejs.org/"
    MISSING_TOOLS=1
fi

if ! check_tool "python3"; then
    print_warning "Install Python 3.10+: https://www.python.org/downloads/"
    MISSING_TOOLS=1
fi

# Check optional tools
if ! check_tool "kubectl"; then
    print_warning "Install kubectl for EKS deployments: https://kubernetes.io/docs/tasks/tools/"
fi

if ! check_tool "cdk"; then
    print_warning "Install AWS CDK: npm install -g aws-cdk"
fi

# Install Python dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    print_info "Python dependencies available in requirements.txt"
    if command -v python3 &> /dev/null; then
        print_info "For local development, create a virtual environment:"
        print_info "python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    else
        print_warning "Python3 not found"
    fi
fi

# Install CDK dependencies for ECS infrastructure
if [ -f "infrastructure/package.json" ]; then
    print_info "Installing ECS CDK dependencies..."
    cd infrastructure
    npm install
    cd ..
    print_status "ECS CDK dependencies installed"
fi

# Install CDK dependencies for EKS infrastructure
if [ -f "infrastructure/-eks/package.json" ]; then
    print_info "Installing EKS CDK dependencies..."
    cd infrastructure/-eks
    npm install
    cd ../..
    print_status "EKS CDK dependencies installed"
fi

# Check git status
print_info "Checking git status..."
if [ -n "$(git status --porcelain)" ]; then
    print_warning "You have uncommitted changes. Consider committing them before uploading to GitHub."
    git status --short
else
    print_status "Working directory is clean"
fi

# Summary
echo ""
echo "📋 Setup Summary:"
echo "=================="

if [ $MISSING_TOOLS -eq 0 ]; then
    print_status "All essential tools are installed"
else
    print_warning "Some tools are missing - install them before deployment"
fi

print_info "Next steps:"
echo "1. Copy .env.example to .env and fill in your credentials (for local development)"
echo "2. Configure AWS credentials: aws configure"
echo "3. Set up GitHub repository secrets (see .github/SETUP.md)"
echo "4. Choose deployment platform:"
echo "   - ECS: cd infrastructure && ./deploy.sh --environment test"
echo "   - EKS: cd infrastructure/-eks && cdk deploy"
echo "5. Push to GitHub to trigger automated deployments"

echo ""
print_status "Project setup complete! 🎉"
print_info "Read README.md for detailed deployment instructions"