"""OpenAI: Basic text generation with system message."""
from openai import OpenAI

client = OpenAI(api_key="...")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a concise technical writer. Keep responses under 100 words."},
        {"role": "user", "content": "Summarize the key benefits of cloud computing in 3 bullet points."},
    ],
    max_tokens=200,
    temperature=0.7,
)
print(response.choices[0].message.content)
