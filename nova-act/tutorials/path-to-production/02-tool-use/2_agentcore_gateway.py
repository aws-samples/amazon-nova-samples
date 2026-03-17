#!/usr/bin/env python3
"""
AgentCore Gateway Integration for GPU Capacity Planning

This script demonstrates AgentCore Gateway integration with Nova Act for infrastructure planning.
Combines AWS Knowledge MCP server, Calculator Lambda functions, and browser automation.

Prerequisites:
- Nova Act installed: pip install nova-act
- boto3 installed: pip install boto3
- AWS credentials configured with AgentCore Gateway permissions
- Understanding of AgentCore Gateway concepts

Setup:
1. Run this script to set up Gateway with multiple tool types
2. Script will interactively guide through deployment steps
3. Workflow demonstrates GPU capacity planning for LLM training

Note: Creates AWS resources (Lambda, Gateway) that may incur costs.
"""

import subprocess
import json
import boto3
import time
import zipfile
import io
import os
from nova_act import NovaAct, workflow


def create_workflow_definition():
    """Interactively create workflow definition in Nova Act Service."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mWorkflow Definition Setup\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    workflow_name = "gateway-integration-demo"
    
    # Check if workflow already exists
    try:
        result = subprocess.run(
            ['act', 'workflow', 'describe', workflow_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"\033[93m[OK]\033[0m Workflow definition '{workflow_name}' already exists")
            return True
    except Exception:
        pass
    
    print(f"\nThis script uses the @workflow decorator to define a workflow:")
    print(f"\n\033[96m@workflow(workflow_definition_name=\"{workflow_name}\", model_id=\"nova-act-latest\")\033[0m")
    print(f"\033[96mdef demonstrate_gateway_workflow():\033[0m")
    print(f"\033[96m    with MCPClient(lambda: streamablehttp_client(gateway_url)) as client:\033[0m")
    print(f"\033[96m        tools = client.list_tools_sync()\033[0m")
    print(f"\033[96m        with NovaAct(starting_page=\"...\", tools=tools) as nova:\033[0m")
    print(f"\033[96m            result = nova.act(\"Plan GPU infrastructure\")\033[0m")
    print(f"\033[96m            return {{\"recommendation\": result}}\033[0m")
    
    print(f"\n\033[93m[ACTION REQUIRED]\033[0m Create workflow definition in Nova Act Service?")
    print(f"  This enables AWS logging for workflow execution")
    print(f"  Workflow name: {workflow_name}")
    
    response = input(f"\nCreate workflow definition? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print(f"\033[91m[SKIPPED]\033[0m Workflow definition not created")
        return False
    
    try:
        print(f"\n\033[93m[CREATING]\033[0m Creating workflow definition...")
        result = subprocess.run(
            ['act', 'workflow', 'create', '--name', workflow_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"\033[92m✓ Created:\033[0m Workflow definition '{workflow_name}'")
            
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            region = boto3.session.Session().region_name or 'us-east-1'
            
            print(f"\n  ARN: arn:aws:nova-act:{region}:{identity['Account']}:workflow-definition/{workflow_name}")
            print(f"  Logging: Enabled (CloudWatch Logs)")
            return True
        else:
            print(f"\033[91m[ERROR]\033[0m Failed to create workflow definition")
            print(f"  {result.stderr}")
            return False
            
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Failed to create workflow definition: {e}")
        return False


def deploy_calculator_lambda():
    """Deploy calculator Lambda function for Gateway."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mCalculator Lambda Deployment\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    lambda_client = boto3.client('lambda')
    iam_client = boto3.client('iam')
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    function_name = 'gateway-calculator-tools'
    
    # Check if Lambda already exists
    try:
        lambda_client.get_function(FunctionName=function_name)
        print(f"\033[93m[OK]\033[0m Lambda function '{function_name}' already exists")
        
        response = input(f"\nUse existing Lambda function? (yes/no): ").strip().lower()
        if response == 'yes':
            return function_name
    except lambda_client.exceptions.ResourceNotFoundException:
        pass
    
    print(f"\n\033[93m[ACTION REQUIRED]\033[0m Deploy calculator Lambda function?")
    print(f"  Function: {function_name}")
    print(f"  Tools: multiply_numbers, divide_numbers")
    print(f"  Purpose: GPU capacity calculations")
    
    response = input(f"\nDeploy Lambda function? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print(f"\033[91m[SKIPPED]\033[0m Lambda deployment skipped")
        return None
    
    try:
        # Create IAM role for Lambda
        print(f"\n\033[93m[CREATING]\033[0m Creating IAM role...")
        role_name = 'gateway-calculator-lambda-role'
        
        try:
            role = iam_client.get_role(RoleName=role_name)
            role_arn = role['Role']['Arn']
            print(f"\033[93m[OK]\033[0m Using existing role: {role_name}")
        except iam_client.exceptions.NoSuchEntityException:
            role = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                })
            )
            role_arn = role['Role']['Arn']
            
            # Attach basic execution policy
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            print(f"\033[92m✓ Created:\033[0m IAM role {role_name}")
            time.sleep(10)  # Wait for role propagation
        
        # Create Lambda deployment package
        print(f"\n\033[93m[CREATING]\033[0m Creating Lambda deployment package...")
        
        lambda_code_path = os.path.join(os.path.dirname(__file__), 'calculator-tools', 'lambda_function_code.py')
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(lambda_code_path, 'lambda_function.py')
        
        zip_buffer.seek(0)
        
        # Create Lambda function
        print(f"\n\033[93m[CREATING]\033[0m Creating Lambda function...")
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.12',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_buffer.read()},
            Description='Calculator tools for GPU capacity planning',
            Timeout=30,
            MemorySize=128
        )
        
        print(f"\033[92m✓ Created:\033[0m Lambda function {function_name}")
        print(f"  ARN: arn:aws:lambda:{boto3.session.Session().region_name}:{account_id}:function:{function_name}")
        
        return function_name
        
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Failed to deploy Lambda: {e}")
        return None


