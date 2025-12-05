"""
Utility functions for Amazon Nova Text-to-SQL fine-tuning and evaluation.

This module contains helper functions extracted from the nova-micro-sft-peft-lora notebook
to improve code organization and reusability.
"""

import json
import time
import re
import boto3
import uuid
from typing import Dict, List, Optional
from botocore.config import Config
from botocore.exceptions import ClientError
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


# Configuration
MAX_ATTEMPTS = 3
my_config = Config(connect_timeout=60*3, read_timeout=60*3)


def create_bedrock_conversation(record):
    """
    Convert SQL dataset record to bedrock-conversation-2024 format.
    
    Args:
        record: Dictionary with 'context', 'question', and 'answer' keys
        
    Returns:
        Dictionary in bedrock-conversation-2024 format
    """
    system_message = (
        f"You are a powerful text-to-SQL model. Your job is to answer questions about a database. "
        f"You can use the following table schema for context: {record['context']}"
    )
    user_message = f"Return the SQL query that answers the following question: {record['question']}"
    assistant_message = record['answer']
    
    return {
        'schemaVersion': 'bedrock-conversation-2024',
        'system': [{'text': system_message}],
        'messages': [
            {'role': 'user', 'content': [{'text': user_message}]},
            {'role': 'assistant', 'content': [{'text': assistant_message}]}
        ]
    }
# Function to check deployment status
def check_deployment_status(bedrock_client, deployment_arn):
    """
    Check the status of a custom model deployment
    
    Parameters:
    -----------
    deployment_arn : str
        ARN of the deployment to check
        
    Returns:
    --------
    status : str
        Current status of the deployment
    """
    
    try:
        response = bedrock_client.get_custom_model_deployment(
            customModelDeploymentIdentifier=deployment_arn
        )
        status = response.get('status')
        print(f"Deployment status: {status}")
        return status
    
    except Exception as e:
        print("failed")
        print(f"Error checking deployment status: {e}")
        return None

def prepare_dataset_for_nova(sample):
    """
    Prepare dataset in the required format for Nova models.
    
    Args:
        sample: Dictionary with 'system' and 'messages' keys
        
    Returns:
        Dictionary with formatted 'system' and 'messages'
    """
    messages = {'system': [], 'messages': []}
    
    # Extract system message
    if 'system' in sample and sample['system']:
        system_text = sample['system'][0]['text']
        messages['system'] = [{'text': system_text}]
    
    # Process messages
    for message in sample['messages']:
        role = message['role']
        content = message['content'][0]['text'] if message['content'] else ''
        
        messages['messages'].append({
            'role': role,
            'content': [{'text': content}]
        })
    
    return messages


def deploy_for_on_demand(bedrock_client, model_name, s3_uri, role_arn):
    """
    Deploy a PEFT/LoRA fine-tuned Nova model for on-demand inference.
    
    Args:
        bedrock_client: Boto3 Bedrock client
        model_name: Name for the custom model
        s3_uri: S3 URI of the model artifacts
        role_arn: IAM role ARN with necessary permissions
        
    Returns:
        Model ARN string
    """
    try:
        client_request_token = str(uuid.uuid4())
        
        model_source_config = {
            's3DataSource': {
                's3Uri': s3_uri,  
            }
        }
        
        response = bedrock_client.create_custom_model(
            modelName=model_name,
            roleArn=role_arn,
            modelSourceConfig=model_source_config,
            clientRequestToken=client_request_token
        )
        
        print(f"Model import initiated: {response['modelArn']}")
        return response['modelArn']
        
    except ClientError as e:
        print(f"Error: {e}")
        raise


def wait_for_model_active(bedrock_client, model_arn):
    """
    Wait until model deployment is Active.
    
    Args:
        bedrock_client: Boto3 Bedrock client
        model_arn: ARN of the model to check
        
    Returns:
        True if successful, False if failed
    """
    while True:
        response = bedrock_client.get_custom_model(modelIdentifier=model_arn)
        status = response['modelStatus']
        print(f"Status: {status}")
        
        if status == 'Active':
            print("✓ Model is ready for on-demand inference!")
            return True
        elif status == 'Failed':
            print(f"✗ Failed: {response.get('failureMessage')}")
            return False
            
        time.sleep(60)


