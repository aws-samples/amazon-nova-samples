import AudioPlayer from "./lib/play/AudioPlayer";
import ChatHistoryManager from "./lib/util/ChatHistoryManager.js";

const audioPlayer = new AudioPlayer();

export class WebSocketEventManager {
    constructor(wsUrl, config = {}) {
        this.wsUrl = wsUrl;
        this.config = config;
        this.promptName = null;
        this.audioContentName = null;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.currentAudioConfig = null;
        this.isProcessing = false;
        this.displayAssistantText = false;
        this.role = null;
        this.chat = { history: [] };
        this.chatRef = { current: this.chat };
        this.events = [];
        this.audioPlayer = audioPlayer; // Expose audioPlayer for external access

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

        // Get the last item from history
        const lastItem = this.chat.history[this.chat.history.length - 1];
        if (!lastItem) return;

        // Check if this message already exists in the DOM
        const existingMessages = chatContainer.querySelectorAll('.message');
        const lastMessageIndex = existingMessages.length - 1;
        
        if (lastItem.endOfConversation) {
            // Only add if not already present
            if (lastMessageIndex < 0 || !existingMessages[lastMessageIndex].classList.contains('system')) {
                const endDiv = document.createElement('div');
                endDiv.className = 'message system';
                endDiv.textContent = "Conversation ended";
                chatContainer.appendChild(endDiv);
                this.scrollToBottom(chatContainer);
            }
        } else if (lastItem.role) {
            const historyIndex = this.chat.history.length - 1;
            
            // Check if we need to update existing message or add new one
            if (lastMessageIndex >= 0) {
                const lastDomMessage = existingMessages[lastMessageIndex];
                const lastDomRole = lastDomMessage.classList.contains('user') ? 'USER' : 
                                   lastDomMessage.classList.contains('assistant') ? 'ASSISTANT' : 'SYSTEM';
                
                // If same role, update the content
                if (lastDomRole === lastItem.role) {
                    const contentDiv = lastDomMessage.querySelector('div:not(.role-label)');
                    if (contentDiv) {
                        contentDiv.textContent = lastItem.message || "No content";
                    }
                    this.scrollToBottom(chatContainer);
                    return;
                }
            }
            
            // Add new message
            const messageDiv = document.createElement('div');
            const roleLowerCase = lastItem.role.toLowerCase();
            messageDiv.className = `message ${roleLowerCase}`;

            const roleLabel = document.createElement('div');
            roleLabel.className = 'role-label';
            roleLabel.textContent = lastItem.role;
            messageDiv.appendChild(roleLabel);

            const content = document.createElement('div');
            content.className = 'message-content';
            content.textContent = lastItem.message || "No content";
            messageDiv.appendChild(content);

            chatContainer.appendChild(messageDiv);
            
            // Smooth scroll to bottom after adding new message
            requestAnimationFrame(() => {
                this.scrollToBottom(chatContainer);
            });
        }
    }