def create_gateway(lambda_function_name):
    """Create AgentCore Gateway with multiple targets."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mAgentCore Gateway Setup\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    agentcore_client = boto3.client('bedrock-agentcore-control')
    iam_client = boto3.client('iam')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    region = boto3.session.Session().region_name or 'us-east-1'
    gateway_name = 'enterprise-tool-gateway'
    role_name = f'agentcore-{gateway_name}-role'
    
    # Check if Gateway already exists
    existing_gateway_id = None
    try:
        gateways = agentcore_client.list_gateways(maxResults=100)
        for gw in gateways.get('items', []):
            if gw.get('name') == gateway_name:
                gateway_id = gw['gatewayId']
                print(f"\033[93m[OK]\033[0m Gateway '{gateway_name}' already exists")
                print(f"  ID: {gateway_id}")
                
                response = input(f"\nUse existing Gateway? (yes/no): ").strip().lower()
                if response == 'yes':
                    # Check existing targets
                    targets = agentcore_client.list_gateway_targets(gatewayIdentifier=gateway_id)
                    target_count = len(targets.get('items', []))
                    print(f"\n  Existing targets: {target_count}")
                    
                    if target_count == 0:
                        print(f"\033[93m[WARNING]\033[0m No targets registered on this Gateway")
                        existing_gateway_id = gateway_id
                        # Continue to target registration below
                    else:
                        return gateway_id
                else:
                    print(f"\033[91m[SKIPPED]\033[0m Gateway setup skipped")
                    return None
    except Exception as e:
        print(f"\033[91m[WARNING]\033[0m Could not check existing gateways: {e}")
        print(f"  Proceeding with creation...")
    
    # If we have an existing Gateway with no targets, skip creation
    if existing_gateway_id:
        gateway_id = existing_gateway_id
    else:
        # Create new Gateway
        print(f"\n\033[93m[ACTION REQUIRED]\033[0m Create AgentCore Gateway?")
        print(f"  Gateway: {gateway_name}")
        print(f"  Purpose: Unified MCP endpoint for AWS Knowledge + Calculator tools")
        
        print(f"\n\033[38;5;214m{'─'*60}\033[0m")
        print(f"\033[38;5;214mCode to be executed:\033[0m")
        print(f"\033[38;5;214m{'─'*60}\033[0m")
        print(f"""
