"""Configuration constants for Nova 2 Sonic application."""

# Audio Configuration
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_SIZE = 1024

# AWS Configuration
DEFAULT_MODEL_ID = 'amazon.nova-2-sonic-v1:0'
DEFAULT_REGION = 'us-east-1'

# Model Configuration
MAX_TOKENS = 1024
TOP_P = 0.0
TEMPERATURE = 0.0

# Debug
DEBUG = False
