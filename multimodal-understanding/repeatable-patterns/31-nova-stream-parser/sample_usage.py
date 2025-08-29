import boto3
import json
from NovaStreamParser.nova_parsed_event_stream import( 
    parse_invoke_model_with_response_stream,
    parse_converse_stream
)


@parse_converse_stream("thinking")
def process_converse_stream(response_stream):
    return response_stream


@parse_invoke_model_with_response_stream(target_tag_name="thinking")
def process_invoke_model_with_response_stream(response_stream):
    return response_stream


system_text = """
You are a friend and helpful assistant that answers questions about the weather. 
The user and you will engage in a dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios.
You can use the tool to get the weather for a city.
You can use the tool multiple times to get the weather for multiple cities.
You can use the tool to get the weather for multiple cities at once.
"""
postamble = "\nWhen reasoning on your replies, place the reasoning in <thinking</thinking> tags."
system_prompt = [{ "text": system_text + postamble }]
inference_config = { "maxTokens": 1024, "topP": 0.9, "temperature": 0.7 }

tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": "getWeather",
                    "description": "A tool to get the weather",
                    "inputSchema": {
                        "json": {
                            "type" : "object",
                            "properties": {
                                "city": {
                                    "type": "string",
                                    "description": "A tool to get the weather for a particular city."
                                }
                            },
                            "required" : ["city"]
                        }
                    }
                }
            }
        ],
        "toolChoice" : {
            "auto" : {}
        }
    }

messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": "Hi what's the weather?"
                }
            ]
        },
        {
            "role": "assistant",
            "content" : [
                {
                    "text": "Hi there! Could you please tell me which city you're interested in?"
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "text": "Yes, I'm in Seattle, Washington"
                }
            ]
        },
        {
            "role": "assistant",
            "content" : [
                {
                    "text" : "<thinking>I need to get the weather for Seattle, Washington.</thinking>"
                },
                {
                    "toolUse": {
                        'name': 'getWeather',
                        'toolUseId': '4356828f-a39c-4e4e-b9d5-dcf6027a4c7a',
                        'input': {
                            'city': 'Seattle, Washington'
                        }
                    }
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "text": "Actually, I'm in Tacoma, Washington."
                }
            ]
        }
    ]

body = {
    "system": system_prompt,
    "inferenceConfig": inference_config,
    "toolConfig": tool_config,
    "messages": messages
}

LITE_MODEL_ID = "us.amazon.nova-lite-v1:0"
modelId = LITE_MODEL_ID

# Create a Bedrock Runtime client in the AWS Region of your choice.
client = boto3.client("bedrock-runtime", region_name="us-east-1")

print(" ----------- Invoke Model Stream -------------")
# EG - Create wrapper class around client???
response = client.invoke_model_with_response_stream(
    modelId=modelId,
    body=json.dumps(body)
)

response_stream = response.get('body')
# for event in response_stream:
#     print(event)


for event in process_invoke_model_with_response_stream(response_stream):
    print(event)

print(" ----------- Converse Stream -------------")

response = client.converse_stream(
    modelId=LITE_MODEL_ID, 
    messages=body["messages"], 
    system=body["system"], 
    inferenceConfig=body["inferenceConfig"],
    toolConfig=body["toolConfig"]
)

response_stream = response.get('stream')
for event in process_converse_stream(response_stream):
    print(event)