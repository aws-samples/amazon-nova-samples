import json
import os
import base64
import boto3

def download_s3_image_to_base64(s3_uri, s3_client):
    """Download image from S3 and convert to base64."""
    bucket = s3_uri.split('/')[2]
    key = '/'.join(s3_uri.split('/')[3:])
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return base64.b64encode(response['Body'].read()).decode('utf-8')

def load_test_data(metadata_path):
    """Load test data from Bedrock conversation format."""
    test_data = []
    with open(metadata_path, 'r') as f:
        for line in f:
            data = json.loads(line)
            user_content = data['messages'][0]['content']
            prompt = next(item['text'] for item in user_content if 'text' in item)
            s3_uri = next(item['image']['source']['s3Location']['uri'] for item in user_content if 'image' in item)
            expected = data['messages'][1]['content'][0]['text']
            system = data['system'][0]['text']
            
            test_data.append({
                'prompt': prompt,
                's3_uri': s3_uri,
                'expected': expected,
                'system': system
            })
    return test_data

def batch_inference_to_file(metadata_path, model, output_file, n_samples, region_name="us-east-1"):
    """Run inference on n samples and save responses to file."""
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=region_name)
    s3_client = boto3.client("s3", region_name=region_name)
    
    test_data = load_test_data(metadata_path)[:n_samples]
    
    results = []
    for i, item in enumerate(test_data, 1):
        try:
            base64_string = download_s3_image_to_base64(item['s3_uri'], s3_client)
            
            request_body = {
                "messages": [{
                    "role": "user",
                    "content": [
                        {"image": {"format": "jpeg", "source": {"bytes": base64_string}}},
                        {"text": item['prompt']}
                    ]
                }],
                "system": [{"text": item['system']}],
                "inferenceConfig": {"max_new_tokens": 500, "top_p": 0.9, "temperature": 0.0}
            }

            response = bedrock_runtime.invoke_model(
                modelId=model,
                body=json.dumps(request_body)
            )
            
            model_response = json.loads(response["body"].read())
            response_text = model_response["output"]["message"]["content"][0]["text"]
            
            results.append({
                'sample_id': i,
                'image': os.path.basename(item['s3_uri']),
                'prompt': item['prompt'],
                'model_response': response_text,
                'expected': item['expected']
            })
            
            print(f"Processed sample {i}/{n_samples}")
            
        except Exception as e:
            print(f"Error processing sample {i}: {str(e)}")
            results.append({
                'sample_id': i,
                'error': str(e)
            })
    
    # Save results to file
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {output_file}")
    return results