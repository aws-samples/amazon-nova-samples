# inline_agent.py
import json
import boto3
import uuid
import os
import time
import logging
from datetime import datetime
import asyncio
from threading import Lock
from typing import Any, Dict, Optional

# --- Constants ---
DEFAULT_REGION = os.getenv("AWS_REGION", "us-east-1")
DEFAULT_MODEL_ID = os.getenv("FOUNDATION_MODEL", "amazon.nova-lite-v1:0")
DEFAULT_SCHEMA_FILE = "./integration/booking_openapi.json"
DEFAULT_LOG_WAIT_TIME = 2
LAMBDA_ARN_ENV = "BOOKING_LAMBDA_ARN"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("inline_agent")

# --- Global Orchestrator Instance and Lock ---
_orchestrator: Optional["InlineAgentOrchestrator"] = None
_orchestrator_lock = Lock()

class InlineAgentOrchestrator:
    """Orchestrates interactions with Amazon Bedrock Inline Agents for booking management."""
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = self._get_default_config()
        if config:
            self.config.update(config)
        self._validate_config()
        self.client = boto3.client('bedrock-agent-runtime', region_name=self.config["region"])
        self.logs_client = boto3.client('logs', region_name=self.config["region"])
        self.schema = self._load_schema(self.config["schema_file"])
        self.lambda_arn = self._get_lambda_arn()
        self.lambda_name = self.lambda_arn.split(':')[-1]
        self.session_id = str(uuid.uuid4())
        self.lambda_log_group = f"/aws/lambda/{self.lambda_name}"
        logger.info(f"Session initialized: {self.session_id}")

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        return {
            "region": DEFAULT_REGION,
            "model_id": DEFAULT_MODEL_ID,
            "schema_file": DEFAULT_SCHEMA_FILE,
            "log_wait_time": DEFAULT_LOG_WAIT_TIME
        }

    def _validate_config(self) -> None:
        if not os.path.isfile(self.config["schema_file"]):
            raise RuntimeError(f"API schema file not found: {self.config['schema_file']}")
        if not os.getenv(LAMBDA_ARN_ENV):
            raise RuntimeError(f"{LAMBDA_ARN_ENV} environment variable must be set. Please run setup_booking_resources.sh and ensure .env is loaded.")

    @staticmethod
    def _load_schema(schema_file: str) -> Dict[str, Any]:
        try:
            with open(schema_file) as f:
                schema = json.load(f)
            logger.info(f"Loaded API schema from {schema_file}")
            return schema
        except Exception as e:
            logger.error(f"Failed to load API schema: {str(e)}")
            raise RuntimeError(f"Failed to load API schema: {str(e)}")

    @staticmethod
    def _get_lambda_arn() -> str:
        lambda_arn = os.getenv(LAMBDA_ARN_ENV)
        if not lambda_arn:
            raise RuntimeError(f"{LAMBDA_ARN_ENV} environment variable must be set.")
        logger.info(f"Using Lambda ARN: {lambda_arn}")
        return lambda_arn

    def invoke(self, query: str) -> str:
        try:
            time_before_call = datetime.now()
            logger.info(f"Invoking agent with query: {query}")
            logger.info(f"Session ID: {self.session_id}")
            request_params = self._prepare_request_params(query)
            logger.info("Sending request to Bedrock inline agent")
            agent_resp = self.client.invoke_inline_agent(**request_params)
            agent_answer = self._process_response(agent_resp)
            return agent_answer
        except Exception as e:
            logger.error(f"Error invoking agent: {str(e)}", exc_info=True)
            return f"Error invoking agent: {str(e)}"

    def _prepare_request_params(self, query: str) -> Dict[str, Any]:
        return {
            "inputText": query,
            "foundationModel": self.config["model_id"],
            "instruction": self._get_agent_instruction(),
            "sessionId": self.session_id,
            "endSession": False,
            "enableTrace": False,
            "actionGroups": [{
                'actionGroupName': 'BookingAPI',
                'actionGroupExecutor': {'lambda': self.lambda_arn},
                'apiSchema': {'payload': json.dumps(self.schema)}
            }]
        }

    @staticmethod
    def _get_agent_instruction() -> str:
        return InlineAgentOrchestrator.generate_agent_instruction()

    @staticmethod
    def generate_agent_instruction() -> str:
        """Generate the agent instruction string for inline agents. Edit here to customize agent behavior."""
        return (
            "You are a helpful assistant that can manage bookings. Use the BookingAPI to handle booking operations.\n"
            "\nWhen a user wants to update, view, or delete a booking but doesn't know the booking ID:\n"
            "1. Use the findBookingsByCustomer endpoint to search for bookings by customer name\n"
            "2. If bookings are found, show the results and ask which one they want to update\n"
            "3. If no bookings are found, inform the user and suggest creating a new booking\n"
            "\nWhen displaying booking information to the user:\n"
            "1. Format the information in a clear, readable way\n"
            "2. Include all relevant details like booking date, service type, and status\n"
            "3. If multiple bookings are found, list them all and ask which one the user wants to work with\n"
            "\nAlways try to extract customer names from the query to find relevant bookings before asking for a booking ID.\n"
            "Always specify the function name when invoking the Lambda function.\n"
            "\nIMPORTANT: When you use a tool (such as BookingAPI), ALWAYS use the tool's output to answer the user's question. Do not guess or make up an answer if a tool result is available. If the tool returns booking details, your answer MUST reflect the actual tool output.\n"
            "If only one booking is found for the customer, proceed to update it as requested by the user, without asking for confirmation. Only ask for confirmation if multiple bookings are found.\n"
            "When the user provides a date or time in natural language (e.g., \"6pm EST\", \"Sunday 2pm\"), interpret and convert it to a standard ISO 8601 format (e.g., \"2023-10-01T18:00:00-05:00\") before calling the API.\n"
            "Always use the field names as defined in the OpenAPI schema (e.g., booking_date).\n"
            "If the user provides a date/time in a non-standard format, do not ask the user to rephrase; instead, do your best to interpret and convert it automatically."
        )

    def _process_response(self, agent_resp: Dict[str, Any]) -> str:
        if agent_resp["ResponseMetadata"]["HTTPStatusCode"] != 200:
            logger.error(f"API Response was not 200: {agent_resp}")
            return f"API Response was not 200: {agent_resp}"
        agent_answer = ""
        event_stream = agent_resp["completion"]
        try:
            for event in event_stream:
                if "chunk" in event:
                    chunk_text = event["chunk"]["bytes"].decode("utf8")
                    logger.info(f"Chunk: {chunk_text}")
                    agent_answer += chunk_text
            return agent_answer
        except Exception as e:
            logger.error(f"Caught exception while processing response from invokeAgent:", exc_info=True)
            return f"Error processing agent response: {str(e)}"

    def get_lambda_logs(self, start_time: datetime) -> str:
        try:
            start_time_ms = int(start_time.timestamp() * 1000)
            end_time_ms = int(datetime.now().timestamp() * 1000)
            response = self.logs_client.describe_log_streams(
                logGroupName=self.lambda_log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            log_streams = response.get('logStreams', [])
            if not log_streams:
                return "No log streams found for Lambda function"
            log_stream_name = log_streams[0]['logStreamName']
            logs_response = self.logs_client.get_log_events(
                logGroupName=self.lambda_log_group,
                logStreamName=log_stream_name,
                startTime=start_time_ms,
                endTime=end_time_ms,
                limit=100
            )
            log_events = logs_response.get('events', [])
            if not log_events:
                return "No log events found for Lambda function in the specified time range"
            formatted_logs = [
                f"{datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')}: {event['message']}"
                for event in log_events
            ]
            return "\n".join(formatted_logs)
        except Exception as e:
            logger.error(f"Error getting Lambda logs: {str(e)}", exc_info=True)
            return f"Error getting Lambda logs: {str(e)}"

def get_orchestrator() -> InlineAgentOrchestrator:
    global _orchestrator
    with _orchestrator_lock:
        if _orchestrator is None:
            _orchestrator = InlineAgentOrchestrator()
        return _orchestrator

async def invoke_agent(query: str) -> str:
    orchestrator = get_orchestrator()
    try:
        return await asyncio.to_thread(orchestrator.invoke, query)
    except AttributeError:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, orchestrator.invoke, query)

async def cleanup_agent() -> None:
    """Clean up the orchestrator resources and reset the global instance."""
    global _orchestrator
    logger.info("Cleaning up inline agent resources")
    try:
        with _orchestrator_lock:
            if _orchestrator is not None:
                # Release any resources if needed
                logger.info(f"Releasing resources for session: {_orchestrator.session_id}")
                _orchestrator = None
                logger.info("Inline agent resources cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during inline agent cleanup: {str(e)}", exc_info=True)
        raise

def main() -> None:
    try:
        agent = InlineAgentOrchestrator()
        user_query = input("Enter your query: ")
        logger.info(f"Testing query: {user_query}")
        response = agent.invoke(user_query)
        logger.info(f"Response: {response}\n")
    except Exception as e:
        logger.error("Uncaught exception in main:", exc_info=True)
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
