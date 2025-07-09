/**
 * Converts a base64 encoded string to a Float32Array for audio playback
 * @param {string} base64String - Base64 encoded audio data
 * @returns {Float32Array} - Audio data as normalized float32 values
 */
function base64ToFloat32Array(base64String) {
    try {
        // Decode base64 to binary string
        const binaryString = atob(base64String);
        
        // Create byte array from binary string
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        // Convert to Int16Array (PCM format)
        const int16Array = new Int16Array(bytes.buffer);
        
        // Convert to Float32Array (normalized audio)
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            // Normalize to range [-1.0, 1.0]
            float32Array[i] = int16Array[i] / 32768.0;
        }

        return float32Array;
    } catch (error) {
        console.error("Error converting base64 to Float32Array:", error);
        // Return empty array on error
        return new Float32Array(0);
    }
}

/**
 * Creates a test tone for audio system verification
 * @param {number} frequency - Frequency of the tone in Hz
 * @param {number} duration - Duration in seconds
 * @param {number} sampleRate - Sample rate in Hz
 * @returns {Float32Array} - Audio data as normalized float32 values
 */
function createTestTone(frequency = 440, duration = 1, sampleRate = 24000) {
    const samples = Math.floor(duration * sampleRate);
    const tone = new Float32Array(samples);
    
    for (let i = 0; i < samples; i++) {
        // Generate sine wave
        tone[i] = Math.sin(2 * Math.PI * frequency * i / sampleRate) * 0.5;
    }
    
    return tone;
}

export { base64ToFloat32Array, createTestTone };
