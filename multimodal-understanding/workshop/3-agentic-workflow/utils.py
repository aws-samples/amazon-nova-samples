import boto3
import json
import time
import zipfile
import logging
import pprint
from io import BytesIO
import pandas as pd
import os
import re
from typing import List, Tuple
from functools import partial

region = os.environ['AWS_REGION']
session = boto3.session.Session(region_name=region)

iam_client = session.client('iam')
sts_client = session.client('sts')
account_id = sts_client.get_caller_identity()["Account"]
dynamodb_client = session.client('dynamodb')
dynamodb_resource = session.resource('dynamodb')
lambda_client = session.client('lambda')
bedrock_agent_client = session.client('bedrock-agent')
bedrock_agent_runtime_client = session.client('bedrock-agent-runtime')
bedrock_client = session.client(service_name="bedrock-runtime")
cf_client = session.client("cloudformation")


logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Using region {region} for this workshop")

# CloudFormation template names for stack lookup
CF_TEMPLATE_NAMES = ["workshop-studio", "mmu_understanding_workshop", "mmu-workshop", "mmu-workshop-test"]


def create_lambda(lambda_function_name, lambda_iam_role):
    # add to function

    # Package up the lambda function code
    s = BytesIO()
    z = zipfile.ZipFile(s, 'w')
    z.write("lambda_function.py")
    z.close()
    zip_content = s.getvalue()
    try:
        # Create Lambda Function
        lambda_function = lambda_client.create_function(
            FunctionName=lambda_function_name,
            Runtime='python3.12',
            Timeout=60,
            Role=lambda_iam_role['Role']['Arn'],
            Code={'ZipFile': zip_content},
            Handler='lambda_function.lambda_handler'
        )
    except lambda_client.exceptions.ResourceConflictException:
        print("Lambda function already exists, retrieving it")
        lambda_function = lambda_client.get_function(
            FunctionName=lambda_function_name
        )
        lambda_function = lambda_function['Configuration']

    return lambda_function


def create_lambda_role(agent_name, dynamodb_table_name):
    lambda_function_role = f'{agent_name}-lambda-role'
    dynamodb_access_policy_name = f'{agent_name}-dynamodb-policy'
    # Create IAM Role for the Lambda function
    try:
        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        assume_role_policy_document_json = json.dumps(assume_role_policy_document)

        lambda_iam_role = iam_client.create_role(
            RoleName=lambda_function_role,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )

        # Pause to make sure role is created
        time.sleep(10)
    except iam_client.exceptions.EntityAlreadyExistsException:
        lambda_iam_role = iam_client.get_role(RoleName=lambda_function_role)

    # Attach the AWSLambdaBasicExecutionRole policy
    iam_client.attach_role_policy(
        RoleName=lambda_function_role,
        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    )

    # Create a policy to grant access to the DynamoDB table
    dynamodb_access_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem"
                ],
                "Resource": "arn:aws:dynamodb:{}:{}:table/{}".format(
                    region, account_id, dynamodb_table_name
                )
            }
        ]
    }

    # Create the policy
    dynamodb_access_policy_json = json.dumps(dynamodb_access_policy)
    try:
        dynamodb_access_policy = iam_client.create_policy(
            PolicyName=dynamodb_access_policy_name,
            PolicyDocument=dynamodb_access_policy_json
        )
    except iam_client.exceptions.EntityAlreadyExistsException:
        dynamodb_access_policy = iam_client.get_policy(
            PolicyArn=f"arn:aws:iam::{account_id}:policy/{dynamodb_access_policy_name}"
        )

    # Attach the policy to the Lambda function's role
    iam_client.attach_role_policy(
        RoleName=lambda_function_role,
        PolicyArn=dynamodb_access_policy['Policy']['Arn']
    )
    return lambda_iam_role


def invoke_agent_helper(query, session_id, agent_id, alias_id, enable_trace=False, session_state=None):
    end_session: bool = False
    if not session_state:
        session_state = {}

    # invoke the agent API
    agent_response = bedrock_agent_runtime_client.invoke_agent(
        inputText=query,
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        enableTrace=enable_trace,
        endSession=end_session,
        sessionState=session_state
    )

    if enable_trace:
        logger.info(pprint.pprint(agent_response))

    event_stream = agent_response['completion']
    try:
        for event in event_stream:
            if 'chunk' in event:
                data = event['chunk']['bytes']
                if enable_trace:
                    logger.info(f"Final answer ->\n{data.decode('utf8')}")
                agent_answer = data.decode('utf8')
                return agent_answer
                # End event indicates that the request finished successfully
            elif 'trace' in event:
                if enable_trace:
                    logger.info(json.dumps(event['trace'], indent=2))
            else:
                raise Exception("unexpected event.", event)
    except Exception as e:
        raise Exception("unexpected event.", e)