def create_model_deployment(bedrock_client, custom_model_arn):
    """
    Create an on-demand inferencing deployment for the custom model.
    
    Args:
        bedrock_client: Boto3 Bedrock client
        custom_model_arn: ARN of the custom model to deploy
        
    Returns:
        Deployment ARN string or None if failed
    """
    try:
        print(f"Creating on-demand inferencing deployment for model: {custom_model_arn}")
        
        # Generate a unique name for the deployment
        deployment_name = f"nova-sql-deployment-{time.strftime('%Y%m%d-%H%M%S')}"
        
        # Create the deployment
        response = bedrock_client.create_custom_model_deployment(
            modelArn=custom_model_arn,
            modelDeploymentName=deployment_name,
            description=f"on-demand inferencing deployment for model: {custom_model_arn}",
        )
        
        # Get the deployment ARN
        deployment_arn = response.get('customModelDeploymentArn')
        
        print(f"Deployment request submitted. Deployment ARN: {deployment_arn}")
        return deployment_arn
    
    except Exception as e:
        print(f"Error creating deployment: {e}")
        return None


def check_deployment_status(bedrock_client, deployment_arn):
    """
    Check the status of a model deployment.
    
    Args:
        bedrock_client: Boto3 Bedrock client
        deployment_arn: ARN of the deployment to check
        
    Returns:
        Status string or None if error
    """
    try:
        response = bedrock_client.get_custom_model_deployment(
            customModelDeploymentIdentifier=deployment_arn
        )
        status = response.get('status')
        print(f"Deployment status: {status}")
        return status
    
    except Exception as e:
        print(f"Error checking deployment status: {e}")
        return None


def ask_nova_micro(messages, system="", model_resource=None, region='us-east-1'):
    """
    Send a prompt to custom Nova Micro model using Converse API.
    
    Args:
        messages: List of message dictionaries or string prompt
        system: System prompt string
        model_resource: Model ARN
        region: AWS region
        
    Returns:
        List containing [raw_prompt_text, response_text]
    """
    bedrock_runtime = boto3.client(service_name='bedrock-runtime', config=my_config, region_name=region)
    raw_prompt_text = str(messages)
    
    if type(messages) == str:
        messages = [{"role": "user", "content": [{"text": messages}]}]
    elif type(messages) == list and len(messages) > 0:
        # Convert old format to new Converse format if needed
        formatted_messages = []
        for msg in messages:
            if "content" in msg and isinstance(msg["content"], str):
                # Convert string content to new format
                formatted_messages.append({
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}]
                })
            else:
                formatted_messages.append(msg)
        messages = formatted_messages
    
    converse_params = {
        "modelId": model_resource,  
        "messages": messages,
        "inferenceConfig": {
            "maxTokens": 300,
            "temperature": 0,
            "topP": 0.9
        }
    }
    
    # Add system prompt if provided
    if system:
        converse_params["system"] = [{"text": system}]
    
    attempt = 1
    while True:
        try:
            response = bedrock_runtime.converse(**converse_params)
            results = response['output']['message']['content'][0]['text']
            break
        except Exception as e:
            print("Error with calling Bedrock Converse: " + str(e))
            attempt += 1
            if attempt > MAX_ATTEMPTS:
                print("Max attempts reached!")
                results = str(e)
                break
            else:  # retry in 2 seconds
                time.sleep(2)
    
    return [raw_prompt_text, results]


