import boto3
import json
import secrets
from enum import Enum
from typing import List, Optional
from botocore.config import Config
from bedrock_model import BedrockModel


class BedrockAmazonImage():
    def __init__(self, region='us-east-1', modelId = BedrockModel.NOVA_CANVAS):
        self.region = region
        self.modelId = modelId
        self.bedrock = boto3.client(
            service_name = 'bedrock-runtime',
            region_name=self.region,
            config = Config(
                connect_timeout=300,
                read_timeout=300,
                retries={'max_attempts': 5}
            ),
        )

    def generate_image(self, body: str):
        response = self.bedrock.invoke_model(
            body=body,
            modelId=self.modelId,
            accept="application/json",
            contentType="application/json"
        )
        response_body = json.loads(response.get("body").read())
        return response_body.get("images")
    

class TitanImageSize(Enum):
    SIZE_512x512 = (512, 512)       # 1:1
    SIZE_1024x1024 = (1024, 1024)   # 1:1
    SIZE_768x768 = (768, 768)       # 1:1
    SIZE_768x1152 = (768, 1152)     # 2:3
    SIZE_384x576 = (384, 576)       # 2:3
    SIZE_1152x768 = (1152, 768)     # 3:2
    SIZE_576x384 = (576, 384)       # 3:2
    SIZE_768x1280 = (768, 1280)     # 3:5
    SIZE_384x640 = (384, 640)       # 3:5
    SIZE_1280x768 = (1280, 768)     # 5:3
    SIZE_640x384 = (640, 384)       # 5:3
    SIZE_896x1152 = (896, 1152)     # 7:9
    SIZE_448x576 = (448, 576)       # 7:9
    SIZE_1152x896 = (1152, 896)     # 9:7
    SIZE_576x448 = (576, 448)       # 9:7
    SIZE_768x1408 = (768, 1408)     # 6:11
    SIZE_384x704 = (384, 704)       # 6:11
    SIZE_1408x768 = (1408, 768)     # 11:6
    SIZE_704x384 = (704, 384)       # 11:6
    SIZE_640x1408 = (640, 1408)     # 5:11
    SIZE_320x704 = (320, 704)       # 5:11
    SIZE_1408x640 = (1408, 640)     # 11:5
    SIZE_704x320 = (704, 320)       # 11:5
    SIZE_1152x640 = (1152, 640)     # 9:5
    SIZE_1173x640 = (1173, 640)     # 16:9

    def __init__(self, width, height):
        self.width = width
        self.height = height


class NovaImageSize(Enum):
    SIZE_512x512 = (512, 512)       # 1:1
    SIZE_1024x1024 = (1024, 1024)   # 1:1
    SIZE_2048x2048 = (2048, 2048)   # 1:1
    SIZE_336x1024 = (336, 1024)     # 1:3
    SIZE_512x1024 = (512, 1024)     # 1:2
    SIZE_512x2048 = (512, 2048)     # 1:4
    SIZE_576x1024 = (576, 1024)     # 9:16
    SIZE_672x1024 = (672, 1024)     # 2:3
    SIZE_720x1280 = (720, 1280)     # 9:16
    SIZE_816x1024 = (816, 1024)     # 4:5
    SIZE_1024x4096 = (1024, 4096)   # 1:4
    SIZE_1168x3536 = (1168, 3536)   # 1:3
    SIZE_1440x2896 = (1440, 2896)   # 1:2
    SIZE_1520x2720 = (1520, 2720)   # 9:16
    SIZE_1664x2512 = (1664, 2512)   # 2:3
    SIZE_1824x2288 = (1824, 2288)   # 4:5
    SIZE_1024x336 = (1024, 336)     # 3:1
    SIZE_1024x512 = (1024, 512)     # 2:1
    SIZE_1024x576 = (1024, 576)     # 16:9
    SIZE_1024x627 = (1024, 627)     # 3:2
    SIZE_1024x816 = (1024, 816)     # 5:4
    SIZE_1280x720 = (1280, 720)     # 16:9
    SIZE_2048x512 = (2048, 512)     # 4:1
    SIZE_2288x1824 = (2288, 1824)   # 5:4
    SIZE_2512x1664 = (2512, 1664)   # 3:2
    SIZE_2720x1520 = (2720, 1520)   # 16:9
    SIZE_2896x1440 = (2896, 1440)   # 2:1
    SIZE_3536x1168 = (3536, 1168)   # 3:1
    SIZE_4096x1024 = (4096, 1024)   # 4:1

    def __init__(self, width, height):
        self.width = width
        self.height = height


class ControlMode(Enum):
    CANNY_EDGE = "CANNY_EDGE"
    SEGMENTATION = "SEGMENTATION"

