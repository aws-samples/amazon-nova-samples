"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NovaSonicBidirectionalStreamClient = exports.StreamSession = void 0;
const client_bedrock_runtime_1 = require("@aws-sdk/client-bedrock-runtime");
const node_http_handler_1 = require("@smithy/node-http-handler");
const node_crypto_1 = require("node:crypto");
const rxjs_1 = require("rxjs");
const operators_1 = require("rxjs/operators");
const rxjs_2 = require("rxjs");
const consts_1 = require("./consts");
const bedrock_kb_client_1 = require("./bedrock-kb-client");
const consts_2 = require("./consts");
const appointment_tools_1 = require("./appointment-tools");
class StreamSession {
    constructor(sessionId, client) {
        this.sessionId = sessionId;
        this.client = client;
        this.audioBufferQueue = [];
        this.maxQueueSize = 200; // Maximum number of audio chunks to queue
        this.isProcessingAudio = false;
        this.isActive = true;
    }
    // Register event handlers for this specific session
    onEvent(eventType, handler) {
        this.client.registerEventHandler(this.sessionId, eventType, handler);
        return this; // For chaining
    }
    async setupPromptStart() {
        this.client.setupPromptStartEvent(this.sessionId);
    }
    async setupSystemPrompt(textConfig = consts_1.DefaultTextConfiguration, systemPromptContent = consts_1.DefaultSystemPrompt) {
        this.client.setupSystemPromptEvent(this.sessionId, textConfig, systemPromptContent);
    }
    async setupStartAudio(audioConfig = consts_1.DefaultAudioInputConfiguration) {
        this.client.setupStartAudioEvent(this.sessionId, audioConfig);
    }
    // Stream audio for this session
    async streamAudio(audioData) {
        // Check queue size to avoid memory issues
        if (this.audioBufferQueue.length >= this.maxQueueSize) {
            // Queue is full, drop oldest chunk
            this.audioBufferQueue.shift();
            console.log("Audio queue full, dropping oldest chunk");
        }
        // Queue the audio chunk for streaming
        this.audioBufferQueue.push(audioData);
        this.processAudioQueue();
    }
    // Process audio queue for continuous streaming
    async processAudioQueue() {
        if (this.isProcessingAudio || this.audioBufferQueue.length === 0 || !this.isActive)
            return;
        this.isProcessingAudio = true;
        try {
            // Process all chunks in the queue, up to a reasonable limit
            let processedChunks = 0;
            const maxChunksPerBatch = 5; // Process max 5 chunks at a time to avoid overload
            while (this.audioBufferQueue.length > 0 && processedChunks < maxChunksPerBatch && this.isActive) {
                const audioChunk = this.audioBufferQueue.shift();
                if (audioChunk) {
                    await this.client.streamAudioChunk(this.sessionId, audioChunk);
                    processedChunks++;
                }
            }
        }
        finally {
            this.isProcessingAudio = false;
            // If there are still items in the queue, schedule the next processing using setTimeout
            if (this.audioBufferQueue.length > 0 && this.isActive) {
                setTimeout(() => this.processAudioQueue(), 0);
            }
        }
    }
    // Get session ID
    getSessionId() {
        return this.sessionId;
    }
    async endAudioContent() {
        if (!this.isActive)
            return;
        await this.client.sendContentEnd(this.sessionId);
    }
    async endPrompt() {
        if (!this.isActive)
            return;
        await this.client.sendPromptEnd(this.sessionId);
    }
    async close() {
        if (!this.isActive)
            return;
        this.isActive = false;
        this.audioBufferQueue = []; // Clear any pending audio
        await this.client.sendSessionEnd(this.sessionId);
        console.log(`Session ${this.sessionId} close completed`);
    }
}
exports.StreamSession = StreamSession;
class NovaSonicBidirectionalStreamClient {
    constructor(config) {
        this.activeSessions = new Map();
        this.sessionLastActivity = new Map();
        this.sessionCleanupInProgress = new Set();
        const http2Client = new node_http_handler_1.NodeHttp2Handler({
            requestTimeout: 300000,
            sessionTimeout: 300000,
            disableConcurrentStreams: false,
            maxConcurrentStreams: 20,
            ...config.requestHandlerConfig,
        });
        if (!config.clientConfig.credentials) {
            throw new Error("No credentials provided");
        }
        this.bedrockRuntimeClient = new client_bedrock_runtime_1.BedrockRuntimeClient({
            ...config.clientConfig,
            credentials: config.clientConfig.credentials,
            region: config.clientConfig.region || "us-east-1",
            requestHandler: http2Client
        });
        this.inferenceConfig = config.inferenceConfig ?? {
            maxTokens: 1024,
            topP: 0.9,
            temperature: 0.7,
        };
    }
    isSessionActive(sessionId) {
        const session = this.activeSessions.get(sessionId);
        return !!session && session.isActive;
    }
    getActiveSessions() {
        return Array.from(this.activeSessions.keys());
    }
    getLastActivityTime(sessionId) {
        return this.sessionLastActivity.get(sessionId) || 0;
    }
    updateSessionActivity(sessionId) {
        this.sessionLastActivity.set(sessionId, Date.now());
    }
    isCleanupInProgress(sessionId) {
        return this.sessionCleanupInProgress.has(sessionId);
    }
    // Create a new streaming session
    createStreamSession(sessionId = (0, node_crypto_1.randomUUID)(), config) {
        if (this.activeSessions.has(sessionId)) {
            throw new Error(`Stream session with ID ${sessionId} already exists`);
        }
        const session = {
            queue: [],
            queueSignal: new rxjs_1.Subject(),
            closeSignal: new rxjs_1.Subject(),
            responseSubject: new rxjs_1.Subject(),
            toolUseContent: null,
            toolUseId: "",
            toolName: "",
            responseHandlers: new Map(),
            promptName: (0, node_crypto_1.randomUUID)(),
            inferenceConfig: config?.inferenceConfig ?? this.inferenceConfig,
            isActive: true,
            isPromptStartSent: false,
            isAudioContentStartSent: false,
            audioContentId: (0, node_crypto_1.randomUUID)()
        };
        this.activeSessions.set(sessionId, session);
        return new StreamSession(sessionId, this);
    }
    async processToolUse(toolName, toolUseContent) {
        const tool = toolName.toLowerCase();
        console.log(`Processing tool use for: ${tool}`);
        switch (tool) {
            // Keep existing tool cases
            case "retrieve_health_info":
                console.log(`Retrieving health information: ${JSON.stringify(toolUseContent)}`);
                const kbContent = await this.parseToolUseContent(toolUseContent);
                if (!kbContent) {
                    throw new Error('parsedContent is undefined');
                }
                return this.queryHealthKnowledgeBase(kbContent?.query, kbContent?.maxResults);
            case "greeting":
                console.log(`Generating greeting: ${JSON.stringify(toolUseContent)}`);
                return this.generateGreeting(toolUseContent);
            case "safety_response":
                console.log(`Generating safety response: ${JSON.stringify(toolUseContent)}`);
                return this.generateSafetyResponse(toolUseContent);
            // Add new appointment tool cases
            case "check_doctor_availability":
                console.log(`Checking doctor availability: ${JSON.stringify(toolUseContent)}`);
                return (0, appointment_tools_1.checkDoctorAvailability)(toolUseContent);
            case "check_appointments":
                console.log(`Checking appointments: ${JSON.stringify(toolUseContent)}`);
                return (0, appointment_tools_1.checkAppointments)(toolUseContent);
            case "schedule_appointment":
                console.log(`Scheduling appointment: ${JSON.stringify(toolUseContent)}`);
                return (0, appointment_tools_1.scheduleAppointment)(toolUseContent);
            case "cancel_appointment":
                console.log(`Cancelling appointment: ${JSON.stringify(toolUseContent)}`);
                return (0, appointment_tools_1.cancelAppointment)(toolUseContent);
            default:
                console.log(`Tool ${tool} not supported`);
                throw new Error(`Tool ${tool} not supported`);
        }
    }
    generateGreeting(toolUseContent) {
        try {
            let content = JSON.parse(toolUseContent.content || "{}");
            const greetingType = content.greeting_type || "initial";
            const userName = content.user_name || "";
            let greeting = "";
            switch (greetingType) {
                case "initial":
                    greeting = "Hello! I'm Ada, your Health Guide Assistant. I can help you with information about common health conditions, preventive care recommendations, and appointment scheduling. How can I assist you today?";
                    break;
                case "returning_user":
                    greeting = `Welcome back${userName ? ', ' + userName : ''}! How can I assist you with health information today?`;
                    break;
                case "help_offer":
                    greeting = "I notice you might need some help. I can provide information about common health conditions, preventive care, or help with scheduling appointments. What would you like to know about?";
                    break;
                default:
                    greeting = "Hello! I'm Ada, your Health Guide Assistant. How can I help you today?";
            }
            return {
                greeting: greeting,
                capabilities: [
                    "Information about common health conditions",
                    "Preventive care recommendations",
                    "Appointment scheduling guidance"
                ]
            };
        }
        catch (error) {
            console.error("Error generating greeting:", error);
            return {
                greeting: "Hello! I'm Ada, your Health Guide Assistant. How can I help you today?",
                error: String(error)
            };
        }
    }
    generateSafetyResponse(toolUseContent) {
        try {
            let content = JSON.parse(toolUseContent.content || "{}");
            const topic = content.topic || "this topic";
            const requestType = content.request_type || "other";
            const suggestedAction = content.suggested_action || "redirect";
            const category = content.category || "";
            let response = "";
            let alternativeSuggestion = "";
            // Determine appropriate response based on request type
            switch (requestType) {
                case "medical_advice":
                case "diagnosis":
                case "treatment":
                    response = `I'm not able to provide specific ${requestType.replace('_', ' ')} about ${topic}. As an AI assistant, I can only offer general health information, not personalized medical advice.`;
                    alternativeSuggestion = "For personalized medical guidance, please consult with a qualified healthcare provider.";
                    break;
                case "prescription":
                    response = `I cannot provide prescriptions or medication recommendations for ${topic} or any condition. Only licensed healthcare professionals can prescribe medications.`;
                    alternativeSuggestion = "Please speak with your doctor about medication options for your condition.";
                    break;
                case "emergency":
                    response = `This sounds like it could be a medical emergency. I'm not equipped to help with emergency situations.`;
                    alternativeSuggestion = "Please contact emergency services (911) immediately or go to your nearest emergency room.";
                    break;
                case "personal_info":
                    response = `I'm not able to access, store, or process personal health information about ${topic} or other medical records.`;
                    alternativeSuggestion = "For access to your medical records, please contact your healthcare provider directly.";
                    break;
                case "off_topic":
                case "non_health":
                    let categoryText = category ? ` about ${category}` : "";
                    response = `I'm specifically designed to discuss health-related topics only, so I can't assist with questions${categoryText} about ${topic}.`;
                    alternativeSuggestion = "If you have questions about common health conditions, preventive care, or appointment scheduling, I'd be happy to help with those.";
                    break;
                case "harmful":
                    response = `I cannot provide information on ${topic} as it could potentially be harmful.`;
                    alternativeSuggestion = "I'm designed to provide helpful health information that promotes wellbeing. Let me know if you have health-related questions I can assist with.";
                    break;
                case "illegal":
                    response = `I cannot provide information or assistance regarding ${topic} as it may be related to illegal activities.`;
                    alternativeSuggestion = "I'm programmed to provide health information within legal and ethical boundaries. I'd be happy to help with legitimate health questions.";
                    break;
                default:
                    response = `I'm not able to provide information about ${topic} as it's outside my knowledge domain.`;
                    alternativeSuggestion = "I can help with information about common health conditions, preventive care, and appointment scheduling instead.";
            }
            return {
                response: response,
                alternative_suggestion: alternativeSuggestion,
                appropriate_topics: [
                    "Common health conditions and symptoms",
                    "Preventive care recommendations",
                    "General appointment scheduling guidance"
                ],
                request_details: {
                    type: requestType,
                    topic: topic,
                    category: category || "N/A"
                }
            };
        }
        catch (error) {
            console.error("Error generating safety response:", error);
            return {
                response: "I'm unable to provide information on this topic. I can only help with general health information about common conditions, preventive care, and appointment scheduling.",
                error: String(error)
            };
        }
    }
    async queryPatientDatabase(query, filters = {}) {
        // You'll implement your database search logic here
        // This function would connect to your database and return results
        // Mock implementation for now
        return {
            results: [
                {
                    id: "patient123",
                    name: "Ed Fraga",
                    lastVisit: "2024-04-15",
                    nextAppointment: "2025-06-20",
                    relevance: 0.92
                }
            ]
        };
    }
    async queryHealthKnowledgeBase(query, numberOfResults = 3) {
        // Create a client instance
        const kbClient = new bedrock_kb_client_1.BedrockKnowledgeBaseClient();
        // Replace with your actual Knowledge Base ID
        const KNOWLEDGE_BASE_ID = 'JXXSUEEVME';
        try {
            console.log(`Searching for: "${query}"`);
            // Retrieve information from the Knowledge Base
            const results = await kbClient.retrieveFromKnowledgeBase({
                knowledgeBaseId: KNOWLEDGE_BASE_ID,
                query,
                numberOfResults: numberOfResults
            });
            console.log(`Results: ${JSON.stringify(results)}`);
            return { results: results };
        }
        catch (error) {
            console.error("Error:", error);
            return {};
        }
    }
    async parseToolUseContent(toolUseContent) {
        try {
            // Check if the content field exists and is a string
            if (toolUseContent && typeof toolUseContent.content === 'string') {
                // Parse the JSON string into an object
                const parsedContent = JSON.parse(toolUseContent.content);
                // Return the parsed content
                return {
                    query: parsedContent.query,
                    maxResults: parsedContent?.maxResults
                };
            }
            return null;
        }
        catch (error) {
            console.error("Failed to parse tool use content:", error);
            return null;
        }
    }
    // Stream audio for a specific session
    async initiateSession(sessionId) {
        const session = this.activeSessions.get(sessionId);
        if (!session) {
            throw new Error(`Stream session ${sessionId} not found`);
        }
        try {
            // Set up initial events for this session
            this.setupSessionStartEvent(sessionId);
            // Create the bidirectional stream with session-specific async iterator
            const asyncIterable = this.createSessionAsyncIterable(sessionId);
            console.log(`Starting bidirectional stream for session ${sessionId}...`);
            const response = await this.bedrockRuntimeClient.send(new client_bedrock_runtime_1.InvokeModelWithBidirectionalStreamCommand({
                modelId: "amazon.nova-sonic-v1:0",
                body: asyncIterable,
            }));
            console.log(`Stream established for session ${sessionId}, processing responses...`);
            // Process responses for this session
            await this.processResponseStream(sessionId, response);
        }
        catch (error) {
            console.error(`Error in session ${sessionId}: `, error);
            this.dispatchEventForSession(sessionId, 'error', {
                source: 'bidirectionalStream',
                error
            });
            // Make sure to clean up if there's an error
            if (session.isActive) {
                this.closeSession(sessionId);
            }
        }
    }
    // Dispatch events to handlers for a specific session
    dispatchEventForSession(sessionId, eventType, data) {
        const session = this.activeSessions.get(sessionId);
        if (!session)
            return;
        const handler = session.responseHandlers.get(eventType);
        if (handler) {
            try {
                handler(data);
            }
            catch (e) {
                console.error(`Error in ${eventType} handler for session ${sessionId}: `, e);
            }
        }
        // Also dispatch to "any" handlers
        const anyHandler = session.responseHandlers.get('any');
        if (anyHandler) {
            try {
                anyHandler({ type: eventType, data });
            }
            catch (e) {
                console.error(`Error in 'any' handler for session ${sessionId}: `, e);
            }
        }
    }
    createSessionAsyncIterable(sessionId) {
        if (!this.isSessionActive(sessionId)) {
            console.log(`Cannot create async iterable: Session ${sessionId} not active`);
            return {
                [Symbol.asyncIterator]: () => ({
                    next: async () => ({ value: undefined, done: true })
                })
            };
        }
        const session = this.activeSessions.get(sessionId);
        if (!session) {
            throw new Error(`Cannot create async iterable: Session ${sessionId} not found`);
        }
        let eventCount = 0;
        return {
            [Symbol.asyncIterator]: () => {
                console.log(`AsyncIterable iterator requested for session ${sessionId}`);
                return {
                    next: async () => {
                        try {
                            // Check if session is still active
                            if (!session.isActive || !this.activeSessions.has(sessionId)) {
                                console.log(`Iterator closing for session ${sessionId}, done = true`);
                                return { value: undefined, done: true };
                            }
                            // Wait for items in the queue or close signal
                            if (session.queue.length === 0) {
                                try {
                                    await Promise.race([
                                        (0, rxjs_2.firstValueFrom)(session.queueSignal.pipe((0, operators_1.take)(1))),
                                        (0, rxjs_2.firstValueFrom)(session.closeSignal.pipe((0, operators_1.take)(1))).then(() => {
                                            throw new Error("Stream closed");
                                        })
                                    ]);
                                }
                                catch (error) {
                                    if (error instanceof Error) {
                                        if (error.message === "Stream closed" || !session.isActive) {
                                            // This is an expected condition when closing the session
                                            if (this.activeSessions.has(sessionId)) {
                                                console.log(`Session \${ sessionId } closed during wait`);
                                            }
                                            return { value: undefined, done: true };
                                        }
                                    }
                                    else {
                                        console.error(`Error on event close`, error);
                                    }
                                }
                            }
                            // If queue is still empty or session is inactive, we're done
                            if (session.queue.length === 0 || !session.isActive) {
                                console.log(`Queue empty or session inactive: ${sessionId} `);
                                return { value: undefined, done: true };
                            }
                            // Get next item from the session's queue
                            const nextEvent = session.queue.shift();
                            eventCount++;
                            //console.log(`Sending event #${ eventCount } for session ${ sessionId }: ${ JSON.stringify(nextEvent).substring(0, 100) }...`);
                            return {
                                value: {
                                    chunk: {
                                        bytes: new TextEncoder().encode(JSON.stringify(nextEvent))
                                    }
                                },
                                done: false
                            };
                        }
                        catch (error) {
                            console.error(`Error in session ${sessionId} iterator: `, error);
                            session.isActive = false;
                            return { value: undefined, done: true };
                        }
                    },
                    return: async () => {
                        console.log(`Iterator return () called for session ${sessionId}`);
                        session.isActive = false;
                        return { value: undefined, done: true };
                    },
                    throw: async (error) => {
                        console.log(`Iterator throw () called for session ${sessionId} with error: `, error);
                        session.isActive = false;
                        throw error;
                    }
                };
            }
        };
    }
    // Process the response stream from AWS Bedrock
    async processResponseStream(sessionId, response) {
        const session = this.activeSessions.get(sessionId);
        if (!session)
            return;
        try {
            for await (const event of response.body) {
                if (!session.isActive) {
                    console.log(`Session ${sessionId} is no longer active, stopping response processing`);
                    break;
                }
                if (event.chunk?.bytes) {
                    try {
                        this.updateSessionActivity(sessionId);
                        const textResponse = new TextDecoder().decode(event.chunk.bytes);
                        try {
                            const jsonResponse = JSON.parse(textResponse);
                            if (jsonResponse.event?.contentStart) {
                                this.dispatchEvent(sessionId, 'contentStart', jsonResponse.event.contentStart);
                            }
                            else if (jsonResponse.event?.textOutput) {
                                this.dispatchEvent(sessionId, 'textOutput', jsonResponse.event.textOutput);
                            }
                            else if (jsonResponse.event?.audioOutput) {
                                this.dispatchEvent(sessionId, 'audioOutput', jsonResponse.event.audioOutput);
                            }
                            else if (jsonResponse.event?.toolUse) {
                                this.dispatchEvent(sessionId, 'toolUse', jsonResponse.event.toolUse);
                                // Store tool use information for later
                                session.toolUseContent = jsonResponse.event.toolUse;
                                session.toolUseId = jsonResponse.event.toolUse.toolUseId;
                                session.toolName = jsonResponse.event.toolUse.toolName;
                            }
                            else if (jsonResponse.event?.contentEnd &&
                                jsonResponse.event?.contentEnd?.type === 'TOOL') {
                                // Process tool use
                                console.log(`Processing tool use for session ${sessionId}`);
                                this.dispatchEvent(sessionId, 'toolEnd', {
                                    toolUseContent: session.toolUseContent,
                                    toolUseId: session.toolUseId,
                                    toolName: session.toolName
                                });
                                console.log("calling tooluse");
                                console.log("tool use content : ", session.toolUseContent);
                                // function calling
                                const toolResult = await this.processToolUse(session.toolName, session.toolUseContent);
                                // Send tool result
                                this.sendToolResult(sessionId, session.toolUseId, toolResult);
                                // Also dispatch event about tool result
                                this.dispatchEvent(sessionId, 'toolResult', {
                                    toolUseId: session.toolUseId,
                                    result: toolResult
                                });
                            }
                            else if (jsonResponse.event?.contentEnd) {
                                this.dispatchEvent(sessionId, 'contentEnd', jsonResponse.event.contentEnd);
                            }
                            else {
                                // Handle other events
                                const eventKeys = Object.keys(jsonResponse.event || {});
                                console.log(`Event keys for session ${sessionId}: `, eventKeys);
                                console.log(`Handling other events`);
                                if (eventKeys.length > 0) {
                                    this.dispatchEvent(sessionId, eventKeys[0], jsonResponse.event);
                                }
                                else if (Object.keys(jsonResponse).length > 0) {
                                    this.dispatchEvent(sessionId, 'unknown', jsonResponse);
                                }
                            }
                        }
                        catch (e) {
                            console.log(`Raw text response for session ${sessionId}(parse error): `, textResponse);
                        }
                    }
                    catch (e) {
                        console.error(`Error processing response chunk for session ${sessionId}: `, e);
                    }
                }
                else if (event.modelStreamErrorException) {
                    console.error(`Model stream error for session ${sessionId}: `, event.modelStreamErrorException);
                    this.dispatchEvent(sessionId, 'error', {
                        type: 'modelStreamErrorException',
                        details: event.modelStreamErrorException
                    });
                }
                else if (event.internalServerException) {
                    console.error(`Internal server error for session ${sessionId}: `, event.internalServerException);
                    this.dispatchEvent(sessionId, 'error', {
                        type: 'internalServerException',
                        details: event.internalServerException
                    });
                }
            }
            console.log(`Response stream processing complete for session ${sessionId}`);
            this.dispatchEvent(sessionId, 'streamComplete', {
                timestamp: new Date().toISOString()
            });
        }
        catch (error) {
            console.error(`Error processing response stream for session ${sessionId}: `, error);
            this.dispatchEvent(sessionId, 'error', {
                source: 'responseStream',
                message: 'Error processing response stream',
                details: error instanceof Error ? error.message : String(error)
            });
        }
    }
    // Add an event to a session's queue
    addEventToSessionQueue(sessionId, event) {
        const session = this.activeSessions.get(sessionId);
        if (!session || !session.isActive)
            return;
        this.updateSessionActivity(sessionId);
        session.queue.push(event);
        session.queueSignal.next();
    }
    // Set up initial events for a session
    setupSessionStartEvent(sessionId) {
        console.log(`Setting up initial events for session ${sessionId}...`);
        const session = this.activeSessions.get(sessionId);
        if (!session)
            return;
        // Session start event
        this.addEventToSessionQueue(sessionId, {
            event: {
                sessionStart: {
                    inferenceConfiguration: session.inferenceConfig
                }
            }
        });
    }
    setupPromptStartEvent(sessionId) {
        console.log(`Setting up prompt start event for session ${sessionId}...`);
        const session = this.activeSessions.get(sessionId);
        if (!session)
            return;
        // Log the exact tool configuration for debugging
        console.log("Setting up tools with names:", [
            "retrieve_health_info",
            "greeting",
            "safety_response"
        ]);
        // Prompt start event
        this.addEventToSessionQueue(sessionId, {
            event: {
                promptStart: {
                    promptName: session.promptName,
                    textOutputConfiguration: {
                        mediaType: "text/plain",
                    },
                    audioOutputConfiguration: consts_1.DefaultAudioOutputConfiguration,
                    toolUseOutputConfiguration: {
                        mediaType: "application/json",
                    },
                    toolConfiguration: {
                        "toolChoice": {
                            'any': {}
                        },
                        tools: [
                            {
                                toolSpec: {
                                    name: "retrieve_health_info",
                                    description: "Use this tool only to retrieve information about health conditions, preventive care, and appointment scheduling from the knowledge base.",
                                    inputSchema: {
                                        json: consts_1.KnowledgeBaseToolSchema
                                    }
                                }
                            },
                            {
                                toolSpec: {
                                    name: "greeting",
                                    description: "Introduces yourself and the Health Guide Assistant to the user with an appropriate greeting.",
                                    inputSchema: {
                                        json: consts_1.GreetingToolSchema
                                    }
                                }
                            },
                            {
                                toolSpec: {
                                    name: "safety_response",
                                    description: "Provides a safe response when users ask about topics outside the assistant's domain or request inappropriate medical advice.",
                                    inputSchema: {
                                        json: consts_1.SafetyToolSchema
                                    }
                                }
                            },
                            {
                                toolSpec: {
                                    name: "check_doctor_availability",
                                    description: "Use this tool to check the availability of doctors, either by ID or specialty. ONLY use after collecting information about which doctor or specialty the patient is interested in.",
                                    inputSchema: {
                                        json: consts_2.CheckDoctorAvailabilitySchema
                                    }
                                }
                            },
                            {
                                toolSpec: {
                                    name: "check_appointments",
                                    description: "Use this tool to check existing appointments for a doctor or patient. You must have either a doctor ID or a patient name to use this tool.",
                                    inputSchema: {
                                        json: consts_2.CheckAppointmentsSchema
                                    }
                                }
                            },
                            {
                                toolSpec: {
                                    name: "schedule_appointment",
                                    description: "Use this tool ONLY after collecting ALL required information: patient name, doctor ID, date, time, and reason. Always check availability before scheduling.",
                                    inputSchema: {
                                        json: consts_2.ScheduleAppointmentSchema
                                    }
                                }
                            },
                            {
                                toolSpec: {
                                    name: "cancel_appointment",
                                    description: "Use this tool to cancel an existing appointment. You must have the appointment ID. If the user doesn't know their appointment ID, use check_appointments first.",
                                    inputSchema: {
                                        json: consts_2.CancelAppointmentSchema
                                    }
                                }
                            }
                        ]
                    },
                },
            }
        });
        session.isPromptStartSent = true;
    }
    setupSystemPromptEvent(sessionId, textConfig = consts_1.DefaultTextConfiguration, systemPromptContent = consts_1.DefaultSystemPrompt) {
        console.log(`Setting up systemPrompt events for session ${sessionId}...`);
        const session = this.activeSessions.get(sessionId);
        if (!session)
            return;
        // Text content start
        const textPromptID = (0, node_crypto_1.randomUUID)();
        this.addEventToSessionQueue(sessionId, {
            event: {
                contentStart: {
                    promptName: session.promptName,
                    contentName: textPromptID,
                    type: "TEXT",
                    interactive: true,
                    role: "SYSTEM",
                    textInputConfiguration: textConfig,
                },
            }
        });
        // Text input content
        this.addEventToSessionQueue(sessionId, {
            event: {
                textInput: {
                    promptName: session.promptName,
                    contentName: textPromptID,
                    content: systemPromptContent,
                },
            }
        });
        // Text content end
        this.addEventToSessionQueue(sessionId, {
            event: {
                contentEnd: {
                    promptName: session.promptName,
                    contentName: textPromptID,
                },
            }
        });
    }
    setupStartAudioEvent(sessionId, audioConfig = consts_1.DefaultAudioInputConfiguration) {
        console.log(`Setting up startAudioContent event for session ${sessionId}...`);
        const session = this.activeSessions.get(sessionId);
        if (!session)
            return;
        console.log(`Using audio content ID: ${session.audioContentId}`);
        // Audio content start
        this.addEventToSessionQueue(sessionId, {
            event: {
                contentStart: {
                    promptName: session.promptName,
                    contentName: session.audioContentId,
                    type: "AUDIO",
                    interactive: true,
                    role: "USER",
                    audioInputConfiguration: audioConfig,
                },
            }
        });
        session.isAudioContentStartSent = true;
        console.log(`Initial events setup complete for session ${sessionId}`);
    }
    // Stream an audio chunk for a session
    async streamAudioChunk(sessionId, audioData) {
        const session = this.activeSessions.get(sessionId);
        if (!session || !session.isActive || !session.audioContentId) {
            throw new Error(`Invalid session ${sessionId} for audio streaming`);
        }
        // Convert audio to base64
        const base64Data = audioData.toString('base64');
        this.addEventToSessionQueue(sessionId, {
            event: {
                audioInput: {
                    promptName: session.promptName,
                    contentName: session.audioContentId,
                    content: base64Data,
                },
            }
        });
    }
    // Send tool result back to the model
    async sendToolResult(sessionId, toolUseId, result) {
        const session = this.activeSessions.get(sessionId);
        console.log("inside tool result");
        if (!session || !session.isActive)
            return;
        console.log(`Sending tool result for session ${sessionId}, tool use ID: ${toolUseId}`);
        const contentId = (0, node_crypto_1.randomUUID)();
        // Tool content start
        this.addEventToSessionQueue(sessionId, {
            event: {
                contentStart: {
                    promptName: session.promptName,
                    contentName: contentId,
                    interactive: false,
                    type: "TOOL",
                    role: "TOOL",
                    toolResultInputConfiguration: {
                        toolUseId: toolUseId,
                        type: "TEXT",
                        textInputConfiguration: {
                            mediaType: "text/plain"
                        }
                    }
                }
            }
        });
        // Tool content input
        const resultContent = typeof result === 'string' ? result : JSON.stringify(result);
        this.addEventToSessionQueue(sessionId, {
            event: {
                toolResult: {
                    promptName: session.promptName,
                    contentName: contentId,
                    content: resultContent
                }
            }
        });
        // Tool content end
        this.addEventToSessionQueue(sessionId, {
            event: {
                contentEnd: {
                    promptName: session.promptName,
                    contentName: contentId
                }
            }
        });
        console.log(`Tool result sent for session ${sessionId}`);
    }
    async sendContentEnd(sessionId) {
        const session = this.activeSessions.get(sessionId);
        if (!session || !session.isAudioContentStartSent)
            return;
        await this.addEventToSessionQueue(sessionId, {
            event: {
                contentEnd: {
                    promptName: session.promptName,
                    contentName: session.audioContentId,
                }
            }
        });
        // Wait to ensure it's processed
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    async sendPromptEnd(sessionId) {
        const session = this.activeSessions.get(sessionId);
        if (!session || !session.isPromptStartSent)
            return;
        await this.addEventToSessionQueue(sessionId, {
            event: {
                promptEnd: {
                    promptName: session.promptName
                }
            }
        });
        // Wait to ensure it's processed
        await new Promise(resolve => setTimeout(resolve, 300));
    }
    async sendSessionEnd(sessionId) {
        const session = this.activeSessions.get(sessionId);
        if (!session)
            return;
        await this.addEventToSessionQueue(sessionId, {
            event: {
                sessionEnd: {}
            }
        });
        // Wait to ensure it's processed
        await new Promise(resolve => setTimeout(resolve, 300));
        // Now it's safe to clean up
        session.isActive = false;
        session.closeSignal.next();
        session.closeSignal.complete();
        this.activeSessions.delete(sessionId);
        this.sessionLastActivity.delete(sessionId);
        console.log(`Session ${sessionId} closed and removed from active sessions`);
    }
    // Register an event handler for a session
    registerEventHandler(sessionId, eventType, handler) {
        const session = this.activeSessions.get(sessionId);
        if (!session) {
            throw new Error(`Session ${sessionId} not found`);
        }
        session.responseHandlers.set(eventType, handler);
    }
    // Dispatch an event to registered handlers
    dispatchEvent(sessionId, eventType, data) {
        const session = this.activeSessions.get(sessionId);
        if (!session)
            return;
        const handler = session.responseHandlers.get(eventType);
        if (handler) {
            try {
                handler(data);
            }
            catch (e) {
                console.error(`Error in ${eventType} handler for session ${sessionId}:`, e);
            }
        }
        // Also dispatch to "any" handlers
        const anyHandler = session.responseHandlers.get('any');
        if (anyHandler) {
            try {
                anyHandler({ type: eventType, data });
            }
            catch (e) {
                console.error(`Error in 'any' handler for session ${sessionId}:`, e);
            }
        }
    }
    async closeSession(sessionId) {
        if (this.sessionCleanupInProgress.has(sessionId)) {
            console.log(`Cleanup already in progress for session ${sessionId}, skipping`);
            return;
        }
        this.sessionCleanupInProgress.add(sessionId);
        try {
            console.log(`Starting close process for session ${sessionId}`);
            await this.sendContentEnd(sessionId);
            await this.sendPromptEnd(sessionId);
            await this.sendSessionEnd(sessionId);
            console.log(`Session ${sessionId} cleanup complete`);
        }
        catch (error) {
            console.error(`Error during closing sequence for session ${sessionId}:`, error);
            // Ensure cleanup happens even if there's an error
            const session = this.activeSessions.get(sessionId);
            if (session) {
                session.isActive = false;
                this.activeSessions.delete(sessionId);
                this.sessionLastActivity.delete(sessionId);
            }
        }
        finally {
            // Always clean up the tracking set
            this.sessionCleanupInProgress.delete(sessionId);
        }
    }
    // Same for forceCloseSession:
    forceCloseSession(sessionId) {
        if (this.sessionCleanupInProgress.has(sessionId) || !this.activeSessions.has(sessionId)) {
            console.log(`Session ${sessionId} already being cleaned up or not active`);
            return;
        }
        this.sessionCleanupInProgress.add(sessionId);
        try {
            const session = this.activeSessions.get(sessionId);
            if (!session)
                return;
            console.log(`Force closing session ${sessionId}`);
            // Immediately mark as inactive and clean up resources
            session.isActive = false;
            session.closeSignal.next();
            session.closeSignal.complete();
            this.activeSessions.delete(sessionId);
            this.sessionLastActivity.delete(sessionId);
            console.log(`Session ${sessionId} force closed`);
        }
        finally {
            this.sessionCleanupInProgress.delete(sessionId);
        }
    }
}
exports.NovaSonicBidirectionalStreamClient = NovaSonicBidirectionalStreamClient;