    scrollToBottom(container) {
        if (!container) return;
        container.scrollTop = container.scrollHeight;
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
                console.error("Error parsing message:", e, "Raw data:", JSON.stringify(event.data));
            }
        };

        this.socket.onerror = (error) => {
            console.error("WebSocket Error:", error);
            this.updateStatus("Connection error", "error");
            this.isProcessing = false;
        };

        this.socket.onclose = (event) => {
            console.log("WebSocket Disconnected", JSON.stringify(event));
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
            console.log("Sending event:", JSON.stringify(event, null, 2));
            this.socket.send(JSON.stringify(event));
        } catch (error) {
            console.error("Error sending event:", error);
            this.updateStatus("Error sending message", "error");
        }
    }

    logEvent(eventType, eventData) {
        const timestamp = new Date().toLocaleTimeString();
        const eventLog = {
            type: eventType,
            timestamp: timestamp,
            data: eventData
        };
        this.events.push(eventLog);
        this.updateEventViewer(eventLog);
    }

    updateEventViewer(eventLog) {
        const eventList = document.getElementById('event-list');
        if (!eventList) return;

        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        
        const eventType = document.createElement('div');
        eventType.className = 'event-type';
        eventType.textContent = eventLog.type;
        
        const eventTimestamp = document.createElement('div');
        eventTimestamp.className = 'event-timestamp';
        eventTimestamp.textContent = eventLog.timestamp;
        
        const eventSummary = document.createElement('div');
        eventSummary.className = 'event-summary';
        eventSummary.textContent = this.getEventSummary(eventLog);
        
        const eventDetails = document.createElement('div');
        eventDetails.className = 'event-details';
        eventDetails.textContent = JSON.stringify(eventLog.data, null, 2);
        
        eventItem.appendChild(eventType);
        eventItem.appendChild(eventTimestamp);
        eventItem.appendChild(eventSummary);
        eventItem.appendChild(eventDetails);
        
        // Toggle details on click
        eventItem.addEventListener('click', () => {
            eventItem.classList.toggle('expanded');
        });
        
        eventList.appendChild(eventItem);
        
        // Auto-scroll to bottom
        const eventViewer = document.getElementById('event-viewer-content');
        if (eventViewer) {
            eventViewer.scrollTop = eventViewer.scrollHeight;
        }
    }

    getEventSummary(eventLog) {
        const { type, data } = eventLog;
        switch (type) {
            case 'completionStart':
                return `Prompt: ${data.promptName?.substring(0, 8)}...`;
            case 'contentStart':
                return `${data.role} - ${data.type}`;
            case 'textOutput':
                return data.content?.substring(0, 50) + (data.content?.length > 50 ? '...' : '');
            case 'audioOutput':
                return 'Audio chunk received';
            case 'contentEnd':
                return `Type: ${data.type}, Reason: ${data.stopReason}`;
            case 'completionEnd':
                return 'Completion finished';
            default:
                return 'Event data available';
        }
    }

    handleMessage(data) {
        if (!data.event) {
            console.error("Received message without event:", JSON.stringify(data));
            return;
        }

        const event = data.event;
        console.log("Event received");

        try {
            // Handle completionStart
            if (event.completionStart) {
                console.log("Completion start received:", JSON.stringify(event.completionStart));
                this.promptName = event.completionStart.promptName;
                this.logEvent('completionStart', event.completionStart);
            }
            // Handle contentStart
            else if (event.contentStart) {
                console.log("Content start received:", JSON.stringify(event.contentStart));
                this.role = event.contentStart.role;
                this.logEvent('contentStart', event.contentStart);
                if (event.contentStart.type === "AUDIO") {
                    this.currentAudioConfig = event.contentStart.audioOutputConfiguration;
                }
                if (event.contentStart.type === "TEXT") {
                    // Check for speculative content
                    let isSpeculative = false;
                    try {
                        if (event.contentStart.additionalModelFields) {
                            console.log("Additional model fields:", event.contentStart.additionalModelFields)
                            const additionalFields = JSON.parse(event.contentStart.additionalModelFields);
                            isSpeculative = additionalFields.generationStage === "SPECULATIVE";
                            if (isSpeculative) {
                                console.log("Received speculative content");
                                this.displayAssistantText = true;
                            }
                            else {
                                this.displayAssistantText = false;
                            }
                        }
                    } catch (e) {
                        console.error("Error parsing additionalModelFields:", e);
                    }
                }

            }
            // Handle textOutput
            else if (event.textOutput) {
                console.log("Text output received:", JSON.stringify(event.textOutput));
                this.logEvent('textOutput', event.textOutput);
                const messageData = {
                    role: this.role
                };
                if (messageData.role === "USER" || (messageData.role === "ASSISTANT" && this.displayAssistantText)) {
                    messageData.content = event.textOutput.content;
                }
                this.handleTextOutput(messageData);
            }
            // Handle audioOutput
            else if (event.audioOutput) {
                console.log("Audio output received");
                this.logEvent('audioOutput', { size: event.audioOutput.content?.length || 0 });
                if (this.currentAudioConfig) {
                    audioPlayer.playAudio(this.base64ToFloat32Array(event.audioOutput.content));
                }
            }
            // Handle contentEnd
            else if (event.contentEnd) {
                console.log("Content end received:", JSON.stringify(event.contentEnd));
                this.logEvent('contentEnd', event.contentEnd);
                switch (event.contentEnd.type) {
                    case "TEXT":
                        if (event.contentEnd.stopReason.toUpperCase() === "END_TURN") {
                            this.chatHistoryManager.endTurn();
                        }
                        else if (event.contentEnd.stopReason.toUpperCase() === "INTERRUPTED") {
                            audioPlayer.bargeIn();
                        }
                        break;
                    default:
                        console.log("Received content end for type:", JSON.stringify(event.contentEnd.type));
                }
            }
            // Handle completionEnd
            else if (event.completionEnd) {
                console.log("Completion end received:", JSON.stringify(event.completionEnd));
                this.logEvent('completionEnd', event.completionEnd);
            }
            else {
                console.warn("Unknown event type received:", JSON.stringify(Object.keys(event)[0]));
            }
        } catch (error) {
            console.error("Error processing message:", error);
            console.error("Event data:", JSON.stringify(event));
        }
    }

    handleTextOutput(data) {
        console.log("Processing text output:", data);
        if (data.content) {
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

    sendTextInput(textContent) {
        if (!this.promptName) {
            console.error("Cannot send text input - no active prompt");
            return;
        }

        const textContentName = crypto.randomUUID();

        // Send contentStart for text
        const contentStartEvent = {
            event: {
                contentStart: {
                    promptName: this.promptName,
                    contentName: textContentName,
                    type: "TEXT",
                    interactive: true,
                    role: "USER",
                    textInputConfiguration: {
                        mediaType: "text/plain"
                    }
                }
            }
        };
        this.sendEvent(contentStartEvent);

        // Send the text input
        const textInputEvent = {
            event: {
                textInput: {
                    promptName: this.promptName,
                    contentName: textContentName,
                    content: textContent
                }
            }
        };
        this.sendEvent(textInputEvent);

        // Send contentEnd for text
        const contentEndEvent = {
            event: {
                contentEnd: {
                    promptName: this.promptName,
                    contentName: textContentName
                }
            }
        };
        this.sendEvent(contentEndEvent);

        console.log(`Text input sent: ${textContent}`);
    }

    startSession() {
        console.log("Starting session...");
        const sessionStartEvent = {
            event: {
                sessionStart: {
                    inferenceConfiguration: {
                        maxTokens: 1024,
                        topP: 0.9,
                        temperature: 0.7
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
        const getDefaultToolSchema = JSON.stringify({
            "type": "object",
            "properties": {},
            "required": []
        });

        const getWeatherToolSchema = JSON.stringify({
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name for which to get weather information. Can include country or state for disambiguation (e.g., 'London, UK' or 'Portland, Oregon')."
                }
            },
            "required": ["city"]
        });

  /*     French	ambre	florian
Italian	beatrice	lorenzo
German	greta	lennart
*/

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
                        voiceId: this.config.voiceId || "tiffany",
                        encoding: "base64",
                        audioType: "SPEECH"
                    },
                    toolUseOutputConfiguration: {
                        mediaType: "application/json"
                    },
                    toolConfiguration: {
                        tools: [{
                            toolSpec: {
                                name: "getDateAndTimeTool",
                                description: "get information about the current date and current time",
                                inputSchema: {
                                    json: getDefaultToolSchema
                                }
                            }
                        },
                        {
                            toolSpec: {
                                name: "getWeatherTool",
                                description: "Get the current weather for a given city or location by name.",
                                inputSchema: {
                                    json: getWeatherToolSchema
                                }
                            }
                        }
                        ],
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
                    role: "SYSTEM",
                    interactive: true,
                    textInputConfiguration: {
                        mediaType: "text/plain"
                    }
                }
            }
        };
        this.sendEvent(contentStartEvent);

        const systemPrompt = this.config.systemPrompt || `You are a friend. You and the user will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation.`
        /*`Your task is to support Allianz insured callers in reporting their mileage. To accomplish this, you can use the kma_tool. Engage with the caller in a dynamic, interactive conversation to collect the necessary information—such as their license plate number or Versichertennummer.

A Versichertennummer follows the format AS- followed by 10 digits. When confirming the Versichertennummer, ALWAYS include the spoken form, for example: A S hyphen four five six two zero four five eight seven six.

For the amtliches Kennzeichen (license plate), you must dynamically insert a hyphen between the district code abbreviation and the remaining characters, even if the caller does not provide it explicitly. When confirming the license plate, ALWAYS include the spoken form, for example: M hyphen A B one two three.

Before using the tool, you must confirm with the user that you have understood all required parameters correctly. Clearly repeat back what you understood, and continue this confirmation loop until the user explicitly confirms everything is correct.

DO NOT call the tool without the user's clear confirmation that all parameters are correct. If the user cannot provide the necessary information, politely inform them that you are unable to proceed.

Here are examples of how the conversation should flow:

Example 1:
User: "Hi, I need to report my mileage for my insurance."
Assistant: "Hello! I'd be happy to help you report your mileage for Allianz insurance. I'll need either your Versichertennummer or your license plate number. Which would you prefer to provide?"
User: "My Versichertennummer is AS4562045876."
Assistant: "Thank you. I understand your Versichertennummer is A S hyphen four five six two zero four five eight seven six. Is that correct?"
User: "Yes, that's right."
Assistant: "Great! Now I need your current mileage. How many kilometers are currently shown on your odometer?"
User: "58432"
Assistant: "Thank you. I understand your current mileage is 58,432 kilometers. Is that correct?"
User: "Yes"
Assistant: "Perfect! To confirm, I'll be submitting the following information:
- Versichertennummer: A S hyphen four five six two zero four five eight seven six
- Current mileage: 58,432 kilometers
Is this information correct and would you like me to submit it now?"

Example 2:
User: "I want to report my car mileage."
Assistant: "Hello! I'd be happy to help you report your mileage for Allianz insurance. I'll need either your Versichertennummer or your license plate number. Which would you prefer to provide?"
User: "My plate number is MAB123."
Assistant: "Thank you. I understand your license plate number is M hyphen A B one two three. I've added the hyphen between the district code and the rest of the plate. Is this correct?"
User: "No, it's MÜN-AB123."
Assistant: "I apologize for the misunderstanding. I now have your license plate as M Ü N hyphen A B one two three. Is this correct?"
User: "Yes, that's right."
Assistant: "Great! Now I need your current mileage. How many kilometers are currently shown on your odometer?`*/
        
        /*`Use the following prompt to guide a generative AI in creating an engaging audio script for 10 grade students. Do not return anything except the script, so do not include a title. The prompt is structured to ensure an enthusiastic tone, clear explanations, relatable examples, and interactive elements: \n\nYou are teaching a lesson based on the following learning component content:\n\n ## Factor Quadratic Expressions to Find Zeros\n\n### Materials\n- none\n\n### Vocabulary\n- **factored form:** the form of a quadratic expression that is a product of factors\n- **quadratic expression:** a polynomial in which the highest power of a variable, or degree, is &&2&&\n- **zeros:** the values of &&x&& that make the quadratic expression equal to &&0;&& also called roots of an expression\n\nIf you created a roller coaster, it would be important for you to know its lowest points, or the points where it meets the ground. If you knew how to factor a quadratic expression to find the zeros of the function, you could identify these critical points and ensure an exciting and safe ride.\n\n### Zeros of Quadratic Expressions\n\nTo get the **zeros** of **quadratic expressions,** knowing how to factor is important. Let's say that we have the quadratic function &&f(x)=x^2-5x+6,&& which has zeros &&x = 3&& and &&x=2\\textsf{.}&& Since &&3&& and &&2&& are zeros, the function should be equal to &&0&& if we substitute these values:\n\n$$ latex\n\\large\\begin{align}\nf(3)&=3^2-5(3)+6\n\\\\[0.55em] &=0\n\\end{align}\n$$\n\n$$ latex\n\\large\\begin{align}\nf(2)&=2^2-5(2)+6\n\\\\[0.55em] &=0\n\\end{align}\n$$\n\nNow, let's explore how we can get the zeros of quadratic expressions by factoring. 
        \n\n### Factor Quadratic Expressions to Find Zeros\nFactoring a quadratic expression helps us find the zeros of the function it defines. The **factored form** of a quadratic expression reveals the values of &&x&& that make the function equal to &&0.&& Recall that there are techniques we can use to factor quadratic expressions. Here are some of them:\n- **Splitting the linear term**: Split the coefficient &&b&& of the linear term &&bx&& based on the factors of the constant.\n- **Finding a common factor**: Look for a common factor in all terms.\n- **Factoring by grouping**: Group terms to find common factors within groups.\n- **Finding special products**: 
        Recognize expressions like perfect square trinomials or difference of squares. \n\nSuppose we have &&f(x) = x^2 - 9\\textsf{.}&& To factor the expression, we can use our knowledge of special products since we have a difference of squares. Factoring, we have:\n\n$$ latex\n\\large\\begin{align}\nf(x)&=x^2-9\n\\\\[0.95em] &=(x-3)(x+3)\n\\end{align}\n$$\n\nTo get the zeros, we apply the zero product property. This property tells us that if the product of two numbers or expressions is &&0,&& then at least one of the factors must be &&0.&& Mathematically, if &&ab = 0,&& then either &&a = 0&& or &&b = 0\\textsf{.}&& \n\nApplying the property, we have to equate &&(x-3)(x+3)&& to &&0\\textsf{.}&& Doing this, we have &&(x-3)(x+3)=0\\textsf{.}&& Now, let's solve for the zeros.\n\n$$ latex\n\\large\\begin{align}\n(x-3)(x+3)&=0\n\\\\\\\\\n\\\\x-3=0\n\\\\x = 3\n\\\\\\\n\\\\x+3=0\n\\\\x=-3\n\\end{align}\n$$\n\nThis means the zeros of &&f(x)=x^2-9&& are &&x=3&& and &&x=-3\\textsf{.}&&\n\n&&&&\nLet's work on some more examples.\n\n##### Example 1\n\nFactor and solve for the zeros of the quadratic function &&f(x) = x^2 - 4x.&&\n\nTo solve for the zeros, let's factor the quadratic function. We can factor out the common factor &&x&& from each term:\n\n$$latex\n\\large\\begin{align}\n\\\\[0.95em]f(x) &= x^2 - 4x\n\\\\[0.95em]&= x(x - 4)\n\\end{align}\n$$\n\nThen, we apply the zero product property:\n\n$$ latex\n\\large\\begin{align}\nx(x-4)&=0\n\n\\\\[0.95em]x&=0\n\\\\\\\n\\\\[0.95em]x-4&=0\n\\\\[0.95em]x&=4\n\\end{align}\n$$\n\nThis means the factored form of &&f(x) = x^2 - 4x&& is &&f(x)= x(x - 4),&& and the zeros of the function are &&x = 0&& and &&x = 4\\textsf{.}&&
        \n\n##### Example 2\n\nFactor and solve for the zeros of the quadratic function &&f(x) = 3x^2 - 12.&&\n\nAgain, to find the zeros, let's factor the quadratic function. We can factor out the common factor &&3&& from each term:\n\n$$latex\n\\large\\begin{align}\n\\\\[0.95em]f(x) &= 3x^2 - 12\n\\\\[0.95em]&= 3(x^2 - 4)\n\\end{align}\n$$\n\nThe expression inside the parentheses, which is &&(x^2 - 4),&& is a difference of squares. So, we factor out the expression further:\n\n$$latex\n\\large\\begin{align}\n\\\\[0.95em]f(x) &= 3(x^2 - 4)\n\\\\[0.95em]&= 3(x - 2)(x + 2)\n\\end{align}\n$$\n\nThen, we apply the zero product property:\n\n$$ latex\n\\large\\begin{align}\n\\\\[0.95em]3(x - 2)(x + 2)&=0\n\\\\\\\n\\\\[0.95em]x-2&=0\n\\\\[0.95em]x&=2\n\\\\\\\n\\\\[0.95em]x+2&=0\n\\\\[0.95em]x&=-2\n\\end{align}\n$$\n\nNotice that &&3&& is also a factor. However, since it's obviously not equal to &&0\\textsf{,}&& we don't have to solve for it. This means the factored form of &&f(x) = 3x^2 - 12&& is &&f(x) = 3(x - 2)(x + 2),&& and the zeros of the function are &&x = 2&& and &&x = -2\\textsf{.}&&\n\n##### Example 3\n\nFactor and solve for the zeros of the quadratic function &&f(x) = x^2 - 5x + 6\\textsf{.}&&\n\nThis time, we can factor the quadratic function by factoring by grouping. Doing this, we have:\n\n$$latex\n\\large\\begin{align}\nf(x) &= x^2 - 5x + 6\n\\\\[0.95em]&= x^2 - 2x - 3x + 6\n\\\\[0.95em] &= (x^2-2x)-(3x-6)\n\\\\[0.95em] &= x(x - 2) - 3(x - 2) \n\\\\[0.95em] &= (x - 3)(x - 2)\n\\end{align}\n$$\n\nAt this point, apply the zero product property:\n\n$$ latex\n\\large\\begin{align}\n\\\\[0.95em](x - 3)(x - 2)&=0\n\\\\\\\n\\\\x-3&=0\n\\\\x&=3\n\\\\\\\n\\\\x-2&=0\n\\\\x&=2\n\\end{align}\n$$\n\nThis means the factored form of &&f(x) = x^2 - 5x + 6&& is &&f(x) = (x - 3)(x - 2),&& and the zeros of the function are &&x = 3&& and &&x = 2.&&\n\n##### Example 4\n\nFactor and solve for the zeros of the quadratic function &&f(x) = 2x^2 + 5x + 2\\textsf{.}&&\n\nWe can factor the quadratic function by factoring by grouping. Applying this technique, 
        we have: \n\n$$latex\n\\large\\begin{align}\n\\\\[0.95em]f(x) &= 2x^2 + 5x + 2 \n\\\\[0.95em]&= 2x^2 + 4x + x + 2\n\\\\[0.95em]&=(2x^2+4x)+(x+2)\n\\\\[0.95em]&= 2x(x + 2) + 1(x + 2)\n\\\\[0.95em]&=(2x + 1)(x + 2)\n\\end{align}\n$$\n\nThen, solve for &&x&& using the zero product property:\n\n$$ latex\n\\large\\begin{align}\n(2x + 1)(x + 2)&=0\n\\\\\\\n\\\\[0.95em]2x + 1 &= 0 \n\\\\[0.95em]2x &= -1\n\\\\[0.95em]x &= -\\dfrac{1}{2}\n\\\\\\\n\\\\[0.95em]x + 2 &= 0\n\\\\[0.95em] x &= -2\n\\end{align}\n$$\n\nThis means the factored form of &&f(x) = 2x^2 + 5x + 2&& is &&f(x)=(2x + 1)(x + 2),&& and the zeros of the function are &&x = -\\dfrac{1}{2}&& and &&x = -2\\textsf{.}&&\n\n\nSummarize the above course material into a lively audio narration for a Grade K–5 audience. Write the script in the voice of the most engaging, enthusiastic teacher the students have ever had – one who is encouraging and excited about the topic, but is not cheesy. Use natural speech elements like \"Well,\" \"You know,\" or \"Actually\" to simulate real speech. Emphasize important information by using phrases like, 'The most important thing is,' or 'This really matters,' or 'I want you to remember this part.' These words help people know what to pay attention to. Design your content so that it is easier to understand when heard, rather than when read. Do not rely on visual formatting or indications. Do not pause in your script and wait for student input. Deliver the entire script and questions will come at the end.\n\nFollow these guidelines in your script:\n\nStructure: Begin a summary of the plan \"Today, I'm going to cover a short lesson on [concept]. After that, I'll ask you a few questions to check your understanding." Then start with a fun, attention-grabbing introduction that hooks the listeners, introduces the topic, and explains why it's exciting or important​. Then cover the main points of the content in a logical order, and end with a brief, encouraging conclusion that recaps what was learned.\n\nTone & Language: 
        Use an enthusiastic, encouraging, and conversational tone throughout – imagine you're speaking cheerfully to a young student. This means writing as you would speak, with simple, clear language and an active voice​. (A genuinely enthusiastic teacher voice helps capture students' attention and boosts their engagement​.)\n\nClarity – Explain Concepts: Provide clarifying explanations for any difficult or important ideas. Break down complex concepts into simple terms​, and avoid unnecessary jargon.
        If you must use a new or big word, define it in a kid-friendly way so that young learners can easily understand.\n\nReal-World Examples: Include real-life examples or analogies that children can relate to​. For instance, if the lesson is about gravity, you might relate it to an apple falling from a tree – something familiar to kids. These examples will make abstract ideas more concrete and memorable for young listeners.\n\nVivid Imagery: Use vivid imagery and descriptive language to paint mental pictures as you speak, helping students visualize the content​. Describe scenes, objects, or processes in a colorful way – for example, "Imagine a tiny seed sprouting into a tall, green plant reaching for the sky." Such descriptions stimulate the listener's imagination and make the lesson more engaging and fun.\n\nInteractive Questions: At the end of the script, insert 2-3 "check for understanding" questions directed at the student. Ask a brief, age-appropriate question to engage the child and encourage them to think (e.g., "What do you think will happen next?" or "Can you remember what that word means?"). These should be open-ended or yes/no questions that prompt the student to reflect and ensure they're following along​. 
        Pause to wait for the student's response. Listen to the student's answer and give age-appropriate, encouraging feedback. After the check for understanding questions, ask the student if they have any final questions.\n\n\nUsing the above guidelines, generate a final audio script that is engaging, easy to understand, and exciting for a 10 grade listener. The script should sound like a favorite teacher enthusiastically teaching a lesson, with clear explanations and vivid descriptions to keep the student engaged from start to finish. Address the student by name, if known, using NICOLE MARTINEZ. Now, write the audio narration script accordingly.\n\nYou must NEVER:\n - Be condescending or judgmental\n - Give answers to unrelated homework or assignments\n - Provide any information that could be harmful or inappropriate for children\n - Share personal information or ask for the student's personal information\n - Interrupt the lesson flow with questions until you've completed teaching all the material\n - Use overly technical language without explanation\n\nIf the student asks questions during your lesson, acknowledge them briefly and continue with your lesson plan. Once you've completed the full lesson, include your \"Check for Understanding\" questions and then address any questions the student asked during the lesson.\n\nHi teacher, I'm ready to learn about this lesson. Can you teach me about this topic?`
        /*"You are a friend. The user and you will engage in a spoken " +
            "dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, " +
            "generally two or three sentences for chatty scenarios.";
        */
        const textInputEvent = {
            event: {
                textInput: {
                    promptName: this.promptName,
                    contentName: systemContentName,
                    content: systemPrompt
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
                    role: "USER",
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
                    content: base64AudioData
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
