import AudioPlayer from "./lib/play/AudioPlayer";
import ChatHistoryManager from "./lib/util/ChatHistoryManager.js";

const audioPlayer = new AudioPlayer();

export class WebSocketEventManager {
    constructor(wsUrl) {
        this.wsUrl = wsUrl;
        this.promptName = null;
        this.audioContentName = null;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.currentAudioConfig = null;
        this.isProcessing = false;

        this.chat = { history: [] };
        this.chatRef = { current: this.chat };

        this.chatHistoryManager = ChatHistoryManager.getInstance(
            this.chatRef,
            (newChat) => {
                this.chat = { ...newChat };
                this.chatRef.current = this.chat;
                this.updateChatUI();
            }
        );

        this.connect();
    }

    updateChatUI() {
        const chatContainer = document.getElementById('chat-container');
        if (!chatContainer) {
            console.error("Chat container not found");
            return;
        }

        // Clear existing chat messages
        chatContainer.innerHTML = '';

        // Add all messages from history
        this.chat.history.forEach(item => {
            if (item.endOfConversation) {
                const endDiv = document.createElement('div');
                endDiv.className = 'message system';
                endDiv.textContent = "Conversation ended";
                chatContainer.appendChild(endDiv);
                return;
            }

            if (item.role) {
                const messageDiv = document.createElement('div');
                const roleLowerCase = item.role.toLowerCase();
                messageDiv.className = `message ${roleLowerCase}`;

                const roleLabel = document.createElement('div');
                roleLabel.className = 'role-label';
                roleLabel.textContent = item.role;
                messageDiv.appendChild(roleLabel);

                const content = document.createElement('div');
                content.textContent = item.message || "No content";
                messageDiv.appendChild(content);

                chatContainer.appendChild(messageDiv);
            }
        });
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }


    connect() {
        if (this.socket) {
            this.socket.close();
        }
        this.socket = new WebSocket(this.wsUrl);
        this.setupSocketListeners();
    }

    setupSocketListeners() {
        this.socket.onopen = () => {
            console.log("WebSocket Connected");
            this.updateStatus("Connected", "connected");
            this.isProcessing = true;
            this.startSession();
            audioPlayer.start();
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (e) {
                console.error("Error parsing message:", e, "Raw data:", event.data);
            }
        };

        this.socket.onerror = (error) => {
            console.error("WebSocket Error:", error);
            this.updateStatus("Connection error", "error");
            this.isProcessing = false;
        };

        this.socket.onclose = (event) => {
            console.log("WebSocket Disconnected", event);
            this.updateStatus("Disconnected", "disconnected");
            this.isProcessing = false;
            audioPlayer.stop();
            if (this.isProcessing) {
                console.log("Attempting to reconnect...");
                setTimeout(() => this.connect(), 1000);
            }
        };
    }

