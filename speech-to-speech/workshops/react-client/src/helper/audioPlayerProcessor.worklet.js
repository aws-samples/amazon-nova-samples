// Audio sample buffer to minimize reallocations
class ExpandableBuffer {
    constructor() {
        // Start with half a second's worth of buffered audio capacity
        this.buffer = new Float32Array(12000);
        this.readIndex = 0;
        this.writeIndex = 0;
        this.underflowedSamples = 0;
        this.isInitialBuffering = true;
        this.initialBufferLength = 2400;  // 100ms at 24kHz - reduced for better responsiveness
        this.lastWriteTime = 0;
        this.debug = true;
    }

    write(samples) {
        const now = Date.now();
        this.lastWriteTime = now;

        if (this.writeIndex + samples.length <= this.buffer.length) {
            // Enough space to append the new samples
            this.buffer.set(samples, this.writeIndex);
        }
        else {
            // Not enough space ...
            if (samples.length <= this.readIndex) {
                // ... but we can shift samples to the beginning of the buffer
                const subarray = this.buffer.subarray(this.readIndex, this.writeIndex);
                this.buffer.set(subarray, 0);
                this.writeIndex -= this.readIndex;
                this.readIndex = 0;
                this.buffer.set(samples, this.writeIndex);
            }
            else {
                // ... and we need to grow the buffer capacity to make room for more audio
                const newLength = Math.max((samples.length + this.writeIndex - this.readIndex) * 2, 24000);
                const newBuffer = new Float32Array(newLength);
                newBuffer.set(this.buffer.subarray(this.readIndex, this.writeIndex), 0);
                this.writeIndex -= this.readIndex;
                this.readIndex = 0;
                this.buffer = newBuffer;
                this.buffer.set(samples, this.writeIndex);
            }
        }
        
        this.writeIndex += samples.length;
        
        if (this.writeIndex - this.readIndex >= this.initialBufferLength) {
            // Filled the initial buffer length, so we can start playback with some cushion
            this.isInitialBuffering = false;
            if (this.debug) {
                console.log(`[AudioWorklet] Buffer ready for playback: ${this.writeIndex - this.readIndex} samples`);
            }
        }
    }

    read(destination) {
        let copyLength = 0;
        
        if (!this.isInitialBuffering) {
            // Only start to play audio after we've built up some initial cushion
            copyLength = Math.min(destination.length, this.writeIndex - this.readIndex);
            
            if (copyLength > 0) {
                destination.set(this.buffer.subarray(this.readIndex, this.readIndex + copyLength));
                this.readIndex += copyLength;
            }
        }

        if (copyLength < destination.length) {
            // Not enough samples (buffer underflow). Fill the rest with silence.
            destination.fill(0, copyLength);
            this.underflowedSamples += destination.length - copyLength;
            
            if (this.debug && copyLength === 0 && this.writeIndex > 0) {
                console.log(`[AudioWorklet] Buffer underflow: needed ${destination.length}, had ${this.writeIndex - this.readIndex}`);
            }
        }
        
        if (this.readIndex >= this.writeIndex) {
            // Ran out of audio, reset indices
            this.readIndex = 0;
            this.writeIndex = 0;
            
            // Only set initial buffering if we actually ran out
            if (copyLength === 0) {
                this.isInitialBuffering = true;
            }
        }
    }

    clearBuffer() {
        this.readIndex = 0;
        this.writeIndex = 0;
        this.isInitialBuffering = true;
        if (this.debug) {
            console.log('[AudioWorklet] Buffer cleared');
        }
    }
    
    getBufferState() {
        return {
            available: this.writeIndex - this.readIndex,
            capacity: this.buffer.length,
            isBuffering: this.isInitialBuffering
        };
    }
}

class AudioPlayerProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.playbackBuffer = new ExpandableBuffer();
        this.sampleRate = 24000; // Default, will be updated if needed
        this.lastProcessTime = 0; // Initialize with 0
        this.processCount = 0; // For debugging
        
        this.port.onmessage = (event) => {
            if (event.data.type === "audio") {
                this.playbackBuffer.write(event.data.audioData);
                
                // Send buffer state back to main thread
                this.port.postMessage({
                    type: "buffer-state",
                    state: this.playbackBuffer.getBufferState()
                });
            }
            else if (event.data.type === "initial-buffer-length") {
                // Override the current playback initial buffer length
                this.playbackBuffer.initialBufferLength = event.data.bufferLength;
            }
            else if (event.data.type === "barge-in") {
                this.playbackBuffer.clearBuffer();
            }
            else if (event.data.type === "set-sample-rate") {
                this.sampleRate = event.data.sampleRate;
            }
        };
    }

    process(inputs, outputs, parameters) {
        const output = outputs[0][0]; // Assume one output with one channel
        
        // AudioWorkletProcessor provides currentTime as a global property
        this.processCount++;
        
        // Only check timing occasionally to reduce message traffic
        if (this.processCount % 100 === 0) {
            // Use performance.now() or just send a heartbeat
            this.port.postMessage({
                type: "process-check",
                count: this.processCount
            });
        }
        
        // Process audio
        this.playbackBuffer.read(output);
        
        return true; // True to continue processing
    }
}

registerProcessor("audio-player-processor", AudioPlayerProcessor);
