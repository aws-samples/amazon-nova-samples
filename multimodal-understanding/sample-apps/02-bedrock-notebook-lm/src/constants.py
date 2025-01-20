"""
constants.py
"""

from pathlib import Path

# Key constants
APP_TITLE = "Bedrock NotebookLM"
CHARACTER_LIMIT = 1000_000

# Gradio-related constants
GRADIO_CACHE_DIR = "./gradio_cached_examples/tmp/"
GRADIO_CLEAR_CACHE_OLDER_THAN = 1 * 24 * 60 * 60  # 1 day

# Error messages-related constants
ERROR_MESSAGE_NO_INPUT = (
    "Please provide at least one PDF file, URL, s3 address or video file"
)
ERROR_MESSAGE_NOT_PDF = "The provided file is not a PDF. Please upload only PDF files."
ERROR_MESSAGE_READING_PDF = "Error reading the PDF file"
ERROR_MESSAGE_TOO_LONG = "The total content is too long. Please ensure the combined text from PDFs and URL is fewer than {CHARACTER_LIMIT} characters."


# Suno related constants
SUNO_LANGUAGE_MAPPING = {
    "English": "en",
    "Chinese": "zh",
    "French": "fr",
    "German": "de",
    "Hindi": "hi",
    "Italian": "it",
    "Japanese": "ja",
    "Korean": "ko",
    "Polish": "pl",
    "Portuguese": "pt",
    "Russian": "ru",
    "Spanish": "es",
    "Turkish": "tr",
}

# Jina Reader-related constants
JINA_READER_URL = "https://r.jina.ai/"
JINA_RETRY_ATTEMPTS = 3
JINA_RETRY_DELAY = 5  # in seconds

# UI-related constants
UI_DESCRIPTION = """
Generate Podcasts from PDFs and Videos in AWS.

Built with:
- Bedrock for LLMs
- Polly for TTS

"""
UI_AVAILABLE_LANGUAGES = list(set(SUNO_LANGUAGE_MAPPING.keys()))
UI_INPUTS = {
    "region": {"label": "AWS Region"},
    "video_upload": {
        "label": "📄 Upload your Video",
        "file_types": [".mp4"],
        "file_count": "single",
    },
    "file_upload": {
        "label": "📄 Upload your file(s)",
        "file_types": [".pdf"],
        "file_count": "multiple",
    },
    "url": {
        "label": " 🔗 Paste a URL (optional)",
        "placeholder": "Enter a URL to include its content",
    },
    "s3": {
        "label": " 🔗 Paste a S3 URL (optional)",
        "placeholder": "Enter a S3 URL to include its content",
    },
    "question": {
        "label": "Do you have a specific question or topic in mind?",
        "placeholder": "Enter a question or topic",
    },
    "tone": {
        "label": " 🎭 Choose the tone",
        "choices": ["Fun", "Formal"],
        "value": "Fun",
    },
    "length": {
        "label": " ⏱️ Choose the length",
        "choices": ["Short", "Long"],
        "value": "Short",
    },
    "models": {
        "label": " 🤖 Choose the model",
        "choices": [],
        "value": "Nova Pro",
    },
}

UI_OUTPUTS = {
    "audio": {"label": "🔊 Podcast", "format": "mp3"},
    "transcript": {
        "label": "📜 Transcript",
    },
}
UI_API_NAME = "generate_podcast"
UI_ALLOW_FLAGGING = "never"
UI_CONCURRENCY_LIMIT = 3
UI_EXAMPLES = [
    [
        [str(Path("examples/1310.4546v1.pdf"))],
        "",
        "Explain this paper to me like I'm 5 years old",
        "Fun",
        "Short (1-2 min)",
        "English",
        True,
    ],
    [
        [],
        "https://en.wikipedia.org/wiki/Hugging_Face",
        "How did Hugging Face become so successful?",
        "Fun",
        "Short (1-2 min)",
        "English",
        False,
    ],
    [
        [],
        "https://simple.wikipedia.org/wiki/Taylor_Swift",
        "Why is Taylor Swift so popular?",
        "Fun",
        "Short (1-2 min)",
        "English",
        False,
    ],
]
UI_CACHE_EXAMPLES = False
UI_SHOW_API = True
AWS_REGION = "us-east-1"