agentcore_client.create_gateway(
    name='{gateway_name}',
    roleArn='{role_name}',
    protocolType='MCP',
    authorizerType='NONE',
    description='Gateway for GPU capacity planning'
)""")
        print(f"\033[38;5;214m{'─'*60}\033[0m")
        
        response = input(f"\nCreate Gateway? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print(f"\033[91m[SKIPPED]\033[0m Gateway creation skipped")
            return None
        
        try:
            # Create Gateway IAM role
            
            try:
                role = iam_client.get_role(RoleName=role_name)
                role_arn = role['Role']['Arn']
                print(f"\n\033[93m[OK]\033[0m Using existing IAM role: {role_name}")
            except iam_client.exceptions.NoSuchEntityException:
                print(f"\n\033[93m[ACTION REQUIRED]\033[0m Create IAM role for Gateway?")
                print(f"  Role: {role_name}")
                print(f"  Trust: bedrock-agentcore.amazonaws.com")
                print(f"  Permissions: Gateway operations, Lambda invoke")
            
            print(f"\n\033[38;5;214m{'─'*60}\033[0m")
            print(f"\033[38;5;214mCode to be executed:\033[0m")
            print(f"\033[38;5;214m{'─'*60}\033[0m")
            print(f"""
iam_client.create_role(
    RoleName='{role_name}',
    AssumeRolePolicyDocument={{
        "Version": "2012-10-17",
        "Statement": [{{
            "Effect": "Allow",
            "Principal": {{"Service": "bedrock-agentcore.amazonaws.com"}},
            "Action": "sts:AssumeRole",
            "Condition": {{
                "StringEquals": {{"aws:SourceAccount": "{account_id}"}},
                "ArnLike": {{"aws:SourceArn": "arn:aws:bedrock-agentcore:{region}:{account_id}:*"}}
            }}
        }}]
    }}
)

iam_client.put_role_policy(
    RoleName='{role_name}',
    PolicyName='AgentCoreGatewayPolicy',
    PolicyDocument={{
        "Version": "2012-10-17",
        "Statement": [{{
            "Effect": "Allow",
            "Action": ["bedrock-agentcore:*", "bedrock:*", 
                      "lambda:InvokeFunction", "secretsmanager:GetSecretValue"],
            "Resource": "*"
        }}]
    }}
)""")
            print(f"\033[38;5;214m{'─'*60}\033[0m")
            
            response = input(f"\nCreate IAM role? (yes/no): ").strip().lower()
            
            if response != 'yes':
                print(f"\033[91m[SKIPPED]\033[0m IAM role creation skipped - cannot create Gateway")
                return None
            
            print(f"\n\033[93m[CREATING]\033[0m Creating IAM role...")
            role = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                        "Condition": {
                            "StringEquals": {"aws:SourceAccount": account_id},
                            "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"}
                        }
                    }]
                })
            )
            role_arn = role['Role']['Arn']
            
            # Attach policy
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName='AgentCoreGatewayPolicy',
                PolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "bedrock-agentcore:*",
                            "bedrock:*",
                            "lambda:InvokeFunction",
                            "secretsmanager:GetSecretValue"
                        ],
                        "Resource": "*"
                    }]
                })
            )
            
            print(f"\033[92m✓ Created:\033[0m IAM role {role_name}")
            time.sleep(10)  # Wait for role propagation
        
            # Create Gateway
            print(f"\n\033[93m[CREATING]\033[0m Creating Gateway...")
            
            gateway_response = agentcore_client.create_gateway(
                name=gateway_name,
                roleArn=role_arn,
                protocolType='MCP',
                authorizerType='NONE',
                description='Gateway for GPU capacity planning with AWS Knowledge MCP and Calculator tools'
            )
            
            gateway_id = gateway_response['gatewayId']
            gateway_url = gateway_response['gatewayUrl']
            
            print(f"\033[92m✓ Created:\033[0m Gateway {gateway_name}")
            print(f"  ID: {gateway_id}")
            print(f"  URL: {gateway_url}")
            
            # Wait for Gateway to be ready
            print(f"\n\033[93m[WAITING]\033[0m Waiting for Gateway to be ready...")
            for i in range(30):
                gw = agentcore_client.get_gateway(gatewayIdentifier=gateway_id)
                if gw['status'] == 'READY':
                    print(f"\033[92m✓ Ready:\033[0m Gateway is ready")
                    break
                time.sleep(2)
        
        except Exception as e:
            print(f"\033[91m[ERROR]\033[0m Failed to create Gateway: {e}")
            return None
    
    # Register targets (for both new and existing gateways with 0 targets)
    try:
        # Note: AWS Knowledge MCP requires OAuth configuration which is beyond this tutorial's scope
        # We'll register the Lambda calculator tools instead
        print(f"\n\033[93m[INFO]\033[0m Skipping AWS Knowledge MCP target (requires OAuth setup)")
        print(f"  For production use, configure OAuth provider for MCP servers")
        
        # Register Calculator Lambda target
        print(f"\n\033[93m[DEBUG]\033[0m lambda_function_name = {lambda_function_name}")
        if lambda_function_name:
            print(f"\n\033[93m[ACTION REQUIRED]\033[0m Register Calculator Lambda as target?")
            print(f"  Lambda: {lambda_function_name}")
            print(f"  Tools: multiply_numbers, divide_numbers")
            
            print(f"\n\033[38;5;214m{'─'*60}\033[0m")
            print(f"\033[38;5;214mCode to be executed:\033[0m")
            print(f"\033[38;5;214m{'─'*60}\033[0m")
            print(f"""
