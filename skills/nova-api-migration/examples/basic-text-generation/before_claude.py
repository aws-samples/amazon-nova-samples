"""Claude: Basic text generation with system prompt."""
from anthropic import Anthropic

client = Anthropic(api_key="...")

response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=200,
    system="You are a concise technical writer. Keep responses under 100 words.",
    messages=[{"role": "user", "content": "Summarize the key benefits of cloud computing in 3 bullet points."}],
    temperature=0.7,
)
print(response.content[0].text)
