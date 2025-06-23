# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import json
import base64
import boto3
import pathlib
from botocore.config import Config
from botocore.exceptions import ClientError

from mistral_common.protocol.instruct.messages import (
    UserMessage,
)
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer


# Sonnet 3.5 default quota only available in us-west-2
BEDROCK_CONFIG = Config(
    region_name = 'us-west-2',
    signature_version = 'v4',
    read_timeout = 500,
    retries = {
        'max_attempts': 3,
        'mode': 'standard'
    }
)


BEDROCK_RT = boto3.client("bedrock-runtime", config = BEDROCK_CONFIG)

BEDROCK_EAST_CONFIG = Config(
    region_name = 'us-east-1',
    signature_version = 'v4',
    read_timeout = 500,
    retries = {
        'max_attempts': 3,
        'mode': 'standard'
    }
)

BEDROCK_RT_EAST = boto3.client("bedrock-runtime", config = BEDROCK_EAST_CONFIG)

HAIKU_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
SONNET35_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"
SONNET_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
OPUS_MODEL_ID = "anthropic.claude-3-opus-20240229-v1:0"

LLAMA3_8B_MODEL_ID = "meta.llama3-8b-instruct-v1:0"
LLAMA3_70B_MODEL_ID = "meta.llama3-70b-instruct-v1:0"

LLAMA31_8B_MODEL_ID = "meta.llama3-1-8b-instruct-v1:0"
LLAMA31_70B_MODEL_ID = "meta.llama3-1-70b-instruct-v1:0"

LLAMA32_1B_MODEL_ID = "us.meta.llama3-2-1b-instruct-v1:0"
LLAMA32_3B_MODEL_ID = "us.meta.llama3-2-3b-instruct-v1:0"
LLAMA32_11B_MODEL_ID = "us.meta.llama3-2-11b-instruct-v1:0"
LLAMA32_90B_MODEL_ID = "us.meta.llama3-2-90b-instruct-v1:0"

MISTRAL_L_MODEL_ID = "mistral.mistral-large-2402-v1:0"
MISTRAL_S_MODEL_ID = "mistral.mistral-small-2402-v1:0"
MISTRAL_L2_MODEL_ID = "mistral.mistral-large-2407-v1:0"

NOVA_PRO_MODEL_ID = "us.amazon.nova-pro-v1:0"
NOVA_LITE_MODEL_ID = "us.amazon.nova-lite-v1:0"
NOVA_MICRO_MODEL_ID = "us.amazon.nova-micro-v1:0"
NOVA_PREMIER_MODEL_ID ="us.amazon.nova-premier-v1:0"


CLAUDE_ID_LIST = [ HAIKU_MODEL_ID, 
                  SONNET35_MODEL_ID,
                  SONNET_MODEL_ID,
                  OPUS_MODEL_ID ]

LLAMA_ID_LIST = [LLAMA3_8B_MODEL_ID, 
                 LLAMA3_70B_MODEL_ID, 
                 LLAMA31_8B_MODEL_ID, 
                 LLAMA31_70B_MODEL_ID,
                 LLAMA32_1B_MODEL_ID,
                 LLAMA32_3B_MODEL_ID,
                 LLAMA32_11B_MODEL_ID,
                 LLAMA32_90B_MODEL_ID ]

MISTRAL_LIST = [MISTRAL_L_MODEL_ID, 
                MISTRAL_S_MODEL_ID ]

MISTRAL_V2_LIST = [MISTRAL_L2_MODEL_ID]

MISTRAL_ALL_LIST = MISTRAL_LIST + MISTRAL_V2_LIST

NOVA_LIST = [ NOVA_PRO_MODEL_ID, 
             NOVA_LITE_MODEL_ID, 
             NOVA_MICRO_MODEL_ID,
            NOVA_PREMIER_MODEL_ID]

