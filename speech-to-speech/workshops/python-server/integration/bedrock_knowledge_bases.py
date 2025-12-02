import json
import boto3
import os

KB_ID = os.environ.get('KB_ID')
KB_REGION = os.environ.get('KB_REGION', 'us-east-1')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=KB_REGION) 

def retrieve_kb(query):
    results = []
    # Call KB
    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=KB_ID,
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
    if "retrievalResults" in response:
        for r in response["retrievalResults"]:
            results.append(r["content"]["text"])
    return results

def retrieve_and_generation(query):
    results = []
    custom_prompt = """
      You are a question answering agent. I will provide you with a set of search results.
      The user will provide you with a question. Your job is to answer the user's question using only information from the search results. 
      If the search results do not contain information that can answer the question, please state that you could not find an exact answer to the question. 
      Just because the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion.
                                  
      Here are the search results in numbered order:
      $search_results$

      $output_format_instructions$
      """
    response = bedrock_agent_runtime.retrieve_and_generate(
            input={
                'text': query
            },
        retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': KB_ID,
            'modelArn': 'anthropic.claude-3-haiku-20240307-v1:0', 
            'retrievalConfiguration': {
                'vectorSearchConfiguration': {
                    'numberOfResults': 2 # will fetch top N documents which closely match the query
                    }
                },
                'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': custom_prompt
                        }
                    }
            }
        }
    )
    if "citations" in response:
        for r in response["citations"]:
            results.append(r["generatedResponsePart"]["textResponsePart"]["text"])
    return results