def ask_claude(messages, system="", model_version="sonnet", region='us-east-1'):
    """
    Send a prompt to Claude via Bedrock for LLM-as-a-judge evaluation.
    
    Args:
        messages: List of message dictionaries or string prompt
        system: System prompt string
        model_version: Claude model version
        region: AWS region
        
    Returns:
        List containing [raw_prompt_text, response_text]
    """
    bedrock = boto3.client(service_name='bedrock-runtime', config=my_config, region_name=region)
    raw_prompt_text = str(messages)
    
    if type(messages) == str:
        messages = [{"role": "user", "content": messages}]
    
    prompt_json = {
        "system": system,
        "messages": messages,
        "max_tokens": 3000,
        "temperature": 0.7,
        "anthropic_version": "",
        "top_k": 250,
        "top_p": 0.7,
        "stop_sequences": ["\n\nHuman:"]
    }
    
    modelId = 'us.anthropic.claude-3-5-haiku-20241022-v1:0'
    
    attempt = 1
    while True:
        try:
            response = bedrock.invoke_model(
                body=json.dumps(prompt_json), 
                modelId=modelId, 
                accept='application/json', 
                contentType='application/json'
            )
            response_body = json.loads(response.get('body').read())
            results = response_body.get("content")[0].get("text")
            break
        except Exception as e:
            print("Error with calling Bedrock: " + str(e))
            attempt += 1
            if attempt > MAX_ATTEMPTS:
                print("Max attempts reached!")
                results = str(e)
                break
            else:
                time.sleep(2)
    
    return [raw_prompt_text, results]


def prepare_evaluation_samples(test_data, num_samples=100):
    """
    Prepare evaluation data for testing the fine-tuned model.
    
    Args:
        test_data: List of test records
        num_samples: Number of samples to prepare
        
    Returns:
        List of evaluation sample dictionaries
    """
    eval_samples = []
    
    for i, record in enumerate(test_data[:num_samples]):
        system_prompt = record['system'][0]['text']
        user_question = record['messages'][0]['content'][0]['text']
        expected_sql = record['messages'][1]['content'][0]['text']
        
        eval_samples.append({
            'id': i,
            'system': system_prompt,
            'query': user_question,
            'expected_response': expected_sql
        })
    
    return eval_samples


def test_sql_generation(eval_samples, model_arn, region='us-east-1'):
    """
    Test the fine-tuned model on SQL generation tasks using Bedrock.
    
    Args:
        eval_samples: List of evaluation samples
        model_arn: ARN of the deployed model
        region: AWS region
        
    Returns:
        List of result dictionaries
    """
    results = []
    print(f"Generating finetuned Nova Micro SQL of : {len(eval_samples)} samples")
    
    for sample in eval_samples:
        system_prompt = sample['system']
        user_query = sample['query']
        
        messages = [
            {
                "role": "user",
                "content": [{"text": user_query}]
            }
        ]
        
        try:
            raw_prompt, generated_sql = ask_nova_micro(
                messages=messages,
                system=system_prompt,
                model_resource=model_arn,
                region=region
            )
            
            results.append({
                'id': sample['id'],
                'query': user_query,
                'system_prompt': system_prompt,
                'expected_sql': sample['expected_response'],
                'generated_sql': generated_sql,
                'status': 'success'
            })            
        except Exception as e:
            results.append({
                'id': sample['id'],
                'query': user_query,
                'system_prompt': system_prompt,
                'expected_sql': sample['expected_response'],
                'generated_sql': f'Error: {str(e)}',
                'status': 'error'
            })
    
    return results


def get_score(system, user, assistant, generated, region='us-east-1'):
    """
    Calculate the correctness score for SQL query responses using LLM-as-a-judge.
    
    Args:
        system: System prompt/schema
        user: User question
        assistant: Correct answer
        generated: Generated answer to evaluate
        region: AWS region
        
    Returns:
        Score string (0-100)
    """
    question = user
    correct_answer = assistant
    test_answer = generated
    
    formatted_prompt = (
        "You are a data science teacher that is introducing students to SQL. Consider the following question and schema:\n"
        f"<question>{question}</question>\n"
        f"<schema>{system}</schema>\n"
        "Here is the correct answer:\n"
        f"<correct_answer>{correct_answer}</correct_answer>\n"
        "Here is the student's answer:\n"
        f"<student_answer>{test_answer}</student_answer>\n\n"
        "Please provide a numeric score from 0 to 100 on how well the student's answer matches the correct answer for this question.\n"
        "The score should be high if the answers say essentially the same thing.\n"
        "The score should be lower if some parts are missing, or if extra unnecessary parts have been included.\n"
        "The score should be 0 for an entirely wrong answer. Put the score in <SCORE> XML tags.\n"
        "Do not consider your own answer to the question, but instead score based only on the correct answer above."
    )

    _, result = ask_claude(formatted_prompt, model_version="sonnet", region=region)
    pattern = r'<SCORE>(.*?)</SCORE>'
    match = re.search(pattern, result)
    
    return match.group(1) if match else "0"


