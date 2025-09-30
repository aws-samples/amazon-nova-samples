# This is only required by the instructor-led workshop
#!/bin/bash

start=$(date +%s)

# Start virtual environment
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip

# install dependencies
pip install -r requirements.txt

# Deploy Strands agents to AgentCore Runtime
# # Banking agent
cd ./banking_agent
python ./deploy.py

cd ..

# Mortgage agent
cd ./mortgage_agent
python ./deploy.py
cd ..

echo -n "AgentCore Runtime deployment completed."

end=$(date +%s)
elapsed=$((end - start))
echo "Time elapsed: $elapsed seconds"