def get_bedrock_response( user_message="Hello!",
                         system = "",
                         assistant_message= "",
                         max_tokens=250, 
                         temp=0,
                         topK=50, 
                         stop_sequences=["Human:"], 
                         model_id = SONNET35_MODEL_ID, 
                         text_only=True):
    '''
    Bedrock helper function to invoke Bedrock call
    '''
    if model_id in CLAUDE_ID_LIST:
        response = get_claude_response(user_message=user_message,
                                       system = system,
                                       assistant_message= assistant_message,
                                       max_tokens=max_tokens, 
                                       temp=temp,
                                       topK=topK, 
                                       stop_sequences=stop_sequences, 
                                       model_id = model_id)
    elif model_id in LLAMA_ID_LIST:
        response = get_llama3_response( user_message = user_message,
                                      system_message = system,
                                      assistant_message = assistant_message,
                                      max_tokens=max_tokens, 
                                      temp=temp,
                                      stop_sequences=stop_sequences, 
                                      model_id = model_id)
    elif model_id in MISTRAL_LIST:
        response = get_mistral_response( user_message = user_message,
                                        system_message = system,
                                        assistant_message = assistant_message,
                                        max_tokens=max_tokens, 
                                        temp=temp,
                                        model_id = model_id)
    elif model_id in MISTRAL_V2_LIST:
        response = get_mistral_v2_response( user_message=user_message,
                                           system = system,
                                           assistant_message= assistant_message,
                                           max_tokens=max_tokens, 
                                           temp=temp,
                                           topK=topK, 
                                           stop_sequences=stop_sequences, 
                                           model_id = model_id )
    elif model_id in NOVA_LIST:
        response = get_nova_response( user_message=user_message,
                                           system = system,
                                           assistant_message= assistant_message,
                                           max_tokens=max_tokens, 
                                           temp=temp,
                                           topK=topK, 
                                           stop_sequences=stop_sequences, 
                                           model_id = model_id )
    else:
        return "Unknown Bedrock Model ID"

    if text_only:
        response = get_bedrock_text_only_response( response, model_id=model_id )

    return response

def get_bedrock_text_only_response( response, model_id=SONNET35_MODEL_ID):
    '''
    Simple function to get the text only response from the raw Bedrock response
    '''

    if model_id in CLAUDE_ID_LIST:
        response = get_claude_response_text( response )
    elif model_id in LLAMA_ID_LIST:
        response = get_llama_response_text( response )
    elif model_id in MISTRAL_LIST:
        response = get_mistral_response_text( response )
    elif model_id in MISTRAL_V2_LIST:
        response = get_mistral_v2_response_text( response )
    elif model_id in NOVA_LIST:
        response = get_nova_response_text( response )

    return response 


############################
#          CLAUDE          #
############################

def create_claude_body( messages = [{"role": "user", "content": "Hello!"}], 
                       system = "You are an AI chatbot.",
                       max_tokens=2048, 
                       temp=0, 
                       topK=250, 
                       stop_sequences=["Human"]):
    """
    Simple function for creating a body for Anthropic Claude models for the Messages API.
    https://docs.anthropic.com/claude/reference/messages_post
    """
    body = {
        "messages": messages,
        "max_tokens": max_tokens,
        "system":system,
        "temperature": temp,
        "anthropic_version":"",
        "top_k": topK,
        "stop_sequences": stop_sequences
    }
    
    return body

def get_claude_response(user_message="Hello!", 
                        system = "You are an AI chatbot.",
                        assistant_message= "",
                        max_tokens=250, 
                        temp=0,
                        topK=250, 
                        stop_sequences=["Human:"], 
                        model_id = SONNET35_MODEL_ID):
    """
    Simple function for calling Claude via boto3 and the invoke_model API. 
    """
    
    if assistant_message == "":
        messages = [{"role": "user", "content": user_message}]
    else:
        messages = [{"role": "user", "content": user_message}, {"role": "assistant", "content": assistant_message}]
    
    body = create_claude_body(messages=messages, 
                              system = system,
                              max_tokens=max_tokens, 
                              temp=temp,
                              topK=topK, 
                              stop_sequences=stop_sequences)
    
    response = BEDROCK_RT.invoke_model(modelId=model_id, body=json.dumps(body))
    response = json.loads(response['body'].read().decode('utf-8'))
    
    return response

