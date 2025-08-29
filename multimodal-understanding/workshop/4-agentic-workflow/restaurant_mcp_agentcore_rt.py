"""
Restaurant MCP Server for Amazon Bedrock AgentCore Runtime
Implements core MCP protocol functionality for restaurant booking system
"""

import uuid
import boto3
import sys
import logging
from typing import Dict, Any
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import current_time
from bedrock_agentcore import BedrockAgentCoreApp
import structlog

# Configure structured logging for both development and production
def configure_logging():
    """Configure structured logging compatible with Strands and AgentCore"""
    
    # Shared processors for both environments
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Choose output format based on environment (TTY for development)
    if sys.stderr.isatty():
        # Pretty printing for development
        processors = shared_processors + [
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # JSON output for production/AgentCore
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

# Initialize logging
configure_logging()
logger = structlog.get_logger(__name__)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table = None

# Initialize BedrockAgentCore app
app = BedrockAgentCoreApp()


agent_instruction="""
## Role
You are a ABC Restaurant Booking agent. You are in charge of restaurant reservations.

## Instructions
- Handle restaurant reservations inquiries and requests from users
- Create new bookings when requested with appropriate details - ask user for any required info
- Retrieve booking information when asked - use the get_booking_details tool for this
- update a booking - use the update_booking tool for this
- Cancel reservations when requested - use the delete_booking tool for this
- Be professional and courteous in all interactions
- Use the current_time tool to understand relative date terms like "today", "tomorrow", "next friday", etc.

## Output Requirements
- When responding to the end user, don't output your thinking steps
- Only give useful information to the end user
- Confirm all successful bookings, changes, and cancellations clearly"""

# Initialize the Amazon Bedrock model
model = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0",  # Using Amazon Nova Pro model
    max_tokens=3000,
    temperature=1,
    top_p=1,
    additional_request_fields={
        "inferenceConfig": {
            "topK": 1,
        },
    }
)


def init_dynamodb(table_name: str):
    """Initialize DynamoDB table"""
    global table
    table = dynamodb.Table(table_name)
    logger.info("DynamoDB table initialized", table_name=table_name)

@tool
def get_booking_details(booking_id: str) -> dict:
    """
    Retrieve the details of a specific restaurant booking using its unique identifier.

    This function queries the DynamoDB table to fetch the complete information
    associated with a given booking ID. It's useful for retrieving the full
    details of a reservation, including date, name, hour, and number of guests.

    Args:
        booking_id (str): The unique identifier of the booking to retrieve.
                          This should be a string, typically an 8-character UUID.

    Returns:
        dict: A dictionary containing the booking details if found. The structure includes:
              - booking_id (str): The unique identifier of the booking
              - date (str): The date of the booking in YYYY-MM-DD format
              - name (str): The name associated with the reservation
              - hour (str): The time of the booking in HH:MM format
              - num_guests (int): The number of guests for the booking
              
              If no booking is found, it returns a dictionary with a 'message' key
              indicating that no booking was found.
              In case of an error, it returns a dictionary with an 'error' key
              containing the error message.

    Raises:
        Exception: If there's an error in accessing the DynamoDB table or processing the request.
                   The error is caught and returned in the response dictionary.

    Example:
        >>> get_booking_details("12345678")
        {'booking_id': '12345678', 'date': '2023-05-15', 'name': 'John Doe', 'hour': '19:30', 'num_guests': 4}
    """
    try:
        logger.info("Retrieving booking details", booking_id=booking_id)
        response = table.get_item(Key={'booking_id': booking_id})
        if 'Item' in response:
            logger.info("Booking found", booking_id=booking_id, booking=response['Item'])
            return response['Item']
        else:
            logger.warning("Booking not found", booking_id=booking_id)
            return {'message': f'No booking found with ID {booking_id}'}
    except Exception as e:
        logger.error("Failed to retrieve booking", booking_id=booking_id, error=str(e), exc_info=True)
        return {'error': str(e)}

