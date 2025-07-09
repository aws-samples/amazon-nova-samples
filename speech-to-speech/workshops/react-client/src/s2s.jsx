import './index.css'
import React from 'react';
import { Grid, Icon, Alert, Button, Modal, Box, SpaceBetween, Container, Header, FormField, Select, Textarea, Checkbox, Slider, ColumnLayout, Input } from '@cloudscape-design/components';

import Meter from './components/meter.jsx';
import EventsList from './components/eventsList.jsx';
import AudioPlayer from './helper/audioPlayer';
import {SonicEvent, SonicLanguages} from './helper/sonicEvent';
import { base64ToFloat32Array } from './helper/audioHelper';

class SonicChatBot extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            status: "loading", // null, loading, loaded
            alert: null,
            sessionStarted: false,
            showEventJson: false,
            showConfig: false,
            selectedEvent: null,

            conversationMessages: {},
            events: [],
            audioChunks: [],
            audioPlayPromise: null,
            includeConversationHistory: false,

            promptName: null,
            textContentName: null,
            audioContentName: null,

            showUsage: false,

            // Geolocation data
            geolocationWatchId: null,
            currentLocation: null,

            // S2S config items
            configAudioInput: null,
            configSystemPrompt: SonicEvent.DEFAULT_SYSTEM_PROMPT,
            configAudioOutput: SonicEvent.DEFAULT_AUDIO_OUTPUT_CONFIG,
            configVoiceIdOption: SonicLanguages[0],
            configToolUse: JSON.stringify(SonicEvent.DEFAULT_TOOL_CONFIG, null, 2),
            configConversationHistory: JSON.stringify(SonicEvent.DEFAULT_CONVERSATION_HISTORY, null, 2),
            configTemperature: SonicEvent.DEFAULT_INFER_CONFIG.temperature,
            configMaxTokens: SonicEvent.DEFAULT_INFER_CONFIG.maxTokens,
            configTopP: SonicEvent.DEFAULT_INFER_CONFIG.topP,
        };
        this.socket = null;
        this.mediaRecorder = null;
        this.audioContext = null;
        this.workletNode = null;
        this.audioStream = null;
        this.conversationListEndRef = React.createRef();
        this.stateRef = React.createRef();
        this.eventsDisplayRef = React.createRef();
        this.meterRef = React.createRef();
        this.audioPlayer = new AudioPlayer();
    }

    componentDidMount() {
        this.stateRef.current = this.state;

        // Initialize audio player with user interaction handling
        this.initAudioPlayer();

        // Add event listener for user interaction to enable audio
        document.addEventListener('click', this.handleUserInteraction);
        document.addEventListener('keydown', this.handleUserInteraction);

        // Set up mutation observer to watch for changes in conversation area
        this.setupConversationObserver();

        // Add window resize listener
        window.addEventListener('resize', this.handleResize);

        // Initial resize calculation
        this.handleResize();

        // Set up scroll indicators
        this.setupScrollIndicators();
    }

    setShowUsageState = (value) => {
        this.setState({ showUsage: value });
    }

    setupConversationObserver = () => {
        // Wait for everything to be available in the DOM
        setTimeout(() => {
            const conversationList = document.querySelector('.conversation-list');
            if (conversationList) {
                this.conversationObserver = new MutationObserver((mutations) => {
                    this.scrollToBottom();
                });

                this.conversationObserver.observe(conversationList, {
                    childList: true,     // Watch for changes to child elements
                    subtree: true,       // Watch the entire subtree
                    characterData: true  // Watch for changes to text content
                });

                console.log('Conversation observer set up successfully');
            }
        }, 1000); // Give the component time to render
    }

    componentWillUnmount() {
        this.audioPlayer.stop();

        // Clean up audio resources if they exist
        if (this.workletNode) {
            this.workletNode.disconnect();
        }

        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
        }

        if (this.audioContext) {
            this.audioContext.close().catch(err => console.error("Error closing audio context:", err));
        }

        // Remove event listeners
        document.removeEventListener('click', this.handleUserInteraction);
        document.removeEventListener('keydown', this.handleUserInteraction);
        window.removeEventListener('resize', this.handleResize);

        // Remove scroll event listeners
        const conversationList = document.querySelector('.conversation-list');
        const eventsList = document.querySelector('.events-list');
        if (conversationList) conversationList.removeEventListener('scroll', this.updateScrollIndicator);
        if (eventsList) eventsList.removeEventListener('scroll', this.updateScrollIndicator);

        // Clean up mutation observer
        if (this.conversationObserver) {
            this.conversationObserver.disconnect();
        }
    }

    // Handle window resize
    handleResize = () => {
        const c = document.querySelector('.s2s');
        if (c) {
            let availableHeight = c.offsetHeight;
            availableHeight += 30; // negative margin and padding;
            availableHeight -= c.children[0].offsetHeight;
            availableHeight -= c.children[1].offsetHeight;

            let stretchContainer = document.querySelector('[data-stretch="true"]');

            if (stretchContainer) {
                stretchContainer.style.height = `${availableHeight}px`;
                stretchContainer.children[0].style.height = `${availableHeight}px`;
                stretchContainer.children[1].style.height = `${availableHeight}px`;
            }
        }

        // Store current scroll positions
        const conversationScrollTop = document.querySelector('.conversation-list')?.scrollTop || 0;
        const eventsScrollTop = document.querySelector('.events-list')?.scrollTop || 0;

        // Let the layout adjust
        requestAnimationFrame(() => {
            // Restore scroll positions
            const conversationList = document.querySelector('.conversation-list');
            const eventsList = document.querySelector('.events-list');

            if (conversationList) conversationList.scrollTop = conversationScrollTop;
            if (eventsList) eventsList.scrollTop = eventsScrollTop;

            // If we're at the bottom, make sure we stay there
            if (this.isScrolledToBottom(conversationList)) {
                this.scrollToBottom();
            }

            // Also trigger a scroll in the events display if it exists
            if (this.eventsDisplayRef.current && this.isScrolledToBottom(eventsList)) {
                this.eventsDisplayRef.current.scrollToBottom();
            }

            // Update scroll indicators
            this.updateScrollIndicators();
        });
    }

    // Helper to check if element is scrolled to bottom
    isScrolledToBottom = (element) => {
        if (!element) return false;
        const scrollBottom = element.scrollHeight - element.clientHeight;
        return Math.abs(element.scrollTop - scrollBottom) < 10; // Within 10px of bottom
    }

    // Set up scroll indicators to show content is scrollable
    setupScrollIndicators = () => {
        // Wait for the DOM to be ready
        setTimeout(() => {
            const conversationList = document.querySelector('.conversation-list');
            conversationList?.addEventListener('scroll', this.updateScrollIndicators);

            const eventsList = document.querySelector('.events-list');
            eventsList?.addEventListener('scroll', this.updateScrollIndicators);

            this.updateScrollIndicators();
        }, 3000);
    }

    // Update scroll indicators for all scrollable elements
    updateScrollIndicators = () => {
        const conversationList = document.querySelector('.conversation-list');
        this.updateScrollIndicator(conversationList);

        const eventsList = document.querySelector('.events-list');
        this.updateScrollIndicator(eventsList);
    }

    // Update scroll indicator for a specific element
    updateScrollIndicator = (element) => {
        if (!element) return;

        const hasScrollableContent = element.scrollHeight > element.clientHeight;
        const isScrolledToTop = element.scrollTop <= 10;
        const isScrolledToBottom = Math.abs((element.scrollHeight - element.clientHeight) - element.scrollTop) <= 10;

        // Add/remove classes based on scroll position
        element.classList.toggle('has-more-content', hasScrollableContent);
        element.classList.toggle('scrolled-to-top', isScrolledToTop);
        element.classList.toggle('scrolled-to-bottom', isScrolledToBottom);
    }

    // Initialize audio player
    initAudioPlayer = async () => {
        try {
            await this.audioPlayer.start();
            console.log("[AudioPlayer] initialized successfully");
        } catch (err) {
            console.error("[AudioPlayer] failed to initialize:", err);
            this.setState({ alert: "Failed to initialize audio system. Please reload the page." });
        }
    }

    // Handle user interaction to enable audio
    handleUserInteraction = () => {
        // Only need to do this once
        if (this.userInteractionHandled) return;

        // Try to resume audio context
        if (this.audioPlayer && this.audioPlayer.audioContext) {
            this.audioPlayer.resumeAudioContext();
            this.userInteractionHandled = true;

            // Remove event listeners after successful interaction
            document.removeEventListener('click', this.handleUserInteraction);
            document.removeEventListener('keydown', this.handleUserInteraction);
        }
    }


    componentDidUpdate(prevProps, prevState) {
        this.stateRef.current = this.state;

        // Check if conversation messages have changed
        const prevKeys = Object.keys(prevState.conversationMessages);
        const currentKeys = Object.keys(this.state.conversationMessages);

        // Scroll to bottom if:
        // 1. New messages were added
        // 2. Content of existing messages changed
        if (prevKeys.length !== currentKeys.length ||
            JSON.stringify(this.state.conversationMessages) !== JSON.stringify(prevState.conversationMessages)) {
            this.scrollToBottom();
        }
    }

    // Helper method to scroll to bottom of conversation
    scrollToBottom = () => {
        if (this.conversationListEndRef.current) {
            // Use requestAnimationFrame to ensure DOM has updated before scrolling
            requestAnimationFrame(() => {
                this.conversationListEndRef.current.scrollIntoView({
                    behavior: 'smooth',
                    block: 'end'
                });
            });
        }
    }

    sendEvent(event) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(event));
            event.timestamp = Date.now();

            this.eventsDisplayRef.current.displayEvent(event, "out");
        }
    }

    cancelAudio() {
        this.audioPlayer.bargeIn();
        this.setState({ isPlaying: false });
    }

    handleIncomingMessage(message) {
        const eventName = Object.keys(message?.event)[0];
        const role = message.event[eventName]["role"];
        const content = message.event[eventName]["content"];
        const contentId = message.event[eventName].contentId;
        let stopReason = message.event[eventName].stopReason;
        const contentType = message.event[eventName].type;
        let conversationMessages = this.state.conversationMessages;

        switch (eventName) {
            case "textOutput":
                // Detect interruption
                if (role === "ASSISTANT" && content.startsWith("{")) {
                    const evt = JSON.parse(content);
                    if (evt.interrupted === true) {
                        this.cancelAudio()
                    }
                }

                if (conversationMessages.hasOwnProperty(contentId)) {
                    conversationMessages[contentId].content = content;
                    conversationMessages[contentId].role = role;
                    if (conversationMessages[contentId].raw === undefined)
                        conversationMessages[contentId].raw = [];
                    conversationMessages[contentId].raw.push(message);
                }
                this.setState({ conversationMessages: conversationMessages }, () => {
                    // Scroll to bottom after state update is complete
                    this.scrollToBottom();
                });
                break;
            case "audioOutput":
                try {
                    // Ensure audio player is initialized
                    if (!this.audioPlayer.initialized) {
                        console.log("[AudioPlayer] not initialized, initializing now...");
                        this.initAudioPlayer().then(() => {
                            this.processAudioOutput(message, eventName);
                        });
                    } else {
                        this.processAudioOutput(message, eventName);
                    }
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

                    conversationMessages[contentId] = {
                        "content": "",
                        "role": role,
                        "generationStage": generationStage,
                        "raw": [],
                    };
                    conversationMessages[contentId].raw.push(message);
                    this.setState({ conversationMessages: conversationMessages }, () => {
                        // Scroll to bottom after state update is complete
                        this.scrollToBottom();
                    });
                }
                break;
            case "contentEnd":
                if (contentType === "TEXT") {
                    if (conversationMessages.hasOwnProperty(contentId)) {
                        if (conversationMessages[contentId].raw === undefined)
                            conversationMessages[contentId].raw = [];
                        conversationMessages[contentId].raw.push(message);
                        conversationMessages[contentId].stopReason = stopReason;
                    }
                    this.setState({ conversationMessages: conversationMessages }, () => {
                        // Scroll to bottom after state update is complete
                        this.scrollToBottom();
                    });
                }
                break;
            case "usageEvent":
                if (this.meterRef.current) {
                    this.meterRef.current.updateMeter(message);
                }
                break;
            case "toolUse":
                if (message.event[eventName]["toolName"] === "locateMe") {
                    this.updateLocationData();
                }
                break;
            default:
                break;
        }

        this.eventsDisplayRef.current.displayEvent(message, "in");
    }

    updateLocationData() {
        // Make GET request to checkip.amazonaws.com
        fetch('https://checkip.amazonaws.com')
            .then(response => response.text())
            .then(data => {
                const publicIpAddress = data.trim();
                this.setState({ publicIpAddress: publicIpAddress });
                this.sendEvent(SonicEvent.customStateUpdate(publicIpAddress, null));
                console.log('Public IP Address:', publicIpAddress);
            })
            .catch(error => {
                console.error('Error fetching IP address:', error);
            });

        // Request geolocation data
        if (!navigator.geolocation) {
            console.error('Geolocation not supported or allowed.');
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.sendEvent(SonicEvent.customStateUpdate(null, position));
                console.log('Geolocation data sent to backend:', position);
            },
            (error) => {
                console.error('Geolocation error:', error.message);
            },
            {
                enableHighAccuracy: false,
                timeout: 10000,
                maximumAge: 10*60*1000,
            }
        );
    }

    // Helper method to process audio output
    processAudioOutput(message, eventType) {
        const base64Data = message.event[eventType].content;

        // Log audio data length for debugging
        console.log(`Received audio data: ${base64Data.length} bytes`);

        // Convert and play audio
        const audioData = base64ToFloat32Array(base64Data);
        console.log(`Converted to ${audioData.length} audio samples`);

        // Play the audio
        this.audioPlayer.playAudio(audioData);
    }

    handleSessionChange = e => {
        if (this.state.sessionStarted) {
            // End session
            this.endSession();
            this.cancelAudio();
            if (this.meterRef.current) this.meterRef.current.stop();
            this.audioPlayer.start();
            // State is already updated in endSession
        }
        else {
            // Start session
            this.setState({
                conversationMessages: {},
                events: [],
            });
            if (this.eventsDisplayRef.current) this.eventsDisplayRef.current.cleanup();
            if (this.meterRef.current) this.meterRef.current.start();

            // Init S2sSessionManager
            try {
                if (this.socket === null || this.socket.readyState !== WebSocket.OPEN) {
                    this.connectWebSocket();
                }

                // Start microphone
                this.startMicrophone();
                // State is updated in startMicrophone
            } catch (error) {
                console.error('Error accessing microphone: ', error);
                this.setState({ alert: "Error accessing microphone: " + error.message });
            }
        }
    }

    connectWebSocket() {
        // Connect to the S2S WebSocket server
        if (this.socket === null || this.socket.readyState !== WebSocket.OPEN) {
            const promptName = crypto.randomUUID();
            const textContentName = crypto.randomUUID();
            const audioContentName = crypto.randomUUID();
            this.setState({
                promptName: promptName,
                textContentName: textContentName,
                audioContentName: audioContentName
            })

            const wsUrl = import.meta.env.REACT_APP_WEBSOCKET_URL ? import.meta.env.REACT_APP_WEBSOCKET_URL : "ws://localhost:8081/ws"
            this.socket = new WebSocket(wsUrl);
            this.socket.onopen = () => {
                console.log("WebSocket connected!");

                // Create inference config with user-configured parameters
                const inferenceConfig = {
                    ...SonicEvent.DEFAULT_INFER_CONFIG,
                    temperature: this.state.configTemperature,
                    maxTokens: this.state.configMaxTokens,
                    topP: this.state.configTopP
                };
                this.sendEvent(SonicEvent.sessionStart(inferenceConfig));

                const audioConfig = SonicEvent.DEFAULT_AUDIO_OUTPUT_CONFIG;
                audioConfig.voiceId = this.state.configVoiceIdOption.value;
                const toolConfig = this.state.configToolUse ? JSON.parse(this.state.configToolUse) : SonicEvent.DEFAULT_TOOL_CONFIG;

                this.sendEvent(SonicEvent.promptStart(promptName, audioConfig, toolConfig));

                this.sendEvent(SonicEvent.contentStartText(promptName, textContentName));

                this.sendEvent(SonicEvent.textInput(promptName, textContentName, this.state.configSystemPrompt));
                this.sendEvent(SonicEvent.contentEnd(promptName, textContentName));

                if (this.state.includeConversationHistory) {
                    let conversationHistory = JSON.parse(this.state.configConversationHistory);
                    if (conversationHistory === null) conversationHistory = SonicEvent.DEFAULT_CONVERSATION_HISTORY;
                    for (const message of conversationHistory) {
                        const contentName = crypto.randomUUID();
                        this.sendEvent(SonicEvent.contentStartText(promptName, contentName, message.role));
                        this.sendEvent(SonicEvent.textInput(promptName, contentName, message.content));
                        this.sendEvent(SonicEvent.contentEnd(promptName, contentName));
                    }

                }

                this.sendEvent(SonicEvent.contentStartAudio(promptName, audioContentName));
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

            // Load the audio worklet module
            const workletUrl = new URL('./helper/microphoneProcessor.worklet.js', import.meta.url).href;
            await audioContext.audioWorklet.addModule(workletUrl);

            // Create the audio worklet node
            const workletNode = new AudioWorkletNode(audioContext, 'microphone-processor');

            // Create and connect the media stream source
            const source = audioContext.createMediaStreamSource(stream);
            source.connect(workletNode);

            // Connect the worklet node to the destination to keep the audio graph active
            // We're not actually outputting audio, this is just to keep the node processing
            workletNode.connect(audioContext.destination);

            // Initialize the worklet with the input sample rate
            workletNode.port.postMessage({
                type: 'init',
                inputSampleRate: audioContext.sampleRate
            });

            // Handle audio data from the worklet
            workletNode.port.onmessage = (msg) => {
                if (msg.data.type === 'audio' && this.state.sessionStarted) {
                    const pcmData = msg.data.audioData;

                    // Convert Int16Array to binary string
                    const buffer = new ArrayBuffer(pcmData.length * 2);
                    const view = new DataView(buffer);

                    for (let i = 0; i < pcmData.length; i++) {
                        view.setInt16(i * 2, pcmData[i], true);
                    }

                    // Convert to binary string and base64 encode
                    let binary = '';
                    for (let i = 0; i < view.byteLength; i++) {
                        binary += String.fromCharCode(view.getUint8(i));
                    }

                    const currentState = this.stateRef.current;
                    const event = SonicEvent.audioInput(
                        currentState.promptName,
                        currentState.audioContentName,
                        btoa(binary)
                    );
                    this.sendEvent(event);
                }
            };

            // Store references for cleanup
            this.audioContext = audioContext;
            this.workletNode = workletNode;
            this.audioStream = stream;

            window.audioCleanup = () => {
                if (this.workletNode) {
                    this.workletNode.disconnect();
                }
                if (this.audioStream) {
                    this.audioStream.getTracks().forEach(track => track.stop());
                }
                if (this.audioContext) {
                    this.audioContext.close().catch(err => console.error("Error closing audio context:", err));
                }
            };

            this.mediaRecorder = new MediaRecorder(stream);
            this.mediaRecorder.ondataavailable = (event) => {
                this.state.audioChunks.push(event.data);
            };
            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.state.audioChunks, { type: 'audio/webm' });
                this.sendEvent(SonicEvent.audioInput(this.state.promptName, this.state.audioContentName, btoa(audioBlob)));
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

            // Clean up audio resources
            if (this.workletNode) {
                this.workletNode.disconnect();
                this.workletNode = null;
            }

            if (this.audioStream) {
                this.audioStream.getTracks().forEach(track => track.stop());
                this.audioStream = null;
            }

            if (this.audioContext) {
                this.audioContext.close().catch(err => console.error("Error closing audio context:", err));
                this.audioContext = null;
            }

            // Close S2sSessionManager
            this.sendEvent(SonicEvent.contentEnd(this.state.promptName, this.state.audioContentName));
            this.sendEvent(SonicEvent.promptEnd(this.state.promptName));
            this.sendEvent(SonicEvent.sessionEnd());

            // Close websocket
            this.socket.close();

            this.setState({ sessionStarted: false });
        }
    }
    render() {
        return (
            <div key="0" className="s2s">
                <Grid gridDefinition={[{ colspan: 12 }]}>
                    <div>
                        <h1>Amazon Nova Sonic sample app</h1>
                        {this.state.alert !== null && this.state.alert.length > 0 ?
                            <div><Alert type="warning">
                                {this.state.alert}
                            </Alert><br /></div> : ""}
                    </div>
                </Grid>

                <Grid gridDefinition={[{ colspan: 3 }, { colspan: 4 }, { colspan: 4 }, { colspan: 1 }]}>
                    <Button variant='primary' onClick={this.handleSessionChange}>
                        <Icon name={this.state.sessionStarted ? "microphone-off" : "microphone"} />&nbsp;&nbsp;
                        {this.state.sessionStarted ? "End Conversation" : "Start Conversation"}
                    </Button>
                    <div className='conversationhistory'>
                        <Checkbox checked={this.state.includeConversationHistory} onChange={({ detail }) => this.setState({ includeConversationHistory: detail.checked })}>Include conversation history</Checkbox>
                        <div className='desc'>You can view and edit the sample conversation history in the settings.</div>
                    </div>
                    <Meter
                        ref={this.meterRef}
                        showUsage={this.state.showUsage}
                        onShowUsageChange={this.setShowUsageState}
                    />
                    <div className='settings'>
                        <Button onClick={() => this.setState({ showConfig: true }) }>
                            <Icon name="settings" />
                        </Button>
                    </div>
                </Grid>
                <Grid data-stretch="true" gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
                    <Container fitHeight={true} header={
                        <Header variant="h2">Conversation</Header>
                    }>
                        <div className="conversation-list">
                            {Object.keys(this.state.conversationMessages).map((key, index) => {
                                const msg = this.state.conversationMessages[key];
                                return <div key={key} className='item'>
                                    <div className={msg.role === "USER" ? "user" : "bot"} onClick={() =>
                                        this.setState({
                                            showEventJson: true,
                                            selectedEvent: { events: msg.raw }
                                        })
                                    }>
                                        <Icon name={msg.role === "USER" ? "user-profile" : "gen-ai"} />&nbsp;&nbsp;
                                        {msg.content}
                                        {msg.role === "ASSISTANT" && msg.generationStage ? ` [${msg.generationStage}]` : ""}
                                    </div>
                                </div>
                            })}
                            <div ref={this.conversationListEndRef}></div>
                        </div>
                    </Container>
                    <Container fitHeight={true} header={
                        <Header variant="h2">Events</Header>
                    }>
                        <EventsList
                            ref={this.eventsDisplayRef}
                            showUsage={this.state.showUsage}
                        />
                    </Container>
                </Grid>


                <Modal
                    onDismiss={() => this.setState({ showEventJson: false })}
                    visible={this.state.showEventJson}
                    header="Event Details"
                    size='medium'
                    footer={
                        <Box float="right">
                            <SpaceBetween direction="horizontal" size="xs">
                                <Button variant="link" onClick={() => this.setState({ showEventJson: false })}>Close</Button>
                            </SpaceBetween>
                        </Box>
                    }
                >
                    <div className='eventdetail'>
                        <pre id="jsonDisplay">
                            {this.state.selectedEvent && this.state.selectedEvent.events.map(e => {
                                const eventType = Object.keys(e?.event)[0];
                                if (eventType === "audioInput" || eventType === "audioOutput")
                                    e.event[eventType].content = e.event[eventType].content.substr(0, 10) + "...";
                                const ts = new Date(e.timestamp).toLocaleString(undefined, {
                                    year: "numeric",
                                    month: "2-digit",
                                    day: "2-digit",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                    second: "2-digit",
                                    fractionalSecondDigits: 3, // Show milliseconds
                                    hour12: false // 24-hour format
                                });
                                var displayJson = { ...e };
                                delete displayJson.timestamp;
                                return ts + "\n" + JSON.stringify(displayJson, null, 2) + "\n";
                            })}
                        </pre>
                    </div>
                </Modal>

                <Modal
                    onDismiss={() => this.setState({ showConfig: false })}
                    visible={this.state.showConfig}
                    header="Settings"
                    size='large'
                    footer={
                        <Box float="right">
                            <SpaceBetween direction="horizontal" size="xs">
                                <Button variant="link" onClick={() => this.setState({ showConfig: false })}>Save</Button>
                            </SpaceBetween>
                        </Box>
                    }
                >
                    <div className='config'>
                        <FormField
                            label="Language and Voice"
                            stretch={true}
                        >
                            <Select
                                selectedOption={this.state.configVoiceIdOption}
                                onChange={({ detail }) =>
                                    this.setState({ configVoiceIdOption: detail.selectedOption })
                                }
                                options={SonicLanguages}
                            />
                        </FormField>
                        <br />
                        <FormField
                            label="Inference Parameters"
                            description="Configure model behavior and output constraints"
                            stretch={true}
                        >
                            <ColumnLayout columns={3}>
                                <div>
                                    <FormField
                                        label="Temperature"
                                        description="Predictable vs. creative output"
                                    >
                                        <Slider
                                            onChange={({ detail }) => this.setState({ configTemperature: detail.value })}
                                            value={this.state.configTemperature}
                                            valueFormatter={(value) => Number(value).toFixed(2)}
                                            min={0.0}
                                            max={1.0}
                                            step={0.05}
                                            tickMarks
                                            hideFillLine={false}
                                        />
                                    </FormField>
                                </div>
                                <div>
                                    <FormField
                                        label="topP"
                                        description="Nucleus sampling"
                                    >
                                        <Slider
                                            onChange={({ detail }) => this.setState({ configTopP: detail.value })}
                                            value={this.state.configTopP}
                                            valueFormatter={(value) => Number(value).toFixed(2)}
                                            min={0.0}
                                            max={1.0}
                                            step={0.05}
                                            tickMarks
                                            hideFillLine={false}
                                        />
                                    </FormField>
                                </div>
                                <div>
                                    <FormField
                                        label="Max Tokens"
                                        description="Response length"
                                    >
                                        <Input
                                            onChange={({ detail }) => {
                                                const value = parseInt(detail.value) || 1;
                                                this.setState({ configMaxTokens: Math.max(1, value) });
                                            }}
                                            value={this.state.configMaxTokens.toString()}
                                            type="number"
                                            inputMode="numeric"
                                        />
                                    </FormField>
                                </div>
                            </ColumnLayout>
                        </FormField>
                        <br />
                        <FormField
                            label="System prompt"
                            description="For the speech model"
                            stretch={true}
                        >
                            <Textarea
                                onChange={({ detail }) => this.setState({ configSystemPrompt: detail.value })}
                                value={this.state.configSystemPrompt}
                                placeholder="Speech system prompt"
                                rows={5}
                            />
                        </FormField>
                        <br />
                        <FormField
                            label="Tool use configuration"
                            description="For external integration such as RAG and Agents"
                            stretch={true}
                        >
                            <Textarea
                                onChange={({ detail }) => this.setState({ configToolUse: detail.value })}
                                value={this.state.configToolUse}
                                rows={10}
                                placeholder="{}"
                            />
                        </FormField>
                        <br />
                        <FormField
                            label="Conversation history"
                            description="Sample conversation history to resume conversation"
                            stretch={true}
                        >
                            <Textarea
                                onChange={({ detail }) => this.setState({ configConversationHistory: detail.value })}
                                value={this.state.configConversationHistory}
                                rows={15}
                                placeholder="{}"
                            />
                        </FormField>
                    </div>
                </Modal>
            </div>
        );
    }
}

export default SonicChatBot;
