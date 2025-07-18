# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pandas as pd
from typing import List
import time
from threading import Thread
import concurrent.futures
import json
from llm_core.bedrock_helper import get_bedrock_response, get_bedrock_ondemand_cost, NOVA_PRO_MODEL_ID 
from llm_core.utils import generate_partial_action_items, aggregate_partial_action_items, get_LLM_text_response, get_action_items_stage_1
from llm_core.llm_prompt_bank import (one_stage_meeting_action_prompt,
                             two_stage_partial_meeting_action_generation_prompt, 
                             two_stage_partial_meeting_action_aggregation_prompt)

from llm_core.llm_prompt_bank import (one_stage_meeting_action_system_prompt_v2, 
                                    one_stage_meeting_action_usr_prompt_v2, 
                                    meeting_action_assistant_prompt)

def generate_meeting_action_item(transcript: str,                          
                                max_tokens: int=2000, 
                                temp:float=0, 
                                topK:int=50, 
                                stop_sequences:List=["Human:"], 
                                model_id:str=None, 
                                text_only:bool=True ):
    '''
    Generate meeting-level action items for a given meeting transcript.
    '''

    
    usr_msg = one_stage_meeting_action_prompt.format(meeting_transcript = transcript
    )
    
    response = get_bedrock_response( user_message = usr_msg, 
                                    max_tokens = max_tokens, 
                                    temp = temp,
                                    topK = topK, 
                                    stop_sequences=stop_sequences,
                                    model_id = model_id,
                                    text_only=text_only )
    
    return response


def generate_meeting_action_item_v2(transcript: str,
                                max_tokens: int=2000, 
                                temp:float=0, 
                                topK:int=50, 
                                stop_sequences:List=["Human:", "</action_item>"], 
                                model_id:str=None, 
                                text_only:bool=True ):
    '''
    Generate meeting-level action items for a given meeting transcript.
    '''
            
    usr_msg = one_stage_meeting_action_usr_prompt_v2.format(meeting_transcript = transcript
    )
    
    response = get_bedrock_response( user_message = usr_msg,
                                    system = one_stage_meeting_action_system_prompt_v2,
                                    assistant_message=meeting_action_assistant_prompt,
                                    max_tokens = max_tokens, 
                                    temp = temp,
                                    topK = topK, 
                                    stop_sequences=stop_sequences,
                                    model_id = model_id,
                                    text_only=text_only )
    
    return response



def generate_meeting_action_items_two_stages(df, model_id, temperature, n_chapters):
    
    # Stage 1: Use ThreadPoolExecutor to parallel process single meeting chapter
    
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Map the process_chapter function to the range of chapters
        chapter_results = list(executor.map(get_action_items_stage_1, [two_stage_partial_meeting_action_generation_prompt] * n_chapters,
                                            [transcript]*n_chapters, 
                                            [model_id]*n_chapters, 
                                            [temperature]*n_chapters, 
                                            range(n_chapters))
                              )
    end_time = time.time()
    stage1_latency = end_time - start_time  
    stage1_llm_response = ""
    stage1_cost = 0
    
    # Aggregate results from the threads
    for _, chapter_response, chapter_cost in chapter_results:
        stage1_llm_response += chapter_response
        stage1_cost += chapter_cost

    
    # Stage 2: Compile partial action items into final list

    partial_agg_prompt = two_stage_partial_meeting_action_aggregation_prompt.format(meeting_action_items = stage1_llm_response)
    
    
    start_time = time.time()
    stage2_llm_response_raw = aggregate_partial_action_items(partial_agg_prompt, 
                                                      max_tokens=2000, 
                                                      temp=temperature,
                                                      topP=1, 
                                                      topK=250, 
                                                      model_id=model_id, 
                                                      text_only=False)
    
    end_time = time.time()
    stage2_latency = end_time - start_time
    stage2_cost = get_bedrock_ondemand_cost(stage1_llm_response, stage2_llm_response_raw, model_id=model_id)    
    stage2_llm_response = get_LLM_text_response(model_id, stage2_llm_response_raw)
    
    total_cost = stage1_cost + stage2_cost
    total_latency = stage1_latency + stage2_latency
    
    return stage1_llm_response, stage2_llm_response, total_latency, total_cost 



# ## Example use
# input_file = '../data/test_data/test_1.json'
# transcript = pd.read_json(path_or_buf=input_file, lines=True)
        
# n_chapters = transcript['video_metadata'][0]['n_chapters']
# print(f'Number of chapters: {n_chapters}')

# model_id = NOVA_PRO_MODEL_ID 
# temp = 0.2
# stage1_llm_response, stage2_llm_response, total_latency, total_cost = generate_meeting_action_items_two_stages(transcript, model_id, temp, n_chapters)  

# print(f'stage1_llm_response:, {stage1_llm_response}', '\n')
# print(f'stage2_llm_response: {stage2_llm_response}', '\n')

