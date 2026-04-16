"""Nova Multimodal Embedding helpers for multimodal retrieval."""

import base64
import json
import os
import boto3
import numpy as np

MODEL_ID = "amazon.nova-2-multimodal-embeddings-v1:0"
REGION = "us-east-1"


def _get_bedrock_client(region=REGION):
    return boto3.client("bedrock-runtime", region_name=region)


def generate_text_embedding(text, dim=3072, purpose="GENERIC_INDEX", region=REGION):
    """Generate embedding for a text string."""
    request_body = {
        "taskType": "SINGLE_EMBEDDING",
        "singleEmbeddingParams": {
            "embeddingDimension": dim,
            "embeddingPurpose": purpose,
            "text": {"truncationMode": "END", "value": text},
        },
    }
    response = _get_bedrock_client(region).invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(request_body),
        accept="application/json",
        contentType="application/json",
    )
    result = json.loads(response["body"].read())
    return result["embeddings"][0]["embedding"]


def generate_image_embedding(image_source, dim=3072, purpose="GENERIC_INDEX",
                              detail_level="STANDARD_IMAGE", region=REGION):
    """Generate embedding for an image.

    image_source: local file path (str) or base64-encoded string.
    """
    if isinstance(image_source, str) and os.path.exists(image_source):
        with open(image_source, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
    elif isinstance(image_source, str):
        # Assume it's already base64-encoded
        b64_data = image_source
    else:
        raise ValueError(f"image_source must be a file path or base64 string, got {type(image_source)}")

    fmt = "png"
    if isinstance(image_source, str):
        if image_source.lower().endswith((".jpg", ".jpeg")):
            fmt = "jpeg"

    request_body = {
        "taskType": "SINGLE_EMBEDDING",
        "singleEmbeddingParams": {
            "embeddingPurpose": purpose,
            "embeddingDimension": dim,
            "image": {
                "format": fmt,
                "detailLevel": detail_level,
                "source": {"bytes": b64_data},
            },
        },
    }
    response = _get_bedrock_client(region).invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(request_body),
        accept="application/json",
        contentType="application/json",
    )
    result = json.loads(response["body"].read())
    return result["embeddings"][0]["embedding"]


def generate_document_embedding(image_path, dim=3072, purpose="GENERIC_INDEX", region=REGION):
    """Generate embedding for a document page image using DOCUMENT_IMAGE detail level."""
    return generate_image_embedding(
        image_path, dim=dim, purpose=purpose,
        detail_level="DOCUMENT_IMAGE", region=region
    )


def extract_embedding(response_body, index=0):
    """Extract embedding vector from a Bedrock response body."""
    return response_body["embeddings"][index]["embedding"]


def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    vec1, vec2 = np.array(vec1), np.array(vec2)
    dot = np.dot(vec1, vec2)
    norm1, norm2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot / (norm1 * norm2))


def load_file_as_base64(file_path):
    """Load a local file and return its base64-encoded string."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