@tool
def create_booking(date: str, name: str, hour: str, num_guests: int) -> dict:
    """
    Create a new restaurant booking and store it in the DynamoDB table.

    This function generates a unique booking ID and creates a new entry in the
    DynamoDB table with the provided booking details. It's used to make new
    reservations in the restaurant booking system.

    Args:
        date (str): The date of the booking in YYYY-MM-DD format.
        name (str): The person's name to identify the reservation, typically the guest's name.
        hour (str): The time of the booking in HH:MM format.
        num_guests (int): The number of guests for the booking.

    Returns:
        dict: A dictionary containing the newly created booking ID if successful.
              The structure is:
              - booking_id (str): The unique identifier for the new booking (8-character UUID)
              
              In case of an error, it returns a dictionary with an 'error' key
              containing the error message.

    Raises:
        Exception: If there's an error in generating the UUID, accessing the DynamoDB table,
                   or processing the request. The error is caught and returned in the response dictionary.

    Example:
        >>> create_booking("2023-05-15", "John Doe", "19:30", 4)
        {'booking_id': 'a1b2c3d4'}
    """
    try:
        booking_id = str(uuid.uuid4())[:8]
        booking_data = {
            'booking_id': booking_id,
            'date': date,
            'name': name,
            'hour': hour,
            'num_guests': num_guests
        }
        
        logger.info("Creating new booking", **booking_data)
        table.put_item(Item=booking_data)
        logger.info("Booking created successfully", booking_id=booking_id)
        return {'booking_id': booking_id}
    except Exception as e:
        logger.error("Failed to create booking", date=date, name=name, hour=hour,
                    num_guests=num_guests, error=str(e), exc_info=True)
        return {'error': str(e)}
    
@tool
def delete_booking(booking_id: str) -> dict:
    """
    Delete an existing restaurant booking from the DynamoDB table.

    This function removes a booking entry from the database based on the provided
    booking ID. It's used to cancel reservations in the restaurant booking system.

    Args:
        booking_id (str): The unique identifier of the booking to delete.
                          This should be a string, typically an 8-character UUID.

    Returns:
        dict: A dictionary containing a message indicating the result of the operation.
              If successful, the structure is:
              - message (str): A success message with the deleted booking ID
              
              If the deletion fails (but doesn't raise an exception), it returns a
              dictionary with a message indicating the failure.
              
              In case of an error, it returns a dictionary with an 'error' key
              containing the error message.

    Raises:
        Exception: If there's an error in accessing the DynamoDB table or processing the request.
                   The error is caught and returned in the response dictionary.

    Example:
        >>> delete_booking("a1b2c3d4")
        {'message': 'Booking with ID a1b2c3d4 deleted successfully'}
    """
    try:
        logger.info("Deleting booking", booking_id=booking_id)
        response = table.delete_item(Key={'booking_id': booking_id})
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            logger.info("Booking deleted successfully", booking_id=booking_id)
            return {'message': f'Booking with ID {booking_id} deleted successfully'}
        else:
            logger.error("Failed to delete booking", booking_id=booking_id,
                        http_status=response['ResponseMetadata']['HTTPStatusCode'])
            return {'message': f'Failed to delete booking with ID {booking_id}'}
    except Exception as e:
        logger.error("Exception during booking deletion", booking_id=booking_id,
                    error=str(e), exc_info=True)
        return {'error': str(e)}

@tool
def list_bookings() -> Dict[str, Any]:
    """List all current bookings"""
    try:
        logger.info("Listing all bookings")
        response = table.scan()
        bookings = response.get('Items', [])
        logger.info("Retrieved bookings", count=len(bookings))
        return {'bookings': bookings}
    except Exception as e:
        logger.error("Failed to list bookings", error=str(e), exc_info=True)
        return {'error': str(e)}

