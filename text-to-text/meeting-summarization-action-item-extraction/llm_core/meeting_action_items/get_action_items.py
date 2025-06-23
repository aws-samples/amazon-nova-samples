# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pandas as pd

from llm_core.bedrock_helper import NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID
from llm_core.bedrock_helper import get_bedrock_response
import time

def get_meeting_topic_lst(meeting_transcripts, meeting_id):
    """This function takes a meeting transcript and returns the list of topics"""
    topic_lst = []
    meeting_segs = meeting_transcripts.loc[meeting_id, 'topic_list']
    for seg in range(len(meeting_segs)):
        topic_lst.append(meeting_segs[seg]['topic'])
    
    return topic_lst


def get_meeting_word_cnt(meeting_transcripts, meeting_id):
    """This function takes a meeting transcript and returns the word count"""
    word_cnt = 0
    
    meeting_segs = meeting_transcripts.loc[meeting_id, 'meeting_transcripts']
    for seg in meeting_segs:
        for value in seg.values():
            if isinstance(value, str):
                word_cnt += len(value.split())
    
    return word_cnt


def format_prompt(oai_action_item_prompt, meeting_topic_lst, meeting_trans):
    """This function populates meeting topic and transcript into the prompt template"""
    oai_prompt = oai_action_item_prompt.format(MEETING_SUB_TOPIC = meeting_topic_lst, 
                                        TOPIC_TRANSCRIPT = meeting_trans)

    return oai_prompt


def get_meeting_action_item(prompt, model_id):
    """This function pass the prompt and model_id and get bedrock response for meeting-level action items """
    
    start_time = time.time()
    response = get_bedrock_response(
            user_message = prompt, 
            max_tokens = 2048, 
            model_id = model_id,
            temp = 0,
            topK = 50)
    end_time = time.time()
    
    latency = end_time - start_time 
    #print('Latency for {}: {} seconds'.format(model_id, latency))
        
    return response, latency


def compile_model_results(meeting_transcripts, prompt, model_id, test_size, output_folder):
    """This function compiles meeting-level action item extraction results from a specific model into a single csv file """
    
    model_res = pd.DataFrame(columns=['original_transcript', 'topic_lst', 'meeting_word_cnt', 'latency', 'action_items'])
    
    for meeting_id in range(test_size):  
        word_cnt = get_meeting_word_cnt(meeting_transcripts, meeting_id)
        meeting_trans = meeting_transcripts.loc[meeting_id, 'meeting_transcripts']
        topic_lst = get_meeting_topic_lst(meeting_transcripts, meeting_id)
        custom_prompt = format_prompt(prompt, topic_lst, meeting_trans)
        response, latency = get_meeting_action_item(custom_prompt, model_id)

        record = [meeting_trans, topic_lst, word_cnt, latency, response]
        model_res.loc[len(model_res)] = record

    model_res.to_csv(f'{output_folder}{model_id}_res.csv', index = False) 



oai_action_item_prompt = """
Here is a complete meeting transcript on the following topics {MEETING_SUB_TOPIC}:
"{TOPIC_TRANSCRIPT}"

If there are any important action items assigned for follow-up after the {MEETING_SUB_TOPIC},
Write them in one bulleted list; if there are no action items, write the token "[no_actions]".
"""


if __name__ == "__main__":
    # Currently reading meeting transcripts from train.jsonl as it contains entire meeting transcripts, can be adapted to read chapter-segmented transcripts
    input_file_path = 'QMSumdata/ALL/jsonl/train.jsonl' 
    output_folder = "action_items_res/sampled_test30/"
    
    meeting_transcripts_train = pd.read_json(path_or_buf=input_file_path, lines=True)
    test_size = 30

    model_lst = [NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID] 
   
    
    for model in model_lst:
        print(f'Model currently running inference: {model}')
        compile_model_results(meeting_transcripts_train, oai_action_item_prompt, model, test_size, output_folder)