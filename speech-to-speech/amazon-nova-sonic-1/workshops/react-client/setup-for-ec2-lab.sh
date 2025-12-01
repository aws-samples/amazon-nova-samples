# This is only required by the instructor-led workshop
#!/bin/bash

# Install REACT dependencies
npm install

# Set Websocket URL
VSCODE_PROXY_URI=$(printenv VSCODE_PROXY_URI)
NEW_URL="${VSCODE_PROXY_URI//\{\{port\}\}/8081}"
export REACT_APP_WEBSOCKET_URL="${NEW_URL/https:/wss:}"
echo $REACT_APP_WEBSOCKET_URL

# Start the REACT app
npm start