@tool
def update_booking(booking_id: str = None, name: str = None, new_date: str = None, new_name: str = None, new_hour: str = None, new_num_guests: int = None) -> dict:
    """
    Update an existing restaurant booking. First finds the booking by ID or name, then updates the specified fields.
    
    Args:
        booking_id (str, optional): The unique identifier of the booking to update
        name (str, optional): The name on the booking to search for (if booking_id not provided)
        new_date (str, optional): New date for the booking in YYYY-MM-DD format
        new_name (str, optional): New name for the booking
        new_hour (str, optional): New time for the booking in HH:MM format
        new_num_guests (int, optional): New number of guests
    
    Returns:
        dict: Success message with updated booking details or error message
    """
    try:
        logger.info("Updating booking", booking_id=booking_id, name=name,
                   new_date=new_date, new_name=new_name, new_hour=new_hour,
                   new_num_guests=new_num_guests)
        
        # Find the booking
        booking = None
        if booking_id:
            response = table.get_item(Key={'booking_id': booking_id})
            if 'Item' in response:
                booking = response['Item']
                logger.debug("Booking found by ID", booking_id=booking_id)
        elif name:
            logger.debug("Searching booking by name", name=name)
            # Search by name
            response = table.scan(
                FilterExpression='#name = :name',
                ExpressionAttributeNames={'#name': 'name'},
                ExpressionAttributeValues={':name': name}
            )
            if response['Items']:
                booking = response['Items'][0]
                booking_id = booking['booking_id']
                logger.debug("Booking found by name", name=name, booking_id=booking_id)
        
        if not booking:
            logger.warning("No booking found for update", booking_id=booking_id, name=name)
            return {'error': 'No booking found with the provided information'}
        
        # Update fields
        update_expression = 'SET '
        expression_values = {}
        expression_names = {}
        updates = []
        
        if new_date:
            updates.append('#date = :date')
            expression_values[':date'] = new_date
            expression_names['#date'] = 'date'
        if new_name:
            updates.append('#name = :name')
            expression_values[':name'] = new_name
            expression_names['#name'] = 'name'
        if new_hour:
            updates.append('#hour = :hour')
            expression_values[':hour'] = new_hour
            expression_names['#hour'] = 'hour'
        if new_num_guests:
            updates.append('#num_guests = :num_guests')
            expression_values[':num_guests'] = new_num_guests
            expression_names['#num_guests'] = 'num_guests'

        if not updates:
            logger.warning("No update fields specified", booking_id=booking_id)
            return {'error': 'No updates specified'}
        
        update_expression += ', '.join(updates)
    
        
        logger.info("Executing booking update", booking_id=booking_id, updates=updates)
        table.update_item(
            Key={'booking_id': booking_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names
        )
        
        # Get updated booking
        updated_response = table.get_item(Key={'booking_id': booking_id})
        updated_booking = updated_response['Item']
        
        logger.info("Booking updated successfully", booking_id=booking_id,
                   updated_booking=updated_booking)
        return {'message': f'Booking {booking_id} updated successfully', 'updated_booking': updated_booking}
    except Exception as e:
        logger.error("Failed to update booking", booking_id=booking_id, name=name,
                    error=str(e), exc_info=True)
        return {'error': str(e)}

agent = Agent(
    model=model,
    system_prompt=agent_instruction,
    tools=[current_time, get_booking_details, create_booking, delete_booking, update_booking, list_bookings],
    callback_handler=None
)

@app.entrypoint
async def agent_invocation(payload):
    """Handler for agent invocation"""
    # Create a context-bound logger for this request
    request_logger = logger.bind(
        request_id=str(uuid.uuid4())[:8],
        agent_type="restaurant_booking"
    )
    
    user_message = payload.get(
        "prompt", "No prompt found in input, please guide customer to create a json payload with prompt key"
    )
    
    request_logger.info("Agent invocation started",
                       user_message=user_message[:100] + "..." if len(user_message) > 100 else user_message,
                       payload_keys=list(payload.keys()))
    
    try:
        stream = agent.stream_async(user_message)
        thinking_opening_tag = '<thinking>'
        thinking_closing_tag = '</thinking>'
        response_tracking = '' # for tracking thinking
        in_thinking = False
        response_chunks = 0
        
        async for event in stream:
            if "data" in event:
                response_chunks += 1
                # Only stream text chunks to the client
                response_tracking += event["data"].replace('\n','').replace(' ','')
                # detect opening tag
                if len(response_tracking) <= len(thinking_opening_tag) and response_tracking[:len(response_tracking)] == thinking_opening_tag[:len(response_tracking)]:
                    in_thinking = True
                elif thinking_closing_tag in response_tracking:
                    in_thinking = False

                if not in_thinking:
                    yield event["data"]
        
        request_logger.info("Agent invocation completed",
                          response_chunks=response_chunks,
                          final_response_length=len(response_tracking))
    
    except Exception as e:
        request_logger.error("Agent invocation failed",
                           error=str(e),
                           exc_info=True)
        yield f"Error: {str(e)}"


if __name__ == "__main__":
    # import argparse
    # parser = argparse.ArgumentParser(description="Restaurant Booking MCP Server for AgentCore")
    # parser.add_argument("--table-name", required=True, help="DynamoDB table name")
    # args = parser.parse_args()

    logger.info("Starting Restaurant MCP AgentCore Server")
    init_dynamodb('restaurant_bookings')
    logger.info("Server initialized successfully, starting AgentCore app")
    app.run()