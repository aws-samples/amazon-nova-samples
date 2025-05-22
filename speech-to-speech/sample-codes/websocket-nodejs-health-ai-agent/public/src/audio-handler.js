// audio-handler.js
// Handles all audio-related functionality

import { AudioPlayer } from './lib/play/AudioPlayer.js';
import { addAgentAction, updateAgentStatusUI } from './action-panel.js';
import { showUserThinkingIndicator, hideUserThinkingIndicator } from './chat-ui.js';

// Singleton instance
let instance = null;

class AudioHandler {
  constructor() {
    if (instance) {
      return instance;
    }
    
    instance = this;
    
    // Initialize properties
    this.audioContext = null;
    this.audioStream = null;
    this.isStreaming = false;
    this.processor = null;
    this.sourceNode = null;
    this.socket = null;
    this.audioPlayer = new AudioPlayer();
    this.statusElement = null;
    this.startButton = null;
    this.stopButton = null;
    this.sessionInitialized = false;
  }
  
  /**
   * Initialize the audio handler with required DOM elements and socket
   * @param {Object} config Configuration object with DOM elements and socket
   */
  initialize(config) {
    this.socket = config.socket;
    this.statusElement = config.statusElement;
    this.startButton = config.startButton;
    this.stopButton = config.stopButton;
    
    // Bind event handlers
    this.startButton.addEventListener('click', this.startStreaming.bind(this));
    this.stopButton.addEventListener('click', this.stopStreaming.bind(this));
    
    // Initialize audio
    return this.initAudio();
  }
  
  /**
   * Initialize audio context and request microphone access
   */
  async initAudio() {
    try {
      this.statusElement.textContent = "Requesting microphone access...";
      this.statusElement.className = "connecting";

      // Request microphone access
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      this.audioContext = new AudioContext({
        sampleRate: 16000
      });

      await this.audioPlayer.start();

      this.statusElement.textContent = "Microphone ready. Click Start to begin.";
      this.statusElement.className = "ready";
      this.startButton.disabled = false;
      updateAgentStatusUI('idle', 'Idle');
      
      // Add initial system action
      addAgentAction('system', 'System initialized and ready', 'Health Guide Assistant is ready to help with health questions.');
      
      return true;
    } catch (error) {
      console.error("Error accessing microphone:", error);
      this.statusElement.textContent = "Error: " + error.message;
      this.statusElement.className = "error";
      updateAgentStatusUI('error', 'Error');
      
      return false;
    }
  }
  
  /**
   * Initialize session with the backend
   */
  async initializeSession() {
    if (this.sessionInitialized) return true;

    this.statusElement.textContent = "Initializing session...";

    try {
      // Send events in sequence
      this.socket.emit('promptStart');
      this.socket.emit('systemPrompt');
      this.socket.emit('audioStart');

      // Mark session as initialized
      this.sessionInitialized = true;
      this.statusElement.textContent = "Session initialized successfully";
      addAgentAction('system', 'Session Initialized', 'Connected to Health Guide knowledge base');
      
      return true;
    } catch (error) {
      console.error("Failed to initialize session:", error);
      this.statusElement.textContent = "Error initializing session";
      this.statusElement.className = "error";
      addAgentAction('error', 'Session Initialization Failed', error.message || 'Unknown error');
      
      return false;
    }
  }
  
  /**
   * Start streaming audio to the server
   */
  async startStreaming() {
    if (this.isStreaming) return;

    try {
      // First, make sure the session is initialized
      if (!this.sessionInitialized) {
        await this.initializeSession();
      }

      // Create audio processor
      this.sourceNode = this.audioContext.createMediaStreamSource(this.audioStream);

      // Use ScriptProcessorNode for audio processing
      if (this.audioContext.createScriptProcessor) {
        this.processor = this.audioContext.createScriptProcessor(512, 1, 1);

        this.processor.onaudioprocess = (e) => {
          if (!this.isStreaming) return;

          const inputData = e.inputBuffer.getChannelData(0);

          // Convert to 16-bit PCM
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
          }

          // Convert to base64 (browser-safe way)
          const base64Data = this.arrayBufferToBase64(pcmData.buffer);

          // Send to server
          this.socket.emit('audioInput', base64Data);
        };

        this.sourceNode.connect(this.processor);
        this.processor.connect(this.audioContext.destination);
      }

      this.isStreaming = true;
      this.startButton.disabled = true;
      this.stopButton.disabled = false;
      this.statusElement.textContent = "Streaming... Speak now";
      this.statusElement.className = "recording";
      updateAgentStatusUI('listening', 'Listening');

      // Show user thinking indicator when starting to record
      showUserThinkingIndicator();
      
      // Add action for starting to listen
      addAgentAction('user', 'Listening to User', 'Capturing audio input...');

    } catch (error) {
      console.error("Error starting recording:", error);
      this.statusElement.textContent = "Error: " + error.message;
      this.statusElement.className = "error";
      updateAgentStatusUI('error', 'Error');
      addAgentAction('error', 'Recording Error', error.message || 'Failed to start recording');
    }
  }
  
  /**
   * Stop streaming audio
   */
  stopStreaming() {
    if (!this.isStreaming) return;

    this.isStreaming = false;

    // Clean up audio processing
    if (this.processor) {
      this.processor.disconnect();
      this.sourceNode.disconnect();
    }

    this.startButton.disabled = false;
    this.stopButton.disabled = true;
    this.statusElement.textContent = "Processing...";
    this.statusElement.className = "processing";
    updateAgentStatusUI('thinking', 'Processing');

    this.audioPlayer.stop();
    // Tell server to finalize processing
    this.socket.emit('stopAudio');
    
    // Add action for stopping listening
    addAgentAction('user', 'Audio Input Complete', 'Processing user audio...');

    // Signal that the turn is complete
    return true;
  }
  
  /**
   * Play audio received from the server
   * @param {string} base64AudioData Base64 encoded audio data
   */
  playAudio(base64AudioData) {
    try {
      const audioData = this.base64ToFloat32Array(base64AudioData);
      this.audioPlayer.playAudio(audioData);
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  }
  
  /**
   * Convert ArrayBuffer to base64 string
   * @param {ArrayBuffer} buffer The array buffer to convert
   * @returns {string} Base64 encoded string
   */
  arrayBufferToBase64(buffer) {
    const binary = [];
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < bytes.byteLength; i++) {
      binary.push(String.fromCharCode(bytes[i]));
    }
    return btoa(binary.join(''));
  }
  
  /**
   * Convert base64 string to Float32Array
   * @param {string} base64String Base64 encoded string
   * @returns {Float32Array} Float32Array of audio data
   */
  base64ToFloat32Array(base64String) {
    try {
      const binaryString = window.atob(base64String);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const int16Array = new Int16Array(bytes.buffer);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      return float32Array;
    } catch (error) {
      console.error('Error in base64ToFloat32Array:', error);
      throw error;
    }
  }
}

// Export a singleton instance
export default new AudioHandler();