agentcore_client.create_gateway_target(
    gatewayIdentifier='{gateway_id}',
    name='calculator-tools',
    targetConfiguration={{
        'mcp': {{
            'lambda': {{
                'lambdaArn': 'arn:aws:lambda:{region}:{account_id}:function:{lambda_function_name}',
                'toolSchema': {{
                    'inlinePayload': [calculator_tools_schema]
                }}
            }}
        }}
    }},
    credentialProviderConfigurations=[{{
        'credentialProviderType': 'GATEWAY_IAM_ROLE'
    }}]
)""")
            print(f"\033[38;5;214m{'─'*60}\033[0m")
            
            response = input(f"\nRegister Lambda target? (yes/no): ").strip().lower()
            
            if response == 'yes':
                print(f"\n\033[93m[CREATING]\033[0m Registering Lambda target...")
                
                try:
                    # Load calculator API schema
                    calc_api_path = os.path.join(os.path.dirname(__file__), 'calculator-tools', 'calc-api.json')
                    with open(calc_api_path, 'r') as f:
                        tools_schema = json.load(f)
                    
                    lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:{lambda_function_name}"
                    
                    lambda_target = agentcore_client.create_gateway_target(
                        gatewayIdentifier=gateway_id,
                        name='calculator-tools',
                        targetConfiguration={
                            'mcp': {
                                'lambda': {
                                    'lambdaArn': lambda_arn,
                                    'toolSchema': {
                                        'inlinePayload': tools_schema
                                    }
                                }
                            }
                        },
                        credentialProviderConfigurations=[{
                            'credentialProviderType': 'GATEWAY_IAM_ROLE'
                        }]
                    )
                    
                    print(f"\033[92m✓ Registered:\033[0m Calculator Lambda target")
                    print(f"  Target ID: {lambda_target.get('targetId', 'N/A')}")
                except Exception as e:
                    print(f"\033[91m[ERROR]\033[0m Failed to register Lambda target: {e}")
                    return None
        
        return gateway_id
        
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Failed to create Gateway: {e}")
        return None


@workflow(workflow_definition_name="gateway-integration-demo", model_id="nova-act-latest")
def register_gateway_targets(gateway_id, lambda_function_name):
    """Register targets (tools) with an existing Gateway."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mGateway Target Registration\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    agentcore_client = boto3.client('bedrock-agentcore-control')
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = boto3.session.Session().region_name or 'us-east-1'
    
    # Check existing targets
    targets = agentcore_client.list_gateway_targets(gatewayIdentifier=gateway_id)
    target_count = len(targets.get('items', []))
    print(f"\n  Current targets: {target_count}")
    
    if lambda_function_name:
        print(f"\n\033[93m[ACTION REQUIRED]\033[0m Register Calculator Lambda as target?")
        print(f"  Lambda: {lambda_function_name}")
        print(f"  Tools: multiply_numbers, divide_numbers")
        
        print(f"\n\033[38;5;214m{'─'*60}\033[0m")
        print(f"\033[38;5;214mCode to be executed:\033[0m")
        print(f"\033[38;5;214m{'─'*60}\033[0m")
        print(f"""
agentcore_client.create_gateway_target(
    gatewayIdentifier='{gateway_id}',
    name='calculator-tools',
    targetConfiguration={{
        'mcp': {{
            'lambda': {{
                'lambdaArn': 'arn:aws:lambda:{region}:{account_id}:function:{lambda_function_name}',
                'toolSchema': {{
                    'inlinePayload': [calculator_tools_schema]
                }}
            }}
        }}
    }},
    credentialProviderConfigurations=[{{
        'credentialProviderType': 'GATEWAY_IAM_ROLE'
    }}]
)""")
        print(f"\033[38;5;214m{'─'*60}\033[0m")
        
        response = input(f"\nRegister Lambda target? (yes/no): ").strip().lower()
        
        if response == 'yes':
            print(f"\n\033[93m[CREATING]\033[0m Registering Lambda target...")
            
            try:
                # Load calculator API schema
                calc_api_path = os.path.join(os.path.dirname(__file__), 'calculator-tools', 'calc-api.json')
                with open(calc_api_path, 'r') as f:
                    tools_schema = json.load(f)
                
                lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:{lambda_function_name}"
                
                lambda_target = agentcore_client.create_gateway_target(
                    gatewayIdentifier=gateway_id,
                    name='calculator-tools',
                    targetConfiguration={
                        'mcp': {
                            'lambda': {
                                'lambdaArn': lambda_arn,
                                'toolSchema': {
                                    'inlinePayload': tools_schema
                                }
                            }
                        }
                    },
                    credentialProviderConfigurations=[{
                        'credentialProviderType': 'GATEWAY_IAM_ROLE'
                    }]
                )
                
                print(f"\033[92m✓ Registered:\033[0m Calculator Lambda target")
                print(f"  Target ID: {lambda_target.get('targetId', 'N/A')}")
                return True
            except Exception as e:
                print(f"\033[91m[ERROR]\033[0m Failed to register Lambda target: {e}")
                return False
    
    return False