def get_claude_response_text( response ):
    return response['content'][0]['text']

###########################
#         LLAMA 3         #
###########################

def create_llama3_prompt(user_message = "Hello!",
                         system_message = "You are an AI chatbot.",
                         assistant_message = ""
                        ):
    prompt = f"""
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>{system_message}<|eot_id|>
    <|start_header_id|>user<|end_header_id|>{user_message}<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>{assistant_message}
    """
    return prompt

def get_llama3_response(user_message = "Hello!",
                        system_message = "You are an AI chatbot.",
                        assistant_message = "",
                        max_tokens=250, 
                        temp=0,
                        stop_sequences=["Human:"], 
                        model_id = LLAMA31_70B_MODEL_ID):
    prompt = create_llama3_prompt(user_message=user_message, system_message=system_message,assistant_message=assistant_message)
    #print(prompt)
    try:
        body = {
            "prompt": prompt,
            "temperature": temp,
            "top_p": 1,
            "max_gen_len": max_tokens,
        }

        response = BEDROCK_RT.invoke_model(
            modelId=model_id, body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())
        return response_body

    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        raise
        
def get_llama_response_text(response):
    completion = response["generation"]
    return completion


###########################
#         MISTRAL         #
###########################
def create_mistral_body( user_message = "Hello!",
                        system_message = "You are an AI chatbot.",
                        max_tokens=2048, 
                        temp=0, 
                        topK=50, 
                        stop_sequences=["Human:"]):
    '''
    Create Bedrock call body for Mistral S/L for text completion
    '''
    prompt = f"""<s>[INST] {system_message}\n {user_message} [/INST]"""
    
    body = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "stop": stop_sequences,
        "temperature": temp,
        "top_k": topK,
    }
    
    return body

def get_mistral_response( user_message="Hello!", 
                         system_message = "You are an AI chatbot.",
                         assistant_message= "",
                         max_tokens=250, 
                         temp=0,
                         topK=50, 
                         stop_sequences=["Human:"], 
                         model_id = MISTRAL_L_MODEL_ID):
    """
    Simple function for calling Mistral S/L via boto3 and the invoke_model API for text completion. 
    """
    body = create_mistral_body(user_message=user_message, 
                              system_message = system_message,
                              max_tokens=max_tokens, 
                              temp=temp,
                              topK=topK, 
                              stop_sequences=stop_sequences)
    try:
        response = BEDROCK_RT_EAST.invoke_model(modelId=model_id, body=json.dumps(body))
    except Exception as e:
        response = None
        print(f"Error: {e}")
    
    if response:
        response = json.loads(response['body'].read().decode('utf-8'))
    
    return response

def get_mistral_response_text(response):
    if response:
        return response['outputs'][0]['text']
    else:
        return None

############################
#         MISTRAL L2       #
############################
def create_mistral_v2_body( messages = [{"role": "user", "content": "Hello!"}], 
                           system = "",
                           max_tokens=2048, 
                           temp=0, 
                           topK=250, 
                           stop_sequences=["Human"]):
    """
    Simple function for creating a body for Mistral L2 for the Messages API.
    https://docs.anthropic.com/claude/reference/messages_post
    """
#     body = {
#         "messages": messages,
#         "max_tokens": max_tokens,
#         "temperature": temp,
#         "stop_sequences": stop_sequences
#     }
    body = {
        "messages": messages,
    }    
    return body

