export const SonicLanguages = [
    { label: "American English - Matthew", value: "matthew" },
    { label: "American English - Tiffany", value: "tiffany" },
    { label: "British English - Amy", value: "amy" },
    { label: "French - Florian", value: "florian" },
    { label: "French - Ambre", value: "ambre" },
    { label: "Italian - Lorenzo", value: "lorenzo" },
    { label: "Italian - Beatrice", value: "beatrice" },
    { label: "German - Lennart", value: "lennart" },
    { label: "German - Greta", value: "greta" },
    { label: "Spanish - Carlos", value: "carlos" },
    { label: "Spanish - Lupe", value: "lupe" },
];

export class SonicEvent {
  static DEFAULT_INFER_CONFIG = {
    maxTokens: 1024,
    topP: 0.95,
    temperature: 0.6,
  };

  static DEFAULT_SYSTEM_PROMPT = "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios. If you are asked to stop, only answer with 'OK' and nothing more.";

  static DEFAULT_AUDIO_INPUT_CONFIG = {
    mediaType: "audio/lpcm",
    sampleRateHertz: 16000,
    sampleSizeBits: 16,
    channelCount: 1,
    audioType: "SPEECH",
    encoding: "base64"
  };

  static DEFAULT_AUDIO_OUTPUT_CONFIG = {
    mediaType: "audio/lpcm",
    sampleRateHertz: 24000,
    sampleSizeBits: 16,
    channelCount: 1,
    voiceId: "matthew",
    encoding: "base64",
    audioType: "SPEECH"
  };

