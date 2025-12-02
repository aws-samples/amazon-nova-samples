const DemoProfiles = [
    {
        "name": "Default - get current time and RAG",
        "description": "Simple demo profile with basic system prompt and toolUse like getDateTime",
        "voiceId": "matthew",
        "systemPrompt": "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios.",
        "toolConfig": {
            "tools": [
                {
                    "toolSpec": {
                        "name": "getDateTool",
                        "description": "get information about the date and time",
                        "inputSchema": {
                            "json": "{\"type\":\"object\",\"properties\":{},\"required\":[]}"
                        }
                    }
                },
                {
                    "toolSpec": {
                        "name": "getKbTool",
                        "description": "get information about Amazon Nova, Nova Sonic and Amazon foundation models",
                        "inputSchema": {
                            "json": "{\"type\":\"object\",\"properties\":{\"query\":{\"type\":\"string\",\"description\":\"The question about Amazon Nova\"}},\"required\":[]}"
                        }
                    }
                },
                {
                    "toolSpec": {
                        "name": "getSlowTool",
                        "description": "get information about the weather information of certain location",
                        "inputSchema": {
                            "json": "{\"type\":\"object\",\"properties\":{\"query\":{\"type\":\"string\",\"description\":\"The question\"}},\"required\":[]}"
                        }
                    }
                }
            ]
        }
    },
    {
        "name": "MCP - get location",
        "description": "Simple demo profile with basic system prompt and toolUse like getDateTime",
        "voiceId": "matthew",
        "systemPrompt": "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios.",
        "toolConfig": {
            "tools": [
                {
                    "toolSpec": {
                        "name": "getLocationTool",
                        "description": "Search for places, addresses.",
                        "inputSchema": {
                            "json": "{\"type\": \"object\", \"properties\": {\"tool\": {\"type\": \"string\", \"description\": \"The function name to search the location service. One of: search_places\"}, \"query\": {\"type\": \"string\", \"description\": \"The search query to find relevant information\"}}, \"required\": [\"tool\",\"query\"]}"
                        }
                    }
                }
            ]
        }
    },
    {
        "name": "Strands Agents - get weather",
        "description": "Simple demo profile with basic system prompt and toolUse like getDateTime",
        "voiceId": "matthew",
        "systemPrompt": "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios.",
        "toolConfig": {
            "tools": [{
                "toolSpec": {
                    "name": "externalAgent",
                    "description": "Get weather information for specific locations.",
                    "inputSchema": {
                        "json": "{\"type\":\"object\",\"properties\":{\"query\":{\"type\":\"string\",\"description\":\"The search query to find relevant information\"}},\"required\":[\"tool\",\"query\"]}"
                    }
                }
            }
            ]
        }
    },
    {
        "name": "Customer Service - Finance",
        "description": "A sample voice assistant for customer service, built with a multi-agent architecture.",
        "voiceId": "tiffany",
        "systemPrompt": `You are a helpful customer service assistant for a bank. Follow this structured flow in every interaction:
                1. Greeting
                    "Hello! Welcome to Any Bank. Could I please get your name to start?"
                2. Personalization
                    Use the user's name naturally in the conversation once obtained.
                3. Inquiry Handling
                    "Thank you, [User's Name]. How may I assist you today? I can help with banking and mortgage-related inquiries."
                    If the user hasn't provided their account ID yet and asks about their account balance or mortgage, prompt: "To proceed, could you please provide your account ID?"
                    Convert numeric IDs to words (e.g., 123 becomes "one two three").
                    For banking inquiries, call [ac_bank_agent].
                    For mortgage inquiries, call [ac_mortgage_agent].
                    Do not re-ask for the account ID once it's been provided.
                4. Important Notice
                    If the user asks about non-banking or non-mortgage topics, respond: "Sorry, I can only help with banking or mortgage-related inquiries."
                
                ## Example Interaction Flows
                ### Example 1: Account Balance Inquiry
                Assistant: Hello! Welcome to Any Bank. Could I please get your name to start?
                User: My name is Jamie.
                Assistant: Thank you, Jamie. How may I assist you today?
                User: I need to check my account balance.
                Assistant: To proceed, could you please provide your account ID?
                User: It's 123.
                Assistant: Thank you. Please hold on while I retrieve your account balance.
                call [ac_bank_agent]
                Assistant: Jamie, your current balance is USD 1600.00 with pending transactions of USD 56.25.

                ### Example 2: Mortgage Inquiry
                Assistant: Hello! Welcome to Any Bank. Could I please get your name to start?
                User: I'm Sarah.
                Assistant: Thank you, Sarah. How may I assist you today?
                User: Can you tell me about mortgage refinancing options?
                Assistant: Absolutely, Sarah, here are your mortgage refinance options: Your current mortgage balance is $245,000 with an interest rate of 4.85% and a monthly payment. 
            `,
        "toolConfig": {
            "tools": [
                {
                    "toolSpec": {
                        "name": "ac_bank_agent",
                        "description": `Use this tool whenever the customer asks about their **bank account balance** or **bank statement**.  
                                It should be triggered for queries such as:  
                                - "What’s my balance?"  
                                - "How much money do I have in my account?"  
                                - "Can I see my latest bank statement?"  
                                - "Show me my account summary."`,
                        "inputSchema": {
                            "json": JSON.stringify({
                                "type": "object",
                                "properties": {
                                    "accountId": {
                                        "type": "string",
                                        "description": "This is a user input. It is the bank account Id which is a numeric number."
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "The inquiry to the bank agent such as check account balance, get statement etc."
                                    }
                                },
                                "required": [
                                    "accountId", "query"
                                ]
                            })
                        }
                    }
                },
                {
                    "toolSpec": {
                        "name": "ac_mortgage_agent",
                        "description": `Use this tool whenever the customer has a **mortgage-related inquiry**.  
                                        It should be triggered for queries such as:  
                                        - "What are the current mortgage rates?"  
                                        - "Can I refinance my mortgage?"  
                                        - "How do I apply for a mortgage?"  
                                        - "Tell me about mortgage repayment options.`,
                        "inputSchema": {
                            "json": JSON.stringify({
                                "type": "object",
                                "properties": {
                                    "accountId": {
                                        "type": "string",
                                        "description": "This is a user input. It is the bank account Id which is a numeric number."
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "The inquiry to the mortgage agent such as mortgage rates, refinance, bank reference letter, repayment etc."
                                    }
                                },
                                "required": ["accountId", "query"]
                            })
                        }
                    }
                }
            ]
        }
    }
];

