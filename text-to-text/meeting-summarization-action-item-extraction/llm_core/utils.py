# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import time
import nltk
import json
from nltk import word_tokenize
from llm_core.bedrock_helper import (get_bedrock_response, 
                            get_bedrock_ondemand_cost,
                            MISTRAL_L2_MODEL_ID,
                            MISTRAL_L_MODEL_ID,
                            MISTRAL_S_MODEL_ID,
                            CLAUDE_ID_LIST,
                            LLAMA_ID_LIST,
                            NOVA_LIST)


# tokneize a sentence
def tokenize(sent):    
    tokens = ' '.join(word_tokenize(sent.lower()))
    return tokens

# filter some noises caused by speech recognition
def clean_data(text):
    not_allowable_list = ['um ', 'uh ', 'hmm ', 'mm-hmm ', 'mm ', '{ vocalsound } ', '{ disfmarker } ', '{ pause } ','{ nonvocalsound } ',
                          '{ gap } ', '{vocalsound}','{disfmarker}','{pause}', '{nonvocalsound}','{gap}']
    for w in not_allowable_list: text = text.replace(w, '') 

    text = text.replace('a_m_i_', 'ami')
    text = text.replace('l_c_d_', 'lcd')
    text = text.replace('p_m_s', 'pms')
    text = text.replace('t_v_', 'tv')

    return text


def generate_partial_action_items(usr_msg,
                                max_tokens=2000, 
                                temp=0,
                                topP=1, 
                                topK=250, 
                                stop_sequences=["Human:"], 
                                model_id = None, 
                                text_only=True ):
    
    
    response = get_bedrock_response(usr_msg,  
                                    max_tokens=max_tokens, 
                                    temp=temp,
                                    topK=topK, 
                                    stop_sequences=stop_sequences, 
                                    model_id = model_id, 
                                    text_only=text_only )
    return response


def aggregate_partial_action_items(usr_msg,
                                max_tokens=2000, 
                                temp=0,
                                topP=1, 
                                topK=250, 
                                stop_sequences=["Human:"], 
                                model_id = None, 
                                text_only=True ):
    
    
    response = get_bedrock_response(usr_msg, 
                                    system = "You are a highly skilled AI meeting action items assistant",
                                    max_tokens=max_tokens, 
                                    temp=temp,
                                    topK=topK, 
                                    stop_sequences=stop_sequences, 
                                    model_id = model_id, 
                                    text_only=text_only )
    return response


def get_LLM_text_response(model_id, response):
    
    if model_id == MISTRAL_L2_MODEL_ID:
        response_text = response['choices'][0]['message']['content']
    elif model_id == MISTRAL_L_MODEL_ID or model_id == MISTRAL_S_MODEL_ID:
        response_text = response['outputs'][0]['text']
    elif model_id in CLAUDE_ID_LIST:
        response_text = response['content'][0]['text']
    elif model_id in LLAMA_ID_LIST:
        response_text = response['generation']
    else:
        print("model id unknown")
        
    return response_text


def get_action_items_stage_1(partial_gen_prompt,
                             transcript, 
                             model_id, 
                             temperature, 
                             chapter_num):
    '''This function takes a single chapter of a meeting transcript and return:
        - generated partial action items
        - latency for generating the partial action items
        - cost for generating the partial action items
    '''
    
    curr_chapter = (transcript['chapters'][0][chapter_num]['transcript_text'].lower())
    
    partial_gen_prompt_formatted = partial_gen_prompt.format(chapter_transcript = curr_chapter)
    
    start_time = time.time()
    chapter_response_raw = generate_partial_action_items(partial_gen_prompt_formatted,
                                                     max_tokens=2000, 
                                                     temp=temperature,
                                                     topP=1, 
                                                     topK=250, 
                                                     model_id=model_id, 
                                                     text_only=False)
    end_time = time.time()
    chapter_latency = end_time - start_time
    
    chapter_cost = get_bedrock_ondemand_cost(curr_chapter, chapter_response_raw, model_id = model_id)
   
    chapter_response = get_LLM_text_response(model_id, chapter_response_raw)

    return chapter_latency, chapter_response, chapter_cost



