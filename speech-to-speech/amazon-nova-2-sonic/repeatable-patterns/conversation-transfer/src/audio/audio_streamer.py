"""Audio streaming for microphone input and speaker output."""
import asyncio
from typing import Callable, Awaitable, Optional
import pyaudio
from src.config import INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE, CHANNELS, CHUNK_SIZE
from src.utils import debug_print, time_it, time_it_async


FORMAT = pyaudio.paInt16


class AudioStreamer:
    """Handles continuous audio I/O.

    Implements the StreamCallback protocol (on_audio_output, on_barge_in,
    on_switch_requested) so that SessionController can push events without
    AudioStreamer knowing about stream internals.
    """

    def __init__(
        self,
        send_audio_fn: Callable[[bytes], Awaitable[None]],
        send_audio_content_start_fn: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        self._send_audio = send_audio_fn
        self._send_audio_content_start = send_audio_content_start_fn
        self.is_streaming = False
        self._audio_output_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._stop_event = asyncio.Event()
        self.loop = asyncio.get_event_loop()

        # Initialize PyAudio
        debug_print("Initializing PyAudio")
        self.p = pyaudio.PyAudio()

        # Input stream with callback
        debug_print("Opening input stream")
        self.input_stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.input_callback,
        )

        # Output stream for direct writing
        debug_print("Opening output stream")
        self.output_stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE,
        )

    # --- StreamCallback implementation ---

    def on_audio_output(self, audio_bytes: bytes) -> None:
        """Enqueue decoded audio for playback."""
        self._audio_output_queue.put_nowait(audio_bytes)

    def on_barge_in(self) -> None:
        """Drain the audio output queue so playback stops immediately."""
        while not self._audio_output_queue.empty():
            try:
                self._audio_output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def on_switch_requested(self) -> None:
        """Signal the streaming loop to stop for an agent switch."""
        self._stop_event.set()

    # --- Audio I/O ---

    def input_callback(self, in_data, frame_count, time_info, status):
        """Callback for microphone input."""
        if self.is_streaming and in_data:
            asyncio.run_coroutine_threadsafe(
                self.process_input_audio(in_data),
                self.loop,
            )
        return (None, pyaudio.paContinue)

    async def process_input_audio(self, audio_data: bytes):
        """Process single audio chunk by sending it to SessionController."""
        try:
            await self._send_audio(audio_data)
        except Exception as e:
            if self.is_streaming:
                debug_print(f"Error sending audio input: {e}")

    async def play_output_audio(self):
        """Play audio responses from the internal queue."""
        while self.is_streaming:
            try:
                audio_data = await asyncio.wait_for(
                    self._audio_output_queue.get(),
                    timeout=0.1,
                )

                if audio_data and self.is_streaming:
                    for i in range(0, len(audio_data), CHUNK_SIZE):
                        if not self.is_streaming:
                            break
                        chunk = audio_data[i : i + CHUNK_SIZE]
                        await self.loop.run_in_executor(
                            None, self.output_stream.write, chunk
                        )
                        await asyncio.sleep(0.001)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.is_streaming:
                    print(f"Error playing output: {e}")
                await asyncio.sleep(0.05)

    async def start_streaming(self):
        """Start audio streaming. Blocks until _stop_event is set."""
        if self.is_streaming:
            return

        self.is_streaming = True
        self._stop_event.clear()

        if self._send_audio_content_start:
            await time_it_async(
                "send_audio_content_start",
                self._send_audio_content_start,
            )

        print("🎤 Streaming started. Speak into microphone...")

        if not self.input_stream.is_active():
            self.input_stream.start_stream()

        self.output_task = asyncio.create_task(self.play_output_audio())

        # Wait for stop event (set by on_switch_requested) instead of polling
        await self._stop_event.wait()
        print("🔄 Agent switch detected")
        self.is_streaming = False

        await self.stop_streaming()

    async def stop_streaming(self):
        """Stop audio streaming and release resources."""
        self.is_streaming = False

        # Cancel output task
        if hasattr(self, "output_task") and not self.output_task.done():
            self.output_task.cancel()
            await asyncio.gather(self.output_task, return_exceptions=True)

        # Close streams safely
        if self.input_stream:
            try:
                if self.input_stream.is_active():
                    self.input_stream.stop_stream()
                self.input_stream.close()
            except OSError:
                pass
            self.input_stream = None

        if self.output_stream:
            try:
                if self.output_stream.is_active():
                    self.output_stream.stop_stream()
                self.output_stream.close()
            except OSError:
                pass
            self.output_stream = None

        if self.p:
            self.p.terminate()
            self.p = None