def create_agent_role(agent_name, agent_foundation_model, kb_id=None):
    agent_bedrock_allow_policy_name = f"{agent_name}-ba"
    agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{agent_name}'
    # Create IAM policies for agent
    statements = [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel*",
                "bedrock:CreateInferenceProfile"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:*:inference-profile/*",
                "arn:aws:bedrock:*:*:application-inference-profile/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:GetInferenceProfile",
                "bedrock:ListInferenceProfiles",
                "bedrock:DeleteInferenceProfile",
                "bedrock:TagResource",
                "bedrock:UntagResource",
                "bedrock:ListTagsForResource"
            ],
            "Resource": [
                "arn:aws:bedrock:*:*:inference-profile/*",
                "arn:aws:bedrock:*:*:application-inference-profile/*"
            ]
        }
    ]
    # add Knowledge Base retrieve and retrieve and generate permissions if agent has KB attached to it
    if kb_id:
        statements.append(
            {
                "Sid": "QueryKB",
                "Effect": "Allow",
                "Action": [
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/{kb_id}"
                ]
            }
        )

    bedrock_agent_bedrock_allow_policy_statement = {
        "Version": "2012-10-17",
        "Statement": statements
    }

    bedrock_policy_json = json.dumps(bedrock_agent_bedrock_allow_policy_statement)
    try:
        agent_bedrock_policy = iam_client.create_policy(
            PolicyName=agent_bedrock_allow_policy_name,
            PolicyDocument=bedrock_policy_json
        )
    except iam_client.exceptions.EntityAlreadyExistsException:
        agent_bedrock_policy = iam_client.get_policy(
            PolicyArn=f"arn:aws:iam::{account_id}:policy/{agent_bedrock_allow_policy_name}"
        )

    # Create IAM Role for the agent and attach IAM policies
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)
    try:
        agent_role = iam_client.create_role(
            RoleName=agent_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )

        # Pause to make sure role is created
        time.sleep(10)
    except iam_client.exceptions.EntityAlreadyExistsException:
        agent_role = iam_client.get_role(
            RoleName=agent_role_name,
        )

    iam_client.attach_role_policy(
        RoleName=agent_role_name,
        PolicyArn=agent_bedrock_policy['Policy']['Arn']
    )
    return agent_role


def create_agent_core_execution_role(agent_name):
    agent_core_policy_name = f"{agent_name}-agentcore-policy"
    agent_core_role_name = f'AgentCoreExecutionRole_{agent_name}'

    # logger.info(f"Using region {region}")
    
    # Create IAM policy for agent core
    agent_core_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ECRImageAccess",
                "Effect": "Allow",
                "Action": [
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer"
                ],
                "Resource": [
                    f"arn:aws:ecr:{region}:{account_id}:repository/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogStreams",
                    "logs:CreateLogGroup"
                ],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogGroups"
                ],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                ]
            },
            {
                "Sid": "ECRTokenAccess",
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets"
                ],
                "Resource": [
                    "*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "cloudformation:DescribeStacks"
                ],
                "Resource": [
                    f"arn:aws:cloudformation:{region}:{account_id}:stack/*",
                    f"arn:aws:cloudformation:{region}:{account_id}:stack/*/*"
                ]
            },
            {
                "Effect": "Allow",
                "Resource": "*",
                "Action": "cloudwatch:PutMetricData",
                "Condition": {
                    "StringEquals": {
                        "cloudwatch:namespace": "bedrock-agentcore"
                    }
                }
            },
            {
                "Sid": "GetAgentAccessToken",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetWorkloadAccessToken",
                    "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                    "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/{agent_name}-*"
                ]
            },
            {
                "Sid": "BedrockModelInvocation",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:ApplyGuardrail"
                ],
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:{region}:{account_id}:*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:CreateAgentRuntime",
                    "bedrock-agentcore:InvokeAgentRuntime"
                ],
                "Resource": [
                    "*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:GetEvent",
                    "bedrock-agentcore:DeleteEvent",
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/*"
                ]
            }
        ]
    }

    policy_json = json.dumps(agent_core_policy)
    try:
        agent_core_policy_response = iam_client.create_policy(
            PolicyName=agent_core_policy_name,
            PolicyDocument=policy_json
        )
    except iam_client.exceptions.EntityAlreadyExistsException:
        agent_core_policy_response = iam_client.get_policy(
            PolicyArn=f"arn:aws:iam::{account_id}:policy/{agent_core_policy_name}"
        )

    # trust policy for agent core rt exec role
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AssumeRolePolicy",
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": f"{account_id}"
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                    }
                }
            }
        ]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)
    try:
        agent_core_role = iam_client.create_role(
            RoleName=agent_core_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )
        time.sleep(10)
    except iam_client.exceptions.EntityAlreadyExistsException:
        agent_core_role = iam_client.get_role(
            RoleName=agent_core_role_name,
        )
    # attaching policies
    iam_client.attach_role_policy(
        RoleName=agent_core_role_name,
        PolicyArn=agent_core_policy_response['Policy']['Arn']
    )

    # attaching bedrock agent core full access
    iam_client.attach_role_policy(
        RoleName=agent_core_role_name,
        PolicyArn="arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess"
    )
    return agent_core_role['Role']['Arn']


def delete_agent_roles_and_policies(agent_name, kb_policy_name):
    agent_bedrock_allow_policy_name = f"{agent_name}-ba"
    agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{agent_name}'
    dynamodb_access_policy_name = f'{agent_name}-dynamodb-policy'
    lambda_function_role = f'{agent_name}-lambda-role'

    for policy in [agent_bedrock_allow_policy_name, kb_policy_name]:
        try:
            iam_client.detach_role_policy(
                RoleName=agent_role_name,
                PolicyArn=f'arn:aws:iam::{account_id}:policy/{policy}'
            )
        except Exception as e:
            print(f"Could not detach {policy} from {agent_role_name}")
            print(e)

    for policy in [dynamodb_access_policy_name]:
        try:
            iam_client.detach_role_policy(
                RoleName=lambda_function_role,
                PolicyArn=f'arn:aws:iam::{account_id}:policy/{policy}'
            )
        except Exception as e:
            print(f"Could not detach {policy} from {lambda_function_role}")
            print(e)

    try:
        iam_client.detach_role_policy(
            RoleName=lambda_function_role,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
    except Exception as e:
        print(f"Could not detach AWSLambdaBasicExecutionRole from {lambda_function_role}")
        print(e)

    for role_name in [agent_role_name, lambda_function_role]:
        try:
            iam_client.delete_role(
                RoleName=role_name
            )
        except Exception as e:
            print(f"Could not delete role {role_name}")
            print(e)

    for policy in [agent_bedrock_allow_policy_name, kb_policy_name, dynamodb_access_policy_name]:
        try:
            iam_client.delete_policy(
                PolicyArn=f'arn:aws:iam::{account_id}:policy/{policy}'
            )
        except Exception as e:
            print(f"Could not delete policy {policy}")
            print(e)


def clean_up_resources(
        table_name, lambda_function, lambda_function_name, agent_action_group_response, agent_functions,
        agent_id, kb_id, alias_id
):
    action_group_id = agent_action_group_response['agentActionGroup']['actionGroupId']
    action_group_name = agent_action_group_response['agentActionGroup']['actionGroupName']
    # Delete Agent Action Group, Agent Alias, and Agent
    try:
        bedrock_agent_client.update_agent_action_group(
            agentId=agent_id,
            agentVersion='DRAFT',
            actionGroupId= action_group_id,
            actionGroupName=action_group_name,
            actionGroupExecutor={
                'lambda': lambda_function['FunctionArn']
            },
            functionSchema={
                'functions': agent_functions
            },
            actionGroupState='DISABLED',
        )
        bedrock_agent_client.disassociate_agent_knowledge_base(
            agentId=agent_id,
            agentVersion='DRAFT',
            knowledgeBaseId=kb_id
        )
        bedrock_agent_client.delete_agent_action_group(
            agentId=agent_id,
            agentVersion='DRAFT',
            actionGroupId=action_group_id
        )
        bedrock_agent_client.delete_agent_alias(
            agentAliasId=alias_id,
            agentId=agent_id
        )
        bedrock_agent_client.delete_agent(agentId=agent_id)
        print(f"Agent {agent_id}, Agent Alias {alias_id}, and Action Group have been deleted.")
    except Exception as e:
        print(f"Error deleting Agent resources: {e}")

    # Delete Lambda function
    try:
        lambda_client.delete_function(FunctionName=lambda_function_name)
        print(f"Lambda function {lambda_function_name} has been deleted.")
    except Exception as e:
        print(f"Error deleting Lambda function {lambda_function_name}: {e}")

    # Delete DynamoDB table
    try:
        dynamodb_client.delete_table(TableName=table_name)
        print(f"Table {table_name} is being deleted...")
        waiter = dynamodb_client.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name)
        print(f"Table {table_name} has been deleted.")
    except Exception as e:
        print(f"Error deleting table {table_name}: {e}")


# =============================================================================
# CLOUDFORMATION UTILITIES (from utilities.py)
# =============================================================================

def get_cf_stack():
    """Use boto3 to lookup information about the CF stack."""
    import sys
    for name in CF_TEMPLATE_NAMES:
        print(f"Trying stack name {name}...", file=sys.stderr)
        try:
            response = cf_client.describe_stacks(StackName=name)
            return response
        except Exception as ex:
            pass
    return None


def extract_CF_outputs(*output_names: List[str]) -> List[str]:
    """
    Given a list of names of outputs in CF_TEMPLATE_NAME, return the
    corresponding value (or None, if the output doesn't exist).
    """
    response = get_cf_stack()
    outputs = response['Stacks'][0]['Outputs']

    def output_key_matches(x: dict, output_name: str) -> bool:
        return x["OutputKey"] == output_name

    required_outputs = [next(filter(partial(output_key_matches, output_name=output_name), outputs),
                             None)
                        for output_name in output_names]
    required_values = [output["OutputValue"] if output else None
                       for output in required_outputs]
    return required_values


def extract_s3_bucket(s3_url_a_like: str) -> str:
    """
    Given an S3 location, like 's3://<bucket-name>/<key>', return
    the <key> part.
    """
    if s3_url_a_like.startswith("s3://"):
        s3_url_a_like = s3_url_a_like[5:]
    try:
        return s3_url_a_like.split("/")[0]
    except:
        return s3_url_a_like


def extract_tag(response: str, name: str, greedy: bool = True) -> Tuple[str, int]:
    """
    Extract content between XML-style tags.
    
    Args:
        response: String containing the tags
        name: Tag name to extract
        greedy: If True, use greedy matching; if False, use non-greedy
        
    Returns:
        Tuple of (extracted content, end position)
        
    Example:
        >>> extract_tag("foo <a>baz</a> bar", "a")
        ('baz', 10)
    """
    import sys
    patn = f"<{name}>(.*)</{name}>" if greedy else\
           f"<{name}>(.*?)</{name}>"
    match = re.search(patn, response, re.DOTALL)
    if match:
        return match.group(1).strip(), match.end(1)
    else:
        print(f"Couldn't find tag {name} in <<<{response}>>>", file=sys.stderr)
        return "", -1


def initialize_database_from_cloudformation(
    database_name: str = 'customer_db',
    logger_instance = None
):
    """
    Initialize database configuration from CloudFormation outputs.
    
    Args:
        database_name: Name of the database to connect to (default: 'customer_db')
        logger_instance: Optional logger instance for structured logging
        
    Returns:
        SQLAlchemy engine configured with CloudFormation database credentials
        
    Raises:
        RuntimeError: If database configuration cannot be initialized from CloudFormation
    """
    from sqlalchemy import create_engine
    
    # Use provided logger or create a simple one
    if logger_instance:
        db_logger = logger_instance.bind(operation="database_initialization")
    else:
        db_logger = None
    
    try:
        if db_logger:
            db_logger.info("Extracting database configuration from CloudFormation outputs")
        
            mysql_host, mysql_user, mysql_password = extract_CF_outputs(
                "RDSInstanceEndpoint", "DbUser", "DbPassword"
            )
            
            db_logger.info(
                "Database configuration extracted successfully",
                host=mysql_host,
                database=database_name,
                user=mysql_user
            )
        
            db_logger.info("Creating database engine", host=mysql_host, database=database_name)
            
            engine = create_engine(
                f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:3306/{database_name}"
            )
            
            db_logger.info("Database engine created successfully")
        
            return engine
        
    except Exception as e:
        if db_logger:
            db_logger.error(
                "Failed to initialize database configuration",
                error=str(e),
                error_type=type(e).__name__
            )
        raise RuntimeError(
            "Database configuration could not be initialized. "
            "Please ensure CloudFormation stack outputs are available and accessible."
        ) from e