@workflow(workflow_definition_name="gateway-integration-demo", model_id="nova-act-latest")
def demonstrate_gateway_workflow(gateway_id, model_size_b):
    """GPU capacity planning using Gateway tools and browser automation."""
    
    try:
        from mcp.client.streamable_http import streamablehttp_client
        from strands.tools.mcp import MCPClient
        
        # Get Gateway endpoint
        agentcore_client = boto3.client('bedrock-agentcore-control')
        gateway = agentcore_client.get_gateway(gatewayIdentifier=gateway_id)
        gateway_url = gateway['gatewayUrl']
        
        print(f"\n\033[93m[CONNECTING]\033[0m Connecting to Gateway...")
        
        with MCPClient(
            lambda: streamablehttp_client(gateway_url)
        ) as gateway_client:
            tools = gateway_client.list_tools_sync()
            print(f"\033[92m✓ Connected:\033[0m Gateway tools available")
            print(f"  Tool count: {len(tools)}")
            
            if len(tools) == 0:
                return {
                    "status": "error",
                    "message": "No tools available from Gateway. Ensure targets are registered."
                }
            
            # Use NovaAct with Gateway tools for calculations
            with NovaAct(
                starting_page="https://www.nvidia.com/en-us/data-center/h100/",
                tools=tools
            ) as nova:
                # Step 1: Get GPU memory from Nvidia page
                gpu_memory_result = nova.act_get(
                    "Find the memory capacity in GB for a single H100 GPU on this page"
                )
                gpu_memory = gpu_memory_result.response
                
                # Step 2: Calculate memory requirements (model_size_b × 2 bytes for FP16)
                memory_calc_result = nova.act_get(
                    f"Use the multiply_numbers tool to calculate: {model_size_b} multiplied by 2"
                )
                memory_calc = memory_calc_result.response
                
                # Step 3: Calculate total GPU memory per P5.48xlarge (8 GPUs × 80GB)
                total_per_instance_result = nova.act_get(
                    "Use the multiply_numbers tool to calculate: 8 multiplied by 80"
                )
                total_per_instance = total_per_instance_result.response
                
                # Step 4: Calculate instances needed (memory_calc ÷ 640GB per instance)
                instances_calc_result = nova.act_get(
                    f"Use the divide_numbers tool to calculate: {memory_calc} divided by 640"
                )
                instances_calc = float(instances_calc_result.response.strip('"'))
                instances_needed = int(instances_calc) + (1 if instances_calc % 1 > 0 else 0)
            
            return {
                "status": "completed",
                "model_size": f"{model_size_b}B parameters",
                "gpu_memory": gpu_memory,
                "model_memory_gb": memory_calc,
                "total_per_instance_gb": total_per_instance,
                "instances_decimal": instances_calc,
                "instances_needed": instances_needed,
                "equation": f"{memory_calc}GB ÷ {total_per_instance}GB = {instances_calc:.4f} → {instances_needed} instance(s)"
            }
                
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Gateway workflow failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