class OutpaintMode(Enum):
    DEFAULT = "DEFAULT"
    PRECISE = "PRECISE"

class ImageParams:
    def __init__(self, count: int = 1, width: int = 512, height: int = 512, cfg: float = 8.0, seed: Optional[int] = None):
        self._config = self._default_configuration(count=count, width=width, height=height, cfg=cfg, seed=seed)

    '''
    Image Configuration
    '''
    def _default_configuration(self, count: int = 1, width: int = 512, height: int = 512, cfg: float = 8.0, seed: Optional[int] = None) -> dict:
        return {
            "imageGenerationConfig": {
                "numberOfImages": count,  # [1, 5]
                "width": width,
                "height": height,
                "cfgScale": cfg,  # [1.0, 10.0]
                "seed": seed if seed is not None else secrets.randbelow(2147483647)
            }
        }
    
    def get_configuration(self):
        return self._config

    def set_configuration(self, count: int = 1, width: int = 512, height: int = 512, cfg: float = 8.0):
        self._config = self._default_configuration(count, width, height, cfg)

    def _prepare_body(self, task_type: str, params: dict) -> str:
        body = {
            "taskType": task_type,
            **params
        }
        body.update(self._config)
        return json.dumps(body)


    '''
    Text To Image (with image conditioning)
    '''
    def text_to_image(self,
                      text: str,
                      negative_text: Optional[str] = None,
                      condition_image: Optional[str] = None,
                      control_mode: ControlMode = ControlMode.CANNY_EDGE,
                      control_strength: float = 0.7) -> str:
        params = {
            "textToImageParams": {
                "text": text,
            }
        }

        if negative_text is not None:
            params["textToImageParams"]["negativeText"] = negative_text

        if condition_image is not None:
            params["textToImageParams"].update({
                "conditionImage": condition_image,
                "controlMode": control_mode.value,
                "controlStrength": control_strength
            })

        return self._prepare_body("TEXT_IMAGE", params)
    

    '''
    INPAINTING
    '''
    def inpainting(self,
                   image: str,
                   text: str,
                   mask_prompt: str,                   
                   negative_text: Optional[str] = None) -> str:
        params = {
            "inPaintingParams": {
                "text": text,
                "image": image,
                "maskPrompt": mask_prompt,
                "returnMask": False,
            }
        }

        if negative_text is not None:
            params["inPaintingParams"]["negativeText"] = negative_text

        return self._prepare_body("INPAINTING", params)


    '''
    OUTPAINTING
    '''
    def outpainting(self,
                    image: str,
                    text: str,
                    mask_prompt: Optional[str] = None,
                    mask_image: Optional[str] = None,
                    mode: Optional[OutpaintMode] = OutpaintMode.DEFAULT,
                    negative_text: Optional[str] = None) -> str:
        params = {
            "outPaintingParams": {
                "text": text,
                "image": image,
                "outPaintingMode": mode.value
            }
        }
        
        if mask_prompt:
            params["outPaintingParams"]["maskPrompt"] = mask_prompt
        elif mask_image:
            params["outPaintingParams"]["maskImage"] = mask_image
            
        if negative_text is not None:
            params["outPaintingParams"]["negativeText"] = negative_text

        return self._prepare_body("OUTPAINTING", params)


    '''
    IMAGE_VARIATION
    '''
    def image_variant(self,
                      images: List[str],
                      text: Optional[str] = None,
                      negative_text: Optional[str] = None,
                      similarity: float = 0.7) -> str:
        params = {
            "imageVariationParams": {
                "images": images,
                "similarityStrength": similarity,  # [0.2, 1.0]
            }
        }

        if text is not None:
            params["imageVariationParams"]["text"] = text

        if negative_text is not None:
            params["imageVariationParams"]["negativeText"] = negative_text

        return self._prepare_body("IMAGE_VARIATION", params)


    '''
    COLOR_GUIDED_GENERATION
    '''
    def color_guide(self,
                    text: str,
                    colors: List[str],
                    negative_text: Optional[str] = None,
                    reference_image: Optional[str] = None) -> str:
        params = {
            "colorGuidedGenerationParams": {
                "text": text,
                "colors": colors,
            }
        }

        if negative_text is not None:
            params["colorGuidedGenerationParams"]["negativeText"] = negative_text

        if reference_image is not None:
            params["colorGuidedGenerationParams"]["referenceImage"] = reference_image

        return self._prepare_body("COLOR_GUIDED_GENERATION", params)


    '''
    BACKGROUND_REMOVAL
    '''
    def background_removal(self, image: str) -> str:
        params = {
            "backgroundRemovalParams": {
                "image": image,
            }
        }
        return self._prepare_body("BACKGROUND_REMOVAL", params)
