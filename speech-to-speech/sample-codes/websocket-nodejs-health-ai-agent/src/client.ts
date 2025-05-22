import {
  BedrockRuntimeClient,
  BedrockRuntimeClientConfig,
  InvokeModelWithBidirectionalStreamCommand,
  InvokeModelWithBidirectionalStreamInput,
} from "@aws-sdk/client-bedrock-runtime";
import {
  NodeHttp2Handler,
  NodeHttp2HandlerOptions,
} from "@smithy/node-http-handler";
import { Provider } from "@smithy/types";
import { Buffer } from "node:buffer";
import { randomUUID } from "node:crypto";
import { InferenceConfig } from "./types";
import { Subject } from 'rxjs';
import { take } from 'rxjs/operators';
import { firstValueFrom } from 'rxjs';
import {
  DatabaseToolSchema,
  DefaultAudioInputConfiguration,
  DefaultAudioOutputConfiguration,
  DefaultSystemPrompt,
  DefaultTextConfiguration,
  GreetingToolSchema,
  KnowledgeBaseToolSchema,
  SafetyToolSchema
} from "./consts";
import { BedrockKnowledgeBaseClient } from "./bedrock-kb-client";

import {
  CheckDoctorAvailabilitySchema,
  CheckAppointmentsSchema,
  ScheduleAppointmentSchema,
  CancelAppointmentSchema
} from './consts';

import {
  checkDoctorAvailability,
  checkAppointments,
  scheduleAppointment,
  cancelAppointment
} from './appointment-tools';

export interface NovaSonicBidirectionalStreamClientConfig {
  requestHandlerConfig?:
  | NodeHttp2HandlerOptions
  | Provider<NodeHttp2HandlerOptions | void>;
  clientConfig: Partial<BedrockRuntimeClientConfig>;
  inferenceConfig?: InferenceConfig;
}

export class StreamSession {
  private audioBufferQueue: Buffer[] = [];
  private maxQueueSize = 200; // Maximum number of audio chunks to queue
  private isProcessingAudio = false;
  private isActive = true;

  constructor(
    private sessionId: string,
    private client: NovaSonicBidirectionalStreamClient
  ) { }

  // Register event handlers for this specific session
  public onEvent(eventType: string, handler: (data: any) => void): StreamSession {
    this.client.registerEventHandler(this.sessionId, eventType, handler);
    return this; // For chaining
  }

  public async setupPromptStart(): Promise<void> {
    this.client.setupPromptStartEvent(this.sessionId);
  }

  public async setupSystemPrompt(
    textConfig: typeof DefaultTextConfiguration = DefaultTextConfiguration,
    systemPromptContent: string = DefaultSystemPrompt): Promise<void> {
    this.client.setupSystemPromptEvent(this.sessionId, textConfig, systemPromptContent);
  }

  public async setupStartAudio(
    audioConfig: typeof DefaultAudioInputConfiguration = DefaultAudioInputConfiguration
  ): Promise<void> {
    this.client.setupStartAudioEvent(this.sessionId, audioConfig);
  }


  // Stream audio for this session
  public async streamAudio(audioData: Buffer): Promise<void> {
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
  private async processAudioQueue() {
    if (this.isProcessingAudio || this.audioBufferQueue.length === 0 || !this.isActive) return;

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
    } finally {
      this.isProcessingAudio = false;

      // If there are still items in the queue, schedule the next processing using setTimeout
      if (this.audioBufferQueue.length > 0 && this.isActive) {
        setTimeout(() => this.processAudioQueue(), 0);
      }
    }
  }
  // Get session ID
  public getSessionId(): string {
    return this.sessionId;
  }

  public async endAudioContent(): Promise<void> {
    if (!this.isActive) return;
    await this.client.sendContentEnd(this.sessionId);
  }

  public async endPrompt(): Promise<void> {
    if (!this.isActive) return;
    await this.client.sendPromptEnd(this.sessionId);
  }

  public async close(): Promise<void> {
    if (!this.isActive) return;

    this.isActive = false;
    this.audioBufferQueue = []; // Clear any pending audio

    await this.client.sendSessionEnd(this.sessionId);
    console.log(`Session ${this.sessionId} close completed`);
  }
}