def main(payload):
    """
    Main function demonstrating Gateway integration for GPU planning.
    
    Args:
        payload: Input parameters for workflow execution
    """
    print(f"\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mAgentCore Gateway Integration - GPU Planning\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Create workflow definition
    if not create_workflow_definition():
        print(f"\n\033[91m[STOPPED]\033[0m Cannot proceed without workflow definition")
        return
    
    # Deploy calculator Lambda
    lambda_function_name = deploy_calculator_lambda()
    
    # Create Gateway with targets
    gateway_id = create_gateway(lambda_function_name)
    
    if not gateway_id:
        print(f"\n\033[91m[STOPPED]\033[0m Cannot proceed without Gateway")
        return
    
    # Register targets with Gateway
    if not register_gateway_targets(gateway_id, lambda_function_name):
        print(f"\n\033[93m[WARNING]\033[0m No targets registered")
    
    # Execute workflow
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mGateway-Integrated Workflow\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Get model size from user
    print(f"\n\033[93m[INPUT REQUIRED]\033[0m Enter model size for capacity planning:")
    model_size_b = input(f"  Model parameters (in billions, e.g., 120): ").strip()
    
    try:
        model_size_b = float(model_size_b)
    except ValueError:
        print(f"\033[91m[ERROR]\033[0m Invalid input. Using default 120B")
        model_size_b = 120.0
    
    print(f"\n\033[93m[ACTION REQUIRED]\033[0m Execute GPU planning workflow?")
    print(f"  Model: {model_size_b}B parameters")
    print(f"  This will use Gateway tools and browser automation")
    
    response = input(f"\nExecute workflow? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print(f"\033[91m[SKIPPED]\033[0m Workflow execution skipped")
        return
    
    result = demonstrate_gateway_workflow(gateway_id, model_size_b)
    
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mResults\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    if result.get("status") == "completed":
        print(f"\n\033[92m✓ Workflow Completed\033[0m")
        print(f"\n\033[38;5;214m{'─'*60}\033[0m")
        print(f"\033[38;5;214mGPU Capacity Planning Summary\033[0m")
        print(f"\033[38;5;214m{'─'*60}\033[0m")
        print(f"\n  Model: {result.get('model_size')}")
        print(f"  Memory Required: {result.get('model_memory_gb')}GB (FP16 precision)")
        print(f"  Instance Type: P5.48xlarge (8× H100 {result.get('gpu_memory')} GPUs)")
        print(f"  Total Memory per Instance: {result.get('total_per_instance_gb')}GB")
        print(f"\n\033[92m  → Instances Required: {result.get('instances_needed')}\033[0m")
        print(f"\n  Calculation: {result.get('equation')}")
    else:
        print(f"\n\033[91mStatus: {result.get('status')}\033[0m")
        print(f"  Message: {result.get('message', 'Unknown error')}")
    
    print(f"\n\033[38;5;214m{'='*60}\033[0m")


if __name__ == "__main__":
    main({})
