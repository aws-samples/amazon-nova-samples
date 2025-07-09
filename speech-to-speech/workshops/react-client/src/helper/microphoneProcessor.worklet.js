class MicrophoneProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.targetSampleRate = 16000;
        this.inputSampleRate = 48000; // Default, will be updated from main thread
        this.resampleRatio = this.targetSampleRate / this.inputSampleRate;
        this.bufferSize = 512;
        this.buffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
        this.resampleBuffer = new Float32Array(Math.ceil(this.bufferSize * this.resampleRatio));
        
        // Setup message handling from main thread
        this.port.onmessage = (event) => {
            if (event.data.type === 'init') {
                this.inputSampleRate = event.data.inputSampleRate;
                this.resampleRatio = this.targetSampleRate / this.inputSampleRate;
                this.resampleBuffer = new Float32Array(Math.ceil(this.bufferSize * this.resampleRatio));
            }
        };
    }

    process(inputs, outputs) {
        const input = inputs[0][0]; // Get the first channel of the first input
        
        if (!input || input.length === 0) {
            return true;
        }

        // Process the input data
        for (let i = 0; i < input.length; i++) {
            this.buffer[this.bufferIndex++] = input[i];
            
            // When buffer is full, process and send it
            if (this.bufferIndex >= this.bufferSize) {
                this.processBuffer();
                this.bufferIndex = 0;
            }
        }
        
        return true; // Keep the processor alive
    }
    
    processBuffer() {
        // Simple linear resampling
        const resampledLength = Math.ceil(this.bufferSize * this.resampleRatio);
        for (let i = 0; i < resampledLength; i++) {
            const sourceIndex = i / this.resampleRatio;
            const sourceIndexFloor = Math.floor(sourceIndex);
            const sourceIndexCeil = Math.min(sourceIndexFloor + 1, this.bufferSize - 1);
            const fraction = sourceIndex - sourceIndexFloor;
            
            // Linear interpolation
            this.resampleBuffer[i] = (1 - fraction) * this.buffer[sourceIndexFloor] + 
                                    fraction * this.buffer[sourceIndexCeil];
        }
        
        // Convert to Int16 PCM
        const pcmBuffer = new Int16Array(resampledLength);
        for (let i = 0; i < resampledLength; i++) {
            const s = Math.max(-1, Math.min(1, this.resampleBuffer[i]));
            pcmBuffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        // Send the processed buffer to the main thread
        this.port.postMessage({
            type: 'audio',
            audioData: pcmBuffer
        });
    }
}

registerProcessor('microphone-processor', MicrophoneProcessor);
