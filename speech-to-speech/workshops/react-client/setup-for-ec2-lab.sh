#!/usr/bin/env bash

# This is only required by the instructor-led workshop

# install react dependencies
npm install

# set correct WebSocket URL
VSCODE_PROXY_URI=$(printenv VSCODE_PROXY_URI)
NEW_URL="${VSCODE_PROXY_URI//\{\{port\}\}/8081}"
NEW_URL="${NEW_URL/https:/wss:}"
export REACT_APP_WEBSOCKET_URL="${NEW_URL}ws"

export REACT_APP_BASE='/proxy/3000/'

# start the react app
npm start
