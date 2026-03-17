"""  
LLM Judge Lambda POC - Working implementation using Amazon Bedrock  
"""  
  
import json  
import time  
import boto3  
  
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')  
JUDGE_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"  
SYSTEM_PROMPT = "You must output ONLY a number between 0.0 and 1.0. No explanations, no text, just the number."  
  
JUDGE_PROMPT_TEMPLATE = """Compare the following two responses and rate how similar they are on a scale of 0.0 to 1.0, where:  
- 1.0 means the responses are semantically equivalent (same meaning, even if worded differently)  
- 0.5 means the responses are partially similar  
- 0.0 means the responses are completely different or contradictory  
  
Response A: {response_a}  
  
Response B: {response_b}  
  
Output ONLY a number between 0.0 and 1.0. No explanations."""  
  
  
def lambda_graded(response_a: str, response_b: str, max_retries: int = 3) -> float:  
    """Call Bedrock to compare responses and return similarity score."""  
    prompt = JUDGE_PROMPT_TEMPLATE.format(response_a=response_a, response_b=response_b)  
      
    for attempt in range(max_retries):  
        try:  
            response = bedrock_runtime.converse(  
                modelId=JUDGE_MODEL_ID,  
                messages=[{"role": "user", "content": [{"text": prompt}]}],  
                system=[{"text": SYSTEM_PROMPT}],  
                inferenceConfig={"temperature": 0.0, "maxTokens": 10}  
            )  
            print(f"Bedrock call successful: {response}")  
            output = response['output']['message']['content'][0]['text'].strip()  
            score = float(output)  
            print(f"Score parsed: {score}")  
            return max(0.0, min(1.0, score))  
                  
        except Exception as e:  
            if "ThrottlingException" in str(e) and attempt < max_retries - 1:  
                time.sleep(2 ** attempt)  
            else:  
                print(f"Bedrock call failed: {e}")  
                return None  
    return None  
  
  
def lambda_handler(event, context):  
    """AWS Lambda handler - processes samples from RFTEvalInvoker."""  
    try:  
        samples = event if isinstance(event, list) else [event]  
        results = []  
          
        for sample in samples:  
            sample_id = sample.get("id", "unknown")  
            messages = sample.get("messages", [])  
              
            # Extract assistant response (response A)  
            response_a = ""  
            for msg in messages:  
                if msg.get("role") in ["assistant", "nova_assistant"]:  
                    response_a = msg.get("content", "")  
                    break  
              
            # Extract reference answer from root level (no longer in metadata)  
            reference_answer = sample.get("reference_answer", "")  
              
            # Handle both string and dict reference_answer formats  
            if isinstance(reference_answer, dict):  
                # If reference_answer is a dict, extract the explanation or compliant field  
                response_b = reference_answer.get("explanation", reference_answer.get("compliant", ""))  
            else:  
                response_b = reference_answer  
              
            if not response_a or not response_b:  
                results.append({  
                    "id": sample_id,  
                    "aggregate_reward_score": 0.0,  
                    "metrics_list": [{"name": "similarity_score", "value": 0.0, "type": "Metric"}]  
                })  
                continue  
              
            # Get similarity score  
            score = lambda_graded(response_a, response_b)  
              
            results.append({  
                "id": sample_id,  
                "aggregate_reward_score": score,  
                "metrics_list": [  
                    {  
                        "name": "similarity_score",  
                        "value": score,  
                        "type": "Metric"  
                    }  
                ]  
            })  
          
        return {"statusCode": 200, "body": json.dumps(results)}  
          
    except Exception as e:  
        print(f"Error: {e}")  
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
