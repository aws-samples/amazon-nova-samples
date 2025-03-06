import { WebSocketEventManager } from './websocketEvents.js';

let mediaRecorder;
let wsManager;

async function startStreaming() {
    wsManager = new WebSocketEventManager('ws://localhost:8081/interact-s2s');

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,           // Mono
                sampleRate: 16000,         // 16kHz
                sampleSize: 16,            // 16-bit
                echoCancellation: true,    // Enable echo cancellation
                noiseSuppression: true,    // Enable noise suppression
                autoGainControl: true      // Enable automatic gain control
            }
        });

        // Create AudioContext for processing
        const audioContext = new AudioContext({
            sampleRate: 16000,
            latencyHint: 'interactive'
        });

        // Create MediaStreamSource
        const source = audioContext.createMediaStreamSource(stream);

        // Create ScriptProcessor for raw PCM data
        const processor = audioContext.createScriptProcessor(1024, 1, 1);

        source.connect(processor);
        processor.connect(audioContext.destination);

        processor.onaudioprocess = (e) => {
            const inputData = e.inputBuffer.getChannelData(0);

            // Convert Float32Array to Int16Array
            const pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
                // Convert float to 16-bit integer
                const s = Math.max(-1, Math.min(1, inputData[i]));
                pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }

            // Convert to base64
            const base64data = btoa(String.fromCharCode.apply(null,
                new Uint8Array(pcmData.buffer)
            ));

            // Send to WebSocket
            if (wsManager) {
                wsManager.sendAudioChunk(base64data);
            }
        };

        document.getElementById("start").disabled = true;
        document.getElementById("stop").disabled = false;

        // Store cleanup functions
        window.audioCleanup = () => {
            processor.disconnect();
            source.disconnect();
            stream.getTracks().forEach(track => track.stop());
        };

    } catch (error) {
        console.error("Error accessing microphone:", error);
    }
}

function stopStreaming() {
    // Cleanup audio processing
    if (window.audioCleanup) {
        window.audioCleanup();
    }

    if (wsManager) {
        wsManager.cleanup();
    }

    document.getElementById("start").disabled = false;
    document.getElementById("stop").disabled = true;
}

// Event listeners
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("start").addEventListener("click", startStreaming);
    document.getElementById("stop").addEventListener("click", stopStreaming);
});

// Ensure audio context is resumed after user interaction
document.addEventListener('click', () => {
    if (wsManager && wsManager.audioContext.state === 'suspended') {
        wsManager.audioContext.resume();
    }
}, { once: true });