def metrics_test(model_id, system, prompt, region='us-east-1'):
    """
    Quick test for Time To First Token (TTFT) and Overall Throughput Per Second (OTPS).
    
    Args:
        model_id: Model ARN
        system: System prompt
        prompt: User prompt
        region: AWS region
        
    Returns:
        Dictionary with ttft_ms, otps, and total_time_ms metrics
    """
    client = boto3.client('bedrock-runtime', region_name=region)
    
    start = time.time()
    first_token_time = None
    output_tokens = 0

    # Use converse stream to get ttft
    response = client.converse_stream(
        modelId=model_id,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 512, "temperature": 0}
    )
    
    for event in response['stream']:
        if first_token_time is None and 'contentBlockDelta' in event:
            first_token_time = time.time()
        
        if 'metadata' in event and 'usage' in event['metadata']:
            output_tokens = event['metadata']['usage']['outputTokens']
    
    end = time.time()
    
    ttft_seconds = first_token_time - start
    total_time_seconds = end - start
    generation_time_seconds = total_time_seconds - ttft_seconds
    
    otps = output_tokens / generation_time_seconds if generation_time_seconds > 0 else 0
    
    # Convert metrics to milliseconds
    ttft_ms = ttft_seconds * 1000
    total_time_ms = total_time_seconds * 1000
    
    results = {
        "ttft_ms": ttft_ms,
        "otps": otps,
        "total_time_ms": total_time_ms
    }
    return results


def run_cold_and_warm_benchmark(
    model_id: str,
    system: str,
    prompt: str,
    num_cold_starts: int = 5,
    num_warm_calls: int = 20,
    cold_start_wait: int = 330,
    region: str = 'us-east-1'
) -> Dict[str, List[float]]:
    """
    Run benchmark with cold starts and warm starts.
    
    Args:
        model_id: Model ARN
        system: System prompt
        prompt: User prompt
        num_cold_starts: Number of cold start measurements (default: 5)
        num_warm_calls: Number of warm calls per cold start (default: 20)
        cold_start_wait: Seconds to wait between cold starts (default: 330s = 5.5 min)
        region: AWS region
    
    Returns:
        Dictionary with cold_start_ttft and warm_start_ttft lists
    """
    import matplotlib.pyplot as plt
    import numpy as np
    cold_start_ttft = []
    warm_start_ttft = []
    
    for cold_run in range(num_cold_starts):
        print(f"COLD START RUN {cold_run + 1}/{num_cold_starts}")
    
        # Wait for cold start (skip on first iteration)
        if cold_run > 0:
            print(f" Waiting {cold_start_wait/60:.1f} minutes for cold start...")
            for remaining in range(cold_start_wait, 0, -30):
                mins, secs = divmod(remaining, 60)
                print(f"   Time remaining: {mins}:{secs:02d}", end='\r')
                time.sleep(30)
            print("\nWait complete!")
        
        # Cold start call
        print(f"\nCold Start Invocation {cold_run + 1}...")
        try:
            result = metrics_test(model_id, system, prompt, region)
            cold_start_ttft.append(result['ttft_ms'])
            print(f"  TTFT: {result['ttft_ms']:.2f}ms")
            print(f" OTPS: {result['otps']:.2f} tokens/s")
        except Exception as e:
            print(f" Error: {e}")
            continue
        
        # Warm calls
        print(f"\nWarm Invocations (1-{num_warm_calls})...")
        for warm_call in range(num_warm_calls):
            try:
                # Small delay between calls 
                time.sleep(0.5)
                
                result = metrics_test(model_id, system, prompt, region)
                warm_start_ttft.append(result['ttft_ms'])
                
                if (warm_call + 1) % 5 == 0:
                    print(f"   [{warm_call + 1}/{num_warm_calls}] TTFT: {result['ttft_ms']:.2f}ms, OTPS: {result['otps']:.2f} tokens/s")
            except Exception as e:
                print(f"   ✗ Error on call {warm_call + 1}: {e}")
                continue
        
        print(f"\n Completed cold start run {cold_run + 1}")
        print(f"   Cold TTFT: {cold_start_ttft[-1]:.2f}ms")
        if len(warm_start_ttft) >= num_warm_calls:
            print(f"   Warm TTFT avg (this run): {sum(warm_start_ttft[-num_warm_calls:])/num_warm_calls:.2f}ms")
    
    results = {
        "cold_start_ttft": cold_start_ttft,
        "warm_start_ttft": warm_start_ttft
    }
    
    return results


