import logging
import uvicorn
import os
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from agent import handle_websocket_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_WS_MESSAGE_SIZE = 10000


def split_large_event(event_dict, max_size=MAX_WS_MESSAGE_SIZE):
    """Split a large event into smaller chunks by dividing the audio field."""
    event_json = json.dumps(event_dict)
    event_size = len(event_json.encode("utf-8"))

    if event_size <= max_size:
        return [event_dict]

    if "audio" not in event_dict or not isinstance(event_dict["audio"], str):
        return [event_dict]

    audio_content = event_dict["audio"]
    template = {k: v for k, v in event_dict.items() if k != "audio"}
    template["audio"] = ""
    overhead = len(json.dumps(template).encode("utf-8"))

    max_content_size = max_size - overhead - 100
    max_content_size = (max_content_size // 4) * 4

    if max_content_size <= 0:
        return [event_dict]

    chunks = []
    for i in range(0, len(audio_content), max_content_size):
        chunk_event = {k: v for k, v in event_dict.items() if k != "audio"}
        chunk_event["audio"] = audio_content[i:i + max_content_size]
        chunks.append(chunk_event)

    return chunks


app = FastAPI(title="Nova 2.5 Sonic Voice Agent Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Nova 2.5 Sonic voice agent demo server...")
    logger.info(f"Region: {os.getenv('AWS_DEFAULT_REGION', 'us-east-1')}")


@app.get("/ping")
async def ping():
    import time
    return {"status": "Healthy", "time_of_last_update": int(time.time())}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def chunked_send_json(event_dict):
        for chunk in split_large_event(event_dict):
            await websocket.send_json(chunk)

    await handle_websocket_session(websocket, send_output=chunked_send_json)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8083"))
    uvicorn.run(app, host=host, port=port)
