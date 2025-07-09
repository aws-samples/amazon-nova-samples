export default class AudioPlayer {
    constructor() {
        this.initialized = false;
        this.audioContext = null;
        this.workletNode = null;
        this.analyser = null;
        this.resumePromise = null;
        this.debugMode = true; // Enable debug logging
    }

    async start() {
        if (this.initialized) return;

        try {
            // Create audio context with explicit options
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ 
                sampleRate: 24000,
                latencyHint: 'interactive'
            });
            
            // Log audio context state
            this.log(`AudioContext created with state: ${this.audioContext.state}`);
            
            // Resume audio context if it's suspended (browser autoplay policy)
            if (this.audioContext.state === 'suspended') {
                this.log('AudioContext is suspended, attempting to resume...');
                this.resumePromise = this.resumeAudioContext();
                await this.resumePromise;
            }
            
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 512;

            // Load the audio worklet with error handling
            try {
                const workletUrl = new URL('./audioPlayerProcessor.worklet.js', import.meta.url).href;
                this.log(`Loading audio worklet from: ${workletUrl}`);
                await this.audioContext.audioWorklet.addModule(workletUrl);
                this.log('Audio worklet loaded successfully');
            } catch (workletError) {
                console.error("Failed to load audio worklet:", workletError);
                // Fallback to ScriptProcessor if worklet fails
                return this.fallbackToScriptProcessor();
            }

            // Create and connect the worklet node
            this.workletNode = new AudioWorkletNode(this.audioContext, "audio-player-processor", {
                outputChannelCount: [1] // Ensure mono output
            });
            
            // Add error handler for the worklet
            this.workletNode.onprocessorerror = (err) => {
                console.error('AudioWorklet processing error:', err);
            };
            
            // Connect the audio graph
            this.workletNode.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);

            this.initialized = true;
            this.log('Audio player initialized successfully');
        } catch (error) {
            console.error("Error initializing audio player:", error);
            // Try fallback method if primary method fails
            return this.fallbackToScriptProcessor();
        }
    }

    // Fallback to ScriptProcessor if AudioWorklet isn't supported or fails
    fallbackToScriptProcessor() {
        this.log('Falling back to ScriptProcessor');
        try {
            if (this.audioContext) {
                // Create script processor node
                const bufferSize = 4096;
                const scriptNode = this.audioContext.createScriptProcessor(bufferSize, 0, 1);
                
                // Buffer for audio data
                let audioBuffer = new Float32Array(0);
                
                scriptNode.onaudioprocess = (e) => {
                    const output = e.outputBuffer.getChannelData(0);
                    
                    if (audioBuffer.length >= output.length) {
                        // Copy data from our buffer to the output
                        output.set(audioBuffer.subarray(0, output.length));
                        // Keep the rest of the buffer
                        audioBuffer = audioBuffer.subarray(output.length);
                    } else {
                        // Not enough data, copy what we have and fill the rest with silence
                        output.set(audioBuffer);
                        output.fill(0, audioBuffer.length);
                        audioBuffer = new Float32Array(0);
                    }
                };
                
                // Connect the script processor
                scriptNode.connect(this.audioContext.destination);
                
                // Store reference
                this.scriptNode = scriptNode;
                this.audioBuffer = audioBuffer;
                
                this.initialized = true;
                this.usingFallback = true;
                this.log('ScriptProcessor fallback initialized');
                return true;
            }
        } catch (fallbackError) {
            console.error("Fallback audio initialization failed:", fallbackError);
            return false;
        }
    }

    // Helper to resume audio context with user interaction
    async resumeAudioContext() {
        if (!this.audioContext) return;
        
        try {
            this.log('Attempting to resume AudioContext...');
            await this.audioContext.resume();
            this.log(`AudioContext resumed, new state: ${this.audioContext.state}`);
            return true;
        } catch (error) {
            console.error("Failed to resume audio context:", error);
            return false;
        }
    }

    bargeIn() {
        if (!this.initialized) return;
        
        this.log('Barge-in requested');
        if (this.usingFallback) {
            // Clear the buffer in fallback mode
            if (this.audioBuffer) {
                this.audioBuffer = new Float32Array(0);
            }
        } else if (this.workletNode) {
            this.workletNode.port.postMessage({
                type: "barge-in",
            });
        }
    }

    stop() {
        this.log('Stopping audio player');
        if (!this.initialized) return;

        if (this.audioContext) {
            this.audioContext.close().catch(err => console.error("Error closing audio context:", err));
        }

        if (this.analyser) {
            this.analyser.disconnect();
        }

        if (this.workletNode) {
            this.workletNode.disconnect();
        }

        if (this.scriptNode) {
            this.scriptNode.disconnect();
        }

        this.initialized = false;
        this.audioContext = null;
        this.analyser = null;
        this.workletNode = null;
        this.scriptNode = null;
        this.audioBuffer = null;
        this.log('Audio player stopped');
    }

    playAudio(samples) {
        if (!this.initialized) {
            console.error("The audio player is not initialized. Call start() before attempting to play audio.");
            return;
        }

        // Ensure audio context is running
        if (this.audioContext && this.audioContext.state !== 'running') {
            this.log(`AudioContext not running (state: ${this.audioContext.state}), attempting to resume...`);
            this.resumeAudioContext();
        }

        this.log(`Playing audio: ${samples.length} samples`);
        
        if (this.usingFallback) {
            // In fallback mode, append to the buffer
            const newBuffer = new Float32Array(this.audioBuffer.length + samples.length);
            newBuffer.set(this.audioBuffer);
            newBuffer.set(samples, this.audioBuffer.length);
            this.audioBuffer = newBuffer;
        } else if (this.workletNode) {
            // Send to worklet
            this.workletNode.port.postMessage({
                type: "audio",
                audioData: samples,
            });
        }
    }
    
    // Helper for conditional logging
    log(message) {
        if (this.debugMode) {
            console.log(`[AudioPlayer] ${message}`);
        }
    }
}
