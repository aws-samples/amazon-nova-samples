# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import sys
sys.path.append( '..' )

from llm_core.bedrock_helper import  NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID

from llm_core.llm_summarizer import input_to_merged_trans

import pandas as pd
import json


exp_name = 'final_json_06022025'
input_folder_path = "../data/test/"
output_folder_path = f"../results/{exp_name}/"

model_family_list = [ 'FINAL' ]

model_ids = [NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID]

print( model_ids )

# df_cols = [ 'transcript' ] + model_ids
df_cols = model_ids

print( df_cols )

summary_df = pd.DataFrame( columns= df_cols )
action_df = pd.DataFrame( columns= df_cols ) 
part_action_df = pd.DataFrame( columns= df_cols ) 

for i in range( 1, 31 ):
    row_dict_summary = {}
    row_dict_action = {}
    row_dict_part_action = {}

    # Get transcript
    trans_file_path = output_folder_path + f"test_{i}_FINAL.json"

    with open( trans_file_path, 'r', encoding='utf-8' ) as f:
        trans_data = json.load( f )
    
    transcript = input_to_merged_trans( trans_data )

    row_dict_summary[ 'transcript' ] = transcript
    row_dict_action[ 'transcript' ] = transcript
    row_dict_part_action[ 'transcript' ] = transcript

    for model_family in model_family_list:
        result_file_path = output_folder_path + f"test_{i}_{model_family}.json"

        with open( result_file_path, 'r', encoding='utf-8' ) as f:
            input_data = json.load( f )

        len_gen = len(input_data[ 'participant_action_items' ])

        for j in range( len_gen ):
            summary_j = input_data[ 'meeting_summary' ][ j ]
            model_name_j = summary_j[ 'source' ]
            summary_j_text = summary_j[ 'text' ]
            summary_j_text = summary_j_text.replace( "<summary>", "" )
            summary_j_text = summary_j_text.split("</summary>")[0] 
            row_dict_summary[ model_name_j ] = summary_j_text

            action_j = input_data[ 'meeting_level_action_items' ][j]
            model_action_j = action_j[ 'source' ]
            action_j_text = action_j[ 'text' ]
            action_j_text = action_j_text.replace( "<action_items>", "" )
            action_j_text = action_j_text.split("</action_items>")[0] 
            row_dict_action[ model_action_j ] = action_j_text

            part_action_j = input_data[ 'participant_action_items' ][j]
            model_part_action_j = part_action_j[ 'source' ]
            part_action_j_text = part_action_j[ 'text' ]
            part_action_j_text = part_action_j_text.replace( "<action_items>", "" )
            part_action_j_text = part_action_j_text.split("</action_items>")[0] 

            row_dict_part_action[ model_part_action_j ] = part_action_j_text

    summary_row = pd.DataFrame([row_dict_summary])
    summary_df = pd.concat( [ summary_df, summary_row ], ignore_index=True)

    action_row = pd.DataFrame([row_dict_action])
    action_df = pd.concat( [ action_df, action_row ], ignore_index=True)

    part_action_row = pd.DataFrame([row_dict_part_action])
    part_action_df = pd.concat( [ part_action_df, part_action_row ], ignore_index=True)

summary_df.to_csv( f'../results/{exp_name}_meeting_summary.csv' )
action_df.to_csv( f'../results/{exp_name}_meeting_level_action_items.csv' )
part_action_df.to_csv( f'../results/{exp_name}_participant_action_items.csv' )

# print( summary_df )