# This is only required by the instructor-led workshop
#!/bin/bash

# Start virtual environment
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip

# install dependencies
pip install -r requirements.txt
pip install boto3 --upgrade

curl -LsSf https://astral.sh/uv/install.sh | sh

# Set websocket server host and port
export HOST="0.0.0.0"
export WS_PORT=8081