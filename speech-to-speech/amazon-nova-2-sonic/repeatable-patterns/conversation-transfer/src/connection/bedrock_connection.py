"""Thin wrapper for the raw bidirectional Bedrock stream.

No parsing, no business logic — just open, send, receive, close.
"""
import json
import logging
import sys
from typing import AsyncIterator

from aws_sdk_bedrock_runtime.client import (
    BedrockRuntimeClient,
    InvokeModelWithBidirectionalStreamOperationInput,
)
from aws_sdk_bedrock_runtime.models import (
    InvokeModelWithBidirectionalStreamInputChunk,
    BidirectionalInputPayloadPart,
)
from aws_sdk_bedrock_runtime.config import Config
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver

from src.utils import debug_print, time_it_async

logger = logging.getLogger("sonic.connection")


class BedrockConnection:
    """Manages the raw bidirectional stream lifecycle with AWS Bedrock.

    Responsibilities:
      - Initialise the Bedrock client
      - Open the bidirectional stream
      - Send raw JSON event strings
      - Yield raw JSON response strings
      - Close the stream (idempotent)
    """

    def __init__(self, model_id: str, region: str) -> None:
        self.model_id = model_id
        self.region = region
        self._client: BedrockRuntimeClient | None = None
        self._stream_response = None
        self._closed = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def open(self) -> None:
        """Initialise the client and open the bidirectional stream.

        Raises on connection failure so the caller can decide how to handle it.
        """
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        self._client = BedrockRuntimeClient(config=config)

        self._stream_response = await time_it_async(
            "invoke_model_with_bidirectional_stream",
            lambda: self._client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
            ),
        )
        self._closed = False
        logger.info("Connection opened (model=%s, region=%s)", self.model_id, self.region)
        debug_print("Connection opened")

    async def send(self, event_json: str) -> None:
        """Send a raw JSON event string to Bedrock.

        Silently logs and returns if the stream is already closed.
        """
        if self._closed or self._stream_response is None:
            debug_print("Send skipped — stream not active")
            return

        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode("utf-8"))
        )

        try:
            await self._stream_response.input_stream.send(event)
        except Exception as e:
            logger.error("Error sending event: %s", e)

    async def receive(self) -> AsyncIterator[str]:
        """Yield raw JSON response strings from Bedrock."""
        if self._stream_response is None:
            debug_print("receive() called but no stream")
            return

        debug_print("receive() loop starting")
        while True:
            try:
                output = await self._stream_response.await_output()
                result = await output[1].receive()

                if result.value and result.value.bytes_:
                    raw = result.value.bytes_.decode("utf-8")
                    yield raw
                else:
                    debug_print("Received empty response")

            except StopAsyncIteration:
                debug_print("Stream ended (StopAsyncIteration)")
                break
            except Exception as e:
                if "InvalidStateError" in str(e) or "CANCELLED" in str(e):
                    debug_print("Stream cancelled")
                elif "ValidationException" in str(e):
                    logger.error("Validation error from Bedrock: %s", e)
                else:
                    logger.error("Error receiving: %s", e)
                break

        debug_print("receive() loop ended")

    async def close(self) -> None:
        """Close the stream and client. Idempotent — safe to call multiple times."""
        if self._closed:
            return

        self._closed = True
        debug_print("Closing connection")

        if self._stream_response is not None:
            try:
                await self._stream_response.input_stream.close()
            except Exception as e:
                debug_print(f"Error closing input stream: {e}")

        self._stream_response = None
        logger.info("Connection closed")
        debug_print("Connection closed")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        """True when the stream has been opened and not yet closed."""
        return self._stream_response is not None and not self._closed
