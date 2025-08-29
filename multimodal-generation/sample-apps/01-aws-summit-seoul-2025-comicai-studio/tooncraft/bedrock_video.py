import boto3
import secrets
from enum import Enum
from typing import Optional
from urllib.parse import urlparse
from botocore.config import Config
from bedrock_model import BedrockModel
from amazon_s3 import S3


class VideoStatus(Enum):
    COMPLETED = "Completed"
    FAILED = "Failed"
    IN_PROGRESS = "InProgress"


class LumaDuration(Enum):
    DURATION_5 = "5s"
    DURATION_9 = "9s"
    
class LumaSize(Enum):
    SIZE_1_1 = "1:1"
    SIZE_3_4 = "3:4"
    SIZE_4_3 = "4:3"
    SIZE_16_9 = "16:9"
    SIZE_9_16 = "9:16"
    SIZE_21_9 = "21:9"
    SIZE_9_21 = "9:21"
    
    
class BedrockAmazonVideo():
    def __init__(self,
                 bucket_name: str,
                 region='us-east-1',
                 modelId = BedrockModel.NOVA_REEL):
        self.bucket_name = bucket_name
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

    def generate_video(
        self,
        text: str,
        image: Optional[str] = None,
        imageFormat: str = 'jpeg',
        seed: Optional[int] = None,
        durationSeconds: int = 6,
        fps: int = 24,
        dimension: str = '1280x720',
    ) -> str:
        """
        Generate a video from text with an optional input image and seed.
        
        Returns:
            str: The invocation ARN for the async task
        """
        model_input = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {
                "text": text
            },
            "videoGenerationConfig": {
                "durationSeconds": durationSeconds,
                "fps": fps,
                "dimension": dimension,
                "seed": seed if seed is not None else secrets.randbelow(2147483647)
            }
        }

        if image:
            model_input["textToVideoParams"]["images"] = [{
                "format": imageFormat,
                "source": {
                    "bytes": image
                }
            }]
            
        return self._generate_video(model_input)
    
    def generate_multishot_video(
        self,
        text: str,
        seed: Optional[int] = None,
        durationSeconds: int = 12, # Must be a multiple of 6 in range [12, 120]
        fps: int = 24, # Must be 24
        dimension: str = '1280x720', # Must be "1280x720"
    ) -> str:
        """
        Generate a video from text with an optional input image and seed.
        
        Returns:
            str: The invocation ARN for the async task
        """
        model_input = {
            "taskType": "MULTI_SHOT_AUTOMATED",
            "multiShotAutomatedParams": {
                "text": text
            },
            "videoGenerationConfig": {
                "durationSeconds": durationSeconds,
                "fps": fps,
                "dimension": dimension,
                "seed": seed if seed is not None else secrets.randbelow(2147483647)
            }
        }
            
        return self._generate_video(model_input)

    def generate_luma_video(
        self,
        prompt: str,
        aspect_ratio: str = LumaSize.SIZE_16_9.value,
        duration: str = LumaDuration.DURATION_9.value,
        seed: int = secrets.randbelow(2147483647),
        resolution: str = '720p',
        loop=True
    ) -> str:
        body = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "seed": seed,
            "resolution": resolution,
            "loop": loop,
        }
        
        return self._generate_video(body=body)

    def query_job(self, invocation_arn: str):
        invocation = self.bedrock.get_async_invoke(
            invocationArn=invocation_arn
        )
        status = invocation.get("status", "")
        s3Uri = invocation.get("outputDataConfig", {}).get("s3OutputDataConfig", {}).get("s3Uri", "")
        return VideoStatus(status), s3Uri, invocation
    
    def list_jobs(self, status: VideoStatus = None, max_results: int = None):
        params = {}
        if status:
            params["status"] = status
        if max_results:
            params["maxResults"] = max_results

        jobs = self.bedrock.list_async_invokes(**params)
        return [ 
            {
                "invocationArn": job.get("invocationArn", ""),
                "status": VideoStatus(job.get("status", "")),
                "s3Uri": job.get("outputDataConfig", {})
                            .get("s3OutputDataConfig", {})
                            .get("s3Uri", ""),
            }
            for job in jobs.get("asyncInvokeSummaries", [])
        ]
    
    def get_video(self, invocation_arn: str = None, s3Uri: str = None):
        if not s3Uri and not invocation_arn:
            raise ValueError("Either 's3Uri' or 'invocation_arn' must be provided.")
        
        if invocation_arn:
            status, s3Uri, _ = self.query_job(invocation_arn)
            if status != VideoStatus.COMPLETED:
                raise ValueError(f"Job is not completed. Status: {status}")
            if not s3Uri:
                raise ValueError(f"No S3 URI found for invocation ARN: {invocation_arn}")
        
        s3 = S3(bucket_name=self.bucket_name)
        parsed_uri = urlparse(s3Uri)
        key = parsed_uri.path.lstrip('/')
        return s3.get_object(f"{key}/output.mp4")
    

    def _generate_video(self, body: dict):
        invocation = self.bedrock.start_async_invoke(
            modelId=self.modelId,
            modelInput=body,
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": f"s3://{self.bucket_name}"
                }
            }
        )
        return invocation['invocationArn']