import os
import boto3

KB_REGION = os.environ.get('KB_REGION', 'us-east-1')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=KB_REGION)

def retrieve_kb(kb_id, query):
    if not kb_id:
        kb_id = os.environ.get('KB_ID')

    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=kb_id,
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': 1,
                'overrideSearchType': 'SEMANTIC',
            }
        },
        retrievalQuery={
            'text': query
        }
    )
    results = []
    if "retrievalResults" in response:
        for r in response["retrievalResults"]:
            results.append(r["content"]["text"])
    return results
