"""Unit tests for BedrockConnection."""
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.connection.bedrock_connection import BedrockConnection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_stream_response():
    """Build a mock stream_response with input_stream.send / .close and await_output."""
    stream = MagicMock()
    stream.input_stream = MagicMock()
    stream.input_stream.send = AsyncMock()
    stream.input_stream.close = AsyncMock()
    stream.await_output = AsyncMock()
    return stream


@pytest_asyncio.fixture
async def connection():
    """Return a BedrockConnection with a mocked stream already open."""
    conn = BedrockConnection(model_id="test-model", region="us-east-1")
    conn._stream_response = _make_stream_response()
    conn._closed = False
    return conn


# ---------------------------------------------------------------------------
# open()
# ---------------------------------------------------------------------------

class TestOpen:
    @pytest.mark.asyncio
    async def test_open_sets_stream_response(self):
        conn = BedrockConnection(model_id="test-model", region="us-east-1")
        mock_stream = _make_stream_response()

        async def fake_time_it_async(label, func):
            return mock_stream

        with patch("src.connection.bedrock_connection.BedrockRuntimeClient") as MockClient, \
             patch("src.connection.bedrock_connection.time_it_async", side_effect=fake_time_it_async):
            await conn.open()

        assert conn._stream_response is mock_stream
        assert conn.is_open is True
        assert conn._closed is False

    @pytest.mark.asyncio
    async def test_open_raises_on_failure(self):
        conn = BedrockConnection(model_id="test-model", region="us-east-1")

        async def failing_time_it_async(label, func):
            raise Exception("Connection refused")

        with patch("src.connection.bedrock_connection.BedrockRuntimeClient") as MockClient, \
             patch("src.connection.bedrock_connection.time_it_async", side_effect=failing_time_it_async):
            with pytest.raises(Exception, match="Connection refused"):
                await conn.open()


# ---------------------------------------------------------------------------
# send()
# ---------------------------------------------------------------------------

class TestSend:
    @pytest.mark.asyncio
    async def test_send_encodes_and_forwards(self, connection):
        event_json = json.dumps({"event": {"sessionStart": {}}})
        await connection.send(event_json)
        connection._stream_response.input_stream.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_on_closed_stream_is_noop(self, connection):
        connection._closed = True
        await connection.send('{"event":{}}')
        connection._stream_response.input_stream.send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_on_none_stream_is_noop(self):
        conn = BedrockConnection(model_id="m", region="r")
        # Should not raise
        await conn.send('{"event":{}}')

    @pytest.mark.asyncio
    async def test_send_logs_error_on_exception(self, connection):
        connection._stream_response.input_stream.send.side_effect = Exception("broken")
        # Should not raise — errors are caught and logged
        await connection.send('{"event":{}}')


# ---------------------------------------------------------------------------
# receive()
# ---------------------------------------------------------------------------

class TestReceive:
    @pytest.mark.asyncio
    async def test_receive_yields_decoded_strings(self, connection):
        payload = '{"event":{"textOutput":{"content":"hi","role":"ASSISTANT"}}}'
        result_mock = MagicMock()
        result_mock.value.bytes_ = payload.encode("utf-8")

        output_mock = AsyncMock(return_value=result_mock)
        connection._stream_response.await_output = AsyncMock(
            side_effect=[(None, MagicMock(receive=output_mock)), StopAsyncIteration]
        )

        results = []
        async for item in connection.receive():
            results.append(item)
            break  # only one item expected

        assert results == [payload]

    @pytest.mark.asyncio
    async def test_receive_stops_on_stop_async_iteration(self, connection):
        connection._stream_response.await_output = AsyncMock(side_effect=StopAsyncIteration)

        results = []
        async for item in connection.receive():
            results.append(item)

        assert results == []

    @pytest.mark.asyncio
    async def test_receive_stops_on_cancelled(self, connection):
        connection._stream_response.await_output = AsyncMock(
            side_effect=Exception("InvalidStateError: CANCELLED")
        )

        results = []
        async for item in connection.receive():
            results.append(item)

        assert results == []

    @pytest.mark.asyncio
    async def test_receive_stops_on_validation_exception(self, connection):
        connection._stream_response.await_output = AsyncMock(
            side_effect=Exception("ValidationException: bad input")
        )

        results = []
        async for item in connection.receive():
            results.append(item)

        assert results == []

    @pytest.mark.asyncio
    async def test_receive_returns_immediately_when_no_stream(self):
        conn = BedrockConnection(model_id="m", region="r")
        results = []
        async for item in conn.receive():
            results.append(item)
        assert results == []

    @pytest.mark.asyncio
    async def test_receive_skips_empty_bytes(self, connection):
        """When result.value.bytes_ is None, nothing is yielded."""
        result_mock = MagicMock()
        result_mock.value.bytes_ = None

        output_mock = AsyncMock(return_value=result_mock)
        connection._stream_response.await_output = AsyncMock(
            side_effect=[(None, MagicMock(receive=output_mock)), StopAsyncIteration]
        )

        results = []
        async for item in connection.receive():
            results.append(item)

        assert results == []


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestClose:
    @pytest.mark.asyncio
    async def test_close_sets_closed_flag(self, connection):
        await connection.close()
        assert connection._closed is True
        assert connection._stream_response is None

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self, connection):
        await connection.close()
        await connection.close()  # second call should be a no-op
        assert connection._closed is True

    @pytest.mark.asyncio
    async def test_close_handles_stream_close_error(self, connection):
        connection._stream_response.input_stream.close.side_effect = Exception("oops")
        await connection.close()  # should not raise
        assert connection._closed is True

    @pytest.mark.asyncio
    async def test_close_on_fresh_connection(self):
        conn = BedrockConnection(model_id="m", region="r")
        await conn.close()  # no stream to close — should be fine
        assert conn._closed is True


# ---------------------------------------------------------------------------
# is_open property
# ---------------------------------------------------------------------------

class TestIsOpen:
    def test_is_open_false_initially(self):
        conn = BedrockConnection(model_id="m", region="r")
        assert conn.is_open is False

    def test_is_open_true_when_stream_active(self, connection):
        assert connection.is_open is True

    def test_is_open_false_after_close(self, connection):
        connection._closed = True
        assert connection.is_open is False
