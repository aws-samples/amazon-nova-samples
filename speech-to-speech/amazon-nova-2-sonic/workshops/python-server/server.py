import asyncio
import websockets
import json
import logging
import warnings
from s2s_session_manager import S2sSessionManager
import argparse
import http.server
import threading
import os
from http import HTTPStatus
from integration.mcp_client import McpLocationClient
from integration.strands_agent import StrandsAgent

# Configure logging
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings("ignore")

DEBUG = False

def debug_print(message):
    """Print only if debug mode is enabled"""
    if DEBUG:
        print(message)

MCP_CLIENT = None
STRANDS_AGENT = None

class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        client_ip = self.client_address[0]
        logger.info(
            f"Health check request received from {client_ip} for path: {self.path}"
        )

        if self.path == "/health" or self.path == "/":
            logger.info(f"Responding with 200 OK to health check from {client_ip}")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps({"status": "healthy"})
            self.wfile.write(response.encode("utf-8"))
            logger.info(f"Health check response sent: {response}")
        else:
            logger.info(
                f"Responding with 404 Not Found to request for {self.path} from {client_ip}"
            )
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()

    def log_message(self, format, *args):
        # Override to use our logger instead
        pass


def start_health_check_server(health_host, health_port):
    """Start the HTTP health check server on port 80."""
    try:
        # Create the server with a socket timeout to prevent hanging
        httpd = http.server.HTTPServer((health_host, health_port), HealthCheckHandler)
        httpd.timeout = 5  # 5 second timeout

        logger.info(f"Starting health check server on {health_host}:{health_port}")

        # Run the server in a separate thread
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = (
            True  # This ensures the thread will exit when the main program exits
        )
        thread.start()

        # Verify the server is running
        logger.info(
            f"Health check server started at http://{health_host}:{health_port}/health"
        )
        logger.info(f"Health check thread is alive: {thread.is_alive()}")

        # Try to make a local request to verify the server is responding
        try:
            import urllib.request

            with urllib.request.urlopen(
                f"http://localhost:{health_port}/health", timeout=2
            ) as response:
                logger.info(
                    f"Local health check test: {response.status} - {response.read().decode('utf-8')}"
                )
        except Exception as e:
            logger.warning(f"Local health check test failed: {e}")

    except Exception as e:
        logger.error(f"Failed to start health check server: {e}", exc_info=True)


async def websocket_handler(websocket):
    aws_region = os.getenv("AWS_DEFAULT_REGION")
    if not aws_region:
        aws_region = "us-east-1"

    stream_manager = None
    forward_task = None
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if 'body' in data:
                    data = json.loads(data["body"])
                if 'event' in data:
                    event_type = list(data['event'].keys())[0]
                    
                    # Handle session start - create new stream manager
                    if event_type == 'sessionStart':
                        # Clean up existing session if any
                        if stream_manager:
                            await stream_manager.close()
                        if forward_task and not forward_task.done():
                            forward_task.cancel()
                            try:
                                await forward_task
                            except asyncio.CancelledError:
                                pass

                        """Handle WebSocket connections from the frontend."""
                        # Create a new stream manager for this connection
                        stream_manager = S2sSessionManager(model_id='amazon.nova-2-sonic-v1:0', region=aws_region, mcp_client=MCP_CLIENT, strands_agent=STRANDS_AGENT)
                        
                        # Initialize the Bedrock stream
                        await stream_manager.initialize_stream()
                        
                        # Start a task to forward responses from Bedrock to the WebSocket
                        forward_task = asyncio.create_task(forward_responses(websocket, stream_manager))

                    # Handle session end - clean up resources
                    elif event_type == 'sessionEnd':
                        if stream_manager:
                            await stream_manager.close()
                            stream_manager = None
                        if forward_task and not forward_task.done():
                            forward_task.cancel()
                            try:
                                await forward_task
                            except asyncio.CancelledError:
                                pass
                            forward_task = None

                    if event_type == "audioInput":
                        debug_print(message[0:180])
                    else:
                        debug_print(message)
                    
                    # Only process events if we have an active stream manager
                    if stream_manager and stream_manager.is_active:
                        # Store prompt name and content names if provided
                        if event_type == 'promptStart':
                            stream_manager.prompt_name = data['event']['promptStart']['promptName']
                        elif event_type == 'contentStart' and data['event']['contentStart'].get('type') == 'AUDIO':
                            stream_manager.audio_content_name = data['event']['contentStart']['contentName']
                        
                        # Handle audio input separately
                        if event_type == 'audioInput':
                            # Extract audio data
                            prompt_name = data['event']['audioInput']['promptName']
                            content_name = data['event']['audioInput']['contentName']
                            audio_base64 = data['event']['audioInput']['content']
                            
                            # Add to the audio queue
                            stream_manager.add_audio_chunk(prompt_name, content_name, audio_base64)
                        else:
                            # Send other events directly to Bedrock
                            await stream_manager.send_raw_event(data)
                    elif event_type not in ['sessionStart', 'sessionEnd']:
                        debug_print(f"Received event {event_type} but no active stream manager")
                        
            except json.JSONDecodeError:
                print("Invalid JSON received from WebSocket")
            except Exception as e:
                print(f"Error processing WebSocket message: {e}")
                if DEBUG:
                    import traceback
                    traceback.print_exc()
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")
    finally:
        # Clean up resources
        if stream_manager:
            await stream_manager.close()
        if forward_task and not forward_task.done():
            forward_task.cancel()
            try:
                await forward_task
            except asyncio.CancelledError:
                pass
        if MCP_CLIENT:
            MCP_CLIENT.cleanup()


