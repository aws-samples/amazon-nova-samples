#!/usr/bin/env python3

import json
import logging
import sys
import warnings
import traceback
import os
import uvicorn
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from session_manager import SessionManager
from integration.mcp_client import McpLocationClient
from integration.strands_agent import StrandsAgent

# Configure logging
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore")

DEBUG = False
MCP_CLIENT = None
STRANDS_AGENT = None
KB_ID = None

def debug_print(message):
    """Print only if debug mode is enabled"""
    if DEBUG:
        print(message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event()
    yield
    await shutdown_event()


async def startup_event():
    """Initialize services when the app starts."""
    global DEBUG, KB_ID, MCP_CLIENT, STRANDS_AGENT

    parser = argparse.ArgumentParser(description='Nova Sonic server')
    parser.add_argument('--agent', type=str, help='Agent integration: "mcp" or "strands"')
    parser.add_argument('--kb-id', type=str, help='Knowledge Base ID for RAG')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    DEBUG = args.debug

    if args.agent == "mcp":
        print("MCP enabled!")
        try:
            MCP_CLIENT = McpLocationClient()
            await MCP_CLIENT.connect_to_server()
        except Exception as ex:
            print(f"Failed to start MCP client: {ex}")

    elif args.agent == "strands":
        print("Strands agent enabled!")
        try:
            STRANDS_AGENT = StrandsAgent()
        except Exception as ex:
            print(f"Failed to start Strands agent: {ex}")
    else:
        print("No agent framework selected.")

    if args.kb_id:
        KB_ID = args.kb_id
        print(f"Using Bedrock Knowledge Base with ID: {KB_ID}")


async def shutdown_event():
    """Clean up resources when the app shuts down."""
    if MCP_CLIENT:
        await MCP_CLIENT.cleanup()


app = FastAPI(
    title="Nova Sonic - sample backend service",
    description="Sample backend using WebSockets to link a browser-based frontend with Amazon Nova Sonic via Amazon Bedrock",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"status": "healthy"}

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    aws_region = os.getenv("AWS_DEFAULT_REGION")
    if not aws_region:
        aws_region = "us-east-1"

    session_manager: SessionManager | None = None

    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")

        session_manager = SessionManager(
            websocket=websocket,
            model_id='amazon.nova-sonic-v1:0',
            region=aws_region,
            mcp_client=MCP_CLIENT,
            strands_agent=STRANDS_AGENT,
            kb_id=KB_ID,
        )
        await session_manager.initialize_stream()

        async for message in websocket.iter_text():
            try:
                await session_manager.handle_incoming_message_from_frontend(message)
            except json.JSONDecodeError:
                print("Invalid JSON received from WebSocket:", message)
            except Exception as e:
                print(f"Error processing WebSocket message: {e}")
                if DEBUG:
                    traceback.print_exc()
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    finally:
        if session_manager:
            await session_manager.close()
        if MCP_CLIENT:
            await MCP_CLIENT.cleanup()
        if STRANDS_AGENT:
            STRANDS_AGENT.close()


if __name__ == "__main__":
    host = str(os.getenv("HOST", "localhost"))
    port = int(os.getenv("WS_PORT", "8081"))
    if not host or not port:
        print(f"HOST and PORT are required. Received HOST: {host}, PORT: {port}")
        sys.exit(1)

    aws_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not aws_key_id or not aws_secret:
        print("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required.")
        sys.exit(1)

    try:
        uvicorn.run(
            "server:app",
            host=host,
            port=port,
            log_level="info" if not DEBUG else "debug"
        )
    except KeyboardInterrupt:
        print("Server stopped by user.")
    except Exception as e:
        print(f"Server error: {e}")
        traceback.print_exc()
