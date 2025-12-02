import { WebSocketEventManager } from './websocketEvents.js';

let wsManager;
let isMuted = false;
let audioContext;
let source;
let processor;
let silentInterval;

// Firefox detection and audio handling
let samplingRatio = 1;
const TARGET_SAMPLE_RATE = 16000;
const isFirefox = navigator.userAgent.toLowerCase().includes('firefox');

// Voice gender mapping
const feminineVoices = ['tiffany', 'amy', 'olivia', 'lupe', 'ambre', 'tina', 'beatrice', 'carolina', 'kiara'];
const masculineVoices = ['matthew', 'carlos', 'florian', 'lennart', 'lorenzo', 'leo', 'arjun'];

// Get configuration values
function getConfiguration() {
    const systemPrompt = document.getElementById('system-prompt').value;
    const voiceId = document.getElementById('voice-select').value;
    return { systemPrompt, voiceId };
}

// Update system prompt based on voice selection
function updateSystemPromptForVoice(voiceId) {
    const systemPromptTextarea = document.getElementById('system-prompt');
    const basePrompt = "You are a warm, professional, and helpful";
    const commonPrompt = "AI assistant. Give accurate answers that sound natural, direct, and human. Start by answering the user's question clearly in 1–2 sentences. Then, expand only enough to make the answer understandable, staying within 3–5 short sentences total. Avoid sounding like a lecture or essay.";

    if (feminineVoices.includes(voiceId)) {
        systemPromptTextarea.value = `${basePrompt} female ${commonPrompt}`;
    } else if (masculineVoices.includes(voiceId)) {
        systemPromptTextarea.value = `${basePrompt} male ${commonPrompt}`;
    }
}

async function startStreaming() {
    const config = getConfiguration();
    wsManager = new WebSocketEventManager('ws://localhost:8081/interact-s2s', config);

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                sampleSize: 16,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        // Create AudioContext for processing
        // Firefox doesn't allow audio context to have different sample rate than what the user media device offers
        if (isFirefox) {
            audioContext = new AudioContext({
                latencyHint: 'interactive'
            });
        } else {
            audioContext = new AudioContext({
                sampleRate: TARGET_SAMPLE_RATE,
                latencyHint: 'interactive'
            });
        }

        // samplingRatio - is only relevant for Firefox, for Chromium based browsers, it's always 1
        samplingRatio = audioContext.sampleRate / TARGET_SAMPLE_RATE;
        console.log(`Debug AudioContext - sampleRate: ${audioContext.sampleRate}, samplingRatio: ${samplingRatio}`);

        // Create MediaStreamSource
        source = audioContext.createMediaStreamSource(stream);

        // Create ScriptProcessor for raw PCM data
        processor = audioContext.createScriptProcessor(512, 1, 1);

        source.connect(processor);
        processor.connect(audioContext.destination);

        processor.onaudioprocess = (e) => {
            if (wsManager) {
                if (isMuted) {
                    // Send silent audio frame when muted
                    sendSilentFrame(512);
                } else {
                    // Send actual audio data
                    const inputData = e.inputBuffer.getChannelData(0);
                    sendAudioFrame(inputData);
                }
            }
        };

        document.getElementById("start").disabled = true;
        document.getElementById("stop").disabled = false;
        document.getElementById("mute").disabled = false;

        // Enable text input when streaming starts
        document.getElementById("text-input").disabled = false;
        document.getElementById("send-text").disabled = false;

        // Store cleanup functions
        window.audioCleanup = () => {
            processor.disconnect();
            source.disconnect();
            stream.getTracks().forEach(track => track.stop());
            if (silentInterval) clearInterval(silentInterval);
        };

    } catch (error) {
        console.error("Error accessing microphone:", error);
    }
}

function sendAudioFrame(inputData) {
    // Handle Firefox resampling
    const numSamples = isFirefox ? Math.round(inputData.length / samplingRatio) : inputData.length;
    const buffer = new ArrayBuffer(numSamples * 2);
    const pcmData = new DataView(buffer);

    if (isFirefox) {
        // Resample for Firefox
        for (let i = 0; i < numSamples; i++) {
            const sourceIndex = Math.floor(i * samplingRatio);
            const sample = inputData[sourceIndex];
            const int16 = Math.max(-32768, Math.min(32767, Math.round(sample * 32767)));
            pcmData.setInt16(i * 2, int16, true);
        }
    } else {
        // Direct conversion for Chromium browsers
        for (let i = 0; i < inputData.length; i++) {
            const int16 = Math.max(-32768, Math.min(32767, Math.round(inputData[i] * 32767)));
            pcmData.setInt16(i * 2, int16, true);
        }
    }

    // Binary data string
    let data = "";
    for (let i = 0; i < pcmData.byteLength; i++) {
        data += String.fromCharCode(pcmData.getUint8(i));
    }

    // Send to WebSocket
    wsManager.sendAudioChunk(btoa(data));
}