const VoicesByLanguage = {
    "English": {
        flag: "🇺🇸🇬🇧🇦🇺",
        voices: [
            {
                label: "Tiffany",
                value: "tiffany",
                locale: "en-US",
                accent: "US",
                gender: "Female",
                polyglot: true,
                polyglotLanguages: "English, French, Italian, German, Spanish, Portuguese, Hindi"
            },
            {
                label: "Matthew",
                value: "matthew",
                locale: "en-US",
                accent: "US",
                gender: "Male",
                polyglot: true,
                polyglotLanguages: "English, French, Italian, German, Spanish, Portuguese, Hindi"
            },
            {
                label: "Amy",
                value: "amy",
                locale: "en-UK",
                accent: "UK",
                gender: "Female",
                polyglot: false
            },
            {
                label: "Olivia",
                value: "olivia",
                locale: "en-AU",
                accent: "AU",
                gender: "Female",
                polyglot: false
            }
        ]
    },
    "French": {
        flag: "🇫🇷",
        voices: [
            {
                label: "Florian",
                value: "florian",
                locale: "fr-FR",
                accent: "FR",
                gender: "Male",
                polyglot: true,
                polyglotLanguages: "with English"
            },
            {
                label: "Ambre",
                value: "ambre",
                locale: "fr-FR",
                accent: "FR",
                gender: "Female",
                polyglot: true,
                polyglotLanguages: "with English"
            }
        ]
    },
    "Italian": {
        flag: "🇮🇹",
        voices: [
            {
                label: "Lorenzo",
                value: "lorenzo",
                locale: "it-IT",
                accent: "IT",
                gender: "Male",
                polyglot: true,
                polyglotLanguages: "with English"
            },
            {
                label: "Beatrice",
                value: "beatrice",
                locale: "it-IT",
                accent: "IT",
                gender: "Female",
                polyglot: true,
                polyglotLanguages: "with English"
            }
        ]
    },
    "German": {
        flag: "🇩🇪",
        voices: [
            {
                label: "Lennart",
                value: "lennart",
                locale: "de-DE",
                accent: "DE",
                gender: "Male",
                polyglot: true,
                polyglotLanguages: "with English"
            },
            {
                label: "Tina",
                value: "tina",
                locale: "de-DE",
                accent: "DE",
                gender: "Female",
                polyglot: true,
                polyglotLanguages: "with English"
            },
            {
                label: "Greta",
                value: "greta",
                locale: "de-DE",
                accent: "DE",
                gender: "Female",
                polyglot: true,
                polyglotLanguages: "with English"
            }
        ]
    },
    "Spanish": {
        flag: "🇪🇸🇺🇸",
        voices: [
            {
                label: "Carlos",
                value: "carlos",
                locale: "en-US/es-US",
                accent: "US/ES",
                gender: "Male",
                polyglot: true,
                polyglotLanguages: "with English"
            },
            {
                label: "Lupe",
                value: "lupe",
                locale: "en-US/es-US",
                accent: "US/ES",
                gender: "Female",
                polyglot: true,
                polyglotLanguages: "with English"
            }
        ]
    },
    "Portuguese": {
        flag: "🇧🇷",
        voices: [
            {
                label: "Carolina",
                value: "carolina",
                locale: "pt-BR",
                accent: "BR",
                gender: "Female",
                polyglot: true,
                polyglotLanguages: "with English"
            },
            {
                label: "Leo",
                value: "leo",
                locale: "pt-BR",
                accent: "BR",
                gender: "Male",
                polyglot: true,
                polyglotLanguages: "with English"
            }
        ]
    },
    "Hindi": {
        flag: "🇮🇳",
        voices: [
            {
                label: "Kiara",
                value: "kiara",
                locale: "en-IN/hi-IN",
                accent: "IN",
                gender: "Female",
                polyglot: true,
                polyglotLanguages: "with English"
            },
            {
                label: "Arjun",
                value: "arjun",
                locale: "en-IN/hi-IN",
                accent: "IN",
                gender: "Male",
                polyglot: true,
                polyglotLanguages: "with English"
            }
        ]
    }
};

// Flatten voices for backward compatibility
const Voices = Object.values(VoicesByLanguage).flatMap(lang =>
    lang.voices.map(voice => ({
        label: `${voice.label} (${voice.accent})`,
        value: voice.value,
        ...voice
    }))
);

export { DemoProfiles, Voices, VoicesByLanguage };