async def forward_responses(websocket, stream_manager):
    """Forward responses from Bedrock to the WebSocket."""
    try:
        while True:
            # Get next response from the output queue
            response = await stream_manager.output_queue.get()
            
            # Send to WebSocket
            try:
                event = json.dumps(response)
                await websocket.send(event)
            except websockets.exceptions.ConnectionClosed:
                break
    except asyncio.CancelledError:
        # Task was cancelled
        pass
    except Exception as e:
        print(f"Error forwarding responses: {e}")
        # Close connection
        websocket.close()
        stream_manager.close()


async def main(host, port, health_port, enable_mcp=False, enable_strands_agent=False):

    if health_port:
        try:
            start_health_check_server(host, health_port)
        except Exception as ex:
            print("Failed to start health check endpoint",ex)
    
    # Init MCP client
    if enable_mcp:
        print("MCP enabled")
        try:
            global MCP_CLIENT
            MCP_CLIENT = McpLocationClient()
            await MCP_CLIENT.connect_to_server()
        except Exception as ex:
            print("Failed to start MCP client",ex)
    
    # Init Strands Agent
    if enable_strands_agent:
        print("Strands agent enabled")
        try:
            global STRANDS_AGENT
            STRANDS_AGENT = StrandsAgent()
        except Exception as ex:
            print("Failed to start MCP client",ex)

    """Main function to run the WebSocket server."""
    try:
        # Start WebSocket server
        async with websockets.serve(websocket_handler, host, port):
            print(f"WebSocket server started at host:{host}, port:{port}")
            
            # Keep the server running forever
            await asyncio.Future()
    except Exception as ex:
        print("Failed to start websocket service",ex)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Nova S2S WebSocket Server')
    parser.add_argument('--agent', type=str, help='Agent intergation "mcp" or "strands".')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    host, port, health_port = None, None, None
    host = str(os.getenv("HOST","localhost"))
    port = int(os.getenv("WS_PORT","8081"))
    if os.getenv("HEALTH_PORT"):
        health_port = int(os.getenv("HEALTH_PORT"))

    enable_mcp = args.agent == "mcp"
    enable_strands = args.agent == "strands"

    aws_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")

    if not host or not port:
        print(f"HOST and PORT are required. Received HOST: {host}, PORT: {port}")
    elif not aws_key_id or not aws_secret:
        print(f"AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required.")
    else:
        try:
            asyncio.run(main(host, port, health_port, enable_mcp, enable_strands))
        except KeyboardInterrupt:
            print("Server stopped by user")
        except Exception as e:
            print(f"Server error: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
        finally:
            if MCP_CLIENT:
                MCP_CLIENT.cleanup()