def plot_ttft_comparison(results: Dict[str, List[float]]):
    """
    Create box plots comparing cold start vs warm start TTFT.
    
    Args:
        results: Dictionary with 'cold_start_ttft' and 'warm_start_ttft' lists
    """
    import matplotlib.pyplot as plt
    import numpy as np
    
    cold_ttft = results['cold_start_ttft']
    warm_ttft = results['warm_start_ttft']
    
    # Create figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot 1: Box plots side by side
    ax1 = axes[0]
    box_data = [cold_ttft, warm_ttft]
    bp = ax1.boxplot(box_data, tick_labels=['Cold Start', 'Warm Start'], patch_artist=True)
    
    # Color the boxes
    colors = ['lightblue', 'lightcoral']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
    
    ax1.set_ylabel('TTFT (ms)', fontsize=12)
    ax1.set_title('Cold Start vs Warm Start TTFT Distribution', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    # Add statistics as text
    cold_mean = np.mean(cold_ttft)
    cold_std = np.std(cold_ttft)
    warm_mean = np.mean(warm_ttft)
    warm_std = np.std(warm_ttft)
    
    ax1.text(0.02, 0.98, 
             f'Cold Start:\n  Mean: {cold_mean:.2f}ms\n  Std: {cold_std:.2f}ms\n  n={len(cold_ttft)}',
             transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
    
    ax1.text(0.98, 0.98,
             f'Warm Start:\n  Mean: {warm_mean:.2f}ms\n  Std: {warm_std:.2f}ms\n  n={len(warm_ttft)}',
             transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.5))
    
    # Plot 2: Individual data points with trend
    ax2 = axes[1]
    
    # Plot cold starts
    cold_indices = range(len(cold_ttft))
    ax2.scatter(cold_indices, cold_ttft, c='blue', s=100, alpha=0.6, label='Cold Start', marker='o')
    
    # Plot warm starts (spread them out between cold starts)
    warm_per_cold = len(warm_ttft) // len(cold_ttft) if len(cold_ttft) > 0 else len(warm_ttft)
    for i, ttft in enumerate(warm_ttft):
        cold_group = i // warm_per_cold if warm_per_cold > 0 else 0
        offset = (i % warm_per_cold) / warm_per_cold if warm_per_cold > 0 else 0
        x_pos = cold_group + offset
        ax2.scatter(x_pos, ttft, c='red', s=30, alpha=0.4, marker='x')
    
    # Add one label for warm starts
    ax2.scatter([], [], c='red', s=30, alpha=0.6, marker='x', label='Warm Start')
    
    ax2.set_xlabel('Test Sequence', fontsize=12)
    ax2.set_ylabel('TTFT (ms)', fontsize=12)
    ax2.set_title('TTFT Over Time (Cold vs Warm)', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right')
    ax2.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print("\n" + "="*50)
    print("BENCHMARK SUMMARY")
    print("="*50)
    print(f"\nCold Start TTFT:")
    print(f"  Mean: {cold_mean:.2f}ms")
    print(f"  Median: {np.median(cold_ttft):.2f}ms")
    print(f"  Std Dev: {cold_std:.2f}ms")
    print(f"  Min: {min(cold_ttft):.2f}ms")
    print(f"  Max: {max(cold_ttft):.2f}ms")
    
    print(f"\nWarm Start TTFT:")
    print(f"  Mean: {warm_mean:.2f}ms")
    print(f"  Median: {np.median(warm_ttft):.2f}ms")
    print(f"  Std Dev: {warm_std:.2f}ms")
    print(f"  Min: {min(warm_ttft):.2f}ms")
    print(f"  Max: {max(warm_ttft):.2f}ms")
    
    print(f"\nImprovement:")
    print(f"  Cold to Warm: {((cold_mean - warm_mean) / cold_mean * 100):.1f}% faster")
    print("="*50)


def compare_models(custom_model_arn, base_model_id, system, prompt, num_runs=5, region='us-east-1'):
    """
    Compare performance between custom SFT model and base Nova Micro model.
    
    Args:
        custom_model_arn: Your SFT custom model ARN
        base_model_id: Base model ID (e.g., 'us.amazon.nova-micro-v1:0')
        system: System prompt
        prompt: User prompt
        num_runs: Number of test runs for averaging (default: 5)
        region: AWS region
        
    Returns:
        Dictionary with comparison results including averages and differences
    """
    print(f"Comparing models over {num_runs} runs...")
    
    custom_results = []
    base_results = []
    
    # Test custom model
    print(f"\nTesting custom model: {custom_model_arn}")
    for i in range(num_runs):
        try:
            result = metrics_test(custom_model_arn, system, prompt, region)
            custom_results.append(result)
            print(f"  Run {i+1}: TTFT={result['ttft_ms']:.2f}ms, OTPS={result['otps']:.2f}")
        except Exception as e:
            print(f"  Run {i+1} failed: {e}")
    
    # Test base model
    print(f"\nTesting base model: {base_model_id}")
    for i in range(num_runs):
        try:
            result = metrics_test(base_model_id, system, prompt, region)
            base_results.append(result)
            print(f"  Run {i+1}: TTFT={result['ttft_ms']:.2f}ms, OTPS={result['otps']:.2f}")
        except Exception as e:
            print(f"  Run {i+1} failed: {e}")
    
    # Calculate averages
    if custom_results and base_results:
        custom_avg_ttft = sum(r['ttft_ms'] for r in custom_results) / len(custom_results)
        custom_avg_otps = sum(r['otps'] for r in custom_results) / len(custom_results)
        
        base_avg_ttft = sum(r['ttft_ms'] for r in base_results) / len(base_results)
        base_avg_otps = sum(r['otps'] for r in base_results) / len(base_results)
        
        # Calculate percentage differences
        ttft_pct_diff = ((custom_avg_ttft - base_avg_ttft) / base_avg_ttft) * 100
        otps_pct_diff = ((custom_avg_otps - base_avg_otps) / base_avg_otps) * 100
        
        print(f"\n{'='*60}")
        print("PERFORMANCE COMPARISON RESULTS")
        print(f"{'='*60}")
        print(f"\nCustom Model:")
        print(f"  Average TTFT: {custom_avg_ttft:.2f}ms")
        print(f"  Average OTPS: {custom_avg_otps:.2f} tokens/s")
        
        print(f"\nBase Model ({base_model_id}):")
        print(f"  Average TTFT: {base_avg_ttft:.2f}ms")
        print(f"  Average OTPS: {base_avg_otps:.2f} tokens/s")
        
        print(f"\nComparison:")
        ttft_diff = custom_avg_ttft - base_avg_ttft
        otps_diff = custom_avg_otps - base_avg_otps
        
        print(f"  TTFT Difference: {ttft_diff:+.2f}ms ({ttft_pct_diff:+.2f}%)")
        print(f"  OTPS Difference: {otps_diff:+.2f} tokens/s ({otps_pct_diff:+.2f}%)")
        
        if ttft_diff < 0:
            print(f"  → Custom model is {abs(ttft_pct_diff):.1f}% FASTER at first token")
        else:
            print(f"  → Custom model is {ttft_pct_diff:.1f}% SLOWER at first token")
            
        if otps_diff > 0:
            print(f"  → Custom model has {otps_pct_diff:.1f}% HIGHER throughput")
        else:
            print(f"  → Custom model has {abs(otps_pct_diff):.1f}% LOWER throughput")
        
        print(f"{'='*60}\n")
        
        return {
            'custom': {
                'avg_ttft_ms': custom_avg_ttft, 
                'avg_otps': custom_avg_otps,
                'results': custom_results
            },
            'base': {
                'avg_ttft_ms': base_avg_ttft, 
                'avg_otps': base_avg_otps,
                'results': base_results
            },
            'differences': {
                'ttft_diff_ms': ttft_diff, 
                'otps_diff': otps_diff,
                'ttft_pct_diff': ttft_pct_diff,
                'otps_pct_diff': otps_pct_diff
            }
        }
    else:
        print("Error: Not enough successful runs to compare")
        return None

def test(test):
    return test

    
def test_model_throughput(
    model_arn: str,
    region: str = "us-east-1",
    test_cases: Optional[List[Dict[str, str]]] = None,
    iterations: int = 50,
    bedrock_client: Optional[boto3.client] = None
) -> pd.DataFrame:
    """
    Test the throughput (tokens per second) of a deployed Bedrock model.
    
    Args:
        model_arn: ARN of the deployed model to test
        region: AWS region where the model is deployed
        test_cases: List of test case dictionaries with 'name', 'system', and 'prompt' keys.
                   If None, uses default text-to-SQL test cases.
        iterations: Number of iterations to run per test case
        bedrock_client: Optional pre-configured Bedrock runtime client
        
    Returns:
        DataFrame containing test results with columns:
        - query_type: Name of the test case
        - iteration: Iteration number
        - ttft_ms: Time to first token in milliseconds
        - total_time_seconds: Total time for the request
        - generation_time_seconds: Time spent generating tokens
        - output_tokens: Number of tokens generated
        - tokens_per_second: Throughput metric
        - status: Success/error status
    """
    print(f"Testing tokens per second for model: {model_arn}")
    
    # Use default test cases if none provided
    if test_cases is None:
        test_cases = [
            {
                "name": "Simple Query",
                "system": "You are a helpful assistant that translates natural language into SQL queries.",
                "prompt": "Return the SQL query that answers the following question: who is the winner and score for the week of august 9?",
            },
            {
                "name": "Medium Query",
                "system": "You are a helpful assistant that translates natural language into SQL queries.",
                "prompt": "Write a SQL query that joins users and orders tables, filters by date, and calculates average order value grouped by user type."
            },
            {
                "name": "Complex Query",
                "system": "You are a helpful assistant that translates natural language into SQL queries.",
                "prompt": "Create a complex SQL query with multiple joins across users, orders, products, and categories tables, with filtering, grouping, and having clauses."
            }
        ]
    
    # Create Bedrock client if not provided
    if bedrock_client is None:
        client = boto3.client('bedrock-runtime', region_name=region)
    else:
        client = bedrock_client
    
    results = []
    
    for test_case in test_cases:
        print(f"Testing: {test_case['name']}")
        
        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}")
            
            try:
                # Start timing
                start = time.time()
                first_token_time = None
                output_tokens = 0
                
                # Call the model
                response = client.converse_stream(
                    modelId=model_arn,
                    system=[{"text": test_case['system']}],
                    messages=[{"role": "user", "content": [{"text": test_case['prompt']}]}],
                    inferenceConfig={"maxTokens": 512, "temperature": 0}
                )
                
                # Process the streaming response
                for event in response['stream']:
                    # Track first token time
                    if first_token_time is None and 'contentBlockDelta' in event:
                        first_token_time = time.time()
                    
                    # Get token usage
                    if 'metadata' in event and 'usage' in event['metadata']:
                        output_tokens = event['metadata']['usage']['outputTokens']
                
                end = time.time()
                
                # Calculate metrics
                if first_token_time is not None:
                    ttft_seconds = first_token_time - start
                    total_time_seconds = end - start
                    generation_time_seconds = total_time_seconds - ttft_seconds
                    
                    if generation_time_seconds > 0:
                        tokens_per_second = output_tokens / generation_time_seconds
                    else:
                        tokens_per_second = 0
                    
                    # Store results
                    results.append({
                        "query_type": test_case['name'],
                        "iteration": i,
                        "ttft_ms": ttft_seconds * 1000,
                        "total_time_seconds": total_time_seconds,
                        "generation_time_seconds": generation_time_seconds,
                        "output_tokens": output_tokens,
                        "tokens_per_second": tokens_per_second,
                        "status": "success"
                    })
                    
                    print(f"    Tokens per second: {tokens_per_second:.2f} (Total tokens: {output_tokens})")
                else:
                    print("    No content received")
                    results.append({
                        "query_type": test_case['name'],
                        "iteration": i,
                        "status": "no_content"
                    })
            
            except Exception as e:
                print(f"    Error: {str(e)}")
                results.append({
                    "query_type": test_case['name'],
                    "iteration": i,
                    "status": f"error: {str(e)}"
                })
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    success_df = df[df['status'] == 'success']
    
    if len(success_df) > 0:
        # Calculate summary statistics
        summary = success_df.groupby('query_type').agg({
            'tokens_per_second': ['mean', 'min', 'max'],
            'output_tokens': ['mean', 'min', 'max'],
            'ttft_ms': ['mean', 'min', 'max']
        })
        
        print("Throughput Summary:")
        print(summary)
        
        print("Overall Throughput Metrics:")
        print(f"  Average tokens per second: {success_df['tokens_per_second'].mean():.2f}")
        print(f"  Average TTFT: {success_df['ttft_ms'].mean():.2f} ms")
        print(f"  Average output tokens: {success_df['output_tokens'].mean():.2f}")
    else:
        print("No successful results to analyze.")
    
    return df


def visualize_throughput_results(df: pd.DataFrame, show_plots: bool = True) -> None:
    """
    Create visualizations for throughput test results.
    
    Args:
        df: DataFrame returned from test_model_throughput()
        show_plots: Whether to display plots (set to False in non-interactive environments)
    """
    success_df = df[df['status'] == 'success']
    
    if len(success_df) == 0:
        print("No successful results to visualize.")
        return
    
    # Create visualization 1: Bar plot of tokens per second by query type
    plt.figure(figsize=(10, 6))
    sns.barplot(x='query_type', y='tokens_per_second', data=success_df)
    plt.title('Tokens Per Second by Query Type')
    plt.ylabel('Tokens Per Second')
    plt.xlabel('Query Type')
    plt.tight_layout()
    if show_plots:
        plt.show()
    
    # Create visualization 2: Boxplot to show distribution
    plt.figure(figsize=(10, 6))
    sns.boxplot(x='query_type', y='tokens_per_second', data=success_df)
    plt.title('Tokens Per Second Distribution')
    plt.ylabel('Tokens Per Second')
    plt.xlabel('Query Type')
    plt.tight_layout()
    if show_plots:
        plt.show()
    
    # Create visualization 3: Scatterplot of tokens vs time
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='output_tokens', y='generation_time_seconds', 
                   hue='query_type', data=success_df)
    plt.title('Generation Time vs Output Tokens')
    plt.ylabel('Generation Time (seconds)')
    plt.xlabel('Output Tokens')
    plt.tight_layout()
    if show_plots:
        plt.show()