  static DEFAULT_TOOL_CONFIG = {
    tools: [
      {
      toolSpec: {
        name: "getDateTool",
        description: "get information about the date and time",
        inputSchema: {
          json: JSON.stringify({
              "type": "object",
              "properties": {},
              "required": []
              }
          )
        }
      }
    },
    {
      toolSpec: {
        name: "getKbTool",
        description: "get information about Amazon Nova, Nova Sonic and Amazon foundation models",
        inputSchema: {
          json: JSON.stringify({
              "type": "object",
              "properties": {
                "query": {
                  "type": "string",
                  "description": "The question about Amazon Nova"
                }},
              "required": []
            }
          )
        }
      }
    },
    {
      toolSpec: {
        name: "getLocationTool",
        description: "Search for places, addresses, or nearby points of interest, and access detailed information about specific locations.",
        inputSchema: {
          json: JSON.stringify({
              "type": "object",
              "properties": {
                "tool": {
                  "type": "string",
                  "description": "The function name to search the location service. One of: search_places, get_place, search_nearby, reverse_geocode",
                },
                "query": {
                  "type": "string",
                  "description": "The search query to find relevant information"
                }
              },
              "required": ["query"]
            }
          )
        }
      }
    },
    {
      toolSpec: {
          name: "locateMe",
          description: "Get my position. Locate Me with a physical address with approximate longitude and latitude. Might need to be called multiple times to improve location estimate accuracy.",
          inputSchema: {
              json: JSON.stringify({
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "publicIpAddress": {
                        "type": "string",
                        "description": "Public IP address"
                    },
                    "geoJson": {
                        "type": "string",
                        "description": "GeoJSON with longitude and latitude"
                    }
                }
            })
          }
      }
    },
    {
      toolSpec: {
        name: "externalAgent",
        description: "Get weather information for specific locations.",
        inputSchema: {
          json: JSON.stringify({
              "type": "object",
              "properties": {
                "query": {
                  "type": "string",
                  "description": "The search query to find relevant information"
                }
              },
              "required": ["query"]
            }
          )
        }
      }
    },
    {
      toolSpec: {
        name: "getBookingDetails",
        description: "Manage bookings and reservations: create, get, update, delete, list, or find bookings by customer name. For update_booking, you can update by booking_id or by customer_name. If booking_id is not provided, all bookings for the given customer_name will be updated.",
        inputSchema: {
          json: JSON.stringify({
              "type": "object",
              "properties": {
                "query": {
                  "type": "string",
                  "description": "The request about booking, reservation"
                }},
              "required": []
            }
          )
        }
      }
    }
  ]
  };

  static DEFAULT_CONVERSATION_HISTORY = [
    {
      "content": "hi there i would like to cancel my hotel reservation",
      "role": "USER"
    },
    {
      "content": "Hello! I'd be happy to assist you with cancelling your hotel reservation. To get started, could you please provide me with your full name and the check-in date for your reservation?",
      "role": "ASSISTANT"
    },
    {
      "content": "yeah so my name is don smith",
      "role": "USER"
    },
    {
      "content": "Thank you, Don. Now, could you please provide me with the check-in date for your reservation?",
      "role": "ASSISTANT"
    },
    {
      "content": "yes so um let me check just a second",
      "role": "USER"
    },
    {
      "content": "Take your time, Don. I'll be here when you're ready.",
      "role": "ASSISTANT"
    }
  ];

  static sessionStart(inferenceConfig = SonicEvent.DEFAULT_INFER_CONFIG) {
    return { event: { sessionStart: { inferenceConfiguration: inferenceConfig } } };
  }

  static promptStart(promptName, audioOutputConfig = SonicEvent.DEFAULT_AUDIO_OUTPUT_CONFIG, toolConfig = SonicEvent.DEFAULT_TOOL_CONFIG) {
    return {
      event: {
        promptStart: {
          promptName: promptName,
          textOutputConfiguration: {
            mediaType: "text/plain"
          },
          audioOutputConfiguration: audioOutputConfig,

        toolUseOutputConfiguration: {
          mediaType: "application/json"
        },
        toolConfiguration: toolConfig
      }
      }
    }
  }

  static contentStartText(promptName, contentName, role="SYSTEM") {
    return {
      event: {
        contentStart: {
          promptName: promptName,
          contentName: contentName,
          type: "TEXT",
          interactive: true,
          role: role,
          textInputConfiguration: {
            mediaType: "text/plain"
          }
        }
      }
    }
  }

  static textInput(promptName, contentName, systemPrompt = SonicEvent.DEFAULT_SYSTEM_PROMPT) {
    return {
      event: {
        textInput: {
          promptName: promptName,
          contentName: contentName,
          content: systemPrompt
        }
      }
    }
  }

  static contentEnd(promptName, contentName) {
    return {
      event: {
        contentEnd: {
          promptName: promptName,
          contentName: contentName
        }
      }
    }
  }

  static contentStartAudio(promptName, contentName, audioInputConfig = SonicEvent.DEFAULT_AUDIO_INPUT_CONFIG) {
    return {
      event: {
        contentStart: {
          promptName: promptName,
          contentName: contentName,
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
    }
  }

  static audioInput(promptName, contentName, content) {
    return {
      event: {
        audioInput: {
          promptName,
          contentName,
          content,
        }
      }
    };
  }

  static contentStartTool(promptName, contentName, toolUseId) {
    return {
      event: {
        contentStart: {
          promptName,
          contentName,
          interactive: false,
          type: "TOOL",
          toolResultInputConfiguration: {
            toolUseId,
            type: "TEXT",
            textInputConfiguration: { mediaType: "text/plain" }
          }
        }
      }
    };
  }

  static textInputTool(promptName, contentName, content) {
    return {
      event: {
        textInput: {
          promptName,
          contentName,
          content,
          role: "TOOL"
        }
      }
    };
  }

  static promptEnd(promptName) {
    return {
      event: {
        promptEnd: {
          promptName
        }
      }
    };
  }

  static sessionEnd() {
    return { event: { sessionEnd: {} } };
  }

  static customStateUpdate(publicIpAddress=null, geolocationPosition=null) {
    return {
      event: {
        APP_CUSTOM_state_update: {
          publicIpAddress: publicIpAddress,
          geolocationPosition: geolocationPosition,
        }
      }
    };
  }
}
