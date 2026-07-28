"""Nova 2 Lite: Basic text generation — identical output regardless of source provider."""
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a concise technical writer. Keep responses under 100 words."}],
    messages=[
        {"role": "user", "content": [{"text": "Summarize the key benefits of cloud computing in 3 bullet points."}]}
    ],
    inferenceConfig={"maxTokens": 200, "temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])
