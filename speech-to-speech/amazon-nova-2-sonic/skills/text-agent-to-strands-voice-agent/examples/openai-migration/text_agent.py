"""
BEFORE: Raw OpenAI function-calling text agent.

A typical text agent using the OpenAI SDK with function calling.
This is the starting point for migration to voice.
"""

import json
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """You are a technical support specialist for CloudCorp.
Help users troubleshoot issues with their cloud infrastructure.
When diagnosing problems, always check the service status first.
Provide step-by-step solutions with exact CLI commands.
Format responses in markdown with code blocks for commands.
Include error codes in your responses for reference."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_service_status",
            "description": "Check the current status of a cloud service",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Name of the service (e.g., 'compute', 'storage', 'database')"
                    }
                },
                "required": ["service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_error_logs",
            "description": "Retrieve recent error logs for a service",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Service name"},
                    "hours": {"type": "integer", "description": "Hours of logs to retrieve", "default": 1}
                },
                "required": ["service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restart_service",
            "description": "Restart a cloud service instance",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Service to restart"},
                    "instance_id": {"type": "string", "description": "Instance ID"}
                },
                "required": ["service_name", "instance_id"]
            }
        }
    }
]


def check_service_status(service_name: str) -> str:
    return json.dumps({"service": service_name, "status": "degraded", "uptime": "99.2%", "incidents": 1})


def get_error_logs(service_name: str, hours: int = 1) -> str:
    return json.dumps({"service": service_name, "errors": [
        {"time": "14:32", "code": "E5012", "msg": "Connection timeout to primary replica"},
        {"time": "14:35", "code": "E5012", "msg": "Connection timeout to primary replica"},
    ]})


def restart_service(service_name: str, instance_id: str) -> str:
    return json.dumps({"status": "restarting", "service": service_name, "instance": instance_id, "eta": "30s"})


def run_text_agent(user_message: str):
    """Run a single turn of the text agent."""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        tools=TOOLS,
    )
    return response