// Session data type
interface SessionData {
  queue: Array<any>;
  queueSignal: Subject<void>;
  closeSignal: Subject<void>;
  responseSubject: Subject<any>;
  toolUseContent: any;
  toolUseId: string;
  toolName: string;
  responseHandlers: Map<string, (data: any) => void>;
  promptName: string;
  inferenceConfig: InferenceConfig;
  isActive: boolean;
  isPromptStartSent: boolean;
  isAudioContentStartSent: boolean;
  audioContentId: string;
}

export class NovaSonicBidirectionalStreamClient {
  private bedrockRuntimeClient: BedrockRuntimeClient;
  private inferenceConfig: InferenceConfig;
  private activeSessions: Map<string, SessionData> = new Map();
  private sessionLastActivity: Map<string, number> = new Map();
  private sessionCleanupInProgress = new Set<string>();


  constructor(config: NovaSonicBidirectionalStreamClientConfig) {
    const http2Client = new NodeHttp2Handler({
      requestTimeout: 300000,
      sessionTimeout: 300000,
      disableConcurrentStreams: false,
      maxConcurrentStreams: 20,
      ...config.requestHandlerConfig,
    });

    if (!config.clientConfig.credentials) {
      throw new Error("No credentials provided");
    }

    this.bedrockRuntimeClient = new BedrockRuntimeClient({
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

  public isSessionActive(sessionId: string): boolean {
    const session = this.activeSessions.get(sessionId);
    return !!session && session.isActive;
  }

  public getActiveSessions(): string[] {
    return Array.from(this.activeSessions.keys());
  }

  public getLastActivityTime(sessionId: string): number {
    return this.sessionLastActivity.get(sessionId) || 0;
  }

  private updateSessionActivity(sessionId: string): void {
    this.sessionLastActivity.set(sessionId, Date.now());
  }

  public isCleanupInProgress(sessionId: string): boolean {
    return this.sessionCleanupInProgress.has(sessionId);
  }


  // Create a new streaming session
  public createStreamSession(sessionId: string = randomUUID(), config?: NovaSonicBidirectionalStreamClientConfig): StreamSession {
    if (this.activeSessions.has(sessionId)) {
      throw new Error(`Stream session with ID ${sessionId} already exists`);
    }

    const session: SessionData = {
      queue: [],
      queueSignal: new Subject<void>(),
      closeSignal: new Subject<void>(),
      responseSubject: new Subject<any>(),
      toolUseContent: null,
      toolUseId: "",
      toolName: "",
      responseHandlers: new Map(),
      promptName: randomUUID(),
      inferenceConfig: config?.inferenceConfig ?? this.inferenceConfig,
      isActive: true,
      isPromptStartSent: false,
      isAudioContentStartSent: false,
      audioContentId: randomUUID()
    };

    this.activeSessions.set(sessionId, session);

    return new StreamSession(sessionId, this);
  }

private async processToolUse(toolName: string, toolUseContent: object): Promise<Object> {
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
            return checkDoctorAvailability(toolUseContent);
            
        case "check_appointments":
            console.log(`Checking appointments: ${JSON.stringify(toolUseContent)}`);
            return checkAppointments(toolUseContent);
            
        case "schedule_appointment":
            console.log(`Scheduling appointment: ${JSON.stringify(toolUseContent)}`);
            return scheduleAppointment(toolUseContent);
            
        case "cancel_appointment":
            console.log(`Cancelling appointment: ${JSON.stringify(toolUseContent)}`);
            return cancelAppointment(toolUseContent);
            
        default:
            console.log(`Tool ${tool} not supported`)
            throw new Error(`Tool ${tool} not supported`);
    }
}

  private generateGreeting(toolUseContent: any): Object {
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
      } catch (error) {
          console.error("Error generating greeting:", error);
          return {
              greeting: "Hello! I'm Ada, your Health Guide Assistant. How can I help you today?",
              error: String(error)
          };
      }
  }

  private generateSafetyResponse(toolUseContent: any): Object {
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
      } catch (error) {
          console.error("Error generating safety response:", error);
          return {
              response: "I'm unable to provide information on this topic. I can only help with general health information about common conditions, preventive care, and appointment scheduling.",
              error: String(error)
          };
      }
  }

