"""Audio streaming for microphone input and speaker output."""
import asyncio
import pyaudio
from src.core.config import INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE, CHANNELS, CHUNK_SIZE
from src.core.utils import debug_print, time_it, time_it_async


FORMAT = pyaudio.paInt16


class AudioStreamer:
    """Handles continuous audio I/O."""
    
    def __init__(self, stream_manager):
        self.stream_manager = stream_manager
        self.is_streaming = False
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
            stream_callback=self.input_callback
        )
        
        # Output stream for direct writing
        debug_print("Opening output stream")
        self.output_stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        )
    
    def input_callback(self, in_data, frame_count, time_info, status):
        """Callback for microphone input."""
        if self.is_streaming and in_data:
            asyncio.run_coroutine_threadsafe(
                self.process_input_audio(in_data),
                self.loop
            )
        return (None, pyaudio.paContinue)
    
    async def process_input_audio(self, audio_data: bytes):
        """Process single audio chunk."""
        try:
            self.stream_manager.add_audio_chunk(audio_data)
        except Exception as e:
            if self.is_streaming:
                print(f"Error processing input: {e}")
    
    async def play_output_audio(self):
        """Play audio responses."""
        while self.is_streaming:
            try:
                # Handle barge-in
                if self.stream_manager.barge_in:
                    while not self.stream_manager.audio_output_queue.empty():
                        try:
                            self.stream_manager.audio_output_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    self.stream_manager.barge_in = False
                    await asyncio.sleep(0.05)
                    continue
                
                # Get audio data
                audio_data = await asyncio.wait_for(
                    self.stream_manager.audio_output_queue.get(),
                    timeout=0.1
                )
                
                if audio_data and self.is_streaming:
                    # Write in chunks
                    for i in range(0, len(audio_data), CHUNK_SIZE):
                        if not self.is_streaming:
                            break
                        
                        chunk = audio_data[i:i + CHUNK_SIZE]
                        await self.loop.run_in_executor(None, self.output_stream.write, chunk)
                        await asyncio.sleep(0.001)
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.is_streaming:
                    print(f"Error playing output: {e}")
                await asyncio.sleep(0.05)
    
    async def start_streaming(self):
        """Start audio streaming."""
        if self.is_streaming:
            return
        
        # Set streaming flag BEFORE starting stream
        self.is_streaming = True
        
        await time_it_async(
            "send_audio_content_start",
            lambda: self.stream_manager.send_audio_content_start_event()
        )
        
        print("🎤 Streaming started. Speak into microphone...")
        
        if not self.input_stream.is_active():
            self.input_stream.start_stream()
        
        self.output_task = asyncio.create_task(self.play_output_audio())
        
        # Wait for stop or agent switch
        while self.is_streaming:
            if self.stream_manager.switch_requested:
                print("🔄 Agent switch detected")
                self.is_streaming = False
                break
            await asyncio.sleep(0.1)
        
        await self.stop_streaming()
    
    async def stop_streaming(self):
        """Stop audio streaming."""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        
        # Cancel tasks
        if hasattr(self, 'output_task') and not self.output_task.done():
            self.output_task.cancel()
            await asyncio.gather(self.output_task, return_exceptions=True)
        
        # Close streams
        if self.input_stream:
            if self.input_stream.is_active():
                self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.output_stream:
            if self.output_stream.is_active():
                self.output_stream.stop_stream()
            self.output_stream.close()
        
        if self.p:
            self.p.terminate()
        
        await self.stream_manager.close()
