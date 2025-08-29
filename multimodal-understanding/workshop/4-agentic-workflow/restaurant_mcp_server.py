import uuid
import boto3
import argparse
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any

# Initialize FastMCP server
mcp = FastMCP("restaurant_booking")

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Restaurant Booking MCP Server")
parser.add_argument("--table-name", help="DynamoDB table name")
args, unknown = parser.parse_known_args()

# Create/get the DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

# Get table name from environment variable, command-line argument, or use default
table_name = args.table_name
table = dynamodb.Table(table_name)


@mcp.tool()
def get_booking_details(booking_id: str) -> Dict[str, Any]:
    """
    Retrieve the details of a specific restaurant booking using its unique identifier.
    
    Args:
        booking_id: The unique identifier of the booking to retrieve.
        
    Returns:
        The booking details if found, otherwise a message indicating no booking was found.
    """
    try:
        response = table.get_item(Key={'booking_id': booking_id})
        if 'Item' in response:
            return response['Item']
        else:
            return {'message': f'No booking found with ID {booking_id}'}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def create_booking(date: str, name: str, hour: str, num_guests: int) -> Dict[str, Any]:
    """
    Create a new restaurant booking and store it in the DynamoDB table.
    
    Args:
        date: The date of the booking in YYYY-MM-DD format.
        name: The name to identify the reservation. Typically the guest's name.
        hour: The time of the booking in HH:MM format.
        num_guests: The number of guests for the booking.
        
    Returns:
        A dictionary containing the booking ID of the newly created reservation.
    """
    try:
        booking_id = str(uuid.uuid4())[:8]
        table.put_item(
            Item={
                'booking_id': booking_id,
                'date': date,
                'name': name,
                'hour': hour,
                'num_guests': num_guests
            }
        )
        return {'booking_id': booking_id}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def delete_booking(booking_id: str) -> Dict[str, Any]:
    """
    Delete an existing restaurant booking from the DynamoDB table.
    
    Args:
        booking_id: The unique identifier of the booking to delete.
        
    Returns:
        A message indicating whether the deletion was successful.
    """
    try:
        response = table.delete_item(Key={'booking_id': booking_id})
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return {'message': f'Booking with ID {booking_id} deleted successfully'}
        else:
            return {'message': f'Failed to delete booking with ID {booking_id}'}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def list_bookings() -> Dict[str, Any]:
    """
    List all current restaurant bookings.
    
    Returns:
        A dictionary containing a list of all bookings.
    """
    try:
        response = table.scan()
        bookings = response.get('Items', [])
        
        # Handle pagination if necessary
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            bookings.extend(response.get('Items', []))
        
        return {'bookings': bookings}
    except Exception as e:
        return {'error': str(e)}


if __name__ == "__main__":
    mcp.run(transport='stdio')