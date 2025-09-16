from bedrock_agentcore_starter_toolkit import Runtime
import boto3
import time, argparse, os

region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

agent_name = "ac_bank_agent"
entrypoint = "./banking_agent.py"

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


# Update the docker with the below environment variables for instrumentation with filtering

def modify_dockerfile(dockerfile_path, env_vars):
    """
    Read a Dockerfile, add environment variable definitions, and write it back.
    
    Args:
        dockerfile_path (str): Path to the Dockerfile
        env_vars (dict): Dictionary of environment variables to add (key-value pairs)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the Dockerfile
        with open(dockerfile_path, 'r') as file:
            content = file.readlines()
        
        # Find the best position to add environment variables
        # Strategy: Look for existing ENV statements and add after the last one
        # If no ENV statements, add after the WORKDIR statement
        # If no WORKDIR, add after the FROM statement
        # If none of the above, add at the beginning
        
        env_positions = []
        workdir_positions = []
        from_positions = []
        
        for i, line in enumerate(content):
            if line.strip().startswith('ENV '):
                env_positions.append(i)
            elif line.strip().startswith('WORKDIR '):
                workdir_positions.append(i)
            elif line.strip().startswith('FROM '):
                from_positions.append(i)
        
        if env_positions:
            insert_position = env_positions[-1] + 1
        elif workdir_positions:
            insert_position = workdir_positions[-1] + 1
        elif from_positions:
            insert_position = from_positions[-1] + 1
        else:
            insert_position = 0
        
        # Create ENV statements for the new variables
        env_statements = []
        for key, value in env_vars.items():
            env_statements.append(f"ENV {key}={value}\n")
        
        # If we're adding after an existing ENV statement, add a blank line for readability
        if env_positions and insert_position > 0:
            if not content[insert_position-1].strip() == '':
                env_statements.insert(0, '\n')
        
        # Insert the new ENV statements
        for i, statement in enumerate(env_statements):
            content.insert(insert_position + i, statement)
        
        # Write the updated content back to the Dockerfile
        with open(dockerfile_path, 'w') as file:
            file.writelines(content)
        
        return True
    
    except Exception as e:
        print(f"Error modifying Dockerfile: {e}")
        return False


# Example usage
dockerfile_path = "Dockerfile"
env_vars = {
    "OTEL_PYTHON_DISTRO": "aws_distro",
    "OTEL_PYTHON_CONFIGURATOR": "aws_configurator",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "https://xray.us-east-1.amazonaws.com/v1/traces",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
    "OTEL_RESOURCE_ATTRIBUTES": "service.name={agent_name}",
    "AGENT_OBSERVABILITY_ENABLED": "true",
    "OTEL_EXPORTER_OTLP_LOGS_HEADERS":"x-aws-log-group=bedrock-agentcore-observability,x-aws-log-stream=default,x-aws-metric-namespace=bedrock-agentcore",
    "OTEL_PYTHON_DISABLED_INSTRUMENTATIONS":"bedrock-agentcore,strands-agents,strands-agents-tools,boto3sqs,botocore,requests,urllib3,httpx,aiohttp-client,asyncio,threading,logging,system_metrics,psutil,sqlite3,redis,pymongo,sqlalchemy,django,flask,tornado,pyramid,falcon,starlette,fastapi,websockets"
}

success = modify_dockerfile(dockerfile_path, env_vars)
if success:
    print(f"Successfully updated {dockerfile_path} with new environment variables")
else:
    print(f"Failed to update {dockerfile_path}")


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
