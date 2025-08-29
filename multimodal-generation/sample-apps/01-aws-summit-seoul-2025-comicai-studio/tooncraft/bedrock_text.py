import boto3
from botocore.config import Config
from bedrock_model import BedrockModel


class BedrockText():
    def __init__(self, region='us-west-2', modelId=BedrockModel.NOVA_LITE_CR, **model_kwargs):
        self.region = region
        self.modelId = modelId
        self.bedrock = boto3.client(
            service_name = 'bedrock-runtime',
            region_name = self.region,
            config = Config(
                connect_timeout=1200,
                read_timeout=1200,
                retries={'max_attempts': 10}
            ),
        )

        self.inference_config = {
            'temperature': 0.1, # [0, 1]
            'maxTokens': 4096, # max tokens
            'topP': 0.9, # [0, 1]
            'stopSequences': ['Human:', 'H: ']
        }
        self.inference_config.update(model_kwargs)

    '''
    Bedrock Converse API
    '''
    def converse(self, text: str, image: bytes = None, system: str = None, format='jpeg'):
        content = []
        if text:
            content.append({'text': text})

        if image:
            content.append({
                'image': {
                    'format': format, # png, jpeg, gif, webp
                    'source': {
                        'bytes': image,
                    }
                }
            })
            
        
        system_prompts = []
        if system:
            system_prompts.append({'text': system})

        response = self.bedrock.converse(
            modelId=self.modelId,
            messages=[
                {
                    'role': 'user',
                    'content': content
                },
            ],
            system=system_prompts,
            inferenceConfig=self.inference_config,
        )
        
        return response

    def converse_output(self, text: str, image: bytes = None, system: str = None, format='jpeg'):
        res = self.converse(text=text, image=image, system=system, format=format)
        if res:
            return res.get('output', {}).get('message', {}).get('content', [])[0].get('text', '')
        return None


    '''
    Bedrock Converse Stream
    '''
    def converse_stream(self, text: str, image: bytes = None, system: str = None, format='jpeg'):
        '''
        Generator that yields assistant's response chunks
        '''
        # 메시지 내용 구성
        content = []
        if text:
            content.append({'text': text})

        if image:
            content.append({
                'image': {
                    'format': format, # png, jpeg, gif, webp
                    'source': {
                        'bytes': image,
                    }
                }
            })

        try:
            response = self.bedrock.converse_stream(
                modelId=self.modelId,
                messages=[
                    {
                        'role': 'user',
                        'content': content
                    },
                ],
                system=[
                    {
                        'text': system
                    },
                ],
                inferenceConfig=self.inference_config,
            )

            stream = response.get('stream')
            if stream:
                for event in stream:
                    if 'contentBlockDelta' in event:
                        delta = event['contentBlockDelta']['delta']
                        if 'text' in delta:
                            yield delta['text']
        except Exception as e:
            print(e)
            return