def get_mistral_v2_response( user_message="Hello!", 
                            system = "",
                            assistant_message= "",
                            max_tokens=250, 
                            temp=0,
                            topK=250, 
                            stop_sequences=["Human:"], 
                            model_id = MISTRAL_L2_MODEL_ID):
    """
    Simple function for calling Mistral L2 via boto3 and the invoke_model API. 
    """
    
    if not system == "":
        messages = [ {"role": "system", "content": system}, {"role": "user", "content": user_message}]
    else:
        messages = [{"role": "user", "content": user_message}]
    
    # if not assistant_message == "":
    #     assist_msg= {"role": "assistant", "content": assistant_message, "prefix": True }
    #     messages.append( assist_msg )
    
    body = create_mistral_v2_body(messages=messages, 
                                  max_tokens=max_tokens, 
                                  temp=temp,
                                  topK=topK, 
                                  stop_sequences=stop_sequences)
    
    response = BEDROCK_RT.invoke_model(modelId=model_id, body=json.dumps(body))
    response = json.loads(response['body'].read().decode('utf-8'))
    
    return response

def get_mistral_v2_response_text(response):
    return response['choices'][0]['message']['content']

def get_mistral_token_length( message ):
    '''
    Simple function to get the token length for Mistral S, L, L2
    '''

    tokenizer = MistralTokenizer.v2()
    model_name = "mistral-small-latest"
    tokenizer = MistralTokenizer.from_model(model_name)

    # Tokenize a list of messages
    tokenized = tokenizer.encode_chat_completion(
        ChatCompletionRequest(
            messages=[
                UserMessage(content=message),
            ],
            model=model_name,
        )
    )
    tokens = tokenized.tokens

    return len( tokens )

#########################
#          Nova         # 
#########################
def create_nova_body( messages = [{"role": "user", "content": "Hello!"}],
                     system = "",
                     max_tokens=2048, 
                     temp=0.5,
                     topP=0.5,
                     topK=250, 
                     stop_sequences=["Human"]):
    """
    Simple function for creating a body for Amazon Nova
    """
    inf_params = {
        "maxTokens": max_tokens,
        "topP": topP,
        "topK": topK, 
        "temperature": temp,       
    }

    body = {
        "schemaVersion": "messages-v1",
        "messages": messages,
        "system": system,
        "inferenceConfig": inf_params,
    }
    #print(f' {body}')
    return body

def get_nova_response(user_message="Hello!",
                      system = "",
                      assistant_message= "",
                      image_path="",
                      max_tokens=512,
                      temp=0.7,
                      topP=0.9,
                      topK=250, 
                      stop_sequences=["Human:"], 
                      model_id = NOVA_LITE_MODEL_ID):
    """
    Simple function for calling Nova via boto3 and the invoke_model API. 
    """
    
    if assistant_message == "":
        messages = [ { "role": "user", "content": [ {"text": user_message} ] } ]
    else:
        messages = [ {"role": "user", "content": [ {"text": user_message} ] }, {"role": "assistant", "content": [ {"text": assistant_message} ] } ]
    
    system_messages = [ { "text": system } ]
   
    # Define the input for the model
   
    
    system_messages = [ { "text": system } ]
    body = {
    "messages": messages,
    "inferenceConfig": {
            "max_new_tokens": 512,
            "temperature":0.2
        },
    "system": system_messages
    }
    '''
    body = create_nova_body(messages=messages, 
                            system = system_messages,
                            max_tokens=max_tokens, 
                            temp=temp,
                            topP=topP,
                            topK=topK, 
                            stop_sequences=stop_sequences)
    '''
    response = BEDROCK_RT_EAST.invoke_model(modelId=model_id, body=json.dumps(body))
    response_decode = json.loads(response['body'].read().decode('utf-8'))
    '''
    response_body = json.loads(response['body'].read())
    res_j_in_tok = response_body[ 'usage' ]['inputTokens']
    res_j_out_tok = response_body[ 'usage' ]['outputTokens']
    res_j_tot_tok = response_body[ 'usage' ]['totalTokens']
    '''
    
    return response_decode #, res_j_in_tok, res_j_out_tok,res_j_tot_tok

def get_nova_response_text( response ):
    return response['output']['message']['content'][0]['text']

