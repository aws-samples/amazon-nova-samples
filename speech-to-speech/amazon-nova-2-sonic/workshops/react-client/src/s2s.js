import React, { createRef } from 'react';
import './s2s.css'
import { Icon, Alert, Button, Modal, Box, SpaceBetween, FormField, Select, Textarea, Checkbox, Input, Container, Header, Badge } from '@cloudscape-design/components';
import S2sEvent from './helper/s2sEvents';
import Meter from './components/meter';
import S2sEventDisplay from './components/eventDisplay';
import Settings from './components/settings';
import { base64ToFloat32Array } from './helper/audioHelper';
import AudioPlayer from './helper/audioPlayer';
import { DemoProfiles, Voices } from './helper/config';

class S2sChatBot extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            status: "loading", // null, loading, loaded
            alert: null,
            sessionStarted: false,
            showEventJson: false,
            showConfig: false,
            selectedEvent: null,

            chatMessages: {},
            events: [],
            audioChunks: [],
            audioPlayPromise: null,
            includeChatHistory: false,

            selectedDemoProfileOption: DemoProfiles ? {
                label: DemoProfiles[0].name,
                value: DemoProfiles[0].name,
                description: DemoProfiles[0].description
            } : {},

            promptName: null,
            textContentName: null,
            audioContentName: null,

            inputText: "",

            showUsage: true,

            // S2S config items
            configAudioInput: null,
            configSystemPrompt: S2sEvent.DEFAULT_SYSTEM_PROMPT,
            configAudioOutput: S2sEvent.DEFAULT_AUDIO_OUTPUT_CONFIG,
            configVoiceIdOption: { label: "Matthew (en-US)", value: "matthew" },
            configTurnSensitivity: "MEDIUM",
            configToolUse: JSON.stringify(S2sEvent.DEFAULT_TOOL_CONFIG, null, 2),
            configChatHistory: JSON.stringify(S2sEvent.DEFAULT_CHAT_HISTORY, null, 2),
            enableParalinguisticDetection: false,
        };
        this.socket = null;
        this.mediaRecorder = null;
        this.chatMessagesEndRef = React.createRef();
        this.stateRef = React.createRef();
        this.eventDisplayRef = React.createRef();
        this.meterRef = React.createRef();
        this.audioPlayer = new AudioPlayer();
    }

    componentDidMount() {
        this.stateRef.current = this.state;

        // Restore saved state from localStorage
        this.restoreStateFromStorage();

        // Initialize audio player early
        this.audioPlayer.start().catch(err => {
            console.error("Failed to initialize audio player:", err);
        });

        // Scroll to bottom on initial load
        setTimeout(() => {
            this.scrollToBottom();
        }, 100);

        // Check if we should auto-start the session after page reload
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('autoStart') === 'true') {
            // Remove the parameter from URL
            const url = new URL(window.location);
            url.searchParams.delete('autoStart');
            window.history.replaceState({}, document.title, url.toString());

            // Auto-start the session after a brief delay
            setTimeout(() => {
                this.startSession();
            }, 500);
        } else {
            // Clean up URL if there are any leftover parameters
            const url = new URL(window.location);
            if (url.searchParams.has('autoStart')) {
                url.searchParams.delete('autoStart');
                window.history.replaceState({}, document.title, url.toString());
            }
        }
    }

    componentWillUnmount() {
        this.audioPlayer.stop();
    }

    saveStateToStorage = () => {
        const stateToSave = {
            includeChatHistory: this.state.includeChatHistory,
            selectedDemoProfileOption: this.state.selectedDemoProfileOption,
            configVoiceIdOption: this.state.configVoiceIdOption,
            configTurnSensitivity: this.state.configTurnSensitivity,
            configSystemPrompt: this.state.configSystemPrompt,
            configToolUse: this.state.configToolUse,
            configChatHistory: this.state.configChatHistory,
            configAudioOutput: this.state.configAudioOutput,
            enableParalinguisticDetection: this.state.enableParalinguisticDetection
        };

        try {
            localStorage.setItem('s2s_saved_state', JSON.stringify(stateToSave));
        } catch (error) {
            console.error('Failed to save state to localStorage:', error);
        }
    }

    restoreStateFromStorage = () => {
        try {
            const savedState = localStorage.getItem('s2s_saved_state');
            if (savedState) {
                const parsedState = JSON.parse(savedState);
                this.setState({
                    includeChatHistory: parsedState.includeChatHistory || false,
                    selectedDemoProfileOption: parsedState.selectedDemoProfileOption || this.state.selectedDemoProfileOption,
                    configVoiceIdOption: parsedState.configVoiceIdOption || this.state.configVoiceIdOption,
                    configTurnSensitivity: parsedState.configTurnSensitivity || this.state.configTurnSensitivity,
                    configSystemPrompt: parsedState.configSystemPrompt || this.state.configSystemPrompt,
                    configToolUse: parsedState.configToolUse || this.state.configToolUse,
                    configChatHistory: parsedState.configChatHistory || this.state.configChatHistory,
                    configAudioOutput: parsedState.configAudioOutput || this.state.configAudioOutput,
                    enableParalinguisticDetection: parsedState.enableParalinguisticDetection || false
                });

                // Clear the saved state after restoring to prevent stale data
                localStorage.removeItem('s2s_saved_state');
            }
        } catch (error) {
            console.error('Failed to restore state from localStorage:', error);
        }
    }

    startSession = () => {
        // Start session logic
        this.setState({
            chatMessages: {},
            events: [],
            sessionStarted: true
        }, () => {
            // Scroll to bottom when starting new session
            this.scrollToBottom();
        });

        if (this.eventDisplayRef.current) this.eventDisplayRef.current.cleanup();
        if (this.meterRef.current) this.meterRef.current.start();

        // Init S2sSessionManager
        try {
            if (this.socket === null || this.socket.readyState !== WebSocket.OPEN) {
                this.connectWebSocket();
            }

            // Start microphone 
            this.startMicrophone();
        } catch (error) {
            console.error('Error accessing microphone: ', error);
        }
    }

    scrollToBottom = () => {
        if (this.chatMessagesEndRef.current) {
            this.chatMessagesEndRef.current.scrollIntoView({
                behavior: 'smooth',
                block: 'end'
            });
        }
    }

    componentDidUpdate(prevProps, prevState) {
        this.stateRef.current = this.state;

        if (prevState.chatMessages.length !== this.state.chatMessages.length) {
            // Check if chat messages have changed by comparing the number of keys
            const prevMessageCount = Object.keys(prevState.chatMessages || {}).length;
            const currentMessageCount = Object.keys(this.state.chatMessages || {}).length;

            if (prevMessageCount !== currentMessageCount) {
                // Use setTimeout to ensure DOM is updated before scrolling
                setTimeout(() => {
                    this.scrollToBottom();
                }, 100);
            }
        }
    }

    sendEvent(event) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(event));
            event.timestamp = Date.now();

            this.eventDisplayRef.current.displayEvent(event, "out");
        }
    }

    cancelAudio() {
        this.audioPlayer.bargeIn();
        this.setState({ isPlaying: false });
    }

    handleIncomingMessage(message) {
        const eventType = Object.keys(message?.event)[0];
        const role = message.event[eventType]["role"];
        const content = message.event[eventType]["content"];
        const contentId = message.event[eventType].contentId;
        let stopReason = message.event[eventType].stopReason;
        const contentType = message.event[eventType].type;
        var chatMessages = this.state.chatMessages;

        switch (eventType) {
            case "textOutput":
                // Detect interruption
                if (role === "ASSISTANT" && content.startsWith("{")) {
                    const evt = JSON.parse(content);
                    if (evt.interrupted === true) {
                        this.cancelAudio()
                    }
                }

                if (chatMessages.hasOwnProperty(contentId)) {
                    chatMessages[contentId].content = content;
                    chatMessages[contentId].role = role;
                    if (chatMessages[contentId].raw === undefined)
                        chatMessages[contentId].raw = [];
                    chatMessages[contentId].raw.push(message);

                    // Limit raw events to prevent memory issues, keep only the most recent 1000
                    if (chatMessages[contentId].raw.length > 1000) {
                        chatMessages[contentId].raw = chatMessages[contentId].raw.slice(-1000);
                    }
                }

                this.setState({ chatMessages: chatMessages }, () => {
                    // Scroll to bottom immediately after state update
                    this.scrollToBottom();
                });

                break;
            case "audioOutput":
                try {
                    const base64Data = message.event[eventType].content;
                    const audioData = base64ToFloat32Array(base64Data);
                    this.audioPlayer.playAudio(audioData);
                } catch (error) {
                    console.error("Error processing audio chunk:", error);
                }
                break;
            case "contentStart":
                if (contentType === "TEXT") {
                    var generationStage = "";
                    if (message.event.contentStart.additionalModelFields) {
                        generationStage = JSON.parse(message.event.contentStart.additionalModelFields)?.generationStage;
                    }

                    chatMessages[contentId] = {
                        "content": "",
                        "role": role,
                        "generationStage": generationStage,
                        "raw": [],
                        "inputSource": "audio", // Messages from ASR are audio-based
                    };
                    chatMessages[contentId].raw.push(message);

                    // Limit raw events to prevent memory issues, keep only the most recent 1000
                    if (chatMessages[contentId].raw.length > 1000) {
                        chatMessages[contentId].raw = chatMessages[contentId].raw.slice(-1000);
                    }

                    this.setState({ chatMessages: chatMessages }, () => {
                        // Scroll to bottom immediately after state update
                        this.scrollToBottom();
                    });
                }
                break;
            case "contentEnd":
                if (contentType === "TEXT") {
                    if (chatMessages.hasOwnProperty(contentId)) {
                        if (chatMessages[contentId].raw === undefined)
                            chatMessages[contentId].raw = [];
                        chatMessages[contentId].raw.push(message);

                        // Limit raw events to prevent memory issues, keep only the most recent 1000
                        if (chatMessages[contentId].raw.length > 1000) {
                            chatMessages[contentId].raw = chatMessages[contentId].raw.slice(-1000);
                        }

                        chatMessages[contentId].stopReason = stopReason;
                    }

                    this.setState({ chatMessages: chatMessages }, () => {
                        // Scroll to bottom immediately after state update
                        this.scrollToBottom();
                    });
                }
                break;
            case "usageEvent":
                if (this.meterRef.current) {
                    this.meterRef.current.updateMeter(message);
                    if (this.state.showUsage === false) {
                        this.setState({ showUsage: true });
                    }
                }
                break;
            default:
                break;

        }

        this.eventDisplayRef.current.displayEvent(message, "in");
    }

    handleSessionChange = e => {
        if (this.state.sessionStarted) {
            // End session
            this.endSession();
            this.cancelAudio();
            if (this.meterRef.current) this.meterRef.current.stop();
            this.audioPlayer.start();
            this.setState({ sessionStarted: false });
        }
        else {
            // Save current state and reload page to start fresh session
            this.saveStateToStorage();

            // Small delay to show the message, then reload
            setTimeout(() => {
                const url = new URL(window.location);
                url.searchParams.set('autoStart', 'true');
                window.location.href = url.toString();
            }, 300);
        }
    }

    connectWebSocket() {
        // Connect to the S2S WebSocket server
        if (this.socket === null || this.socket.readyState !== WebSocket.OPEN) {
            const promptName = crypto.randomUUID();
            const textContentName = crypto.randomUUID();
            const textSentimentContentName = crypto.randomUUID();
            const audioContentName = crypto.randomUUID();
            this.setState({
                promptName: promptName,
                textContentName: textContentName,
                audioContentName: audioContentName
            })

            const ws_url = process.env.REACT_APP_WEBSOCKET_URL ? process.env.REACT_APP_WEBSOCKET_URL : "ws://localhost:8081"
            this.socket = new WebSocket(ws_url);
            this.socket.onopen = () => {
                console.log("WebSocket connected!");

                // sessionStart
                this.sendEvent(S2sEvent.sessionStart(S2sEvent.DEFAULT_INFER_CONFIG, this.state.configTurnSensitivity));

                // promptStart
                var audioConfig = S2sEvent.DEFAULT_AUDIO_OUTPUT_CONFIG;
                audioConfig.voiceId = this.state.configVoiceIdOption.value;
                var toolConfig = this.state.configToolUse ? JSON.parse(this.state.configToolUse) : S2sEvent.DEFAULT_TOOL_CONFIG;

                this.sendEvent(S2sEvent.promptStart(promptName, audioConfig, toolConfig));

                // contentStart: system prompt
                this.sendEvent(S2sEvent.contentStartText(promptName, textContentName));
                this.sendEvent(S2sEvent.textInput(promptName, textContentName, this.state.configSystemPrompt));
                this.sendEvent(S2sEvent.contentEnd(promptName, textContentName));

                // contentStart: paralinguistic (sentiment detection)
                if (this.state.enableParalinguisticDetection) {
                    this.sendEvent(S2sEvent.contentStartText(promptName, textSentimentContentName, "SYSTEM_SPEECH", false));
                    this.sendEvent(S2sEvent.textInput(promptName, textSentimentContentName, S2sEvent.DEFAULT_SENTIMENT_PROMPT));
                    this.sendEvent(S2sEvent.contentEnd(promptName, textSentimentContentName));
                }

                // Chat history
                if (this.state.includeChatHistory) {
                    var chatHistory = JSON.parse(this.state.configChatHistory);
                    if (chatHistory === null) chatHistory = S2sEvent.DEFAULT_CHAT_HISTORY;
                    for (const chat of chatHistory) {
                        const chatHistoryContentName = crypto.randomUUID();
                        this.sendEvent(S2sEvent.contentStartText(promptName, chatHistoryContentName, chat.role));
                        this.sendEvent(S2sEvent.textInput(promptName, chatHistoryContentName, chat.content));
                        this.sendEvent(S2sEvent.contentEnd(promptName, chatHistoryContentName));
                    }

                }

                this.sendEvent(S2sEvent.contentStartAudio(promptName, audioContentName));
            };

            // Handle incoming messages
            this.socket.onmessage = (message) => {
                const event = JSON.parse(message.data);
                this.handleIncomingMessage(event);
            };

            // Handle errors
            this.socket.onerror = (error) => {
                this.setState({ alert: "WebSocket Error: ", error });
                console.error("WebSocket Error: ", error);
            };

            // Handle connection close
            this.socket.onclose = () => {
                console.log("WebSocket Disconnected");
                if (this.state.sessionStarted)
                    this.setState({ alert: "WebSocket Disconnected" });
            };
        }
    }

    async startMicrophone() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            const audioContext = new (window.AudioContext || window.webkitAudioContext)({
                latencyHint: 'interactive'
            });

            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(512, 1, 1);

            source.connect(processor);
            processor.connect(audioContext.destination);

            const targetSampleRate = 16000;

            processor.onaudioprocess = async (e) => {
                if (this.state.sessionStarted) {
                    const inputBuffer = e.inputBuffer;

                    // Create an offline context for resampling
                    const offlineContext = new OfflineAudioContext({
                        numberOfChannels: 1,
                        length: Math.ceil(inputBuffer.duration * targetSampleRate),
                        sampleRate: targetSampleRate
                    });

                    // Copy input to offline context buffer
                    const offlineSource = offlineContext.createBufferSource();
                    const monoBuffer = offlineContext.createBuffer(1, inputBuffer.length, inputBuffer.sampleRate);
                    monoBuffer.copyToChannel(inputBuffer.getChannelData(0), 0);

                    offlineSource.buffer = monoBuffer;
                    offlineSource.connect(offlineContext.destination);
                    offlineSource.start(0);

                    // Resample and get the rendered buffer
                    const renderedBuffer = await offlineContext.startRendering();
                    const resampled = renderedBuffer.getChannelData(0);

                    // Convert to Int16 PCM
                    const buffer = new ArrayBuffer(resampled.length * 2);
                    const pcmData = new DataView(buffer);

                    for (let i = 0; i < resampled.length; i++) {
                        const s = Math.max(-1, Math.min(1, resampled[i]));
                        pcmData.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
                    }

                    // Convert to binary string and base64 encode
                    let binary = '';
                    for (let i = 0; i < pcmData.byteLength; i++) {
                        binary += String.fromCharCode(pcmData.getUint8(i));
                    }

                    const currentState = this.stateRef.current;
                    const event = S2sEvent.audioInput(
                        currentState.promptName,
                        currentState.audioContentName,
                        btoa(binary)
                    );
                    this.sendEvent(event);
                }
            };

            window.audioCleanup = () => {
                processor.disconnect();
                source.disconnect();
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder = new MediaRecorder(stream);
            this.mediaRecorder.ondataavailable = (event) => {
                this.state.audioChunks.push(event.data);
            };
            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.state.audioChunks, { type: 'audio/webm' });
                this.sendEvent(S2sEvent.audioInput(this.state.promptName, this.state.audioContentName, btoa(audioBlob)));
                this.setState({ audioChunks: [] });
            };

            this.mediaRecorder.start();
            this.setState({ sessionStarted: true });
            console.log('Microphone recording started');

        } catch (error) {
            console.error('Error accessing microphone: ', error);
        }
    }

    endSession() {
        if (this.socket) {
            // Close microphone
            if (this.mediaRecorder && this.state.sessionStarted) {
                this.mediaRecorder.stop();
                console.log('Microphone recording stopped');
            }

            // Close S2sSessionManager
            this.sendEvent(S2sEvent.contentEnd(this.state.promptName, this.state.audioContentName));
            this.sendEvent(S2sEvent.promptEnd(this.state.promptName));
            this.sendEvent(S2sEvent.sessionEnd());

            // Close websocket
            this.socket.close();

            this.setState({ sessionStarted: false });
        }

    }

    handleDemoProfileChange = e => {
        this.setState({ selectedDemoProfileOption: e.detail.selectedOption });
        var demoProfile = DemoProfiles.find(obj => obj.name === e.detail.selectedOption.value);
        if (demoProfile) {
            this.setState({
                configVoiceIdOption: Voices.find(i => i.value === demoProfile.voiceId),
                configSystemPrompt: demoProfile.systemPrompt,
                configToolUse: JSON.stringify(demoProfile.toolConfig, null, 4),
            }, () => {
                // Save state after profile change
                this.saveStateToStorage();
            });
        }
    }

    handleSendText = e => {
        if (e.key === "Enter") {
            this.submitText();
        }
    }

    submitText = () => {
        if (!this.state.inputText || !this.state.inputText.trim() || !this.state.sessionStarted) {
            return;
        }

        const textContentName = crypto.randomUUID();

        // Add user text input to chatMessages state
        const chatMessages = { ...this.state.chatMessages };
        chatMessages[textContentName] = {
            content: this.state.inputText,
            role: "USER",
            generationStage: "",
            raw: [],
            inputSource: "text" // Messages from text input are text-based
        };

        this.sendEvent(S2sEvent.contentStartText(this.state.promptName, textContentName, "USER", true));
        this.sendEvent(S2sEvent.textInput(this.state.promptName, textContentName, this.state.inputText));
        this.sendEvent(S2sEvent.contentEnd(this.state.promptName, textContentName));

        this.setState({
            inputText: "",
            chatMessages: chatMessages
        }, () => {
            // Scroll to bottom after adding message
            this.scrollToBottom();
        });
    }

    render() {
        return (
            <div className="s2s">
                {this.state.alert !== null && this.state.alert.length > 0 ?
                    <div><Alert statusIconAriaLabel="Warning" type="warning">
                        {this.state.alert}
                    </Alert><br /></div> : <div />}
                <div className='header'>
                    <div className='header-content'>
                        <div className='app-title'>
                            <h1>Amazon Nova Sonic 2.0 Workshop</h1>
                            {this.state.showUsage && (
                                <div className='meter-container'>
                                    <Meter ref={this.meterRef} />
                                </div>
                            )}
                        </div>
                        <div className='header-left'>
                            <div className='main-action'>
                                <Button variant='primary' onClick={this.handleSessionChange} className="conversation-button">
                                    <Icon name={this.state.sessionStarted ? "microphone-off" : "microphone"} />&nbsp;&nbsp;
                                    {this.state.sessionStarted ? "End Conversation" : "Start Conversation"}
                                </Button>
                            </div>
                            <div className='header-options'>
                                <Checkbox
                                    checked={this.state.includeChatHistory}
                                    onChange={({ detail }) => {
                                        this.setState({ includeChatHistory: detail.checked }, () => {
                                            this.saveStateToStorage();
                                        });
                                    }}
                                    className="chat-history-checkbox"
                                    description="You can view sample chat history in the settings"
                                >
                                    Include chat history
                                </Checkbox>
                            </div>
                        </div>
                        <div className='header-right'>
                            <div className='controls-group'>
                                <div className='profile-selector'>
                                    <span className='profile-label'>Select Profile:</span>
                                    <Select
                                        selectedOption={this.state.selectedDemoProfileOption}
                                        onChange={this.handleDemoProfileChange}
                                        options={DemoProfiles ? DemoProfiles.map(item => ({
                                            label: item.name,
                                            value: item.name,
                                            description: item.description
                                        })) : []}
                                        placeholder="Choose a profile"
                                    />
                                </div>
                                <div className='setting'>
                                    <Button
                                        onClick={() => this.setState({ showConfig: true })}
                                    >
                                        <Icon name="settings" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <br />
                <div className="main-content">
                    <div className="content-columns">
                        <div className="conversation-section">
                            <div className="section-header">
                                <h2>Conversation</h2>
                            </div>
                            <div className="conversation-container">
                                <div className="chatarea">
                                    {Object.keys(this.state.chatMessages).map((key, index) => {
                                        const msg = this.state.chatMessages[key];
                                        //if (msg.stopReason === "END_TURN" || msg.role === "USER")
                                        return <div className='item' key={key}>
                                            <div className={msg.role === "USER" ? "user" : "bot"} onClick={() =>
                                                this.setState({
                                                    showEventJson: true,
                                                    selectedEvent: { events: msg.raw }
                                                })
                                            }>
                                                <Icon name={msg.role === "USER" ? "user-profile" : "gen-ai"} />&nbsp;&nbsp;
                                                {msg.role === "USER" && (
                                                    <Icon
                                                        name={msg.inputSource === "text" ? "edit" : "microphone"}
                                                        className="input-source-icon"
                                                    />
                                                )}&nbsp;
                                                {msg.content}
                                                {msg.role === "ASSISTANT" && msg.generationStage ? ` [${msg.generationStage}]` : ""}
                                            </div>
                                        </div>
                                    })}
                                    <div className='endbar' ref={this.chatMessagesEndRef}></div>
                                </div>
                                <div className="input-container">
                                    <div className="input-wrapper">
                                        <input
                                            type="text"
                                            className="inputtext"
                                            placeholder="Send a message to Nova Sonic"
                                            onChange={(e) => this.setState({ inputText: e.target.value })}
                                            onKeyDown={this.handleSendText}
                                            value={this.state.inputText}
                                            disabled={!this.state.sessionStarted}
                                        />
                                        <Button
                                            variant="primary"
                                            className="submit-button"
                                            onClick={this.submitText}
                                            disabled={!this.state.sessionStarted || !this.state.inputText || !this.state.inputText.trim()}
                                        >
                                            <Icon name="angle-up" />
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="events-section">
                            <div className="section-header">
                                <h2>Events</h2>
                            </div>
                            <div className="events-container">
                                <S2sEventDisplay ref={this.eventDisplayRef}></S2sEventDisplay>
                            </div>
                        </div>
                    </div>
                </div>
                <Modal
                    onDismiss={() => this.setState({ showEventJson: false })}
                    visible={this.state.showEventJson}
                    header={
                        <Header
                            variant="h1"
                            description="Raw event data from conversation messages"
                        >
                            💬 Message Event Details
                        </Header>
                    }
                    size='large'
                    footer={
                        <Box float="right">
                            <SpaceBetween direction="horizontal" size="s">
                                <Button variant="link" onClick={() => this.setState({ showEventJson: false })}>Close</Button>
                                <Button
                                    variant="primary"
                                    onClick={() => {
                                        const eventData = this.state.selectedEvent?.events.map(e => {
                                            const eventType = Object.keys(e?.event)[0];
                                            if (eventType === "audioInput" || eventType === "audioOutput") {
                                                const eventCopy = JSON.parse(JSON.stringify(e));
                                                eventCopy.event[eventType].content = eventCopy.event[eventType].content.substr(0, 10) + "...";
                                                return eventCopy;
                                            }
                                            return e;
                                        });
                                        navigator.clipboard.writeText(JSON.stringify(eventData, null, 2));
                                    }}
                                >
                                    📋 Copy JSON
                                </Button>
                            </SpaceBetween>
                        </Box>
                    }
                >
                    <Container
                        header={
                            <Header
                                variant="h2"
                                description="Timeline of events associated with this message"
                            >
                                📝 Message Event Timeline
                            </Header>
                        }
                    >
                        <div className='event-detail-container'>
                            {this.state.selectedEvent && this.state.selectedEvent.events.map((e, index) => {
                                const eventType = Object.keys(e?.event)[0];
                                const eventCopy = JSON.parse(JSON.stringify(e));

                                if (eventType === "audioInput" || eventType === "audioOutput") {
                                    eventCopy.event[eventType].content = eventCopy.event[eventType].content.substr(0, 10) + "...";
                                }

                                const ts = new Date(e.timestamp).toLocaleString(undefined, {
                                    year: "numeric",
                                    month: "2-digit",
                                    day: "2-digit",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                    second: "2-digit",
                                    fractionalSecondDigits: 3,
                                    hour12: false
                                });

                                delete eventCopy.timestamp;

                                return (
                                    <div key={index} className="event-item">
                                        <div className="event-timestamp">
                                            <Badge color="blue">🕒 {ts}</Badge>
                                        </div>
                                        <div className="event-json">
                                            <pre className="json-display">
                                                {JSON.stringify(eventCopy, null, 2)}
                                            </pre>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </Container>
                </Modal>
                <Settings
                    visible={this.state.showConfig}
                    onDismiss={() => this.setState({ showConfig: false })}
                    configVoiceIdOption={this.state.configVoiceIdOption}
                    configTurnSensitivity={this.state.configTurnSensitivity}
                    configSystemPrompt={this.state.configSystemPrompt}
                    configToolUse={this.state.configToolUse}
                    configChatHistory={this.state.configChatHistory}
                    enableParalinguisticDetection={this.state.enableParalinguisticDetection}
                    onSettingsChange={(updatedSettings) => {
                        this.setState(updatedSettings, () => {
                            this.saveStateToStorage();
                        });
                    }}
                />
            </div>
        );
    }
}

export default S2sChatBot;