    async sendEvent(event) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.error("WebSocket is not open. Current state:", this.socket?.readyState);
            return;
        }

        try {
            //console.log("Sending event:", JSON.stringify(event, null, 2));
            this.socket.send(JSON.stringify(event));
        } catch (error) {
            console.error("Error sending event:", error);
            this.updateStatus("Error sending message", "error");
        }
    }

    handleMessage(data) {
        if (!data.event) {
            console.error("Received message without event:", data);
            return;
        }

        const event = data.event;
        console.log("Event received");

        try {
            // Handle completionStart
            if (event.completionStart) {
                console.log("Completion start received:", event.completionStart);
                this.promptName = event.completionStart.promptName;
            }
            // Handle contentStart
            else if (event.contentStart) {
                console.log("Content start received:", event.contentStart);
                if (event.contentStart.type === "AUDIO") {
                    this.currentAudioConfig = event.contentStart.audioOutputConfiguration;
                    this.audioBuffer = [];
                }
            }
            // Handle textOutput
            else if (event.textOutput) {
                console.log("Text output received:", event.textOutput);
                const messageData = {
                    role: event.textOutput.role
                };
                if(messageData.role === "ASSISTANT" && event.textOutput.content.startsWith("Speculative: ")) {
                    messageData.content = event.textOutput.content.slice(13);
                }
                else if (messageData.role === "USER") {
                    messageData.content = event.textOutput.content;
                }
                this.handleTextOutput(messageData);
            }
            // Handle audioOutput
            else if (event.audioOutput) {
                console.log("Audio output received");
                if (this.currentAudioConfig) {
                    audioPlayer.playAudio(this.base64ToFloat32Array(event.audioOutput.content));
                }
            }
            // Handle contentEnd
            else if (event.contentEnd) {
                console.log("Content end received:", event.contentEnd);
                switch (event.contentEnd.type) {
                    case "TEXT":
                    if (event.contentEnd.stopReason.toUpperCase() === "END_TURN") {
                        this.chatHistoryManager.endTurn();
                     }
                     else if (event.contentEnd.stopReason.toUpperCase()  === "INTERRUPTED") {
                         audioPlayer.bargeIn();
                     }
                     break;
                    default:
                        console.log("Received content end for type:", event.contentEnd.type);
                }
            }
            // Handle completionEnd
            else if (event.completionEnd) {
                console.log("Completion end received:", event.completionEnd);
            }
            else {
                console.warn("Unknown event type received:", Object.keys(event)[0]);
            }
        } catch (error) {
            console.error("Error processing message:", error);
            console.error("Event data:", event);
        }
    }

    handleTextOutput(data) {
        console.log("Processing text output:", data);
        if(data.content) {
            const messageData = {
                role: data.role,
                message: data.content
            };
            this.chatHistoryManager.addTextMessage(messageData);
        }
    }

    base64ToFloat32Array(base64String) {
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
    }

    updateStatus(message, className) {
        const statusDiv = document.getElementById('status');
        if (statusDiv) {
            statusDiv.textContent = message;
            statusDiv.className = `status ${className}`;
        }
    }

    startSession() {
        console.log("Starting session...");
        const sessionStartEvent = {
            event: {
                sessionStart: {
                    inferenceConfiguration: {
                        maxTokens: 10000,
                        topP: 0.95,
                        temperature: 0.9
                    }
                }
            }
        };
        console.log("Sending session start:", JSON.stringify(sessionStartEvent, null, 2));
        this.sendEvent(sessionStartEvent);
        this.startPrompt();
    }

    startPrompt() {
        this.promptName = crypto.randomUUID();
        const toolInputSchema = `{\"$schema\":\"http://json-schema.org/draft-07/schema#\",\"type\":\"object\",\"properties\":{\"chatHistory\":{\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{\"role\":{\"type\":\"string\",\"enum\":[\"SYSTEM\",\"USER\",\"ASSISTANT\"]},\"content\":{\"type\":\"string\"},\"metadata\":{\"type\":\"array\",\"items\":{\"type\":\"string\"}},\"interrupted\":{\"type\":\"object\",\"properties\":{\"status\":{\"type\":\"boolean\"},\"offsetInMilliseconds\":{\"type\":\"string\"}},\"required\":[\"status\",\"offsetInMilliseconds\"],\"additionalProperties\":false}},\"required\":[\"role\",\"content\"]}}},\"required\":[\"chatHistory\"]}`;

        const promptStartEvent = {
            event: {
                promptStart: {
                    promptName: this.promptName,
                    textOutputConfiguration: {
                        mediaType: "text/plain"
                    },
                    audioOutputConfiguration: {
                        mediaType: "audio/lpcm",
                        sampleRateHertz: 24000,
                        sampleSizeBits: 16,
                        channelCount: 1,
                        voiceId: "en_us_matthew",
                        encoding: "base64",
                        audioType: "SPEECH"
                    },
                    toolUseOutputConfiguration: {
                        mediaType: "application/json"
                    },
                    toolConfiguration: {
                        tools: [{
                            toolSpec: {
                                name: "agi-interactive-console::externalLLM",
                                description: "Nova reasoning tool.",
                                inputSchema: {
                                    json: toolInputSchema
                                }
                            }
                        }]
                    }
                }
            }
        };
        this.sendEvent(promptStartEvent);
        this.sendSystemPrompt();
    }

    sendSystemPrompt() {
        const systemContentName = crypto.randomUUID();
        const contentStartEvent = {
            event: {
                contentStart: {
                    promptName: this.promptName,
                    contentName: systemContentName,
                    type: "TEXT",
                    interactive: true,
                    textInputConfiguration: {
                        mediaType: "text/plain"
                    }
                }
            }
        };
        this.sendEvent(contentStartEvent);

        const interactMultiModelTextData =
            "Convert streaming speech to text, call an external model for text responses, emit turn taking events, " +
            "and convert the text to speech. The transcription and response should be in spoken form with no capitalization " +
            "and punctuations.";

        const textInputEvent = {
            event: {
                textInput: {
                    promptName: this.promptName,
                    contentName: systemContentName,
                    content: interactMultiModelTextData,
                    role: "SYSTEM"
                }
            }
        };
        this.sendEvent(textInputEvent);

        const contentEndEvent = {
            event: {
                contentEnd: {
                    promptName: this.promptName,
                    contentName: systemContentName
                }
            }
        };
        this.sendEvent(contentEndEvent);

        this.startAudioContent();
    }

    startAudioContent() {
        this.audioContentName = crypto.randomUUID();
        const contentStartEvent = {
            event: {
                contentStart: {
                    promptName: this.promptName,
                    contentName: this.audioContentName,
                    type: "AUDIO",
                    interactive: true,
                    audioInputConfiguration: {
                        mediaType: "audio/lpcm",
                        sampleRateHertz: 16000,
                        sampleSizeBits: 16,
                        channelCount: 1,
                        audioType: "SPEECH",
                        encoding: "base64"
                    }
                }
            }
        };
        this.sendEvent(contentStartEvent);
    }

    sendAudioChunk(base64AudioData) {
        if (!this.promptName || !this.audioContentName) {
            console.error("Cannot send audio chunk - missing promptName or audioContentName");
            return;
        }

        const audioInputEvent = {
            event: {
                audioInput: {
                    promptName: this.promptName,
                    contentName: this.audioContentName,
                    content: base64AudioData,
                    role: "USER"
                }
            }
        };
        this.sendEvent(audioInputEvent);
    }

    endContent() {
        const contentEndEvent = {
            event: {
                contentEnd: {
                    promptName: this.promptName,
                    contentName: this.audioContentName
                }
            }
        };
        this.sendEvent(contentEndEvent);
    }

    endPrompt() {
        const promptEndEvent = {
            event: {
                promptEnd: {
                    promptName: this.promptName
                }
            }
        };
        this.sendEvent(promptEndEvent);
    }

    endSession() {
        const sessionEndEvent = {
            event: {
                sessionEnd: {}
            }
        };
        this.sendEvent(sessionEndEvent);
        this.socket.close();
    }

    cleanup() {
        this.isProcessing = false;
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            try {
                if (this.audioContentName && this.promptName) {
                    this.endContent();
                    this.endPrompt();
                }
                this.endSession();
            } catch (error) {
                console.error("Error during cleanup:", error);
            }
        }
        this.chatHistoryManager.endConversation();
    }
}
