"""
Minimal FastAPI server for the migrated LangChain voice agent.

Usage:
    MCP_GATEWAY_ARNS='["arn:aws:bedrock-agentcore:..."]' python voice_server.py

Or without tools (voice-only, no tool calling):
    python voice_server.py
"""

import logging
import os
import json
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from voice_agent import handle_websocket_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

gateway_arns = json.loads(os.getenv("MCP_GATEWAY_ARNS", "[]"))

app = FastAPI(title="LangChain-to-Voice Migration Example")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.get("/ping")
async def ping():
    import time
    return {"status": "Healthy", "time_of_last_update": int(time.time())}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    await handle_websocket_session(websocket, default_gateway_arns=gateway_arns)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
