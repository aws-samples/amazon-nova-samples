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
                { "toolSpec": {
                    "name": "getLocationTool",
                    "description": "Search for places, addresses.",
                    "inputSchema": {
                        "json": "{\"type\": \"object\", \"properties\": {\"tool\": {\"type\": \"string\", \"description\": \"The function name to search the location service. One of: search_places\"}, \"query\": {\"type\": \"string\", \"description\": \"The search query to find relevant information\"}}, \"required\": [\"tool\",\"query\"]}"
                    }
                }}
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
        "name": "Bedrock Agents - booking",
        "description": "Simple demo profile with basic system prompt and toolUse like getDateTime",
        "voiceId": "matthew",
        "systemPrompt": `
            You are a helpful virtual assistant that specializes in handling reservations.
            Your goal is to guide the customer step by step to successfully make a reservation.
            Always be polite, professional, and concise.
            If information is missing, ask clarifying questions (e.g., date, time, number of people, special requests).
            Once all details are collected, confirm the reservation back to the customer clearly.
            If the customer asks for something outside reservations, politely redirect them back to the reservation process.
        `,
        "toolConfig": {
            "tools": [
                {
                    "toolSpec": {
                        "name": "getBookingDetails",
                        "description": "Manage bookings and reservations: create, get, update, delete, list, or find bookings by customer name. For update_booking, you can update by booking_id or by customer_name.",
                        "inputSchema": {
                        "json": "{\"type\":\"object\",\"properties\":{\"query\":{\"type\":\"string\",\"description\":\"The request about booking, reservation\"}},\"required\":[]}"
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

const Voices = [
    { label: "Matthew (English US)", value: "matthew" },
    { label: "Tiffany (English US)", value: "tiffany" },
    { label: "Amy (English GB)", value: "amy" },
    { label: "Ambre (French)", value: "ambre" },
    { label: "Florian (French)", value: "florian" },
    { label: "Beatrice (Italian)", value: "beatrice" },
    { label: "Lorenzo (Italian)", value: "lorenzo" },
    { label: "Greta (German)", value: "greta" },
    { label: "Lennart (German)", value: "lennart" },
    { label: "Lupe (Spanish)", value: "lupe"},
    { label: "Carlos (Spanish)", value: "carlos"},
]

export {DemoProfiles, Voices};