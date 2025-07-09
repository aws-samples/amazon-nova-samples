#!/usr/bin/env/bash

# This is only required by the instructor-led workshop.

curl -LsSf https://astral.sh/uv/install.sh | sh

uv venv --python=3.12
uv pip install -r requirements.txt

source .venv/bin/activate

# set Bedrock Agents Lambda ARN to env variable
export BOOKING_LAMBDA_ARN=$(aws cloudformation describe-stacks --stack-name bedrock-agents --query "Stacks[0].Outputs[?OutputKey=='BookingLambdaArn'].OutputValue" --output text)

# set websocket server host and port
export HOST="0.0.0.0"
export WS_PORT=8081
