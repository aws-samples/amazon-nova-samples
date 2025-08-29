import boto3
from urllib.parse import quote, unquote


class S3:
    def __init__(self, bucket_name, region='us-west-2'):
        self.storage = boto3.client('s3', region_name = region)
        self.bucket_name = bucket_name


    def get_object(self, key, include_metadata=False):
        response = self.storage.get_object(Bucket=self.bucket_name, Key=key)
        content = response['Body'].read()
        
        if include_metadata:
            metadata = {
                k.replace('x-amz-meta-', ''): unquote(v)
                for k, v in response.get('Metadata', {}).items()
            }
            return content, metadata
        return content

    def get_object_metadata(self, key):
        try:
            response = self.storage.head_object(Bucket=self.bucket_name, Key=key)
            return {
                k.replace('x-amz-meta-', ''): unquote(v)
                for k, v in response.get('Metadata', {}).items()
            }
        except Exception as e:
            print(f"Error getting metadata for {key}: {e}")
            return {}


    def upload_object(self, bytes, key, metadata=None, extra_args=None):
        extra_args = extra_args or {}
        if metadata:
            formatted_metadata = {
                f'x-amz-meta-{k.lower()}': quote(str(v)) 
                for k, v in metadata.items()
            }
            extra_args['Metadata'] = formatted_metadata
        
        self.storage.upload_fileobj(
            bytes,
            self.bucket_name,
            key,
            ExtraArgs=extra_args
        )
        
    def download_object(self, key, file_path):
        self.storage.download_file(self.bucket_name, key, file_path)