function sendSilentFrame(frameSize) {
    // Create silent audio buffer (all zeros)
    const buffer = new ArrayBuffer(frameSize * 2);
    const pcmData = new DataView(buffer);
    
    for (let i = 0; i < frameSize * 2; i++) {
        pcmData.setUint8(i, 0);
    }
    
    // Binary data string
    let data = "";
    for (let i = 0; i < pcmData.byteLength; i++) {
        data += String.fromCharCode(pcmData.getUint8(i));
    }

    // Send to WebSocket
    wsManager.sendAudioChunk(btoa(data));
}

function toggleMute() {
    isMuted = !isMuted;
    const muteButton = document.getElementById("mute");
    
    if (isMuted) {
        muteButton.textContent = "Unmute";
        muteButton.classList.add("muted");
    } else {
        muteButton.textContent = "Mute";
        muteButton.classList.remove("muted");
    }
}

function stopStreaming() {
    // Immediately clear audio buffer (barge-in)
    if (wsManager && wsManager.audioPlayer) {
        wsManager.audioPlayer.bargeIn();
    }

    // Cleanup audio processing
    if (window.audioCleanup) {
        window.audioCleanup();
    }

    if (wsManager) {
        wsManager.cleanup();
        wsManager = null; // Reset wsManager to allow fresh connection
    }

    document.getElementById("start").disabled = false;
    document.getElementById("stop").disabled = true;
    document.getElementById("mute").disabled = true;

    // Disable text input when not streaming
    document.getElementById("text-input").disabled = true;
    document.getElementById("send-text").disabled = true;

    // Reset mute button
    isMuted = false;
    const muteButton = document.getElementById("mute");
    muteButton.textContent = "Mute";
    muteButton.classList.remove("muted");
}

function sendTextMessage() {
    const textInput = document.getElementById('text-input');
    const message = textInput.value.trim();

    if (!message || !wsManager) {
        return;
    }

    console.log('Sending text message:', message);

    // Add the user's text message to chat history immediately
    const messageData = {
        role: 'USER',
        message: message
    };
    wsManager.chatHistoryManager.addTextMessage(messageData);

    // Send to WebSocket
    wsManager.sendTextInput(message);

    // Clear input
    textInput.value = '';
}

// Event listeners
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("start").addEventListener("click", startStreaming);
    document.getElementById("stop").addEventListener("click", stopStreaming);
    document.getElementById("mute").addEventListener("click", toggleMute);
    document.getElementById("mute").disabled = true;

    // Text input event listeners
    const textInput = document.getElementById('text-input');
    const sendButton = document.getElementById('send-text');

    sendButton.addEventListener('click', sendTextMessage);
    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendTextMessage();
        }
    });

    // Config panel toggle
    const configToggle = document.getElementById('config-toggle');
    const configSection = document.getElementById('config-section');

    configToggle.addEventListener('click', () => {
        configSection.classList.toggle('collapsed');
    });

    // Configuration inputs
    const startButton = document.getElementById("start");
    const stopButton = document.getElementById("stop");
    const systemPromptInput = document.getElementById("system-prompt");
    const voiceSelect = document.getElementById("voice-select");

    // Update system prompt when voice selection changes (before streaming starts)
    voiceSelect.addEventListener('change', (e) => {
        console.log('Voice changed to:', e.target.value);
        console.log('System prompt disabled:', systemPromptInput.disabled);
        if (!systemPromptInput.disabled) {
            updateSystemPromptForVoice(e.target.value);
            console.log('System prompt updated to:', systemPromptInput.value);
        }
    });

    startButton.addEventListener("click", () => {
        systemPromptInput.disabled = true;
        voiceSelect.disabled = true;
        textInput.disabled = false;
        sendButton.disabled = false;
    });

    stopButton.addEventListener("click", () => {
        systemPromptInput.disabled = false;
        voiceSelect.disabled = false;
        textInput.disabled = true;
        sendButton.disabled = true;
    });
});

// Ensure audio context is resumed after user interaction
document.addEventListener('click', () => {
    if (audioContext && audioContext.state === 'suspended') {
        audioContext.resume();
    }
}, { once: true });
