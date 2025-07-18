# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import List
import json
import time

from .bedrock_helper import NOVA_PRO_MODEL_ID
from .bedrock_helper import get_bedrock_ondemand_cost, get_bedrock_text_only_response

from .llm_summarization import generate_topic_segmented_meeting_transcript_combined_v2
from .llm_meeting_actions import generate_meeting_action_item_v2
from .llm_part_actions import generate_person_action_item, generate_person_action_item_v2
from .utils import clean_data

def run_summarizer( input_file_path: str,
                   max_tokens:int=2000, 
                   temp:float=0.5, 
                   topK:int=250, 
                   stop_sequences:List =["Human:"],           
                   model_ids:List=[NOVA_PRO_MODEL_ID], 
                   text_only:bool=True, 
                   prompt_ver:str='default', 
                   save:bool=True,
                   output_file_path: str="output.json", 
                   latency:bool=False, 
                   cost:bool=False,
                   summary_2stage: bool=False,
                   meeting_action_2stage: bool=False,
                   part_action_2stage: bool=False):
    '''
    Run all summarizer and action item extractors.
    '''
    with open( input_file_path, 'r', encoding='utf-8' ) as f:
        input_data = json.load( f )
        
    transcript = input_to_merged_trans( input_data )
    
    summary_list =[]
    meeting_action_list = []
    participant_action_list = []
    
    for model_id in model_ids:
        print( "======================" )
        print( model_id  )  
        ###########################
        #      Summarization      #
        ###########################

       
        if latency:
            start_time = time.time()

        if cost: 
            
            summary = generate_topic_segmented_meeting_transcript_combined_v2( transcript, 
                                                max_tokens, 
                                                temp, 
                                                topK, 
                                                stop_sequences, 
                                                model_id, 
                                                text_only=False )
            if latency:
                end_time = time.time()
                summary_time = end_time - start_time 

            summary_cost = get_bedrock_ondemand_cost( transcript, summary, model_id=model_id )
            summary = get_bedrock_text_only_response( summary, model_id=model_id)
            
        else:
            summary = generate_topic_segmented_meeting_transcript_combined_v2( transcript, 
                                                max_tokens, 
                                                temp, 
                                                topK, 
                                                stop_sequences, 
                                                model_id, 
                                                text_only=True )

            if latency:
                end_time = time.time()
                summary_time = end_time - start_time 
        
        summary_out_dict = output_dict_formatter( summary, 
                                                 temp, 
                                                 model_id, 
                                                 prompt_ver )
        if latency:
            summary_out_dict[ 'latency' ] = summary_time
        
        if cost:
            summary_out_dict[ 'cost' ] = summary_cost
        
        summary_list.append( summary_out_dict )

        #############################
        #      Meeting actions      #
        #############################
        if latency:
            start_time = time.time()

        if cost:
            meeting_action_items = generate_meeting_action_item_v2( transcript, 
                                                                max_tokens, 
                                                                temp, 
                                                                topK, 
                                                                stop_sequences, 
                                                                model_id, 
                                                                text_only=False )
            if latency:
                end_time = time.time()
                action_time = end_time - start_time 
            
            meeting_action_cost = get_bedrock_ondemand_cost( transcript, meeting_action_items, model_id=model_id )
            meeting_action_items = get_bedrock_text_only_response( meeting_action_items, model_id=model_id)
            
        else:
            meeting_action_items = generate_meeting_action_item_v2( transcript, 
                                                                max_tokens, 
                                                                temp, 
                                                                topK, 
                                                                stop_sequences, 
                                                                model_id, 
                                                                text_only=True )
            if latency:
                end_time = time.time()
                action_time = end_time - start_time 

        meeting_action_out_dict = output_dict_formatter( meeting_action_items, 
                                                        temp, 
                                                        model_id, 
                                                        prompt_ver )

        if latency:
            meeting_action_out_dict[ 'latency' ] = action_time
        
        if cost:
            meeting_action_out_dict[ 'cost' ] = meeting_action_cost
        
        meeting_action_list.append( meeting_action_out_dict )

        ##################################
        #      Participants actions      #
        ##################################
        if latency:
            start_time = time.time()

        if cost:
            part_action_items = generate_person_action_item_v2( transcript, 
                                                            max_tokens, 
                                                            temp, 
                                                            topK, 
                                                            stop_sequences, 
                                                            model_id, 
                                                            text_only=False ) 
            if latency:
                end_time = time.time()
                part_action_time = end_time - start_time 

            part_action_cost = get_bedrock_ondemand_cost( transcript, part_action_items, model_id=model_id )
            part_action_items = get_bedrock_text_only_response( part_action_items, model_id=model_id)
            
        else:
            part_action_items = generate_person_action_item_v2( transcript, 
                                                            max_tokens, 
                                                            temp, 
                                                            topK, 
                                                            stop_sequences, 
                                                            model_id, 
                                                            text_only=True ) 
            if latency:
                end_time = time.time()
                part_action_time = end_time - start_time             
        
        part_action_out_dict = output_dict_formatter( part_action_items, 
                                                     temp, 
                                                     model_id, 
                                                     prompt_ver )

        if latency:
            part_action_out_dict[ 'latency' ] = part_action_time

        if cost:
            part_action_out_dict[ 'cost' ] = part_action_cost

        participant_action_list.append( part_action_out_dict )
    
    # Output data formatting
    output_data = input_data
    
    output_data[ 'meeting_summary' ] = summary_list
    output_data[ 'meeting_level_action_items' ] = meeting_action_list
    output_data[ 'participant_action_items' ] = participant_action_list
    
    if save:
        with open(output_file_path, "w", encoding='utf-8') as outfile: 
            json.dump(output_data, outfile)
    
    return output_data
    
    
def output_dict_formatter( response: str, temp:float, model_id:str, prompt_ver:str ):
    '''
    Simple function to format the output dict
    '''
    
    output_dict = { 'metadata': { 'model_name': model_id,
                                 'prompt': prompt_ver,
                                 'temperature': temp,
                                },
                   'source': model_id,
                   'text': response
                  }
    
    return output_dict

def input_to_trans_list( input_data: dict ):
    '''
    Simple helper function that returns the list of transcripts from input JSON dict
    '''
    transcript_list = []
    for chap in input_data['chapters']:
        '''
        preprocess data before combining 
        '''
        preprocessed_transcript = clean_data(chap[ 'transcript_text' ].lower())
        transcript_list.append(preprocessed_transcript )
        
    return transcript_list

def input_to_merged_trans( input_data: dict ):
    '''
    Simple helper function that returns the merged transcript from input JSON dict
    '''
    transcript_list = input_to_trans_list( input_data )
    transcript = "\n\n".join( transcript_list )

    return transcript




