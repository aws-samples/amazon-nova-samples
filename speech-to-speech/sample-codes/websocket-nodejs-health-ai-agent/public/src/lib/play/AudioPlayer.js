import { ObjectExt } from '../util/ObjectsExt.js';

const AudioPlayerWorkletUrl = new URL('./AudioPlayerProcessor.worklet.js', import.meta.url).toString();

export class AudioPlayer {
    constructor() {
        this.onAudioPlayedListeners = [];
        this.initialized = false;
        this.audioContext = null;
        this.analyser = null;
        this.workletNode = null;
        this.recorderNode = null;
        this.gainNode = null;
        this.playbackRate = 1.0;
    }

    /**
     * Add event listener for audio events
     * @param {string} event - Event type ('onAudioPlayed')
     * @param {Function} callback - Callback function
     */
    addEventListener(event, callback) {
        if (event === "onAudioPlayed") {
            this.onAudioPlayedListeners.push(callback);
        } else {
            console.error(`Unsupported event type: ${event}`);
        }
    }

    /**
     * Initialize the audio player
     */
    async start() {
        try {
            this.audioContext = new AudioContext({ sampleRate: 24000 });
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 512;

            // Add gain node for volume control
            this.gainNode = this.audioContext.createGain();
            this.gainNode.gain.value = 1.0;

            // Load worklet module
            await this.audioContext.audioWorklet.addModule(AudioPlayerWorkletUrl);
            
            // Create and connect audio nodes
            this.workletNode = new AudioWorkletNode(this.audioContext, "audio-player-processor");
            this.workletNode.connect(this.gainNode);
            this.gainNode.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);

            // Create recorder node for audio monitoring
            this.recorderNode = this.audioContext.createScriptProcessor(512, 1, 1);
            this.recorderNode.onaudioprocess = this.handleAudioProcess.bind(this);

            this.maybeOverrideInitialBufferLength();
            this.initialized = true;
        } catch (error) {
            console.error('Failed to initialize audio player:', error);
            throw error;
        }
    }

    /**
     * Handle audio processing for monitoring
     * @param {AudioProcessingEvent} event - Audio processing event
     */
    handleAudioProcess(event) {
        const inputData = event.inputBuffer.getChannelData(0);
        const outputData = event.outputBuffer.getChannelData(0);
        outputData.set(inputData);

        // Notify listeners
        const samples = new Float32Array(outputData);
        this.onAudioPlayedListeners.forEach(listener => listener(samples));
    }

    /**
     * Interrupt current audio playback (barge-in)
     */
    bargeIn() {
        if (!this.initialized || !this.workletNode) {
            console.warn('Cannot barge-in: Audio player not initialized');
            return;
        }

        this.workletNode.port.postMessage({
            type: "barge-in",
        });
    }

    /**
     * Stop and cleanup the audio player
     */
    stop() {
        this.initialized = false;

        // Disconnect and cleanup nodes
        [this.analyser, this.workletNode, this.recorderNode, this.gainNode].forEach(node => {
            if (ObjectExt.exists(node)) {
                node.disconnect();
            }
        });

        // Close audio context
        if (ObjectExt.exists(this.audioContext)) {
            this.audioContext.close();
        }

        // Reset all references
        this.audioContext = null;
        this.analyser = null;
        this.workletNode = null;
        this.recorderNode = null;
        this.gainNode = null;
        this.playbackRate = 1.0;
    }

    /**
     * Override initial buffer length from URL parameters (for debugging)
     */
    maybeOverrideInitialBufferLength() {
        const params = new URLSearchParams(window.location.search);
        const value = params.get("audioPlayerInitialBufferLength");
        
        if (value === null) return;

        const bufferLength = parseInt(value);
        if (isNaN(bufferLength)) {
            console.error(`Invalid audioPlayerInitialBufferLength value: ${value}`);
            return;
        }

        this.workletNode.port.postMessage({
            type: "initial-buffer-length",
            bufferLength: bufferLength,
        });
    }

    /**
     * Play audio samples
     * @param {Float32Array} samples - Audio samples to play
     */
    playAudio(samples) {
        if (!this.initialized) {
            console.error("Audio player not initialized. Call start() first.");
            return;
        }

        this.workletNode.port.postMessage({
            type: "audio",
            audioData: samples,
        });
    }

    /**
     * Get current audio samples for visualization
     * @returns {Array<number>|null} Normalized audio samples or null if not initialized
     */
    getSamples() {
        if (!this.initialized) return null;

        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        this.analyser.getByteTimeDomainData(dataArray);
        
        return Array.from(dataArray, sample => (sample / 128) - 1);
    }

    /**
     * Get current audio volume level
     * @returns {number} Volume level (0-1) or 0 if not initialized
     */
    getVolume() {
        if (!this.initialized) return 0;

        const samples = this.getSamples();
        if (!samples) return 0;

        // Calculate RMS (Root Mean Square) for volume
        const sumSquares = samples.reduce((sum, sample) => sum + (sample * sample), 0);
        return Math.sqrt(sumSquares / samples.length);
    }

    /**
     * Adjust audio parameters for safety responses
     * @param {boolean} isEmergency - Whether this is an emergency message
     */
    adjustForSafetyResponse(isEmergency = false) {
        if (!this.initialized || !this.gainNode) return;

        if (isEmergency) {
            this.gainNode.gain.value = 1.2; // Increase volume for emergency
            this.playbackRate = 0.95; // Slow down for clarity
        } else {
            this.gainNode.gain.value = 1.1; // Slight volume increase
            this.playbackRate = 0.98; // Slightly slower
        }

        // Reset to normal after 5 seconds
        this.resetAudioParameters(5000);
    }

    /**
     * Adjust audio parameters for off-topic redirects
     */
    adjustForOffTopicRedirect() {
        if (!this.initialized || !this.gainNode) return;

        this.gainNode.gain.value = 1.05; // Slight volume increase
        this.playbackRate = 0.98; // Slightly slower for emphasis

        // Reset to normal after 3 seconds
        this.resetAudioParameters(3000);
    }

    /**
     * Reset audio parameters to default values
     * @param {number} delay - Delay in milliseconds before reset
     */
    resetAudioParameters(delay = 0) {
        setTimeout(() => {
            if (this.initialized && this.gainNode) {
                this.gainNode.gain.value = 1.0;
                this.playbackRate = 1.0;
            }
        }, delay);
    }

    /**
     * Check if the audio player is ready
     * @returns {boolean} True if initialized and ready
     */
    isReady() {
        return this.initialized && this.audioContext && this.workletNode;
    }
}