  private async queryPatientDatabase(query: string, filters: any = {}): Promise<Object> {
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

  private async queryHealthKnowledgeBase(query: string, numberOfResults: number = 3): Promise<Object> {
    // Create a client instance
    const kbClient = new BedrockKnowledgeBaseClient();

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

    } catch (error) {
      console.error("Error:", error);
      return {};
    }
  }

  private async parseToolUseContent(toolUseContent: any): Promise<{ query: string; maxResults: number; } | null> {
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
    } catch (error) {
      console.error("Failed to parse tool use content:", error);
      return null;
    }
  }

  // Stream audio for a specific session
  public async initiateSession(sessionId: string): Promise<void> {
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

      const response = await this.bedrockRuntimeClient.send(
        new InvokeModelWithBidirectionalStreamCommand({
          modelId: "amazon.nova-sonic-v1:0",
          body: asyncIterable,
        })
      );

      console.log(`Stream established for session ${sessionId}, processing responses...`);

      // Process responses for this session
      await this.processResponseStream(sessionId, response);

    } catch (error) {
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
  private dispatchEventForSession(sessionId: string, eventType: string, data: any): void {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;

    const handler = session.responseHandlers.get(eventType);
    if (handler) {
      try {
        handler(data);
      } catch (e) {
        console.error(`Error in ${eventType} handler for session ${sessionId}: `, e);
      }
    }

    // Also dispatch to "any" handlers
    const anyHandler = session.responseHandlers.get('any');
    if (anyHandler) {
      try {
        anyHandler({ type: eventType, data });
      } catch (e) {
        console.error(`Error in 'any' handler for session ${sessionId}: `, e);
      }
    }
  }

  private createSessionAsyncIterable(sessionId: string): AsyncIterable<InvokeModelWithBidirectionalStreamInput> {

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
          next: async (): Promise<IteratorResult<InvokeModelWithBidirectionalStreamInput>> => {
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
                    firstValueFrom(session.queueSignal.pipe(take(1))),
                    firstValueFrom(session.closeSignal.pipe(take(1))).then(() => {
                      throw new Error("Stream closed");
                    })
                  ]);
                } catch (error) {
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
                    console.error(`Error on event close`, error)
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
            } catch (error) {
              console.error(`Error in session ${sessionId} iterator: `, error);
              session.isActive = false;
              return { value: undefined, done: true };
            }
          },

          return: async (): Promise<IteratorResult<InvokeModelWithBidirectionalStreamInput>> => {
            console.log(`Iterator return () called for session ${sessionId}`);
            session.isActive = false;
            return { value: undefined, done: true };
          },

          throw: async (error: any): Promise<IteratorResult<InvokeModelWithBidirectionalStreamInput>> => {
            console.log(`Iterator throw () called for session ${sessionId} with error: `, error);
            session.isActive = false;
            throw error;
          }
        };
      }
    };
  }

  // Process the response stream from AWS Bedrock
  private async processResponseStream(sessionId: string, response: any): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;

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
              } else if (jsonResponse.event?.textOutput) {
                this.dispatchEvent(sessionId, 'textOutput', jsonResponse.event.textOutput);
              } else if (jsonResponse.event?.audioOutput) {
                this.dispatchEvent(sessionId, 'audioOutput', jsonResponse.event.audioOutput);
              } else if (jsonResponse.event?.toolUse) {
                this.dispatchEvent(sessionId, 'toolUse', jsonResponse.event.toolUse);

                // Store tool use information for later
                session.toolUseContent = jsonResponse.event.toolUse;
                session.toolUseId = jsonResponse.event.toolUse.toolUseId;
                session.toolName = jsonResponse.event.toolUse.toolName;
              } else if (jsonResponse.event?.contentEnd &&
                jsonResponse.event?.contentEnd?.type === 'TOOL') {

                // Process tool use
                console.log(`Processing tool use for session ${sessionId}`);
                this.dispatchEvent(sessionId, 'toolEnd', {
                  toolUseContent: session.toolUseContent,
                  toolUseId: session.toolUseId,
                  toolName: session.toolName
                });

                console.log("calling tooluse");
                console.log("tool use content : ", session.toolUseContent)
                // function calling
                const toolResult = await this.processToolUse(session.toolName, session.toolUseContent);

                // Send tool result
                this.sendToolResult(sessionId, session.toolUseId, toolResult);

                // Also dispatch event about tool result
                this.dispatchEvent(sessionId, 'toolResult', {
                  toolUseId: session.toolUseId,
                  result: toolResult
                });
              } else if (jsonResponse.event?.contentEnd) {
                this.dispatchEvent(sessionId, 'contentEnd', jsonResponse.event.contentEnd);
              }
              else {
                // Handle other events
                const eventKeys = Object.keys(jsonResponse.event || {});
                console.log(`Event keys for session ${sessionId}: `, eventKeys)
                console.log(`Handling other events`)
                if (eventKeys.length > 0) {
                  this.dispatchEvent(sessionId, eventKeys[0], jsonResponse.event);
                } else if (Object.keys(jsonResponse).length > 0) {
                  this.dispatchEvent(sessionId, 'unknown', jsonResponse);
                }
              }
            } catch (e) {
              console.log(`Raw text response for session ${sessionId}(parse error): `, textResponse);
            }
          } catch (e) {
            console.error(`Error processing response chunk for session ${sessionId}: `, e);
          }
        } else if (event.modelStreamErrorException) {
          console.error(`Model stream error for session ${sessionId}: `, event.modelStreamErrorException);
          this.dispatchEvent(sessionId, 'error', {
            type: 'modelStreamErrorException',
            details: event.modelStreamErrorException
          });
        } else if (event.internalServerException) {
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

    } catch (error) {
      console.error(`Error processing response stream for session ${sessionId}: `, error);
      this.dispatchEvent(sessionId, 'error', {
        source: 'responseStream',
        message: 'Error processing response stream',
        details: error instanceof Error ? error.message : String(error)
      });
    }
  }

  // Add an event to a session's queue
  private addEventToSessionQueue(sessionId: string, event: any): void {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.isActive) return;

    this.updateSessionActivity(sessionId);
    session.queue.push(event);
    session.queueSignal.next();
  }


  // Set up initial events for a session
  private setupSessionStartEvent(sessionId: string): void {
    console.log(`Setting up initial events for session ${sessionId}...`);
    const session = this.activeSessions.get(sessionId);
    if (!session) return;

    // Session start event
    this.addEventToSessionQueue(sessionId, {
      event: {
        sessionStart: {
          inferenceConfiguration: session.inferenceConfig
        }
      }
    });
  }

  
  public setupPromptStartEvent(sessionId: string): void {
      console.log(`Setting up prompt start event for session ${sessionId}...`);
      const session = this.activeSessions.get(sessionId);
      if (!session) return;
      
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
            audioOutputConfiguration: DefaultAudioOutputConfiguration,
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
                      json: KnowledgeBaseToolSchema
                    }
                  }
                },
                {
                  toolSpec: {
                    name: "greeting",
                    description: "Introduces yourself and the Health Guide Assistant to the user with an appropriate greeting.",
                    inputSchema: {
                      json: GreetingToolSchema
                    }
                  }
                },
                {
                  toolSpec: {
                    name: "safety_response",
                    description: "Provides a safe response when users ask about topics outside the assistant's domain or request inappropriate medical advice.",
                    inputSchema: {
                      json: SafetyToolSchema
                    }
                  }
                },
                {
                  toolSpec: {
                    name: "check_doctor_availability",
                    description: "Use this tool to check the availability of doctors, either by ID or specialty. ONLY use after collecting information about which doctor or specialty the patient is interested in.",
                    inputSchema: {
                      json: CheckDoctorAvailabilitySchema
                    }
                  }
                },
                {
                  toolSpec: {
                    name: "check_appointments",
                    description: "Use this tool to check existing appointments for a doctor or patient. You must have either a doctor ID or a patient name to use this tool.",
                    inputSchema: {
                      json: CheckAppointmentsSchema
                    }
                  }
                },
                {
                  toolSpec: {
                    name: "schedule_appointment",
                    description: "Use this tool ONLY after collecting ALL required information: patient name, doctor ID, date, time, and reason. Always check availability before scheduling.",
                    inputSchema: {
                      json: ScheduleAppointmentSchema
                    }
                  }
                },
                {
                  toolSpec: {
                    name: "cancel_appointment",
                    description: "Use this tool to cancel an existing appointment. You must have the appointment ID. If the user doesn't know their appointment ID, use check_appointments first.",
                    inputSchema: {
                      json: CancelAppointmentSchema
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

  public setupSystemPromptEvent(sessionId: string,
    textConfig: typeof DefaultTextConfiguration = DefaultTextConfiguration,
    systemPromptContent: string = DefaultSystemPrompt
  ): void {
    console.log(`Setting up systemPrompt events for session ${sessionId}...`);
    const session = this.activeSessions.get(sessionId);
    if (!session) return;
    // Text content start
    const textPromptID = randomUUID();
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

  public setupStartAudioEvent(
    sessionId: string,
    audioConfig: typeof DefaultAudioInputConfiguration = DefaultAudioInputConfiguration
  ): void {
    console.log(`Setting up startAudioContent event for session ${sessionId}...`);
    const session = this.activeSessions.get(sessionId);
    if (!session) return;

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
  public async streamAudioChunk(sessionId: string, audioData: Buffer): Promise<void> {
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
  private async sendToolResult(sessionId: string, toolUseId: string, result: any): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    console.log("inside tool result")
    if (!session || !session.isActive) return;

    console.log(`Sending tool result for session ${sessionId}, tool use ID: ${toolUseId}`);
    const contentId = randomUUID();

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

  public async sendContentEnd(sessionId: string): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.isAudioContentStartSent) return;

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

  public async sendPromptEnd(sessionId: string): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.isPromptStartSent) return;

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

  public async sendSessionEnd(sessionId: string): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;

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
  public registerEventHandler(sessionId: string, eventType: string, handler: (data: any) => void): void {
    const session = this.activeSessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    session.responseHandlers.set(eventType, handler);
  }

  // Dispatch an event to registered handlers
  private dispatchEvent(sessionId: string, eventType: string, data: any): void {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;

    const handler = session.responseHandlers.get(eventType);
    if (handler) {
      try {
        handler(data);
      } catch (e) {
        console.error(`Error in ${eventType} handler for session ${sessionId}:`, e);
      }
    }

    // Also dispatch to "any" handlers
    const anyHandler = session.responseHandlers.get('any');
    if (anyHandler) {
      try {
        anyHandler({ type: eventType, data });
      } catch (e) {
        console.error(`Error in 'any' handler for session ${sessionId}:`, e);
      }
    }
  }

  public async closeSession(sessionId: string): Promise<void> {
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
    } catch (error) {
      console.error(`Error during closing sequence for session ${sessionId}:`, error);

      // Ensure cleanup happens even if there's an error
      const session = this.activeSessions.get(sessionId);
      if (session) {
        session.isActive = false;
        this.activeSessions.delete(sessionId);
        this.sessionLastActivity.delete(sessionId);
      }
    } finally {
      // Always clean up the tracking set
      this.sessionCleanupInProgress.delete(sessionId);
    }
  }

  // Same for forceCloseSession:
  public forceCloseSession(sessionId: string): void {
    if (this.sessionCleanupInProgress.has(sessionId) || !this.activeSessions.has(sessionId)) {
      console.log(`Session ${sessionId} already being cleaned up or not active`);
      return;
    }

    this.sessionCleanupInProgress.add(sessionId);
    try {
      const session = this.activeSessions.get(sessionId);
      if (!session) return;

      console.log(`Force closing session ${sessionId}`);

      // Immediately mark as inactive and clean up resources
      session.isActive = false;
      session.closeSignal.next();
      session.closeSignal.complete();
      this.activeSessions.delete(sessionId);
      this.sessionLastActivity.delete(sessionId);

      console.log(`Session ${sessionId} force closed`);
    } finally {
      this.sessionCleanupInProgress.delete(sessionId);
    }
  }

}