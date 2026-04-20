"""
BEFORE: Generic custom text agent — no framework.

A simple agent loop using boto3 Bedrock converse API directly.
Represents any hand-rolled text agent that someone might want to voice-enable.
"""

import json
import boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

SYSTEM_PROMPT = """You are a restaurant reservation assistant for La Maison.
Help customers make, modify, and cancel reservations.
Always confirm the date, time, party size, and any special requests.
Respond in a structured format:
- Reservation ID: [ID]
- Date: [YYYY-MM-DD]
- Time: [HH:MM]
- Party size: [N]
- Special requests: [notes]
If no tables are available, suggest the nearest alternative time."""

TOOLS = [
    {
        "toolSpec": {
            "name": "check_availability",
            "description": "Check table availability for a given date, time, and party size",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                        "time": {"type": "string", "description": "Time in HH:MM format"},
                        "party_size": {"type": "integer", "description": "Number of guests"}
                    },
                    "required": ["date", "time", "party_size"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "make_reservation",
            "description": "Create a new reservation",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "time": {"type": "string"},
                        "party_size": {"type": "integer"},
                        "customer_name": {"type": "string"},
                        "special_requests": {"type": "string", "default": ""}
                    },
                    "required": ["date", "time", "party_size", "customer_name"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "cancel_reservation",
            "description": "Cancel an existing reservation by ID",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {"type": "string", "description": "The reservation ID"}
                    },
                    "required": ["reservation_id"]
                }
            }
        }
    }
]


def check_availability(date: str, time: str, party_size: int) -> dict:
    return {"available": True, "tables": [{"id": "T12", "seats": 4}, {"id": "T15", "seats": 6}]}


def make_reservation(date: str, time: str, party_size: int, customer_name: str,
                     special_requests: str = "") -> dict:
    return {"reservation_id": "RES-20240304-001", "date": date, "time": time,
            "party_size": party_size, "customer_name": customer_name,
            "special_requests": special_requests, "status": "confirmed"}


def cancel_reservation(reservation_id: str) -> dict:
    return {"reservation_id": reservation_id, "status": "cancelled"}


def run_text_agent(user_message: str, conversation_history: list = None):
    """Run a single turn of the custom text agent using Bedrock Converse."""
    messages = conversation_history or []
    messages.append({"role": "user", "content": [{"text": user_message}]})

    response = bedrock.converse(
        modelId="us.amazon.nova-2-lite-v1:0",
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        toolConfig={"tools": TOOLS},
    )
    return response
