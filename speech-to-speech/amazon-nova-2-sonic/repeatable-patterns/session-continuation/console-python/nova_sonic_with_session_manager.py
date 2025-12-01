import asyncio
import warnings
import pyaudio
from nova_sonic_tool_use import BedrockStreamManager, FORMAT, CHANNELS, INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE, CHUNK_SIZE, debug_print, DEBUG
from session_manager import SessionTransitionManager

# Suppress warnings
warnings.filterwarnings("ignore")

class AudioStreamerWithSessionManager:
    """Handles continuous microphone input and audio output with session management."""

    def __init__(self, session_manager: SessionTransitionManager):
        self.session_manager = session_manager
        self.is_streaming = False
        self.loop = asyncio.get_event_loop()

        # Initialize PyAudio
        print("Initializing PyAudio...")
        self.p = pyaudio.PyAudio()
        print("PyAudio initialized")

        # Initialize separate streams for input and output
        # NOTE: Don't start the input stream yet - it will start when start_streaming() is called
        print("Opening input audio stream...")
        self.input_stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.input_callback,
            start=False  # Don't start automatically - we'll start it explicitly
        )
        print("Input audio stream opened (not started yet)")

        # Output stream for direct writing (no callback)
        print("Opening output audio stream...")
        self.output_stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        )
        print("Output audio stream opened")

    def input_callback(self, in_data, frame_count, time_info, status):
        """Callback function that schedules audio processing in the asyncio event loop"""
        if self.is_streaming and in_data:
            # Schedule the task in the event loop
            asyncio.run_coroutine_threadsafe(
                self.process_input_audio(in_data),
                self.loop
            )
        return (None, pyaudio.paContinue)

    async def process_input_audio(self, audio_data):
        """Process a single audio chunk - routes through session manager"""
        try:
            # Send audio through session manager (it handles routing)
            self.session_manager.add_audio_chunk(audio_data)
        except Exception as e:
            if self.is_streaming:
                print(f"Error processing input audio: {e}")

    async def play_output_audio(self):
        """Play audio responses from Nova Sonic through session manager"""
        while self.is_streaming:
            try:
                # Check for barge-in from active session
                active_manager = self.session_manager.get_active_stream_manager()

                if active_manager and active_manager.barge_in:
                    print("Barge-in detected - clearing audio queue")

                    # Clear audio queues from all sessions
                    if self.session_manager.current_session:
                        current_mgr = self.session_manager.current_session.stream_manager
                        while not current_mgr.audio_output_queue.empty():
                            try:
                                current_mgr.audio_output_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break

                    if self.session_manager.next_session:
                        next_mgr = self.session_manager.next_session.stream_manager
                        while not next_mgr.audio_output_queue.empty():
                            try:
                                next_mgr.audio_output_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break

                    active_manager.barge_in = False
                    await asyncio.sleep(0.05)
                    continue

                # Get audio from session manager (handles routing)
                audio_data = await self.session_manager.get_output_audio()

                if audio_data and self.is_streaming:
                    # Write audio data in chunks
                    chunk_size = CHUNK_SIZE

                    for i in range(0, len(audio_data), chunk_size):
                        if not self.is_streaming:
                            break

                        end = min(i + chunk_size, len(audio_data))
                        chunk = audio_data[i:end]

                        # Write chunk to output stream
                        def write_chunk(data):
                            return self.output_stream.write(data)

                        await asyncio.get_event_loop().run_in_executor(None, write_chunk, chunk)

                        # Brief yield to allow other tasks to run
                        await asyncio.sleep(0.001)

            except asyncio.TimeoutError:
                # No data available, continue
                continue
            except Exception as e:
                if self.is_streaming:
                    print(f"Error playing output audio: {str(e)}")
                    import traceback
                    traceback.print_exc()
                await asyncio.sleep(0.05)

    async def start_streaming(self):
        """Start streaming audio."""
        if self.is_streaming:
            return

        print("Starting audio streaming. Speak into your microphone...")
        print("Press Enter to stop streaming...")

        # Send audio content start event through session manager
        await self.session_manager.send_audio_content_start_event()

        # Set is_streaming BEFORE starting the input stream
        # This ensures the callback will process audio from the very first chunk
        self.is_streaming = True

        # Now start the input stream - callbacks will process audio immediately
        if not self.input_stream.is_active():
            print("Starting input stream...")
            self.input_stream.start_stream()
            print("Input stream started - audio capture is active")

        # Start processing tasks
        self.output_task = asyncio.create_task(self.play_output_audio())

        # Wait for user to press Enter to stop
        await asyncio.get_event_loop().run_in_executor(None, input)

        # Once input() returns, stop streaming
        await self.stop_streaming()

    async def stop_streaming(self):
        """Stop streaming audio."""
        if not self.is_streaming:
            return

        self.is_streaming = False

        # Cancel output task
        if hasattr(self, 'output_task') and not self.output_task.done():
            self.output_task.cancel()
            try:
                await self.output_task
            except asyncio.CancelledError:
                pass

        # Stop and close the streams
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

        # Close all sessions through session manager
        await self.session_manager.close_all_sessions()


async def main(debug=False):
    """Main function to run the application with session management."""
    global DEBUG
    DEBUG = debug

    # Create session transition manager
    session_manager = SessionTransitionManager(config_path="./session_config.json")

    # Initialize first session
    print("\nInitializing first session...")
    await session_manager.initialize_first_session(
        BedrockStreamManager,
        model_id='amazon.nova-sonic-v1:0',
        region='us-east-1'
    )
    print("First session initialized successfully!")

    # Create audio streamer with session manager
    audio_streamer = AudioStreamerWithSessionManager(session_manager)

    try:
        # This will run until the user presses Enter
        await audio_streamer.start_streaming()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        # Clean up
        print("\nCleaning up...")
        await audio_streamer.stop_streaming()
        print("Cleanup complete!")

        # Print recording info
        if session_manager.transition_config["enable_session_recording"] and session_manager.recording_dir:
            print(f"\nSession recordings saved to: {session_manager.recording_dir}")
            print("You can verify the recordings to validate the session transitions.")
            print("\nRecording files:")
            import os
            if os.path.exists(session_manager.recording_dir):
                for filename in sorted(os.listdir(session_manager.recording_dir)):
                    if filename.endswith('.wav'):
                        filepath = os.path.join(session_manager.recording_dir, filename)
                        size_mb = os.path.getsize(filepath) / (1024 * 1024)
                        print(f"  - {filename} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Nova Sonic with Session Management')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    # Set your AWS credentials here or use environment variables
    # os.environ['AWS_ACCESS_KEY_ID'] = "AWS_ACCESS_KEY_ID"
    # os.environ['AWS_SECRET_ACCESS_KEY'] = "AWS_SECRET_ACCESS_KEY"
    # os.environ['AWS_DEFAULT_REGION'] = "us-east-1"

    # Run the main function
    try:
        asyncio.run(main(debug=args.debug))
    except Exception as e:
        print(f"Application error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
