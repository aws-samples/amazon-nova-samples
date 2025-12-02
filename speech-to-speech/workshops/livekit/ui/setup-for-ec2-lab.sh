#!/bin/bash

eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# Run the lk token create command and capture output
OUTPUT=$(lk token create \
  --api-key devkey --api-secret secret \
  --join --room my-first-room --identity user1 \
  --valid-for 24h)

# Extract the access token from the output
LIVEKIT_TOKEN=$(echo "$OUTPUT" | sed -n 's/^Access token: //p')

# Export the token to environment variable
export LIVEKIT_TOKEN

# Set LiveKit Server URL
VSCODE_PROXY_URI=$(printenv VSCODE_PROXY_URI)
if [ -z "$VSCODE_PROXY_URI" ]; then
  echo "Not in workshop enviroment. Use default localhost URL"
  LIVEKIT_SERVER_URL="ws://localhost:7880"
else
  LIVEKIT_SERVER_URL=$(echo "$VSCODE_PROXY_URI" | sed -E 's|https://([^/]+)/proxy/\{\{port\}\}/?|wss://\1/livekit|')
fi
export LIVEKIT_SERVER_URL

echo -e "\nLiveKit server: $LIVEKIT_SERVER_URL"
echo -e "\nAccess token: $LIVEKIT_TOKEN"

# Write to .env file
echo "REACT_APP_LIVEKIT_SERVER_URL=$LIVEKIT_SERVER_URL" > .env
echo "REACT_APP_LIVEKIT_TOKEN=$LIVEKIT_TOKEN" >> .env

# Install web dependency
npm install

# Start website
npm start