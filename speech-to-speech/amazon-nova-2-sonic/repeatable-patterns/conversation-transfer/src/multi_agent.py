"""Multi-agent orchestrator for Nova 2 Sonic conversations."""
import asyncio
import os
import pygame
from typing import List, Dict
from src.core.stream_manager import BedrockStreamManager
from src.audio.audio_streamer import AudioStreamer
from src.agents.agent_config import AGENTS


class MultiAgentSonic:
    """Orchestrates multi-agent voice conversations."""
    
    def __init__(self, model_id: str, region: str, debug: bool = False):
        self.model_id = model_id
        self.region = region
        self.debug = debug
        self.active_agent = "support"
        self.conversation_history: List[Dict[str, str]] = []
        self.agents = AGENTS
        self.stream_manager = None
        self.audio_streamer = None
    
    async def start_conversation(self):
        """Start voice conversation with agent switching."""
        while True:
            try:
                agent_config = self.agents.get(self.active_agent, self.agents["support"])
                print(f"🎤 Starting conversation with {self.active_agent.title()}...")
                
                await asyncio.sleep(2)
                
                # Create components
                self.stream_manager = BedrockStreamManager(
                    model_id=self.model_id,
                    region=self.region,
                    voice_id=agent_config.voice_id,
                    system_prompt=agent_config.instruction,
                    conversation_history=self.conversation_history,
                    active_agent=self.active_agent
                )
                
                self.audio_streamer = AudioStreamer(self.stream_manager)
                
                # Initialize and start
                await self.stream_manager.initialize_stream()
                
                # Stop transition music
                self._stop_music()
                
                # Start conversation
                await self.audio_streamer.start_streaming()
                
                # Check for agent switch
                if self.stream_manager.switch_requested:
                    self.conversation_history = self.stream_manager.conversation_history
                    new_agent = self.stream_manager.new_voice
                    print(f"🔄 Switching: {self.active_agent} → {new_agent}")
                    
                    # Play transition music
                    self._play_music()
                    
                    # Close connection
                    await self.stream_manager.close()
                    
                    self.active_agent = new_agent
                    await self.cleanup()
                    continue
                else:
                    print("👋 Conversation ended")
                    break
                    
            except KeyboardInterrupt:
                print("\n👋 Interrupted by user")
                break
            except Exception as e:
                print(f"Error: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
                break
    
    def _play_music(self):
        """Play transition music."""
        try:
            pygame.mixer.init()
            music_path = os.path.join(os.path.dirname(__file__), "..", "music.mp3")
            if os.path.exists(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.play(-1)
                print("🎵 Playing transition music")
        except Exception as e:
            print(f"Could not play music: {e}")
    
    def _stop_music(self):
        """Stop transition music."""
        try:
            pygame.mixer.music.stop()
            print("🎵 Stopped transition music")
        except:
            pass
    
    async def cleanup(self):
        """Clean up resources."""
        print("🧹 Cleaning up...")
        if self.audio_streamer:
            await self.audio_streamer.stop_streaming()