####################################
#         Cost/token matrix        #
####################################
cost_dict_haiku = { 'input': 0.00000025, 'output': 0.00000125}
cost_dict_sonnet = { 'input': 0.000003, 'output': 0.000015 }
cost_dict_sonnet35 = { 'input': 0.000003, 'output': 0.000015 } 
cost_dict_opus = { 'input': 0.000015, 'output': 0.000075}

cost_dict_llama3_8b = { 'input': 0.0000003, 'output': 0.0000006}
cost_dict_llama3_70b = { 'input': 0.00000265, 'output': 0.0000035}

cost_dict_llama31_8b = { 'input': 0.00000022, 'output': 0.00000022}
cost_dict_llama31_70b = { 'input': 0.00000099, 'output': 0.00000099}

cost_dict_llama32_1b = { 'input': 0.0000001, 'output': 0.0000001}
cost_dict_llama32_3b = { 'input': 0.00000015, 'output': 0.00000015}
cost_dict_llama32_11b = { 'input': 0.00000035, 'output': 0.00000035}
cost_dict_llama32_90b = { 'input': 0.000002, 'output': 0.000002}


cost_dict_mistral_s = { 'input': 0.000001, 'output': 0.000003}
cost_dict_mistral_l = { 'input': 0.000004, 'output': 0.000012}
cost_dict_mistral_l2 = { 'input': 0.000002, 'output': 0.000006}

cost_dict_nova_micro = { 'input': 0.000000035, 'output': 0.00000014}
cost_dict_nova_lite = { 'input': 0.00000006, 'output': 0.00000024}
cost_dict_nova_pro = { 'input': 0.0000008, 'output': 0.0000032}
cost_dict_nova_premier = { 'input': 0.0000025, 'output': 0.0000125}

bedrock_ondemand_cost_dict = {
    HAIKU_MODEL_ID: cost_dict_haiku,
    SONNET_MODEL_ID: cost_dict_sonnet,
    SONNET35_MODEL_ID: cost_dict_sonnet35,
    OPUS_MODEL_ID: cost_dict_opus,
    LLAMA3_8B_MODEL_ID: cost_dict_llama3_8b,
    LLAMA3_70B_MODEL_ID: cost_dict_llama3_70b,
    LLAMA31_8B_MODEL_ID: cost_dict_llama31_8b,
    LLAMA31_70B_MODEL_ID: cost_dict_llama31_70b,
    LLAMA32_1B_MODEL_ID: cost_dict_llama32_1b,
    LLAMA32_3B_MODEL_ID: cost_dict_llama32_3b,
    LLAMA32_11B_MODEL_ID: cost_dict_llama32_11b,
    LLAMA32_90B_MODEL_ID: cost_dict_llama32_90b,
    MISTRAL_S_MODEL_ID: cost_dict_mistral_s,
    MISTRAL_L_MODEL_ID: cost_dict_mistral_l,
    MISTRAL_L2_MODEL_ID: cost_dict_mistral_l2,
    NOVA_MICRO_MODEL_ID: cost_dict_nova_micro,
    NOVA_LITE_MODEL_ID: cost_dict_nova_lite,
    NOVA_PRO_MODEL_ID: cost_dict_nova_pro,
    NOVA_PREMIER_MODEL_ID: cost_dict_nova_premier,
}

