from bedrock_agentcore_starter_toolkit import Runtime
import boto3
import time, argparse, os

region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

agent_name = "ac_mortgage_agent"
entrypoint = "./mortgage_agent.py"
# Prepare docker file
agentcore_runtime = Runtime()

response = agentcore_runtime.configure(
    entrypoint=entrypoint,
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name=agent_name
)
print(f"Initialized docker file for {agent_name}")

# launch agentCore runtime
launch_result = agentcore_runtime.launch()
print(f"Launching AgentCore runtime {agent_name}")

# Check agentcore runtime deployment status
status_response = agentcore_runtime.status()
status = status_response.endpoint['status']
end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
while status not in end_status:
    time.sleep(10)
    status_response = agentcore_runtime.status()
    status = status_response.endpoint['status']
    print(".")
print("AgentCore Runtime deployed succssfully:", agent_name)