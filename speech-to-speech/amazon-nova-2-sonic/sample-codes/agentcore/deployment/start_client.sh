#!/bin/bash

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse command line arguments
WEBSOCKET_FOLDER=""

usage() {
    echo "Usage: $0 <websocket-folder>"
    echo ""
    echo "Arguments:"
    echo "  websocket-folder    Folder containing the client (strands, langchain, echo, or sonic)"
    echo ""
    echo "Example:"
    echo "  ./start_client.sh sonic"
    echo "  ./start_client.sh strands"
    echo "  ./start_client.sh langchain"
    echo "  ./start_client.sh echo"
    echo ""
    exit 1
}

# Check if folder argument is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Error: websocket folder argument is required${NC}"
    echo ""
    usage
fi

WEBSOCKET_FOLDER="$1"

# Resolve the base directory (parent of deployment/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Validate folder exists
if [ ! -d "$BASE_DIR/$WEBSOCKET_FOLDER" ]; then
    echo -e "${RED}❌ Error: Folder not found: $BASE_DIR/$WEBSOCKET_FOLDER${NC}"
    echo ""
    echo "Available folders:"
    for dir in strands langchain echo sonic; do
        if [ -d "$BASE_DIR/$dir" ]; then
            echo "  - $dir"
        fi
    done
    echo ""
    exit 1
fi

echo -e "${BLUE}🚀 Starting $WEBSOCKET_FOLDER Client${NC}"
echo ""

# Check for configuration file
CONFIG_FILE="$BASE_DIR/$WEBSOCKET_FOLDER/setup_config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Error: Configuration file not found: $CONFIG_FILE${NC}"
    echo ""
    echo "Please run setup first:"
    echo "  ./setup.sh $WEBSOCKET_FOLDER"
    echo ""
    exit 1
fi

# Check for jq
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ Error: jq is not installed${NC}"
    echo "Please install jq to parse JSON configuration"
    exit 1
fi

# Load configuration
echo -e "${YELLOW}📋 Loading configuration from $CONFIG_FILE...${NC}"
AGENT_ARN=$(jq -r '.agent_arn' "$CONFIG_FILE")
AWS_REGION=$(jq -r '.aws_region' "$CONFIG_FILE")

if [ -z "$AGENT_ARN" ] || [ "$AGENT_ARN" = "null" ]; then
    echo -e "${RED}❌ Error: Agent ARN not found in configuration${NC}"
    exit 1
fi

if [ -z "$AWS_REGION" ] || [ "$AWS_REGION" = "null" ]; then
    echo -e "${RED}❌ Error: AWS Region not found in configuration${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Configuration loaded${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "   Folder:       $WEBSOCKET_FOLDER"
echo "   Agent ARN:    $AGENT_ARN"
echo "   AWS Region:   $AWS_REGION"
echo ""

# Export environment variables
export AWS_REGION="$AWS_REGION"

# Check if virtual environment exists
if [ ! -d "$BASE_DIR/venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv "$BASE_DIR/venv"
    source "$BASE_DIR/venv/bin/activate"
    pip install -q -r "$BASE_DIR/$WEBSOCKET_FOLDER/client/requirements.txt"
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    source "$BASE_DIR/venv/bin/activate"
fi

# Determine client path
CLIENT_PATH="$BASE_DIR/$WEBSOCKET_FOLDER/client/client.py"

if [ ! -f "$CLIENT_PATH" ]; then
    echo -e "${RED}❌ Error: Client not found: $CLIENT_PATH${NC}"
    exit 1
fi

# Start the client
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Starting Client${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Different clients have different interfaces
case "$WEBSOCKET_FOLDER" in
    "echo")
        echo -e "${YELLOW}Starting Echo client...${NC}"
        echo ""
        python "$CLIENT_PATH" --runtime-arn "$AGENT_ARN"
        ;;
    "sonic"|"strands"|"langchain")
        echo -e "${YELLOW}Starting $WEBSOCKET_FOLDER web client...${NC}"
        echo -e "${YELLOW}The browser will open automatically${NC}"
        echo ""
        python "$CLIENT_PATH" --runtime-arn "$AGENT_ARN"
        ;;
    *)
        echo -e "${RED}❌ Error: Unknown folder type: $WEBSOCKET_FOLDER${NC}"
        exit 1
        ;;
esac
