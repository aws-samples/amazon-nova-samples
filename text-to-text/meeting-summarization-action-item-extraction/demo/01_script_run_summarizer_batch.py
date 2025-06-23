# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import sys
sys.path.append( '..' )

from llm_core.llm_summarizer import run_summarizer
from llm_core.bedrock_helper import NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID

import time 

input_folder_path = "../data/test/"
output_folder_path = "../results/final_json_06022025/"

model_ids = [NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID]
model_family = "FINAL"

temp=0.5

for i in range( 1, 31 ): #number of transcripts to evaluate is 31
    file_name = f"test_{i}.json" 
    out_file_name = f"test_{i}_{model_family}.json"
    input_path = input_folder_path + file_name
    output_path = output_folder_path + out_file_name

    print( file_name )
    
    output = run_summarizer( input_path, 
                            model_ids=model_ids, 
                            topK=250,
                            temp=temp,
                            stop_sequences=["Human:", "</summary>", "</action_items>"],
                            save=True, 
                            output_file_path=output_path, 
                            latency=True, 
                            cost=True)
    
    ######################################
    #      Throttling Error Handling     #
    ######################################
    '''
    try:
         output = run_summarizer( input_path, 
                                 model_ids=model_ids, 
                                 topK=250,
                                 temp=temp,
                                 stop_sequences=["Human:", "</summary>", "</action_items>"],
                                 save=True, 
                                 output_file_path=output_path, 
                                 latency=True, 
                                 cost=True)
    except Exception as e:
         time.sleep(60)
         print( "Waiting 1 min")        
         print( e ) 
         output = run_summarizer( input_path, 
                                 model_ids=model_ids, 
                                 topK=250,
                                 temp=temp,
                                 stop_sequences=["Human:", "</summary>", "</action_items>"],
                                 save=True, 
                                 output_file_path=output_path, 
                                 latency=True, 
                                 cost=True)
        
    '''