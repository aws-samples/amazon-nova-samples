from enum import Enum


class BedrockModel(str, Enum):
    '''
    Language models
    '''
    SONNET_3_7 = "anthropic.claude-3-7-sonnet-20250219-v1:0"
    SONNET_3_7_CR = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    HAIKU_3_5 = "anthropic.claude-3-5-haiku-20241022-v1:0"
    HAIKU_3_5_CR = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    NOVA_PRO = "amazon.nova-pro-v1:0"
    NOVA_PRO_CR = "us.amazon.nova-pro-v1:0"
    NOVA_LITE = "amazon.nova-lite-v1:0"
    NOVA_LITE_CR = "us.amazon.nova-lite-v1:0"
    NOVA_MICRO = "amazon.nova-micro-v1:0"
    NOVA_MICRO_CR = "us.amazon.nova-micro-v1:0"

    '''
    Image, Video generation models
    '''
    TITAN_IMAGE = "amazon.titan-image-generator-v2:0"
    SD3_LARGE = "stability.sd3-large-v1:0"
    STABLE_IMAGE_CORE = "stability.stable-image-core-v1:0"
    STABLE_IMAGE_ULTRA = "stability.stable-image-ultra-v1:0"    
    NOVA_CANVAS = 'amazon.nova-canvas-v1:0'
    NOVA_REEL = "amazon.nova-reel-v1:1"
    LUMA_RAY2 = "luma.ray-v2:0"

    '''
    Embedding models
    '''
    TITAN_TEXT_EMBEDDING = "amazon.titan-embed-text-v2:0"
    TITAN_MULTIMODAL_EMBEDDING = "amazon.titan-embed-image-v1"
    COHERE_MULTILINGUAL = "cohere.embed-multilingual-v3"