def get_bedrock_ondemand_cost( input, output_response, model_id, in_tok=0, out_tok=0, tot_tok=0 ):
    '''
    Simple function to calculate the ondemand cost per query. 
    Must get the raw response from the Bedrock Invoke call
    '''

    if model_id in MISTRAL_ALL_LIST:
        if model_id == MISTRAL_L2_MODEL_ID:
            output_text = get_mistral_v2_response_text( output_response )
            in_tok = get_mistral_token_length( input )
            out_tok = get_mistral_token_length( output_text )
        else:
            output_text = get_mistral_response_text( output_response )
            in_tok = get_mistral_token_length( input )
            out_tok = get_mistral_token_length( output_text )
    elif model_id in CLAUDE_ID_LIST:
        in_tok = output_response[ 'usage' ][ 'input_tokens' ]
        out_tok = output_response[ 'usage' ][ 'output_tokens' ]
    elif model_id in LLAMA_ID_LIST:
        in_tok = output_response[ 'prompt_token_count' ]
        out_tok = output_response[ 'generation_token_count' ]
    
    elif model_id in NOVA_LIST:
        #print(output_response)
        in_tok = output_response[ 'usage' ]['inputTokens']
        out_tok = output_response[ 'usage' ]['outputTokens']
        tot_tok = output_response[ 'usage' ]['totalTokens']
        #print(in_tok)
    in_cost = bedrock_ondemand_cost_dict[ model_id ][ 'input' ] * in_tok
    out_cost = bedrock_ondemand_cost_dict[ model_id ][ 'output' ] * out_tok
    cost = in_cost + out_cost

    return cost


############################
#     Embedding models     #
############################
COHERE_EMBED_ENG_V3 = 'cohere.embed-english-v3'
TITAN_TEXT_EMBED_V2 = "amazon.titan-embed-text-v2:0"


def titan_multimodal_embedding(
    image_path:str=None,  # maximum 2048 x 2048 pixels
    description:str=None, # English only and max input tokens 128
    dimension:int=1024,   # 1,024 (default), 384, 256
    model_id:str="amazon.titan-embed-image-v1"
):
    '''
    Ref: https://github.com/aws-samples/amazon-bedrock-workshop/blob/main/04_Image_and_Multimodal/bedrock-titan-multimodal-embeddings.ipynb
    '''
    payload_body = {}
    embedding_config = {
        "embeddingConfig": { 
             "outputEmbeddingLength": dimension
         }
    }
    
    # You can specify either text or image or both
    if image_path:
        with open(image_path, "rb") as image_file:
            input_image = base64.b64encode(image_file.read()).decode('utf8')
        payload_body["inputImage"] = input_image
    if description:
        payload_body["inputText"] = description

    assert payload_body, "please provide either an image and/or a text description"
#     print("\n".join(payload_body.keys()))

    response = BEDROCK_RT_EAST.invoke_model(
        body=json.dumps({**payload_body, **embedding_config}), 
        modelId=model_id,
        accept="application/json", 
        contentType="application/json"
    )
    embed_vec = json.loads(response.get("body").read())['embedding']
    return embed_vec


def titan_text_embeddings( input_text:str,
                          model_id:str=TITAN_TEXT_EMBED_V2 ):
    """
    Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-embed-text.html
    
    Generate a vector of embeddings for a text input using Amazon Titan Embeddings G1 - Text on demand.
    Args:
        input_text (str): Input text 
        model_id (str): The model ID to use.
    Returns:
        embed_vec (List): Embedding vector.
    """

    # Create request body.
    body = json.dumps({
        "inputText": input_text,
    })

    accept = "application/json"
    content_type = "application/json"

    response = BEDROCK_RT_EAST.invoke_model(
        body=body, 
        modelId=model_id, 
        accept=accept, 
        contentType=content_type
    )

    response_body = json.loads(response.get('body').read())
    embed_vec = response_body['embedding']
    return embed_vec

def cohere_text_embeddings( input_text:str,
                           input_type:str="search_document",
                          model_id:str=COHERE_EMBED_ENG_V3 ):
    """
    Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-embed-text.html
    
    Generate a vector of embeddings for a text input using Amazon Titan Embeddings G1 - Text on demand.
    Args:
        input_text (str): Input text 
        model_id (str): The model ID to use.
    Returns:
        embed_vec (List): Embedding vector.
    """

    # Create request body.
    body = json.dumps({
        "texts": [input_text],
        "input_type": input_type
    })

    accept = "application/json"
    content_type = "application/json"

    response = BEDROCK_RT_EAST.invoke_model(
        body=body, 
        modelId=model_id, 
        accept=accept, 
        contentType=content_type
    )

    response_body = json.loads(response.get('body').read())
    embed_vec = response_body['embeddings'][0]
    return embed_vec