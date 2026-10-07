"""Minimal test: can we connect to Bedrock and get a response?"""
import asyncio
import json
import os

from aws_sdk_bedrock_runtime.client import (
    BedrockRuntimeClient,
    InvokeModelWithBidirectionalStreamOperationInput,
)
from aws_sdk_bedrock_runtime.models import (
    InvokeModelWithBidirectionalStreamInputChunk,
    BidirectionalInputPayloadPart,
)
from aws_sdk_bedrock_runtime.config import Config
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver


MODEL_ID = "amazon.nova-2-sonic-v1:0"
REGION = "us-east-1"


async def send_event(stream, event_dict):
    event_json = json.dumps(event_dict)
    chunk = InvokeModelWithBidirectionalStreamInputChunk(
        value=BidirectionalInputPayloadPart(bytes_=event_json.encode("utf-8"))
    )
    await stream.input_stream.send(chunk)
    print(f"  Sent: {list(event_dict['event'].keys())[0]}", flush=True)


async def main():
    print("=== Bedrock Connection Test ===", flush=True)

    # Check env vars
    key = os.environ.get("AWS_ACCESS_KEY_ID", "")
    region = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("AWS_REGION", ""))
    print(f"AWS_ACCESS_KEY_ID: {'set (' + key[:4] + '...)' if key else 'NOT SET'}", flush=True)
    print(f"AWS_SECRET_ACCESS_KEY: {'set' if os.environ.get('AWS_SECRET_ACCESS_KEY') else 'NOT SET'}", flush=True)
    print(f"AWS_SESSION_TOKEN: {'set' if os.environ.get('AWS_SESSION_TOKEN') else 'NOT SET'}", flush=True)
    print(f"AWS_REGION env: {region or 'NOT SET'}", flush=True)
    print(flush=True)

    # Connect
    print("1. Creating client...", flush=True)
    config = Config(
        endpoint_uri=f"https://bedrock-runtime.{REGION}.amazonaws.com",
        region=REGION,
        aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
    )
    client = BedrockRuntimeClient(config=config)

    print("2. Opening stream...", flush=True)
    stream = await client.invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(model_id=MODEL_ID)
    )
    print("   Stream opened", flush=True)

    # Send minimal init sequence
    print("3. Sending init events...", flush=True)

    await send_event(stream, {
        "event": {"sessionStart": {"inferenceConfiguration": {"maxTokens": 1024, "topP": 0.0, "temperature": 0.0}}}
    })

    prompt_name = "test-prompt"
    await send_event(stream, {
        "event": {"promptStart": {
            "promptName": prompt_name,
            "textOutputConfiguration": {"mediaType": "text/plain"},
            "audioOutputConfiguration": {
                "mediaType": "audio/lpcm", "sampleRateHertz": 24000,
                "sampleSizeBits": 16, "channelCount": 1,
                "voiceId": "matthew", "encoding": "base64", "audioType": "SPEECH"
            },
            "toolUseOutputConfiguration": {"mediaType": "application/json"},
            "toolConfiguration": {"tools": []}
        }}
    })

    content_name = "test-content"
    await send_event(stream, {
        "event": {"contentStart": {
            "promptName": prompt_name, "contentName": content_name,
            "type": "TEXT", "role": "USER", "interactive": True,
            "textInputConfiguration": {"mediaType": "text/plain"}
        }}
    })

    await send_event(stream, {
        "event": {"textInput": {
            "promptName": prompt_name, "contentName": content_name,
            "content": "Say hello in one sentence."
        }}
    })

    await send_event(stream, {
        "event": {"contentEnd": {"promptName": prompt_name, "contentName": content_name}}
    })

    # Try to receive — loop with timeout to catch all responses
    print("4. Waiting for responses (15s timeout)...", flush=True)
    got_response = False
    try:
        deadline = asyncio.get_event_loop().time() + 15.0
        while asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            output = await asyncio.wait_for(stream.await_output(), timeout=remaining)
            result = await output[1].receive()
            if result.value and result.value.bytes_:
                raw = result.value.bytes_.decode("utf-8")
                print(f"   RESPONSE: {raw[:100]}...", flush=True)
                got_response = True
            else:
                print("   Got empty response", flush=True)
    except asyncio.TimeoutError:
        if not got_response:
            print("   TIMEOUT — no response from Bedrock after 15s", flush=True)
        else:
            print("   (timeout after receiving responses — normal)", flush=True)
    except StopAsyncIteration:
        print("   Stream ended", flush=True)
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}", flush=True)

    if not got_response:
        print(flush=True)
        print("=== TROUBLESHOOTING ===", flush=True)
        print("1. Check model access: aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?modelId==`amazon.nova-sonic-v1:0`]'", flush=True)
        print("2. Check token expiry: aws sts get-caller-identity", flush=True)
        print("3. Try a simple Bedrock call: aws bedrock-runtime invoke-model --model-id amazon.nova-lite-v1:0 --region us-east-1 --body '{\"messages\":[{\"role\":\"user\",\"content\":[{\"text\":\"hi\"}]}]}' --cli-binary-format raw-in-base64-out /dev/stdout", flush=True)

    # Cleanup
    try:
        await stream.input_stream.close()
    except:
        pass


if __name__ == "__main__":
    asyncio.run(main())
