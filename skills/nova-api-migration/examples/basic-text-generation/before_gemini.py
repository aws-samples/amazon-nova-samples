"""Gemini: Basic text generation with system instruction."""
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input="Summarize the key benefits of cloud computing in 3 bullet points.",
    system_instruction="You are a concise technical writer. Keep responses under 100 words.",
)
print(interaction.output_text)
